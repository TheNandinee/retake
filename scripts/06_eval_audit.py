import sys
import pandas as pd

rep = pd.read_csv(sys.argv[1])
lab = pd.read_csv("results/signals_BotFails.csv")[["dataset", "episode_index", "fail"]]
d = rep.merge(lab, on=["dataset", "episode_index"])
print(f"{len(d)} audited episodes with labels | {d.fail.sum()} real failures")
for name, pred in [("retake only", d.status.eq("retake")),
                   ("retake+review", d.status.isin(["retake", "review"]))]:
    tp, fp = (pred & (d.fail == 1)).sum(), (pred & (d.fail == 0)).sum()
    print(f"  {name:14s} acc {(pred == (d.fail == 1)).mean():4.0%} | caught {tp}/{(d.fail == 1).sum()} "
          f"| false alarms {fp}/{(d.fail == 0).sum()}")