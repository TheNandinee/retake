import os, re, json
from retake.common import grab_frame
from retake.llm import chat, img_url

VISION_MODEL = os.environ.get("VISION_MODEL", "nvidia/Nemotron-3.5-Super-VL")
SIZE = (448, 336)
EPISODE_FRACS = (0.02, 0.2, 0.4, 0.6, 0.8, 0.98)

PROMPT_V2 = """You are a strict quality auditor for robot demonstration data. A demo is GOOD only if it is safe to train a robot on it.

TASK: "{task}"

Images come in this order:
- REFERENCE (2 images): the START and END of a known-correct demo of this same task, same camera.
  Use them to learn the correct final arrangement, and which side is left/right in this camera view.
- EPISODE (6 images): the demo under review, in time order with timestamps. First = start, last = end.

Flag an anomaly if ANY of these is visible in the EPISODE:
1. Final state differs from the REFERENCE end: object missing, wrong container/side/orientation, task unfinished
2. Dropped, knocked-over, or spilled object; liquid or powder outside its container
3. A human hand or body part inside the workspace while the robot works
4. Wrong object used, or right object used in the wrong place
5. Scene not clean at the start (leftover spill or clutter from a previous take)
Do NOT flag normal variation in speed, path, or exact position when the end result matches the REFERENCE.

Describe first, then decide. Answer ONLY with JSON:
{{"episode_start_state": "one sentence about the first EPISODE image",
  "episode_end_state": "one sentence about the last EPISODE image",
  "matches_reference_end": true|false,
  "human_in_workspace": true|false,
  "anomaly": true|false,
  "failure_type": "none|incomplete|wrong_placement|dropped_object|spill|human_intervention|wrong_object|dirty_scene|collision|other",
  "evidence_time_s": number|null,
  "confidence": 0.0-1.0,
  "reason": "one short sentence"}}"""

PROMPT_V3 = """You are a strict quality auditor for robot demonstration data. A demo is GOOD only if it is safe to train a robot on it.

TASK: "{task}"

Images come in this order:
- REFERENCE (2 images): the START and END of a known-correct demo of this same task, same camera.
  Use them to learn the correct final arrangement, and which side is left/right in this camera view.
- EPISODE (6 images), in time order with timestamps: the first frame, then 4 frames taken just after the
  robot's gripper GRASPED or RELEASED something (the key interaction moments), then the last frame.

Flag an anomaly if ANY of these is visible in the EPISODE:
1. Final state differs from the REFERENCE end: object missing, wrong container/side/orientation, task unfinished
2. Dropped, knocked-over, or spilled object; liquid or powder outside its container
3. A human hand or body part inside the workspace while the robot works
4. Wrong object used, or the right object used on the wrong target (wrong hole, wrong button, wrong plug, wrong box)
5. Scene not clean at the start (leftover spill or clutter from a previous take)

IMPORTANT: Some tasks leave no visible change at the end (pressing buttons, probing, measuring, opening then
closing a lid). For these, judge the MIDDLE frames: is the gripper interacting with the CORRECT target?
Never call a demo incomplete just because its start and end look alike - that is normal for such tasks.
Do NOT flag normal variation in speed, path, or exact position.

Severity: "minor" = cosmetic, does not change the outcome (e.g. a small drip off to the side);
"major" = wrong outcome or teaches wrong behavior; "critical" = safety issue (human in workspace, collision).

Describe first, then decide. Answer ONLY with JSON:
{{"episode_start_state": "one sentence about the first EPISODE image",
  "key_moments": "one sentence on what the gripper interacts with in the middle frames",
  "episode_end_state": "one sentence about the last EPISODE image",
  "human_in_workspace": true|false,
  "anomaly": true|false,
  "severity": "none|minor|major|critical",
  "failure_type": "none|incomplete|wrong_placement|wrong_target|dropped_object|spill|human_intervention|wrong_object|dirty_scene|collision|other",
  "evidence_time_s": number|null,
  "confidence": 0.0-1.0,
  "reason": "one short sentence"}}"""

def _img(content, label, im):
    content += [{"type": "text", "text": label},
                {"type": "image_url", "image_url": {"url": img_url(im.resize(SIZE))}}]

def audit_episode(video, duration, task, ref_video, ref_duration, tag="", prompt=None, times=None):
    prompt = prompt or PROMPT_V2
    times = times or [duration * f for f in EPISODE_FRACS]
    content = [{"type": "text", "text": prompt.format(task=task)}]
    for label, t in [("REFERENCE start:", 0.02 * ref_duration), ("REFERENCE end:", 0.98 * ref_duration)]:
        im = grab_frame(ref_video, t)
        if im is not None: _img(content, label, im)
    frames = []
    for t in times:
        im = grab_frame(video, t)
        if im is None: continue
        frames.append((t, im))
        _img(content, f"EPISODE t={t:.1f}s:", im)

    ans = chat(VISION_MODEL, [{"role": "user", "content": content}], max_tokens=600, think=False, tag=tag)
    m = re.search(r"\{.*\}", ans or "", re.S)
    try:
        v = json.loads(m.group()) if m else {"raw": ans}
    except json.JSONDecodeError:
        v = {"raw": ans}
    v["_frames"] = frames
    return v