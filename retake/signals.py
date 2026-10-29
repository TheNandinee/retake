import numpy as np
from retake.common import to_mat

def gripper_indices(info):
    names = info["features"]["observation.state"].get("names")
    if isinstance(names, dict): names = list(names.values())[0]
    if names and isinstance(names[0], list): names = names[0]
    idx = [i for i, n in enumerate(names or []) if "gripper" in str(n).lower()]
    return idx or [-1]

def _gripper_closes(g):
    g = (g - g.min()) / (np.ptp(g) + 1e-9)
    closes, is_open = 0, g[0] > 0.5
    for x in g:
        if is_open and x < 0.3: is_open = False
        elif not is_open and x > 0.7: is_open = True; closes += 1
    return closes

def episode_signals(ep, fps, grip_idx):
    ep = ep.sort_values("frame_index")
    if len(ep) < 3:
        return {"duration_s": len(ep) / fps, "idle_ratio": 1.0, "longest_idle_s": 0.0,
                "grip_closes": 0, "jerk": 0.0, "track_err": 0.0}
    s = to_mat(ep["observation.state"])
    a = to_mat(ep["action"]) if "action" in ep else s
    gi = [i % s.shape[1] for i in grip_idx]
    joints = np.delete(s, gi, axis=1)

    vel = np.diff(joints, axis=0) * fps
    speed = np.linalg.norm(vel, axis=1)
    idle = speed < 0.1 * (np.percentile(speed, 90) + 1e-9)
    longest = run = 0
    for x in idle:
        run = run + 1 if x else 0
        longest = max(longest, run)

    jerk = np.linalg.norm(np.diff(vel, n=2, axis=0), axis=1).mean() if len(vel) > 3 else 0.0
    return {
        "duration_s":     len(s) / fps,
        "idle_ratio":     float(idle.mean()),
        "longest_idle_s": longest / fps,
        "grip_closes":    sum(_gripper_closes(s[:, i]) for i in gi),
        "jerk":           float(jerk),
        "track_err":      float(np.abs(a - s).mean()),
    }

def gripper_events(ep, fps, grip_idx):
    """Times (s) when any gripper closes (grasp) or opens (release)."""
    ep = ep.sort_values("frame_index")
    s = to_mat(ep["observation.state"])
    events = []
    for i in grip_idx:
        g = s[:, i % s.shape[1]]
        g = (g - g.min()) / (np.ptp(g) + 1e-9)
        is_open = g[0] > 0.5
        for k, x in enumerate(g):
            if is_open and x < 0.3: is_open = False; events.append(k / fps)
            elif not is_open and x > 0.7: is_open = True; events.append(k / fps)
    return sorted(events)