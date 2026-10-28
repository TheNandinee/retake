import sys
from retake.common import DATA, load_info, load_frames, _episodes_meta

repo, sub = sys.argv[1], sys.argv[2]
root = DATA / repo.replace("/", "__") / sub
info, eps, df = load_info(root), _episodes_meta(root), load_frames(root)
fps = info["fps"]
cams = [k for k, v in info["features"].items() if v.get("dtype") == "video"]
print("video columns in meta/episodes:", [c for c in eps.columns if c.startswith("videos/")][:6])

motion_len = df.groupby("episode_index").size().reindex(eps.episode_index).to_numpy() / fps
for c in cams:
    seg = (eps[f"videos/{c}/to_timestamp"] - eps[f"videos/{c}/from_timestamp"]).to_numpy()
    diff = seg - motion_len
    print(f"\n{c}")
    print(f"   video segment vs motion length: max |diff| {abs(diff).max():.2f}s, mean {diff.mean():+.2f}s")
    print(f"   first offsets (s): {eps[f'videos/{c}/from_timestamp'].head(4).round(2).tolist()}")
    print(f"   episodes per file: {eps.groupby(f'videos/{c}/file_index').size().to_dict()}")