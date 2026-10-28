import json
from pathlib import Path
import pandas as pd

p = Path("results/ledger.jsonl")
if not p.exists():
    print("No spend yet."); raise SystemExit
df = pd.DataFrame([json.loads(l) for l in p.read_text().splitlines() if l.strip()])
print(df.groupby("model").agg(calls=("cost", "size"), tokens_in=("in", "sum"),
                              tokens_out=("out", "sum"), usd=("cost", "sum")).round(4))
print(f"\nTOTAL SPENT: ${df.cost.sum():.4f}")