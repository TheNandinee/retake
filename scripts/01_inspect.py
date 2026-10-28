import sys
from retake.common import fetch, find_roots, load_info

repo = sys.argv[1]
full = "--full" in sys.argv
patterns = None if full else ["*.json", "*.jsonl", "*.md", "*.csv", "meta/**", "labels/**", "**/meta/**", "**/labels/**"]
path = fetch(repo, patterns)
print(f"Downloaded to {path}\n")

for root in find_roots(path):
    info = load_info(root)
    print(f"=== {root.relative_to(path)} ===")
    print("version:", info.get("codebase_version"), "| fps:", info.get("fps"),
          "| episodes:", info.get("total_episodes"), "| frames:", info.get("total_frames"))
    print("video_path:", info.get("video_path"))
    for k, v in info.get("features", {}).items():
        print(f"  {k:40s} {v.get('dtype'):10s} {v.get('shape')}  {v.get('names') or ''}")
    print()