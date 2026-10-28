from retake.common import fetch

PATTERNS = {
    "kantine/BotFails": ["*.md", "**/meta/**", "**/data/**", "labels/**", "**/labels/**", "**/*.csv"],
    "sii-rhos-ai/vifailback-dataset-lerobot": ["*.md", "meta/**", "data/chunk-000/**"],
}
for repo, pats in PATTERNS.items():
    print("Fetching", repo)
    print(" ->", fetch(repo, pats))