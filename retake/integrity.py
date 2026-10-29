"""Deterministic data-integrity checks. No AI judgment: every finding is verifiable."""
import hashlib
import numpy as np
from retake.common import to_mat, _episodes_meta

HARD = {"frozen_video", "black_frames", "duplicate_episode", "empty_episode", "nan_values",
        "dead_sensor", "no_motion", "length_mismatch", "timestamp_error", "dropped_frames"}

def _joint_names(info):
    names = info["features"]["observation.state"].get("names")
    if isinstance(names, dict): names = list(names.values())[0]
    if names and isinstance(names[0], list): names = names[0]
    return names

def check_episode(ep, fps):
    """Checks on one episode's motion data. Returns a list of (issue, detail, is_hard)."""
    ep = ep.sort_values("frame_index")
    n, out = len(ep), []
    if n < max(10, fps):
        out.append(("empty_episode", f"only {n} frames ({n / fps:.1f}s)", True))
    s = to_mat(ep["observation.state"])
    a = to_mat(ep["action"]) if "action" in ep else None
    if not np.isfinite(s).all() or (a is not None and not np.isfinite(a).all()):
        out.append(("nan_values", "NaN or infinite values in state/action", True))
    if "timestamp" in ep and n > 1:
        d = np.diff(ep["timestamp"].to_numpy(dtype=float))
        if (d <= 0).any():
            out.append(("timestamp_error", f"{int((d <= 0).sum())} non-increasing timestamps", True))
        gaps = d[d > 1.5 / fps]
        if len(gaps):
            missing = int(np.round((gaps * fps - 1).sum()))
            hard = gaps.max() > 1.0 or missing > 0.05 * n
            out.append(("dropped_frames",
                        f"{len(gaps)} gap(s), ~{missing} frames missing, longest {gaps.max():.2f}s", hard))
    return out

def check_dataset(df, info, root=None):
    """All motion-data checks for every episode of one dataset. Returns {episode_index: [issues]}."""
    fps, names = info["fps"], _joint_names(info)
    res, hashes, s_std, a_std = {}, {}, {}, {}
    for ep_idx, ep in df.groupby("episode_index"):
        e = int(ep_idx)
        ep = ep.sort_values("frame_index")
        res[e] = check_episode(ep, fps)
        s = to_mat(ep["observation.state"])
        a = to_mat(ep["action"]) if "action" in ep else None
        if np.isfinite(s).all() and len(s) >= 10:
            hashes.setdefault(hashlib.md5(np.round(s, 4).tobytes()).hexdigest(), []).append(e)
            s_std[e] = s.std(axis=0)
            if a is not None and a.shape == s.shape and np.isfinite(a).all():
                a_std[e] = a.std(axis=0)

    for eps in hashes.values():
        if len(eps) > 1:
            for e in eps:
                res[e].append(("duplicate_episode",
                               f"motion identical to episode(s) {[x for x in eps if x != e][:5]}", True))

    if s_std:
        med_s = np.median(np.stack(list(s_std.values())), axis=0)
        med_a = np.median(np.stack(list(a_std.values())), axis=0) if a_std else None
        for e, sd in s_std.items():
            if (sd < 1e-6).all():
                res[e].append(("no_motion", "robot never moves: every joint is constant for the whole episode", True))
                continue
            if len(s_std) < 5 or e not in a_std or med_a is None:
                continue
            ad = a_std[e]
            # Dead = sensor reading frozen WHILE the robot was commanded to move that joint.
            # A joint that is simply not used (idle arm, unused wrist) has a constant command too -> not flagged.
            dead = [j for j in range(len(sd))
                    if sd[j] < 1e-6 and med_s[j] > 1e-3 and ad[j] > max(1e-3, 0.1 * med_a[j])]
            if dead:
                jn = [str(names[j]) if names and j < len(names) else f"joint {j}" for j in dead]
                res[e].append(("dead_sensor",
                               f"{', '.join(jn)} reading never changes although the robot was commanded to move it", True))

    if root is not None and "episode_index" not in info.get("video_path", ""):
        try:
            meta = _episodes_meta(root)
            lens = df.groupby("episode_index").size() / fps
            vcols = [c for c in meta.columns if c.startswith("videos/") and c.endswith("/from_timestamp")]
            for _, row in meta.iterrows():
                e = int(row.episode_index)
                if e not in res:
                    continue
                for c in vcols:
                    seg = float(row[c.replace("from_timestamp", "to_timestamp")] - row[c])
                    if abs(seg - lens[e]) > 1.0:
                        res[e].append(("length_mismatch",
                                       f"{c.split('/')[1]} video is {seg:.1f}s but motion is {lens[e]:.1f}s", True))
                        break
        except Exception:
            pass
    return res

def check_frames(frames, moving=True):
    """Checks on frames already grabbed for the vision layer. frames: list of (t, PIL image)."""
    out = []
    if not frames:
        return out
    arr = [np.asarray(im.convert("L").resize((160, 120)), dtype=float) for _, im in frames]
    dark = [t for (t, _), x in zip(frames, arr) if x.mean() < 12 or x.std() < 3]
    if dark:
        out.append(("black_frames", f"blank/black camera frame at {', '.join(f'{t:.1f}s' for t in dark[:3])}", True))
    if len(arr) >= 3 and moving:
        diffs = [np.abs(arr[i + 1] - arr[i]).mean() for i in range(len(arr) - 1)]
        if max(diffs) < 1.0:
            out.append(("frozen_video", f"camera image unchanged across the episode "
                                        f"(max frame difference {max(diffs):.2f}) while the arm moved", True))
    return out