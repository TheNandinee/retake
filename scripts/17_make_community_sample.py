import json, random
import pandas as pd

h = pd.read_csv("evidence/scan_hard_issues.csv")
recs = [json.loads(l) for l in open("results/scan/integrity_scan_v2.jsonl") if l.strip()]
ok = [r for r in recs if "error" not in r and r["episodes"] >= 20 and r.get("version") == "v3.0"]
rng = random.Random(0)
rows = []

# 2 verified-type examples per integrity issue, from different datasets
for t, g in h.groupby("type"):
    seen = set()
    for _, x in g.iterrows():
        if x.dataset in seen:
            continue
        rows.append((x.dataset, int(x.episode), f"flagged:{t}")); seen.add(x.dataset)
        if len(seen) == 2:
            break

# 10 random datasets with no integrity issues x 4 random episodes
bad = set(h.dataset)
pool = [r for r in ok if r["dataset"] not in bad]
for r in rng.sample(pool, 10):
    eps = sorted(int(e) for e in r["hashes"].keys())
    for e in rng.sample(eps, min(4, len(eps))):
        rows.append((r["dataset"], e, "random"))

df = pd.DataFrame(rows, columns=["dataset", "episode_index", "why"]).drop_duplicates(["dataset", "episode_index"])
df.to_csv("evidence/splits/community_sample.csv", index=False)
print(f"{len(df)} episodes from {df.dataset.nunique()} datasets -> evidence/splits/community_sample.csv")
print(df.why.value_counts().to_dict())
print(",".join(sorted(df.dataset.unique())))