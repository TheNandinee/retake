import sys, json, time
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.hf_api import RepoFolder

repo = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
api = HfApi()
t0 = time.time()

def ls(path=""):
    return list(api.list_repo_tree(repo, repo_type="dataset", path_in_repo=path))

def find_root(path, depth=0):
    """Walk down until we find a folder containing meta/ (a LeRobot dataset root)."""
    entries = ls(path)
    names = {e.path.rstrip("/").split("/")[-1] for e in entries}
    if "meta" in names:
        return path
    if depth >= 3:
        return None
    for e in entries:
        if isinstance(e, RepoFolder):
            r = find_root(e.path, depth + 1)
            if r is not None:
                return r
    return None

top = ls()
folders = [e for e in top if isinstance(e, RepoFolder)]
print(f"Top level: {len(top)} entries ({len(folders)} folders)  [{time.time()-t0:.0f}s]")
for e in top[:12]:
    print(f"   {'DIR ' if isinstance(e, RepoFolder) else 'FILE'} {e.path}")

if any(e.path == "meta" for e in top):
    roots = [""]
else:
    roots = []
    for f in folders[:n]:
        r = find_root(f.path, 1)
        if r is not None:
            roots.append(r)
        print(f"   found root: {r}  [{time.time()-t0:.0f}s]")

print()
for r in roots:
    p = f"{r}/meta/info.json" if r else "meta/info.json"
    info = json.loads(open(hf_hub_download(repo, p, repo_type="dataset")).read())
    cams = [k for k, v in info.get("features", {}).items() if v.get("dtype") == "video"]
    print(f"=== {r or '(repo root)'} ===")
    print(f"   version: {info.get('codebase_version')} | fps: {info.get('fps')} | "
          f"episodes: {info.get('total_episodes')} | robot: {info.get('robot_type')}")
    print(f"   video_path: {info.get('video_path')}")
    print(f"   cameras: {cams}")
print(f"\nDone in {time.time()-t0:.0f}s")