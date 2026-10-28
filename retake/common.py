import json, subprocess, io
from pathlib import Path
import numpy as np
import pandas as pd
from huggingface_hub import snapshot_download
from PIL import Image, ImageDraw
from huggingface_hub import hf_hub_download
from huggingface_hub import HfApi
from huggingface_hub.hf_api import RepoFile

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

def fetch_subset(repo, subdir, include_videos=False):
    """Download meta/ and data/ (optionally videos/) of ONE sub-dataset,
    without listing the whole repo (listing a huge repo is what hung before)."""
    local = DATA / repo.replace("/", "__")
    entries = HfApi().list_repo_tree(repo, repo_type="dataset", path_in_repo=subdir, recursive=True)
    for f in entries:
        if not isinstance(f, RepoFile):
            continue
        p = "/" + f.path
        if "/meta/" in p or "/data/" in p or (include_videos and "/videos/" in p):
            hf_hub_download(repo, f.path, repo_type="dataset", local_dir=local)
    return local

_EPISODES = {}
def _episodes_meta(root):
    k = str(root)
    if k not in _EPISODES:
        files = sorted((Path(root) / "meta" / "episodes").rglob("*.parquet"))
        _EPISODES[k] = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    return _EPISODES[k]

def episode_video_seg(repo, path, dataset_rel, ep, cam):
    """Return (local_mp4_path, start_offset_seconds) for one episode.
    LeRobot v2.x: one file per episode (offset 0). v3.x: many episodes per file."""
    root = Path(path) / dataset_rel
    info = load_info(root)
    prefix = "" if str(dataset_rel) in (".", "") else f"{dataset_rel}/"
    tmpl = info["video_path"]
    if "episode_index" in tmpl:
        rel = tmpl.format(episode_chunk=ep // info.get("chunks_size", 1000), video_key=cam, episode_index=ep)
        offset = 0.0
    else:
        eps = _episodes_meta(root)
        rows = eps[eps.episode_index == ep]
        if rows.empty:
            raise KeyError(f"episode {ep} not in meta/episodes of {dataset_rel}")
        row = rows.iloc[0]
        try:
            rel = tmpl.format(video_key=cam,
                              chunk_index=int(row[f"videos/{cam}/chunk_index"]),
                              file_index=int(row[f"videos/{cam}/file_index"]))
            offset = float(row[f"videos/{cam}/from_timestamp"])
        except KeyError:
            raise KeyError(f"v3 episode columns not found for camera {cam}. "
                           f"Available: {[c for c in eps.columns if c.startswith('videos/')][:8]}")
    return hf_hub_download(repo, prefix + rel, repo_type="dataset", local_dir=path), offset

def episode_video(repo, path, dataset_rel, ep, cam):
    """Backwards-compatible: path only (used by older scripts, v2 datasets)."""
    return episode_video_seg(repo, path, dataset_rel, ep, cam)[0]