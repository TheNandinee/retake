import os, re, json, sys
import pandas as pd
from retake.common import DATA, episode_video, contact_sheet
from retake.vision import audit_episode

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
    """A known-good expert demo of the same task, from DEV only, never the episode itself."""
    pool = dev[(dev.dataset == f"BotFails/normal_train/{task_name}_expert") & (dev.key != exclude_key)]
    return pool.sort_values("episode_index").iloc[0]

os.makedirs("results/frames_v2", exist_ok=True)
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

    v = audit_episode(video, r.duration_s, task, ref_video, ref.duration_s, tag=f"v2:{name}:{ep}")
    if v.get("_frames"):
        contact_sheet(v.pop("_frames"), cols=3).save(f"results/frames_v2/{name}_ep{ep}.jpg")
    v.update(dataset=r.dataset, episode_index=ep, fail=int(r.fail), subset=r.subset)
    rows.append(v)
    print(f"[{'FAIL' if r.fail else 'GOOD'}][{r.subset}] {name} ep{ep}: anomaly={v.get('anomaly')} "
          f"type={v.get('failure_type')} human={v.get('human_in_workspace')} | {v.get('reason')}")

res = pd.DataFrame(rows)
res.to_csv("results/vision_v2_dev.csv", index=False)
res["pred"] = res.anomaly.astype(str).str.lower().eq("true")

def report(d, name):
    tp = (d.pred & (d.fail == 1)).sum(); fp = (d.pred & (d.fail == 0)).sum()
    acc = (d.pred == (d.fail == 1)).mean()
    print(f"  {name:10s} acc {acc:4.0%} | caught {tp}/{(d.fail == 1).sum()} | false alarms {fp}/{(d.fail == 0).sum()}")

print("\nVision v2 (reference-conditioned), DEV only:")
for s in ["E006-20", "new-20"]: report(res[res.subset == s], s)
report(res, "ALL-40")
print("  (E006 baseline on the same 20: 60% | caught 6/10 | false alarms 4/10)")