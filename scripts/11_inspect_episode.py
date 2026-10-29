import sys
from retake.common import DATA, load_info, load_frames, episode_video_seg, grab_frame, contact_sheet, to_mat

repo, rel, ep_i = sys.argv[1], sys.argv[2], int(sys.argv[3])
path = DATA / repo.replace("/", "__")
root = path / rel
info, df = load_info(root), load_frames(root)
ep = df[df.episode_index == ep_i].sort_values("frame_index")
s = to_mat(ep["observation.state"])
a = to_mat(ep["action"]) if "action" in ep else s
fps = info["fps"]; dur = len(s) / fps
print(f"{rel} ep{ep_i}: {len(s)} frames ({dur:.1f}s) | robot {info.get('robot_type')}")
print("state  std per joint:", s.std(0).round(4))
print("action std per joint:", a.std(0).round(4))
print("state at start:", s[0].round(2), "| at end:", s[-1].round(2))

cams = [k for k, v in info["features"].items() if v.get("dtype") == "video"]
if cams:
    cam = next((c for c in cams if any(p in c.split(".")[-1] for p in ("top", "front", "high", "side"))), cams[0])
    video, off = episode_video_seg(repo, path, rel, ep_i, cam, remote=True)
    fr = [(t, grab_frame(video, off + t)) for t in [dur * f for f in (0.02, 0.2, 0.4, 0.6, 0.8, 0.98)]]
    out = f"results/inspect_{rel.replace('/', '_')}_ep{ep_i}.jpg"
    contact_sheet([x for x in fr if x[1] is not None], cols=3).save(out)
    print(f"camera {cam} -> {out}")