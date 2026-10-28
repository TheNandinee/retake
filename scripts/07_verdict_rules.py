import sys
import pandas as pd

sig = pd.read_csv("results/signals_BotFails.csv")[
    ["dataset", "episode_index", "fail", "duration_s_z", "longest_idle_s_z"]]
HARD = {"spill", "dropped_object", "human_intervention", "wrong_object",
        "wrong_placement", "collision", "wrong_target"}

def load(p):
    d = pd.read_csv(p)
    d["v_anom"] = d.status.eq("retake") if "status" in d else d.anomaly.astype(str).str.lower().eq("true")
    d = d.drop(columns=[c for c in ["fail", "duration_s_z"] if c in d]).merge(sig, on=["dataset", "episode_index"])
    d["ftype"] = d.failure_type.fillna("none").astype(str)
    d["conf"] = pd.to_numeric(d.confidence, errors="coerce").fillna(0)
    return d

RULES = {
    "R0 any vision anomaly (current)":    lambda d: d.v_anom,
    "R1 visible evidence only":           lambda d: d.v_anom & d.ftype.isin(HARD),
    "R2 R1 + incomplete if short (z<-1)": lambda d: d.v_anom & (d.ftype.isin(HARD) |
                                                    ((d.ftype == "incomplete") & (d.duration_s_z < -1))),
    "R3 R1 + confidence >= 0.9":          lambda d: d.v_anom & d.ftype.isin(HARD) & (d.conf >= 0.9),
}

for p in sys.argv[1:]:
    d = load(p); F = d.fail == 1
    print(f"\n{p}  |  {len(d)} episodes, {F.sum()} real failures")
    print(f"  {'rule':36s} {'precision':>9s}  caught    false alarms")
    for name, rule in RULES.items():
        pred = rule(d)
        tp, fp = (pred & F).sum(), (pred & ~F).sum()
        prec = tp / pred.sum() if pred.sum() else float("nan")
        print(f"  {name:36s} {prec:9.0%}  {tp:>2}/{F.sum():<2}     {fp:>2}/{(~F).sum()}")
    inc = d[d.v_anom & (d.ftype == "incomplete")]
    if len(inc):
        print(f"  'incomplete' verdicts: {len(inc)}, of which correct: {(inc.fail == 1).sum()}")