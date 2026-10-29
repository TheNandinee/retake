"""Unit tests for the deterministic integrity checks (synthetic data, no network, no API keys)."""
import numpy as np
import pandas as pd
from PIL import Image
from retake.integrity import check_dataset, check_frames

FPS = 30
INFO = {"fps": FPS, "features": {"observation.state": {"names": [f"j{i}" for i in range(6)]}},
        "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"}


def make_ds(n_eps=6, n=60, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for e in range(n_eps):
        t = np.linspace(0, 2 * np.pi, n)
        s = np.stack([10 * np.sin(t + 0.3 * e + j) + rng.normal(0, 0.1, n) for j in range(6)], 1).astype(np.float32)
        for i in range(n):
            rows.append({"episode_index": e, "frame_index": i, "timestamp": i / FPS,
                         "observation.state": s[i], "action": s[i] + np.float32(0.1)})
    return pd.DataFrame(rows)


def hard_types(res, e):
    return {t for t, _, hard in res[e] if hard}


def set_col(df, mask, col, arrays):
    df[col] = df[col].astype(object)
    df.loc[mask, col] = pd.Series(list(arrays), index=df.index[mask])


def test_clean_dataset_has_no_hard_issues():
    res = check_dataset(make_ds(), INFO)
    assert all(not hard_types(res, e) for e in res)


def test_no_motion():
    df = make_ds(); m = df.episode_index == 2
    set_col(df, m, "observation.state", [np.ones(6, np.float32)] * m.sum())
    set_col(df, m, "action", [np.ones(6, np.float32)] * m.sum())
    assert "no_motion" in hard_types(check_dataset(df, INFO), 2)


def test_dead_sensor_frozen_reading_while_commanded():
    df = make_ds(); m = df.episode_index == 3
    frozen = [np.r_[np.float32(5.0), s[1:]].astype(np.float32) for s in df.loc[m, "observation.state"]]
    set_col(df, m, "observation.state", frozen)            # joint 0 reading frozen, command still moves
    assert "dead_sensor" in hard_types(check_dataset(df, INFO), 3)


def test_duplicate_episode():
    df = make_ds()
    copy = df[df.episode_index == 0].copy(); copy["episode_index"] = 6
    res = check_dataset(pd.concat([df, copy], ignore_index=True), INFO)
    assert "duplicate_episode" in hard_types(res, 6)


def test_empty_episode():
    df = make_ds()
    df = df[(df.episode_index != 1) | (df.frame_index < 5)]
    assert "empty_episode" in hard_types(check_dataset(df, INFO), 1)


def test_timestamp_error():
    df = make_ds(); idx = df.index[(df.episode_index == 4) & (df.frame_index == 30)][0]
    df.loc[idx, "timestamp"] = 0.0
    assert "timestamp_error" in hard_types(check_dataset(df, INFO), 4)


def test_dropped_frames():
    df = make_ds()
    df = df[~((df.episode_index == 5) & df.frame_index.between(20, 45))]
    assert "dropped_frames" in hard_types(check_dataset(df, INFO), 5)


def test_frozen_and_black_video():
    rng = np.random.default_rng(1)
    frames = [(t, Image.fromarray(rng.integers(0, 255, (120, 160, 3), dtype=np.uint8))) for t in range(6)]
    assert check_frames(frames) == []
    frozen = [(t, frames[0][1]) for t in range(6)]
    assert "frozen_video" in {x[0] for x in check_frames(frozen)}
    black = frames[:2] + [(2, Image.new("RGB", (160, 120), "black"))] + frames[3:]
    assert "black_frames" in {x[0] for x in check_frames(black)}