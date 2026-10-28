import sys
import pandas as pd

rep = pd.read_csv(sys.argv[1])
lab = pd.read_csv("results/signals_BotFails.csv")[["dataset", "episode_index", "fail"]]
d = rep.merge(lab, on=["dataset", "episode_index"])
F = d.fail == 1
print(f"{len(d)} audited episodes with labels | {F.sum()} real failures")
for name, pred in [("RETAKE list", d.status.eq("retake")),
                   ("RETAKE+REVIEW", d.status.isin(["retake", "review"]))]:
    tp, fp = (pred & F).sum(), (pred & ~F).sum()
    prec = tp / pred.sum() if pred.sum() else float("nan")
    print(f"  {name:14s} precision {prec:4.0%} | caught {tp}/{F.sum()} | false alarms {fp}/{(~F).sum()}")