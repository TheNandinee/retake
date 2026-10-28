import sys
from retake.common import DATA, load_info, load_frames, episode_video, grab_frame, contact_sheet, to_mat

repo, rel, ep_i = sys.argv[1], sys.argv[2], int(sys.argv[3])
path = DATA / repo.replace("/", "__")
root = path / rel
info, df = load_info(root), load_frames(root)
ep = df[df.episode_index == ep_i].sort_values("frame_index")
s, a = to_mat(ep["observation.state"]), to_mat(ep["action"])
fps = info["fps"]; dur = len(s) / fps
print(f"{rel} ep{ep_i}: {len(s)} frames ({dur:.1f}s)")
print("state  std per joint:", s.std(0).round(4))
print("action std per joint:", a.std(0).round(4))
print("state at start:", s[0].round(2), "| at end:", s[-1].round(2))

cam = next(k for k, v in info["features"].items() if v.get("dtype") == "video")
v = episode_video(repo, path, rel, ep_i, cam)
fr = [(t, grab_frame(str(v), t)) for t in [dur * f for f in (0.02, 0.2, 0.4, 0.6, 0.8, 0.98)]]
out = f"results/inspect_{root.name}_ep{ep_i}.jpg"
contact_sheet([x for x in fr if x[1] is not None], cols=3).save(out)
print("frames:", out)