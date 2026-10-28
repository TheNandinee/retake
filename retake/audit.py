"""Retake: audit a LeRobot dataset for bad demonstrations.

Usage:
  uv run python -m retake.audit kantine/BotFails --limit 40 --exclude evidence/splits/botfails_TEST_frozen.csv
  uv run python -m retake.audit lerobot/community_dataset_v3 --subset 00ri/so100_battery --limit 10 --out reports/community_test
"""
import os, re, json, time, argparse, datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from retake.common import (DATA, fetch, fetch_subset, find_roots, load_info, load_frames,
                           episode_video_seg, contact_sheet)
from retake.signals import episode_signals, gripper_indices
from retake.vision import audit_episode, VISION_MODEL
from retake.llm import chat, spent, STATS

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b")
LEAK = re.compile(r"\d+\s*[:\-]\s*\d+|anomal|normal test|wrong", re.I)
PAIRED = re.compile(r"_(anomaly|expert)$")

# Failure types backed by something visible in the frames -> eligible for the RETAKE list.
VISIBLE = {"spill", "dropped_object", "human_intervention", "wrong_object",
           "wrong_placement", "collision", "wrong_target"}
SYSTEMATIC_MIN = 3

FEATS = ["duration_s", "idle_ratio", "longest_idle_s", "grip_closes", "jerk", "track_err"]
MOTION_RULES = [
    ("duration_s_z",     "<", -2.0, "much shorter than other demos of this task - possibly incomplete or cut off"),
    ("duration_s_z",     ">",  2.5, "much longer than typical - possible struggling or retries"),
    ("longest_idle_s_z", ">",  2.5, "unusually long pause - operator hesitation"),
    ("grip_closes_z",    ">",  2.5, "unusually many grasps - repeated regrasping"),
    ("jerk_z",           ">",  3.0, "unusually jerky motion"),
    ("track_err_z",      ">",  3.0, "commanded and actual motion diverge - possible collision or blocked arm"),
]

SUMMARY_PROMPT = """You write part of the summary of an automated quality audit of a robot-demonstration training dataset.
Audience: the robotics team that collected the data. Be concrete, brief, and careful: a wrong recommendation could make them throw away good data.

AUDIT STATS (JSON):
{stats}

FLAGGED EPISODES (JSON). status "retake" = visible evidence of a problem in the frames; "review" = unconfirmed, needs a human look.
Each episode has an "id" - refer to episodes ONLY by that exact id.
{findings}

Write Markdown with exactly these four sections, under 400 words in total:
## Verdict
One sentence with the health score and the counts. Episodes are "flagged", never "required" to do anything.
## Caveats
Two sentences: this is an automated audit; on a labeled benchmark the vision layer agreed with human labels about 72% of the time, so a human should check the flagged frames before any episode is removed or re-recorded.
## What we found
First the retake flags grouped by issue type, at most 2 example ids each with what happened. Then the review flags grouped by issue type, at most 2 example ids each. Review flags are unconfirmed: describe them as "possible", never as facts.
## Recommended actions
Which episode ids a human should check first and why. Retake episodes first, then review episodes.

Rules:
- Do NOT write a Hotspots section; it is generated separately from the data.
- Never use these words: systematic, procedural, protocol, delete, require.
- Do not draw conclusions about how the data was collected.
- Use only numbers and ids that appear in the data above."""

BANNED = re.compile(r"systematic|procedural|protocol|delet|requir", re.I)


def norm_name(name):
    return PAIRED.sub("", name)

def group_name(rel, root):
    """Paired expert/anomaly folders (BotFails style) share a task group; otherwise use the full path,
    because different contributors can use the same dataset name."""
    return norm_name(root.name) if PAIRED.search(root.name) else rel

def read_tasks(root):
    out = {}
    pj, pq = root / "meta" / "tasks.jsonl", root / "meta" / "tasks.parquet"
    if pj.exists():
        for line in pj.read_text().splitlines():
            if line.strip():
                d = json.loads(line); out[int(d["task_index"])] = d["task"]
    elif pq.exists():
        t = pd.read_parquet(pq).reset_index()
        tcol = next((c for c in t.columns if c != "task_index" and t[c].dtype == object), None)
        if tcol and "task_index" in t:
            out = {int(i): str(s) for i, s in zip(t["task_index"], t[tcol])}
    return out

def episode_id(dataset, ep_idx):
    if dataset in (".", ""):
        name = "episode"
    elif PAIRED.search(Path(dataset).name):
        name = Path(dataset).name
    else:
        name = dataset
    return f"{name} ep{int(ep_idx)}"

def safe_filename(s):
    return re.sub(r"[^\w.-]+", "_", s)

def motion_table(path, only=None):
    rows, roots = [], {}
    for root in find_roots(path):
        rel = str(root.relative_to(path))
        if only and rel not in only:
            continue
        if not list((root / "data").rglob("*.parquet")):
            continue
        info, df = load_info(root), load_frames(root)
        gidx = gripper_indices(info)
        roots[rel] = (root, info, read_tasks(root))
        grp = group_name(rel, root)
        for ep_idx, ep in df.groupby("episode_index"):
            r = episode_signals(ep, info["fps"], gidx)
            ti = int(ep["task_index"].iloc[0]) if "task_index" in ep else 0
            r.update(dataset=rel, episode_index=int(ep_idx), task_index=ti, task_key=f"{grp}::{ti}")
            rows.append(r)
    m = pd.DataFrame(rows)
    for f in FEATS:
        g = m.groupby("task_key")[f]
        m[f + "_z"] = ((m[f] - g.transform("mean")) / (g.transform("std") + 1e-9)).fillna(0)
    m["group_n"] = m.groupby("task_key")["episode_index"].transform("size")
    m["motion_score"] = m[[f + "_z" for f in FEATS]].abs().max(axis=1)

    def flags(r):
        if r.group_n < 5:
            return []
        out = []
        for col, op, thr, msg in MOTION_RULES:
            v = r[col]
            if (op == "<" and v < thr) or (op == ">" and v > thr):
                out.append(f"{msg} ({v:+.1f} sd)")
        return out
    m["motion_flags"] = m.apply(flags, axis=1)
    m["key"] = m.dataset + ":" + m.episode_index.astype(str)
    return m, roots

def task_text_for(task_key, m, roots):
    ti, cands = int(task_key.split("::")[-1]), []
    for rel in m[m.task_key == task_key].dataset.unique():
        tasks = roots[rel][2]
        if ti in tasks:
            cands.append((0 if rel.endswith("_expert") else 1, tasks[ti]))
    for _, t in sorted(cands):
        if not LEAK.search(t):
            return t
    return task_key.split("::")[0].split("/")[-1].replace("_", " ")

def pick_reference(task_key, m, exclude, self_key, mode="first"):
    """mode='first': lowest-index demo (E008/E012 setting). mode='typical': most typical motion (E010)."""
    g = m[(m.task_key == task_key) & ~m.key.isin(exclude) & (m.key != self_key)]
    if g.empty:
        return None
    g = g.assign(pref=(~g.dataset.str.endswith("_expert")).astype(int))
    order = ["pref", "episode_index"] if mode == "first" else ["pref", "motion_score"]
    return g.sort_values(order).iloc[0]

def select(m, limit, exclude, seed=0):
    pool = m[~m.key.isin(exclude)]
    if not limit or limit >= len(pool):
        return pool
    groups = [g.sample(frac=1, random_state=seed) for _, g in pool.groupby("task_key")]
    picked, i = [], 0
    while len(picked) < limit:
        added = False
        for g in groups:
            if i < len(g) and len(picked) < limit:
                picked.append(g.iloc[i]); added = True
        if not added:
            break
        i += 1
    return pd.DataFrame(picked)

def compute_hotspots(ep):
    out = []
    for t, d in ep.groupby("task_key"):
        rt, rv = d[d.status == "retake"], d[d.status == "review"]
        if rt.empty and rv.empty:
            continue
        types = rt.failure_type.value_counts()
        sys_issue = types.index[0] if len(types) and types.iloc[0] >= SYSTEMATIC_MIN else None
        out.append({"task": t.split("::")[0], "audited": len(d), "retake": len(rt), "review": len(rv),
                    "retake_types": {k: int(v) for k, v in types.items()},
                    "possible_systematic_issue": sys_issue})
    return sorted(out, key=lambda h: (-h["retake"], -h["review"]))

def hotspots_md(hs):
    lines = ["## Hotspots"]
    for h in hs:
        s = f"- **{h['task']}**: {h['retake']} retake, {h['review']} review (of {h['audited']} audited)"
        if h["possible_systematic_issue"]:
            k = h["possible_systematic_issue"]
            s += f" - possible recurring issue: **{k}** in {h['retake_types'][k]} episodes"
        lines.append(s)
    if not any(h["possible_systematic_issue"] for h in hs):
        lines.append(f"- No clear recurring pattern: no task has {SYSTEMATIC_MIN}+ retake episodes with the same visible issue.")
    lines.append("- Review flags are unconfirmed and are not, on their own, evidence of a problem with the data.")
    return "\n".join(lines) + "\n\n"

def write_summary(stats, findings_json):
    msgs = [{"role": "user", "content": SUMMARY_PROMPT.format(stats=json.dumps(stats, indent=1),
                                                              findings=findings_json)}]
    text = chat(JUDGE_MODEL, msgs, max_tokens=3000, think=False, tag="audit:summary")
    if not text:
        return None, []
    bad = [l.strip() for l in text.splitlines() if BANNED.search(l)]
    if bad:
        msgs += [{"role": "assistant", "content": text},
                 {"role": "user", "content": "These lines break the rules (banned words or unsupported conclusions):\n"
                  + "\n".join(f"- {b}" for b in bad) + "\nRewrite the full summary without them, same four sections."}]
        text = chat(JUDGE_MODEL, msgs, max_tokens=3000, think=False, tag="audit:summary-retry") or text
        bad = [l.strip() for l in text.splitlines() if BANNED.search(l)]
        if bad:
            text = "\n".join(l for l in text.splitlines() if not BANNED.search(l))
    return text, bad


def main():
    ap = argparse.ArgumentParser(description="Retake: audit a LeRobot dataset for bad demonstrations")
    ap.add_argument("repo")
    ap.add_argument("--subset", default=None,
                    help="comma-separated sub-dataset paths inside the repo (e.g. 00ri/so100_battery)")
    ap.add_argument("--limit", type=int, default=0, help="max episodes to audit (0 = all)")
    ap.add_argument("--exclude", default=None, help="CSV of dataset,episode_index to skip (e.g. a frozen test split)")
    ap.add_argument("--cam", default=None, help="camera key (default: prefer top/front/side/high, else first)")
    ap.add_argument("--vision", choices=["all", "flagged", "none"], default="all")
    ap.add_argument("--reference", choices=["first", "typical"], default="first")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=None)
    ap.add_argument("--save-all-frames", action="store_true", help="save frame sheets for clean episodes too")
    ap.add_argument("--remote", action="store_true",
                    help="read video frames directly from Hugging Face instead of downloading files")
    a = ap.parse_args()

    path = DATA / a.repo.replace("/", "__")
    only = [s.strip().strip("/") for s in a.subset.split(",")] if a.subset else None
    if only:
        for s in only:
            print(f"Fetching metadata + motion data for {s} ...")
            fetch_subset(a.repo, s)
    elif not list(path.rglob("*.parquet")):
        print("Fetching metadata + motion data (no videos)...")
        fetch(a.repo, ["*.md", "meta/**", "**/meta/**", "data/**", "**/data/**"])
    start_spend, t0 = spent(), time.time()

    print("[1/4] Motion layer...")
    m, roots = motion_table(path, only)
    if m.empty:
        raise SystemExit("No episodes found - check --subset paths.")
    exclude = set()
    if a.exclude:
        e = pd.read_csv(a.exclude)
        exclude = set(e.dataset + ":" + e.episode_index.astype(str))
    sel = select(m, a.limit, exclude)
    print(f"      {len(m)} episodes | auditing {len(sel)} across {sel.task_key.nunique()} task groups "
          f"| {sum(len(f) > 0 for f in sel.motion_flags)} motion-flagged")

    def camera_for(info):
        cams = [k for k, v in info["features"].items() if v.get("dtype") == "video"]
        if a.cam and a.cam in cams:
            return a.cam
        for pref in ("top", "front", "high", "side"):     # third-person views show the scene best
            for c in cams:
                if pref in c.split(".")[-1]:
                    return c
        return cams[0] if cams else None
    cams = {rel: camera_for(info) for rel, (_, info, _) in roots.items()}
    tasks = {k: task_text_for(k, m, roots) for k in sel.task_key.unique()}

    def job(r):
        try:
            if a.vision == "flagged" and not r.motion_flags:
                return r.key, {}
            cam = cams.get(r.dataset)
            if cam is None:
                return r.key, {"error": "no video feature"}
            ref = pick_reference(r.task_key, m, exclude, r.key, a.reference)
            if ref is None:
                return r.key, {}
            video, off = episode_video_seg(a.repo, path, r.dataset, int(r.episode_index), cam, remote=a.remote)
            ref_video, ref_off = episode_video_seg(a.repo, path, ref.dataset, int(ref.episode_index),
                                                   cams.get(ref.dataset, cam), remote=a.remote)
            v = audit_episode(video, r.duration_s, tasks[r.task_key], ref_video, ref.duration_s,
                              tag=f"audit:{r.dataset}:{r.episode_index}",
                              video_offset=off, ref_offset=ref_off)
            return r.key, {"vision": v, "ref": ref.key}
        except Exception as ex:
            return r.key, {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}

    results = {}
    if a.vision != "none":
        print(f"[2/4] Vision layer ({VISION_MODEL}, {a.workers} parallel, reference={a.reference})...")
        with ThreadPoolExecutor(a.workers) as ex:
            futs = [ex.submit(job, r) for _, r in sel.iterrows()]
            for i, f in enumerate(as_completed(futs), 1):
                k, out = f.result(); results[k] = out
                print(f"      {i}/{len(futs)} episodes checked", end="\r")
        print()
        errs = [o["error"] for o in results.values() if "error" in o]
        if errs:
            print(f"      WARNING: {len(errs)} episodes failed in the vision layer. First error: {errs[0]}")

    print("[3/4] Verdicts...")
    out_dir = Path(a.out or f"reports/{a.repo.replace('/', '__')}")
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)
    for old in (out_dir / "frames").glob("*.jpg"):
        old.unlink()
    recs = []
    for _, r in sel.iterrows():
        res = results.get(r.key, {})
        v = res.get("vision") or {}
        frames = v.pop("_frames", None)
        anomaly = str(v.get("anomaly")).lower() == "true"
        ftype = str(v.get("failure_type") or "none")
        if anomaly and ftype in VISIBLE:
            status = "retake"
        elif anomaly or r.motion_flags or "raw" in v or "error" in res:
            status = "review"
        else:
            status = "clean"
        issue = ftype if anomaly else ("motion_only" if r.motion_flags else
                                       "vision_error" if ("raw" in v or "error" in res) else "none")
        rec = dict(id=episode_id(r.dataset, r.episode_index), dataset=r.dataset,
                   episode_index=int(r.episode_index), task_key=r.task_key, task=tasks[r.task_key],
                   camera=cams.get(r.dataset), status=status, vision_anomaly=anomaly, failure_type=issue,
                   duration_s=round(r.duration_s, 1), motion_score=round(r.motion_score, 2),
                   motion_flags=r.motion_flags, reason=v.get("reason"),
                   evidence_time_s=v.get("evidence_time_s"), confidence=v.get("confidence"),
                   human_in_workspace=v.get("human_in_workspace"), reference=res.get("ref"),
                   error=res.get("error"))
        if frames and (status != "clean" or a.save_all_frames):
            fn = safe_filename(rec["id"]) + ".jpg"
            contact_sheet(frames, cols=3).save(out_dir / "frames" / fn)
            rec["frames"] = f"frames/{fn}"
        recs.append(rec)
    ep = pd.DataFrame(recs)

    n = len(ep)
    counts = ep.status.value_counts().to_dict()
    hs = compute_hotspots(ep)
    stats = {
        "dataset": a.repo + (f" [{a.subset}]" if a.subset else ""),
        "audited_episodes": n, "episodes_in_scope": len(m),
        "task_groups": int(ep.task_key.nunique()),
        "clean": counts.get("clean", 0), "review": counts.get("review", 0), "retake": counts.get("retake", 0),
        "health_score_pct": round(100 * counts.get("clean", 0) / n, 1) if n else 0,
        "retake_issue_types": ep[ep.status == "retake"].failure_type.value_counts().to_dict(),
        "review_issue_types": ep[ep.status == "review"].failure_type.value_counts().to_dict(),
        "hotspots": hs,
    }

    print(f"[4/4] Summary ({JUDGE_MODEL})...")
    findings = ep[ep.status != "clean"].head(40)[
        ["id", "status", "failure_type", "reason", "motion_flags", "evidence_time_s"]]
    prose, leftover = write_summary(stats, findings.to_json(orient="records"))
    if prose:
        body = prose if "## Recommended actions" not in prose else \
            prose.replace("## Recommended actions", hotspots_md(hs) + "## Recommended actions", 1)
        if "## Hotspots" not in body:
            body += "\n\n" + hotspots_md(hs)
    else:
        body = "_summary not generated (dry run?)_\n\n" + hotspots_md(hs)

    cost = spent() - start_spend
    stats.update(model_cost_usd=round(cost, 4),
                 cost_per_1000_episodes_usd=(round(1000 * cost / n, 2) if n and STATS["cache_hits"] == 0 else None),
                 fresh_model_calls=STATS["fresh_calls"], cached_model_calls=STATS["cache_hits"],
                 runtime_s=round(time.time() - t0), reference_mode=a.reference,
                 summary_rule_violations_removed=len(leftover),
                 models={"vision": VISION_MODEL, "summary": JUDGE_MODEL},
                 generated_at=datetime.datetime.now().isoformat(timespec="seconds"))

    ep.assign(motion_flags=ep.motion_flags.apply("; ".join)).to_csv(out_dir / "episodes.csv", index=False)
    (out_dir / "report.json").write_text(json.dumps({"stats": stats, "episodes": recs}, indent=1, default=str))
    (out_dir / "summary.md").write_text(f"# Retake audit: {stats['dataset']}\n\n" + body)
    for s, fname in [("retake", "retake_list.txt"), ("review", "review_list.txt"), ("clean", "clean_episodes.txt")]:
        (out_dir / fname).write_text("\n".join(ep[ep.status == s].apply(
            lambda x: f"{x.dataset}\t{x.episode_index}", axis=1)) + "\n")

    print(f"\n=== Retake audit: {stats['dataset']} ===")
    print(f"Health score: {stats['health_score_pct']}%  |  clean {stats['clean']}  review {stats['review']}  retake {stats['retake']}")
    print(f"Retake issues: {stats['retake_issue_types']}")
    print(f"Review issues: {stats['review_issue_types']}")
    print(f"Summary rule violations left after retry: {len(leftover)}")
    if STATS["cache_hits"]:
        print(f"Model cost this run: ${cost:.4f}  ({STATS['cache_hits']} answers reused from cache, "
              f"so no per-1,000 figure; full-run cost measured in E012: $1.12 per 1,000 episodes)  |  {stats['runtime_s']}s")
    else:
        print(f"Model cost: ${cost:.4f}  (${stats['cost_per_1000_episodes_usd']} per 1,000 episodes)  |  {stats['runtime_s']}s")
    print(f"Report: {out_dir}/summary.md")

if __name__ == "__main__":
    main()