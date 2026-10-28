import json, subprocess, io
from pathlib import Path
import numpy as np
import pandas as pd
from huggingface_hub import snapshot_download
from PIL import Image, ImageDraw
from huggingface_hub import hf_hub_download

DATA = Path("data")


# ---------- datasets ----------
def fetch(repo_id, patterns=None):
    local = DATA / repo_id.replace("/", "__")
    snapshot_download(repo_id=repo_id, repo_type="dataset",
                      local_dir=local, allow_patterns=patterns)
    return local


def find_roots(path):
    """A download can contain several LeRobot datasets; each has meta/info.json."""
    return sorted({p.parent.parent for p in Path(path).rglob("meta/info.json")})


def load_info(root):
    return json.loads((Path(root) / "meta" / "info.json").read_text())


def load_frames(root):
    files = sorted((Path(root) / "data").rglob("*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def to_mat(col):
    return np.stack(col.to_numpy()).astype(float)


# ---------- video ----------
def video_for_episode(root, info, ep_idx, key):
    """Returns (video_path, offset_seconds). Handles LeRobot v2.x and v3.x layouts."""
    root, tmpl = Path(root), info["video_path"]
    if "episode_index" in tmpl:  # v2.x: one file per episode
        chunk = ep_idx // info.get("chunks_size", 1000)
        return root / tmpl.format(episode_chunk=chunk, video_key=key,
                                  episode_index=ep_idx), 0.0
    # v3.x: many episodes concatenated per file; offsets live in meta/episodes
    eps = pd.concat([pd.read_parquet(f) for f in (root / "meta" / "episodes").rglob("*.parquet")])
    row = eps[eps.episode_index == ep_idx].iloc[0]
    c = int(row[f"videos/{key}/chunk_index"]); f = int(row[f"videos/{key}/file_index"])
    return (root / tmpl.format(video_key=key, chunk_index=c, file_index=f),
            float(row[f"videos/{key}/from_timestamp"]))


def grab_frame(video, t):
    out = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(video),
                          "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True)
    return Image.open(io.BytesIO(out.stdout)).convert("RGB") if out.stdout else None


def frame_grid(video, offset, times, cell=(320, 240)):
    """3x3 grid of frames, each stamped with its episode-relative timestamp."""
    grid = Image.new("RGB", (cell[0] * 3, cell[1] * 3), "black")
    for i, t in enumerate(times[:9]):
        im = grab_frame(video, offset + t)
        if im is None: continue
        im = im.resize(cell)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 70, 22], fill="black"); d.text((5, 5), f"t={t:.1f}s", fill="yellow")
        grid.paste(im, ((i % 3) * cell[0], (i // 3) * cell[1]))
    return grid


def contact_sheet(ims, cols=4, cell=(448, 336)):
    """ims: list of (t, PIL.Image). Returns one image with timestamps, for human review."""
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cell[0] * cols, cell[1] * rows), "black")
    for i, (t, im) in enumerate(ims):
        im = im.resize(cell)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 80, 22], fill="black"); d.text((5, 5), f"t={t:.1f}s", fill="yellow")
        sheet.paste(im, ((i % cols) * cell[0], (i // cols) * cell[1]))
    return sheet

def episode_video(repo, path, dataset_rel, ep, cam):
    """Download (once) and return the local mp4 path for one episode (LeRobot v2.x)."""
    info = load_info(Path(path) / dataset_rel)
    rel = f"{dataset_rel}/" + info["video_path"].format(
        episode_chunk=ep // info.get("chunks_size", 1000), video_key=cam, episode_index=ep)
    return hf_hub_download(repo, rel, repo_type="dataset", local_dir=path)