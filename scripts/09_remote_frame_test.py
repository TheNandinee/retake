import sys, time
from retake.common import DATA, fetch_subset, load_info, _episodes_meta, grab_frame

repo, sub = sys.argv[1], sys.argv[2]
fetch_subset(repo, sub)                       # meta + motion only, small
root = DATA / repo.replace("/", "__") / sub
info, eps = load_info(root), _episodes_meta(root)
cams = [k for k, v in info["features"].items() if v.get("dtype") == "video"]
cam = next((c for c in cams if any(p in c for p in ("top", "front", "high", "side"))), cams[0])

row = eps.iloc[len(eps) // 2]
rel = info["video_path"].format(video_key=cam,
                                chunk_index=int(row[f"videos/{cam}/chunk_index"]),
                                file_index=int(row[f"videos/{cam}/file_index"]))
url = f"https://huggingface.co/datasets/{repo}/resolve/main/{sub}/{rel}"
off = float(row[f"videos/{cam}/from_timestamp"])
dur = float(row[f"videos/{cam}/to_timestamp"]) - off
print(f"URL: {url}\nepisode {int(row.episode_index)} | camera {cam} | offset {off:.1f}s | length {dur:.1f}s")

for frac in (0.02, 0.5, 0.98):
    t0 = time.time()
    im = grab_frame(url, off + frac * dur)
    print(f"   frame at {frac:.2f}: {'OK ' + str(im.size) if im else 'FAILED'}  ({time.time() - t0:.1f}s)")
    if im:
        im.save(f"results/remote_test_{frac}.jpg")