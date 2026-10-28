import pandas as pd
from pathlib import Path

sig = pd.read_csv("results/signals_BotFails.csv")
seen = pd.read_csv("results/vision_check_BotFails.csv")
key = lambda d: d.dataset + ":" + d.episode_index.astype(str)
sig["key"] = key(sig)
rest = sig[~sig.key.isin(set(key(seen)))]

test = pd.concat([rest[rest.fail == 1].sample(25, random_state=42),
                  rest[rest.fail == 0].sample(25, random_state=42)])
dev = sig[~sig.key.isin(set(test.key))]

Path("evidence/splits").mkdir(parents=True, exist_ok=True)
cols = ["dataset", "episode_index", "fail", "task"]
test[cols].to_csv("evidence/splits/botfails_TEST_frozen.csv", index=False)
dev[cols].to_csv("evidence/splits/botfails_dev.csv", index=False)
print(f"TEST (frozen, never tune on this): {len(test)} episodes | {test.fail.sum()} failures")
print(f"DEV  (tune freely):               {len(dev)} episodes | {dev.fail.sum()} failures")