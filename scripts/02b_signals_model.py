import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score

res = pd.read_csv(sys.argv[1])
FEATS = ["duration_s", "idle_ratio", "longest_idle_s", "grip_closes", "jerk", "track_err"]
Z = [f + "_z" for f in FEATS]
y, groups = res.fail.to_numpy(), res.task.astype(str).to_numpy()

def run(cols, name):
    X = res[cols].fillna(0).to_numpy()
    n_groups = len(set(groups))
    if n_groups >= 3:
        cv, kw, how = GroupKFold(min(5, n_groups)), {"groups": groups}, "held-out TASKS"
    else:
        cv, kw, how = StratifiedKFold(5, shuffle=True, random_state=0), {}, "held-out episodes"
    p = cross_val_predict(LogisticRegression(max_iter=2000, class_weight="balanced"),
                          X, y, cv=cv, method="predict_proba", **kw)[:, 1]
    print(f"  {name:30s} AUROC {roc_auc_score(y, p):.3f}   ({how})")
    return p

print(f"{sys.argv[1]}  | {len(res)} episodes, {res.fail.sum()} failures, {len(set(groups))} tasks")
res["signal_score"] = run(Z, "all motion signals")
run([c for c in Z if c != "duration_s_z"], "WITHOUT duration")
res.to_csv(sys.argv[1], index=False)