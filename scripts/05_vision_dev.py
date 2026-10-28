import os, re, json, sys
import numpy as np
import pandas as pd
from retake.common import DATA, episode_video, contact_sheet, load_info, load_frames
from retake.signals import gripper_indices, gripper_events
from retake.vision import audit_episode, PROMPT_V2, PROMPT_V3, EPISODE_FRACS

VER = sys.argv[1] if len(sys.argv) > 1 else "v3"
REPO, CAM = "kantine/BotFails", "observation.images.logitech_1"
path = DATA / REPO.replace("/", "__")

dev = pd.read_csv("evidence/splits/botfails_dev.csv")
sig = pd.read_csv("results/signals_BotFails.csv")[["dataset", "episode_index", "duration_s"]]
dev = dev.merge(sig, on=["dataset", "episode_index"])
key = lambda d: d.dataset + ":" + d.episode_index.astype(str)
dev["key"] = key(dev)

seen = pd.read_csv("results/vision_check_BotFails.csv")
old = dev[dev.key.isin(set(key(seen)))]
fresh_pool = dev[~dev.key.isin(set(old.key))]
fresh = pd.concat([fresh_pool[fresh_pool.fail == 1].sample(10, random_state=1),
                   fresh_pool[fresh_pool.fail == 0].sample(10, random_state=1)])
sample = pd.concat([old.assign(subset="E006-20"), fresh.assign(subset="new-20")])

def task_text(dataset_rel):
    expert = dataset_rel.split("/")[-1].replace("_anomaly", "_expert")
    p = path / "BotFails" / "normal_train" / expert / "meta" / "tasks.jsonl"
    return json.loads(p.read_text().splitlines()[0])["task"]

def reference_for(task_name, exclude_key):
    pool = dev[(dev.dataset == f"BotFails/normal_train/{task_name}_expert") & (dev.key != exclude_key)]
    return pool.sort_values("episode_index").iloc[0]

_cache = {}
def episode_df(dataset_rel, ep):
    if dataset_rel not in _cache:
        root = path / dataset_rel
        _cache[dataset_rel] = (load_info(root), load_frames(root))
    info, df = _cache[dataset_rel]
    return info, df[df.episode_index == ep]

def keyframe_times(duration, events, n_mid=4):
    """First frame, up to 4 frames just after grasp/release events, last frame.
    Falls back to evenly spaced frames when there are too few events."""
    mids = [t for t in events if 0.05 * duration < t < 0.95 * duration]
    if len(mids) > n_mid:
        idx = np.linspace(0, len(mids) - 1, n_mid).round().astype(int)
        mids = [mids[i] for i in idx]
    fill = [duration * f for f in (0.2, 0.4, 0.6, 0.8)]
    while len(mids) < n_mid:
        c = max(fill, key=lambda x: min([abs(x - m) for m in mids] or [1e9]))
        mids.append(c); fill.remove(c)
    return [0.02 * duration] + sorted(mids) + [0.98 * duration]

os.makedirs(f"results/frames_{VER}", exist_ok=True)
rows = []
for _, r in sample.iterrows():
    ep, name = int(r.episode_index), r.dataset.split("/")[-1]
    task_name = name.replace("_anomaly", "").replace("_expert", "")
    task = task_text(r.dataset)
    if re.search(r"\d+\s*[:\-]\s*\d+|anomal|normal test|wrong", task, re.I):
        raise SystemExit(f"LEAK GUARD: {task!r}")

    ref = reference_for(task_name, r.key)
    video = episode_video(REPO, path, r.dataset, ep, CAM)
    ref_video = episode_video(REPO, path, ref.dataset, int(ref.episode_index), CAM)

    if VER == "v2":
        prompt, times = PROMPT_V2, [r.duration_s * f for f in EPISODE_FRACS]
    else:
        info, epdf = episode_df(r.dataset, ep)
        events = gripper_events(epdf, info["fps"], gripper_indices(info))
        prompt, times = PROMPT_V3, keyframe_times(r.duration_s, [t + 0.5 for t in events])

    v = audit_episode(video, r.duration_s, task, ref_video, ref.duration_s,
                      tag=f"{VER}:{name}:{ep}", prompt=prompt, times=times)
    if v.get("_frames"):
        contact_sheet(v.pop("_frames"), cols=3).save(f"results/frames_{VER}/{name}_ep{ep}.jpg")
    v.update(dataset=r.dataset, task=task_name, episode_index=ep, fail=int(r.fail), subset=r.subset)
    rows.append(v)
    print(f"[{'FAIL' if r.fail else 'GOOD'}][{r.subset}] {name} ep{ep}: anomaly={v.get('anomaly')} "
          f"sev={v.get('severity')} type={v.get('failure_type')} | {v.get('reason')}")

res = pd.DataFrame(rows)
res.to_csv(f"results/vision_{VER}_dev.csv", index=False)
if "anomaly" not in res:
    raise SystemExit("No model answers (dry run?) - skipping metrics.")
res["pred"] = res.anomaly.astype(str).str.lower().eq("true")

def report(d, name, col="pred"):
    tp = (d[col] & (d.fail == 1)).sum(); fp = (d[col] & (d.fail == 0)).sum()
    acc = (d[col] == (d.fail == 1)).mean()
    print(f"  {name:22s} acc {acc:4.0%} | caught {tp}/{(d.fail == 1).sum()} | false alarms {fp}/{(d.fail == 0).sum()}")

print(f"\nVision {VER}, DEV only:")
for s in ["E006-20", "new-20"]: report(res[res.subset == s], s)
report(res, "ALL-40")
if "severity" in res:
    res["pred_major"] = res.pred & res.severity.astype(str).str.lower().isin(["major", "critical"])
    report(res, "ALL-40 (major+ only)", "pred_major")
print("  (v2 on ALL-40: 72% | caught 13/20 | false alarms 4/20)")

print("\nBy task:")
for t, d in res.groupby("task"):
    print(f"  {t:32s} acc {(d.pred == (d.fail == 1)).mean():4.0%}  (n={len(d)})")