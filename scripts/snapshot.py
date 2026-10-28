import sys, json, shutil, subprocess, datetime
from pathlib import Path
from importlib.metadata import version

name = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
dest = Path("evidence/snapshots") / f"{stamp}_{name}"
dest.mkdir(parents=True, exist_ok=True)

for f in Path("results").glob("*.csv"):
    shutil.copy(f, dest / f.name)
if Path("results/ledger.jsonl").exists():
    shutil.copy("results/ledger.jsonl", dest / "ledger.jsonl")

def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True).strip()
    except Exception: return None

meta = {
    "name": name,
    "timestamp": datetime.datetime.now().isoformat(),
    "git_commit": sh("git rev-parse --short HEAD"),
    "git_dirty": bool(sh("git status --porcelain")),
    "packages": {p: version(p) for p in ["numpy", "pandas", "scikit-learn", "openai", "huggingface_hub"]},
    "files": sorted(p.name for p in dest.iterdir()),
}
(dest / "meta.json").write_text(json.dumps(meta, indent=2))
print(f"Saved {len(meta['files'])} files -> {dest}")