import numpy as np
import pandas as pd
from pathlib import Path

base = Path("data/kantine__BotFails/BotFails/labels")
rows, all_vals = [], []
for f in sorted(base.rglob("*_labels.csv")):
    v = pd.read_csv(f, header=None).iloc[:, 0]
    v = pd.to_numeric(v, errors="coerce").dropna().to_numpy()
    all_vals.extend(np.unique(v).tolist())
    idx = np.flatnonzero(v > 0)
    rows.append({
        "dataset": f"BotFails/test/{f.parent.name}",
        "episode_index": int(f.stem.split("_")[1]),
        "n_frames": len(v),
        "anomaly_frames": len(idx),
        "any_anomaly": int(len(idx) > 0),
        "first_anomaly_s": idx[0] / 30 if len(idx) else None,
        "last_anomaly_s": idx[-1] / 30 if len(idx) else None,
    })

lab = pd.DataFrame(rows)
lab.to_csv("results/botfails_labels.csv", index=False)
print("Label values seen:", sorted(set(all_vals)))
print(f"{len(lab)} labeled episodes | with anomaly: {lab.any_anomaly.sum()} | without: {(lab.any_anomaly == 0).sum()}")
print("\nAnomaly duration (s):", (lab.anomaly_frames / 30).describe().round(2).to_dict())
print(lab.head(10).to_string())

# re-score motion signals with TRUE labels
sig = pd.read_csv("results/signals_BotFails.csv")
sig = sig.merge(lab[["dataset", "episode_index", "any_anomaly"]], on=["dataset", "episode_index"], how="left")
sig["fail"] = sig["any_anomaly"].fillna(0).astype(int)
sig.drop(columns="any_anomaly").to_csv("results/signals_BotFails.csv", index=False)
print(f"\nRelabeled signals file: failures={sig.fail.sum()} good={(sig.fail == 0).sum()}")