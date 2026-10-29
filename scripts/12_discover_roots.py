import sys, time
from pathlib import Path
from huggingface_hub import HfApi
from huggingface_hub.hf_api import RepoFolder, RepoFile

repo = sys.argv[1] if len(sys.argv) > 1 else "lerobot/community_dataset_v3"
api = HfApi()
roots_f = Path("evidence/community_roots.txt")
done_f = Path("results/scan/discover_done.txt"); done_f.parent.mkdir(parents=True, exist_ok=True)
done = set(done_f.read_text().split()) if done_f.exists() else set()

top = list(api.list_repo_tree(repo, repo_type="dataset"))
print("top-level files:", [e.path for e in top if isinstance(e, RepoFile)])
contribs = [e.path for e in top if isinstance(e, RepoFolder) and e.path not in done]
print(f"{len(contribs)} contributors left to list", flush=True)

for i, c in enumerate(contribs, 1):
    try:
        kids = [e.path for e in api.list_repo_tree(repo, repo_type="dataset", path_in_repo=c)
                if isinstance(e, RepoFolder)]
    except Exception as ex:
        print(f"  ERR {c}: {str(ex)[:80]}  (will retry on next run)", flush=True)
        time.sleep(30)
        continue
    with roots_f.open("a") as f:
        f.writelines(k + "\n" for k in kids)
    with done_f.open("a") as f:
        f.write(c + "\n")
    if i % 25 == 0:
        print(f"  {i}/{len(contribs)} contributors listed", flush=True)
    time.sleep(0.4)

n = len(set(roots_f.read_text().split()))
print(f"done: {n} datasets in {roots_f}")