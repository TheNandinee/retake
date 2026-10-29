"""E025: post-hoc diagnosis of the frozen test set (no pipeline changes).
Labels: results/signals_BotFails.csv (same source as scripts/06_eval_audit.py)."""
import pandas as pd

rep = pd.read_csv("reports/botfails_TEST/episodes.csv")
lab = pd.read_csv("results/signals_BotFails.csv")[["dataset", "episode_index", "fail"]]
d = rep.merge(lab, on=["dataset", "episode_index"])
d["failure"] = d.fail == 1
d["group"] = d.task_key.str.split("::").str[0]
print(pd.crosstab(d.failure, d.status, margins=True), "\n")

odd = d[d.id.str.contains("_anomaly") & ~d.failure]
print(f"'_anomaly' folder but labeled GOOD: {len(odd)}")
for _, r in odd.iterrows():
    print(f"- {r.id} -> {r.status}")
print()

miss = d[d.failure & (d.status == "clean")]
rev = d[d.failure & (d.status == "review")]
fa = d[~d.failure & (d.status != "clean")]
for name, g in [("MISSED (real failure -> clean)", miss),
                ("CAUGHT ONLY IN REVIEW", rev),
                ("FALSE ALARMS (good -> review/retake)", fa)]:
    print(f"=== {name}: {len(g)} ===")
    for _, r in g.iterrows():
        print(f"- {r.id} | {r.failure_type} | conf {r.confidence} | {str(r.reason)[:150]}")
    print()

print("Mean confidence  missed:", round(miss.confidence.mean(), 2),
      "| caught retake:", round(d[d.failure & (d.status == "retake")].confidence.mean(), 2))
miss[["dataset", "episode_index"]].to_csv("evidence/splits/botfails_TEST_missed.csv", index=False)
