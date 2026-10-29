import json, time, hashlib
from pathlib import Path
import numpy as np
from retake.common import DATA, load_info, load_frames, to_mat
from retake.integrity import check_dataset

REPO = "lerobot/community_dataset_v3"
path = DATA / REPO.replace("/", "__")
roots = list(dict.fromkeys(l.strip() for l in open("evidence/community_roots.txt") if l.strip()))
OUT = Path("results/scan/integrity_scan_v2.jsonl"); OUT.write_text("")
t0 = time.time()
for i, rel in enumerate(roots, 1):
    rec = {"dataset": rel}
    try:
        root = path / rel
        info, df = load_info(root), load_frames(root)
        res = check_dataset(df, info, root)
        hashes = {}
        for e, ep in df.groupby("episode_index"):
            s = to_mat(ep.sort_values("frame_index")["observation.state"])
            if np.isfinite(s).all() and len(s) >= 10:
                hashes[int(e)] = hashlib.md5(np.round(s, 4).tobytes()).hexdigest()
        rec.update(robot=info.get("robot_type"), version=info.get("codebase_version"), fps=info["fps"],
                   episodes=int(df.episode_index.nunique()), frames=len(df),
                   hours=round(len(df) / info["fps"] / 3600, 4),
                   issues=[{"episode": e, "type": t, "detail": d, "hard": h}
                           for e, lst in res.items() for (t, d, h) in lst], hashes=hashes)
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {str(ex)[:200]}"
    with OUT.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    if i % 100 == 0:
        print(f"  {i}/{len(roots)}  ({time.time() - t0:.0f}s)", flush=True)
print(f"done: {len(roots)} datasets in {time.time() - t0:.0f}s -> {OUT}")