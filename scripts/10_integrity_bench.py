"""Corruption benchmark: break clean episodes on purpose and check the integrity layer catches it."""
import numpy as np
import pandas as pd
from PIL import Image
from retake.common import DATA, find_roots, load_info, load_frames, grab_frame
from retake.integrity import check_dataset, check_frames, HARD

rng = np.random.default_rng(0)
path = DATA / "kantine__BotFails"
roots = [r for r in find_roots(path) if r.name.endswith("_expert")]
cache = {r: (load_info(r), load_frames(r)) for r in roots}
N = 30

def corrupt(ep, kind):
    ep = ep.sort_values("frame_index").reset_index(drop=True).copy()
    n = len(ep)
    if kind == "dropped_frames":
        a = int(n * 0.4); ep = ep.drop(index=range(a, a + int(n * 0.15))).reset_index(drop=True)
    elif kind == "empty_episode":
        ep = ep.iloc[:5].copy()
    elif kind == "nan_values":
        s = ep["observation.state"].copy(); x = np.array(s.iloc[n // 2], dtype=float); x[0] = np.nan
        s.iloc[n // 2] = x; ep["observation.state"] = s
    elif kind == "dead_sensor":
        s = np.stack(ep["observation.state"].to_numpy()).astype(float); s[:, 0] = s[0, 0]
        ep["observation.state"] = list(s)
    elif kind == "timestamp_error":
        ts = ep["timestamp"].to_numpy().copy(); ts[n // 2] = ts[n // 2 - 5]; ep["timestamp"] = ts
    return ep

print("=== Motion-data corruptions (each injected into a real clean dataset) ===")
rows = []
for kind in ["dropped_frames", "empty_episode", "nan_values", "dead_sensor", "timestamp_error", "duplicate_episode"]:
    hits = 0
    for _ in range(N):
        root = roots[rng.integers(len(roots))]
        info, df = cache[root]
        target = int(rng.choice(df.episode_index.unique()))
        if kind == "duplicate_episode":
            new = int(df.episode_index.max()) + 1
            copy = df[df.episode_index == target].copy(); copy["episode_index"] = new
            mod, check_ep = pd.concat([df, copy], ignore_index=True), new
        else:
            mod = pd.concat([df[df.episode_index != target],
                             corrupt(df[df.episode_index == target], kind)], ignore_index=True)
            check_ep = target
        found = [i[0] for i in check_dataset(mod, info).get(check_ep, [])]
        hits += kind in found
    rows.append((kind, hits)); print(f"  {kind:18s} detected {hits}/{N}")

print("\n=== False positives on untouched clean data (178 expert episodes) ===")
flagged = []
for root, (info, df) in cache.items():
    for e, issues in check_dataset(df, info).items():
        hard = [i for i in issues if i[2]]
        if hard:
            flagged.append((root.name, e, hard))
print(f"  episodes with a hard integrity issue: {len(flagged)}/{sum(df.episode_index.nunique() for _, df in cache.values())}")
for name, e, hard in flagged[:10]:
    print(f"    {name} ep{e}: {hard}")

print("\n=== Frame corruptions (real frames from downloaded expert videos) ===")
videos = sorted(path.rglob("normal_train/*_expert/videos/**/observation.images.logitech_1/*.mp4"))[:20]
frame_sets = []
for v in videos:
    fr = [(t, grab_frame(str(v), t)) for t in (1.0, 5.0, 10.0, 15.0, 20.0, 25.0)]
    fr = [(t, im) for t, im in fr if im is not None]
    if len(fr) >= 3:
        frame_sets.append(fr)
clean_fp = sum(any(i[2] for i in check_frames(fr)) for fr in frame_sets)
frozen = sum("frozen_video" in [i[0] for i in check_frames([(t, fr[0][1]) for t, _ in fr])] for fr in frame_sets)
black_img = Image.new("RGB", frame_sets[0][0][1].size, "black") if frame_sets else None
black = sum("black_frames" in [i[0] for i in check_frames([fr[0], (fr[1][0], black_img)] + fr[2:])] for fr in frame_sets)
print(f"  clean videos falsely flagged: {clean_fp}/{len(frame_sets)}")
print(f"  frozen_video  detected {frozen}/{len(frame_sets)}")
print(f"  black_frames  detected {black}/{len(frame_sets)}")