import json, collections
from pathlib import Path
import pandas as pd

import sys
SRC = sys.argv[1] if len(sys.argv) > 1 else "results/scan/integrity_scan.jsonl"

recs = {}
for l in open(SRC):
    if not l.strip():
        continue
    r = json.loads(l)
    prev = recs.get(r["dataset"])
    if prev is None or ("error" in prev and "error" not in r):     # retries append; keep the successful one
        recs[r["dataset"]] = r
ok = [r for r in recs.values() if "error" not in r]
err = [r for r in recs.values() if "error" in r]

episodes = sum(r["episodes"] for r in ok)
hours = sum(r["hours"] for r in ok)
scan_secs = sum(r.get("secs", 0) for r in ok)
print("=" * 70)
print(f"DATASETS scanned OK: {len(ok)}   skipped/errors: {len(err)}")
print(f"EPISODES: {episodes:,}   FRAMES: {sum(r['frames'] for r in ok):,}   ROBOT DATA: {hours:,.1f} hours")
print(f"Contributors: {len({r['dataset'].split('/')[0] for r in ok})}   "
      f"total scan time (sum over datasets): {scan_secs / 60:.0f} min   model spend: $0")
print("Robot types:", dict(collections.Counter(r.get("robot") for r in ok).most_common(6)))
if err:
    print("Error types:", dict(collections.Counter(r["error"].split(":")[0] for r in err).most_common(5)))

rows = [dict(dataset=r["dataset"], contributor=r["dataset"].split("/")[0], episode=int(i["episode"]),
             type=i["type"], hard=i["hard"], detail=i["detail"]) for r in ok for i in r.get("issues", [])]
iss = pd.DataFrame(rows, columns=["dataset", "contributor", "episode", "type", "hard", "detail"])
hard = iss[iss.hard]

print("\n" + "=" * 70 + "\nHARD ISSUES BY TYPE (deterministic checks)")
if len(hard):
    t = hard.groupby("type").agg(episodes=("episode", "size"), datasets=("dataset", "nunique"),
                                 contributors=("contributor", "nunique")).sort_values("episodes", ascending=False)
    print(t.to_string())
    bad_eps = hard[["dataset", "episode"]].drop_duplicates()
    print(f"\nEpisodes with >=1 hard issue: {len(bad_eps):,} of {episodes:,} ({100 * len(bad_eps) / episodes:.2f}%)")
    print(f"Datasets with >=1 hard issue: {hard.dataset.nunique()} of {len(ok)} ({100 * hard.dataset.nunique() / len(ok):.1f}%)")
    print("\nWorst datasets:")
    w = hard.groupby("dataset").agg(hard_issues=("episode", "size"),
                                    types=("type", lambda s: dict(collections.Counter(s))))
    eps_per = {r["dataset"]: r["episodes"] for r in ok}
    w["episodes"] = [eps_per[d] for d in w.index]
    print(w.sort_values("hard_issues", ascending=False).head(10).to_string())
soft = iss[~iss.hard]
if len(soft):
    print("\nMinor issues (review):", soft.type.value_counts().to_dict())

print("\n" + "=" * 70 + "\nDUPLICATE DEMOS ACROSS DATASETS")
exclude = set(map(tuple, iss[iss.type.isin(["no_motion", "dead_sensor", "empty_episode"])]
                  [["dataset", "episode"]].values))
h2 = collections.defaultdict(list)
for r in ok:
    for e, h in r.get("hashes", {}).items():
        if (r["dataset"], int(e)) not in exclude:
            h2[h].append((r["dataset"], int(e)))
cross = {h: v for h, v in h2.items() if len({d for d, _ in v}) > 1}
cross_contrib = {h: v for h, v in cross.items() if len({d.split("/")[0] for d, _ in v}) > 1}
print(f"Recordings appearing in 2+ datasets: {len(cross):,} "
      f"(extra copies: {sum(len(v) - 1 for v in cross.values()):,})")
print(f"  ...of which across DIFFERENT contributors: {len(cross_contrib):,}")

ds_hashes = collections.Counter()
pairs = collections.Counter()
for v in h2.values():
    for d in {d for d, _ in v}:
        ds_hashes[d] += 1
    ds = sorted({d for d, _ in v})
    for i in range(len(ds)):
        for j in range(i + 1, len(ds)):
            pairs[(ds[i], ds[j])] += 1
whole = [(a, b, n) for (a, b), n in pairs.items() if n >= 2 and n >= 0.8 * min(ds_hashes[a], ds_hashes[b])]
print(f"Dataset pairs that are >=80% the same recordings (re-uploads): {len(whole)}")
for a, b, n in sorted(whole, key=lambda x: -x[2])[:8]:
    print(f"   {a}  ==  {b}   ({n} shared episodes)")

Path("evidence").mkdir(exist_ok=True)
hard.to_csv("evidence/scan_hard_issues.csv", index=False)
summary = {"datasets_ok": len(ok), "datasets_skipped": len(err), "episodes": episodes, "hours": round(hours, 1),
           "contributors": len({r['dataset'].split('/')[0] for r in ok}),
           "hard_issues_by_type": hard.type.value_counts().to_dict() if len(hard) else {},
           "episodes_with_hard_issue": int(len(hard[["dataset", "episode"]].drop_duplicates())) if len(hard) else 0,
           "datasets_with_hard_issue": int(hard.dataset.nunique()) if len(hard) else 0,
           "cross_dataset_duplicate_recordings": len(cross),
           "cross_contributor_duplicate_recordings": len(cross_contrib),
           "reupload_dataset_pairs": [[a, b, n] for a, b, n in whole]}
Path("evidence/scan_summary.json").write_text(json.dumps(summary, indent=1))

print("\n" + "=" * 70 + "\nVERIFY THESE BY EYE (copy-paste):")
if len(hard):
    for typ, g in hard.groupby("type"):
        for _, x in g.head(2).iterrows():
            print(f"uv run python -m scripts.11_inspect_episode lerobot/community_dataset_v3 {x.dataset} {x.episode}   # {typ}")
print("\nSaved: evidence/scan_summary.json, evidence/scan_hard_issues.csv")