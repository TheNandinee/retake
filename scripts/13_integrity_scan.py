import sys, json, time, hashlib, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from retake.common import DATA, fetch_subset, load_info, load_frames, to_mat
from retake.integrity import check_dataset

REPO = "lerobot/community_dataset_v3"
WORKERS = 2          # gentle on Hugging Face rate limits
path = DATA / REPO.replace("/", "__")
roots = [l.strip() for l in open("evidence/community_roots.txt") if l.strip()]
roots = list(dict.fromkeys(roots))                      # de-duplicate, keep order
if len(sys.argv) > 1:
    roots = roots[:int(sys.argv[1])]

OUT = Path("results/scan/integrity_scan.jsonl"); OUT.parent.mkdir(parents=True, exist_ok=True)

def load_done():
    """Datasets already scanned successfully. Errored ones are NOT done, so they get retried."""
    if not OUT.exists():
        return set()
    done = set()
    for l in OUT.read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            if "error" not in r:
                done.add(r["dataset"])
    return done

done = load_done()
lock = threading.Lock()

def scan(rel):
    t0, rec = time.time(), {"dataset": rel}
    try:
        fetch_subset(REPO, rel)
        root = path / rel
        if not (root / "meta" / "info.json").exists():
            raise FileNotFoundError("no meta/info.json - not a LeRobot dataset folder")
        info, df = load_info(root), load_frames(root)
        fps = info["fps"]
        res = check_dataset(df, info, root)
        hashes = {}
        for e, ep in df.groupby("episode_index"):
            s = to_mat(ep.sort_values("frame_index")["observation.state"])
            if np.isfinite(s).all() and len(s) >= 10:
                hashes[int(e)] = hashlib.md5(np.round(s, 4).tobytes()).hexdigest()
        rec.update(robot=info.get("robot_type"), version=info.get("codebase_version"), fps=fps,
                   episodes=int(df.episode_index.nunique()), frames=len(df),
                   hours=round(len(df) / fps / 3600, 4),
                   issues=[{"episode": e, "type": t, "detail": d, "hard": h}
                           for e, lst in res.items() for (t, d, h) in lst],
                   hashes=hashes, secs=round(time.time() - t0, 1))
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {str(ex)[:200]}"
    with lock:
        with OUT.open("a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec

todo = [r for r in roots if r not in done]
print(f"{len(roots)} datasets | {len(done)} already scanned OK | {len(todo)} to go | {WORKERS} workers", flush=True)
with ThreadPoolExecutor(WORKERS) as ex:
    futs = [ex.submit(scan, r) for r in todo]
    for i, f in enumerate(as_completed(futs), 1):
        r = f.result()
        hard = sum(x["hard"] for x in r.get("issues", []))
        msg = f"ERROR {r['error'][:80]}" if "error" in r else f"{r['episodes']} eps, {hard} hard issues ({r['secs']}s)"
        print(f"[{i}/{len(todo)}] {r['dataset']}: {msg}", flush=True)
print("scan pass complete", flush=True)