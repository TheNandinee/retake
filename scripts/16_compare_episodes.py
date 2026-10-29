import sys
import numpy as np
from retake.common import DATA, load_frames, to_mat

repo, a_ds, a_ep, b_ds, b_ep = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], int(sys.argv[5])
path = DATA / repo.replace("/", "__")

def get(ds, ep):
    df = load_frames(path / ds)
    e = df[df.episode_index == ep].sort_values("frame_index")
    return to_mat(e["observation.state"]), to_mat(e["action"])

sa, aa = get(a_ds, a_ep)
sb, ab = get(b_ds, b_ep)
print(f"A: {a_ds} ep{a_ep}  {len(sa)} frames")
print(f"B: {b_ds} ep{b_ep}  {len(sb)} frames")
if sa.shape == sb.shape:
    print(f"max |state difference|:  {np.abs(sa - sb).max():.6f}")
    print(f"max |action difference|: {np.abs(aa - ab).max():.6f}")
    print("IDENTICAL motion" if np.abs(sa - sb).max() < 1e-4 else "different motion")
else:
    print("different lengths -> not the same recording")