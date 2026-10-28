"""Retake: audit a LeRobot dataset for bad demonstrations.

Usage:
  uv run python -m retake.audit kantine/BotFails --limit 40 --exclude evidence/splits/botfails_TEST_frozen.csv
"""
import os, re, json, time, argparse, datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from retake.common import DATA, fetch, find_roots, load_info, load_frames, episode_video, contact_sheet
from retake.signals import episode_signals, gripper_indices
from retake.vision import audit_episode, VISION_MODEL
from retake.llm import chat, spent

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b")
LEAK = re.compile(r"\d+\s*[:\-]\s*\d+|anomal|normal test|wrong", re.I)
FEATS = ["duration_s", "idle_ratio", "longest_idle_s", "grip_closes", "jerk", "track_err"]
MOTION_RULES = [
    ("duration_s_z",     "<", -2.0, "much shorter than other demos of this task - possibly incomplete or cut off"),
    ("duration_s_z",     ">",  2.5, "much longer than typical - possible struggling or retries"),
    ("longest_idle_s_z", ">",  2.5, "unusually long pause - operator hesitation"),
    ("grip_closes_z",    ">",  2.5, "unusually many grasps - repeated regrasping"),
    ("jerk_z",           ">",  3.0, "unusually jerky motion"),
    ("track_err_z",      ">",  3.0, "commanded and actual motion diverge - possible collision or blocked arm"),
]

SUMMARY_PROMPT = """You write the executive summary of an automated quality audit of a robot-demonstration training dataset.
Audience: the robotics team that collected the data and will train on it. Be concrete and brief.

AUDIT STATS (JSON):
{stats}

FLAGGED EPISODES (JSON). status "retake" = the vision check found a problem; "review" = only motion statistics look unusual:
{findings}

Write Markdown with exactly these sections:
## Verdict
One sentence including the health score.
## What we found
Counts by issue type, each with 1-2 concrete example episodes (task + episode number + what happened, taken from the reasons above).
## Hotspots
Which tasks have the most problems, and any pattern suggesting a systematic collection issue.
## Recommended actions
Which episodes to re-record, which to drop before training, and what to change in the collection process.
## Caveats
This is an automated audit; the vision layer scored 72% accuracy on a labeled benchmark, so review flagged episodes before deleting data.

Use ONLY numbers and episodes from the data above. Do not invent anything."""


def norm_name(name):
    return re.sub(r"_(anomaly|expert)$", "", name)

def read_tasks(root):
    p, out = root / "meta" / "tasks.jsonl", {}
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                d = json.loads(line); out[int(d["task_index"])] = d["task"]
    return out

def motion_table(path):
    rows, roots = [], {}
    for root in find_roots(path):
        if not list((root / "data").rglob("*.parquet")):
            continue
        info, df = load_info(root), load_frames(root)
        gidx, rel = gripper_indices(info), str(root.relative_to(path))
        roots[rel] = (root, info, read_tasks(root))
        for ep_idx, ep in df.groupby("episode_index"):
            r = episode_signals(ep, info["fps"], gidx)
            ti = int(ep["task_index"].iloc[0]) if "task_index" in ep else 0
            r.update(dataset=rel, episode_index=int(ep_idx), task_index=ti,
                     task_key=f"{norm_name(root.name)}::{ti}")
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
    ti, cands = int(task_key.split("::")[1]), []
    for rel in m[m.task_key == task_key].dataset.unique():
        tasks = roots[rel][2]
        if ti in tasks:
            cands.append((0 if rel.endswith("_expert") else 1, tasks[ti]))
    for _, t in sorted(cands):
        if not LEAK.search(t):
            return t
    return task_key.split("::")[0].replace("_", " ")

def pick_reference(task_key, m, exclude, self_key):
    g = m[(m.task_key == task_key) & ~m.key.isin(exclude) & (m.key != self_key)]
    if g.empty:
        return None
    g = g.assign(pref=(~g.dataset.str.endswith("_expert")).astype(int))
    return g.sort_values(["pref", "motion_score"]).iloc[0]

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


def main():
    ap = argparse.ArgumentParser(description="Retake: audit a LeRobot dataset for bad demonstrations")
    ap.add_argument("repo")
    ap.add_argument("--limit", type=int, default=0, help="max episodes to audit (0 = all)")
    ap.add_argument("--exclude", default=None, help="CSV of dataset,episode_index to skip (e.g. a frozen test split)")
    ap.add_argument("--cam", default=None, help="camera key (default: first video feature)")
    ap.add_argument("--vision", choices=["all", "flagged", "none"], default="all")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    path = DATA / a.repo.replace("/", "__")
    if not list(path.rglob("*.parquet")):
        print("Fetching metadata + motion data (no videos)...")
        fetch(a.repo, ["*.md", "meta/**", "**/meta/**", "data/**", "**/data/**"])
    start_spend, t0 = spent(), time.time()

    print("[1/4] Motion layer...")
    m, roots = motion_table(path)
    exclude = set()
    if a.exclude:
        e = pd.read_csv(a.exclude)
        exclude = set(e.dataset + ":" + e.episode_index.astype(str))
    sel = select(m, a.limit, exclude)
    print(f"      {len(m)} episodes in dataset | auditing {len(sel)} across {sel.task_key.nunique()} tasks "
          f"| {sum(len(f) > 0 for f in sel.motion_flags)} motion-flagged")

    info0 = next(iter(roots.values()))[1]
    cams = [k for k, v in info0["features"].items() if v.get("dtype") == "video"]
    cam = a.cam or (cams[0] if cams else None)
    v3_layout = "episode_index" not in info0.get("video_path", "")
    do_vision = a.vision != "none" and cam is not None and not v3_layout
    if v3_layout:
        print("      NOTE: LeRobot v3 video layout not supported yet -> motion-only audit")
    tasks = {k: task_text_for(k, m, roots) for k in sel.task_key.unique()}

    def job(r):
        try:
            if a.vision == "flagged" and not r.motion_flags:
                return r.key, {}
            ref = pick_reference(r.task_key, m, exclude, r.key)
            if ref is None:
                return r.key, {}
            video = episode_video(a.repo, path, r.dataset, int(r.episode_index), cam)
            ref_video = episode_video(a.repo, path, ref.dataset, int(ref.episode_index), cam)
            v = audit_episode(video, r.duration_s, tasks[r.task_key], ref_video, ref.duration_s,
                              tag=f"audit:{r.dataset}:{r.episode_index}")
            return r.key, {"vision": v, "ref": ref.key}
        except Exception as ex:
            return r.key, {"error": str(ex)[:200]}

    results = {}
    if do_vision:
        print(f"[2/4] Vision layer ({VISION_MODEL}, {a.workers} parallel)...")
        with ThreadPoolExecutor(a.workers) as ex:
            futs = [ex.submit(job, r) for _, r in sel.iterrows()]
            for i, f in enumerate(as_completed(futs), 1):
                k, out = f.result(); results[k] = out
                print(f"      {i}/{len(futs)} episodes checked", end="\r")
        print()

    print("[3/4] Verdicts...")
    out_dir = Path(a.out or f"reports/{a.repo.replace('/', '__')}")
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)
    recs = []
    for _, r in sel.iterrows():
        res = results.get(r.key, {})
        v = res.get("vision") or {}
        frames = v.pop("_frames", None)
        anomaly = str(v.get("anomaly")).lower() == "true"
        status = ("retake" if anomaly else
                  "review" if (r.motion_flags or "raw" in v or "error" in res) else "clean")
        rec = dict(dataset=r.dataset, episode_index=int(r.episode_index), task_key=r.task_key,
                   task=tasks[r.task_key], status=status, duration_s=round(r.duration_s, 1),
                   motion_score=round(r.motion_score, 2), motion_flags=r.motion_flags,
                   failure_type=v.get("failure_type"), reason=v.get("reason"),
                   evidence_time_s=v.get("evidence_time_s"), confidence=v.get("confidence"),
                   human_in_workspace=v.get("human_in_workspace"), reference=res.get("ref"),
                   error=res.get("error"))
        if frames and status != "clean":
            stem = Path(r.dataset).name if r.dataset not in (".", "") else "ep"
            fn = f"{stem}_ep{int(r.episode_index)}.jpg"
            contact_sheet(frames, cols=3).save(out_dir / "frames" / fn)
            rec["frames"] = f"frames/{fn}"
        recs.append(rec)
    ep = pd.DataFrame(recs)

    n = len(ep)
    counts = ep.status.value_counts().to_dict()
    by_task = {t: {"audited": len(d), "retake": int((d.status == "retake").sum()),
                   "review": int((d.status == "review").sum())} for t, d in ep.groupby("task_key")}
    stats = {
        "dataset": a.repo, "audited_episodes": n, "episodes_in_dataset": len(m),
        "tasks": int(ep.task_key.nunique()),
        "clean": counts.get("clean", 0), "review": counts.get("review", 0), "retake": counts.get("retake", 0),
        "health_score_pct": round(100 * counts.get("clean", 0) / n, 1) if n else 0,
        "issue_types": ep[ep.status == "retake"].failure_type.value_counts().to_dict(),
        "by_task": by_task,
    }

    print(f"[4/4] Summary ({JUDGE_MODEL})...")
    findings = ep[ep.status != "clean"].head(40)[
        ["task_key", "dataset", "episode_index", "status", "failure_type", "reason", "motion_flags", "evidence_time_s"]]
    summary = chat(JUDGE_MODEL, [{"role": "user", "content": SUMMARY_PROMPT.format(
        stats=json.dumps(stats, indent=1), findings=findings.to_json(orient="records"))}],
        max_tokens=1500, think=False, tag="audit:summary")

    cost = spent() - start_spend
    stats.update(model_cost_usd=round(cost, 4),
                 cost_per_1000_episodes_usd=round(1000 * cost / n, 2) if n else None,
                 runtime_s=round(time.time() - t0),
                 models={"vision": VISION_MODEL, "summary": JUDGE_MODEL},
                 generated_at=datetime.datetime.now().isoformat(timespec="seconds"))

    ep.assign(motion_flags=ep.motion_flags.apply("; ".join)).to_csv(out_dir / "episodes.csv", index=False)
    (out_dir / "report.json").write_text(json.dumps({"stats": stats, "episodes": recs}, indent=1, default=str))
    (out_dir / "summary.md").write_text(f"# Retake audit: {a.repo}\n\n" + (summary or "_summary not generated (dry run?)_"))
    for s, fname in [("retake", "retake_list.txt"), ("review", "review_list.txt"), ("clean", "clean_episodes.txt")]:
        (out_dir / fname).write_text("\n".join(ep[ep.status == s].apply(
            lambda x: f"{x.dataset}\t{x.episode_index}", axis=1)) + "\n")

    print(f"\n=== Retake audit: {a.repo} ===")
    print(f"Health score: {stats['health_score_pct']}%  |  clean {stats['clean']}  review {stats['review']}  retake {stats['retake']}")
    print(f"Issue types: {stats['issue_types']}")
    print(f"Model cost: ${cost:.4f}  (${stats['cost_per_1000_episodes_usd']} per 1,000 episodes)  |  {stats['runtime_s']}s")
    print(f"Report: {out_dir}/summary.md")

if __name__ == "__main__":
    main()