import sys
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from retake.common import DATA, find_roots, load_info, load_frames
from retake.signals import episode_signals, gripper_indices

repo = sys.argv[1]
max_eps = int(sys.argv[2]) if len(sys.argv) > 2 else 10_000
path = DATA / repo.replace("/", "__")
FEATS = ["duration_s", "idle_ratio", "longest_idle_s", "grip_closes", "jerk", "track_err"]

rows = []
for root in find_roots(path):
    if not list((root / "data").rglob("*.parquet")):
        continue
    info, df = load_info(root), load_frames(root)
    gidx = gripper_indices(info)
    rel = str(root.relative_to(path))
    for n, (ep_idx, ep) in enumerate(df.groupby("episode_index")):
        if n >= max_eps: break
        r = episode_signals(ep, info["fps"], gidx)
        r["dataset"], r["episode_index"] = rel, int(ep_idx)
        if "BotFails" in repo:
            r["fail"] = int("anomaly" in rel)
            r["task"] = rel.split("/")[-1].replace("_expert", "").replace("_anomaly", "")
        elif "vifailback" in repo:
            flags = np.stack(ep["complementary_info.vifailback_flags"].to_numpy())
            r["fail"] = int(flags[:, 0].any())
            r["task"] = int(ep["task_index"].iloc[0])
        rows.append(r)
    print(f"  {rel}: {n + 1} episodes")

res = pd.DataFrame(rows)

# z-score each signal within its task, so long tasks aren't flagged just for being long
for f in FEATS:
    g = res.groupby("task")[f]
    res[f + "_z"] = (res[f] - g.transform("mean")) / (g.transform("std") + 1e-9)
res["combo"] = res[[f + "_z" for f in FEATS]].abs().max(axis=1)

out = f"results/signals_{repo.split('/')[-1]}.csv"
res.to_csv(out, index=False)
print(f"\n{len(res)} episodes | failures: {res.fail.sum()} | good: {(res.fail == 0).sum()}  -> {out}")

print("\nAUROC  (0.5 = coin flip, >=0.70 = useful, <0.5 = useful if flipped)")
print(f"  {'signal':18s} {'raw':>6s} {'per-task z':>11s}")
for f in FEATS:
    print(f"  {f:18s} {roc_auc_score(res.fail, res[f]):6.3f} {roc_auc_score(res.fail, res[f + '_z']):11.3f}")
print(f"  {'COMBO (max |z|)':18s} {'':6s} {roc_auc_score(res.fail, res.combo):11.3f}")