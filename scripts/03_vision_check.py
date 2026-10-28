import os, json, re, sys
import pandas as pd
from huggingface_hub import hf_hub_download
from retake.common import DATA, load_info, grab_frame, contact_sheet
from retake.llm import chat, img_url

REPO, N = "kantine/BotFails", int(sys.argv[1]) if len(sys.argv) > 1 else 10
path = DATA / REPO.replace("/", "__")
MODEL = os.environ.get("VISION_MODEL", "nvidia/Nemotron-3.5-Super-VL")
CAM = "observation.images.logitech_1"
os.makedirs("results/frames", exist_ok=True)

sig = pd.read_csv("results/signals_BotFails.csv")
sample = pd.concat([sig[sig.fail == 1].sample(N, random_state=0),
                    sig[sig.fail == 0].sample(N, random_state=0)])


def task_text(root, task_index=0):
    """Always use the EXPERT folder's task description.
    Anomaly folders' task fields describe the anomalies (label leakage), so never send them."""
    expert_name = root.name.replace("_anomaly", "_expert")
    expert_root = path / "BotFails" / "normal_train" / expert_name
    p = expert_root / "meta" / "tasks.jsonl"
    if p.exists():
        return json.loads(p.read_text().splitlines()[0])["task"]
    return expert_name.replace("_expert", "").replace("_", " ")


PROMPT = """You are auditing a robot demonstration before it is used to train a robot.
Task: "{task}"
Below are 8 frames in time order, each labeled with its time in seconds.
Look for anything that goes wrong: dropped or knocked-over objects, missed grasps, wrong object,
collisions, spills, objects left in the wrong place, or the task not being completed.
Answer ONLY with JSON:
{{"anomaly": true|false, "task_completed": true|false,
  "failure_type": "none|dropped_object|missed_grasp|wrong_object|collision|spill|wrong_placement|incomplete|other",
  "evidence_time_s": number|null, "confidence": 0.0-1.0, "reason": "one short sentence"}}"""

out = []
for _, row in sample.iterrows():
    root = path / row.dataset
    info = load_info(root)
    ep = int(row.episode_index)
    rel = f"{row.dataset}/" + info["video_path"].format(
        episode_chunk=ep // info.get("chunks_size", 1000), video_key=CAM, episode_index=ep)
    video = hf_hub_download(REPO, rel, repo_type="dataset", local_dir=path)

    # identical frames + prompt as the first run, so every call is a free cache hit
    times = [row.duration_s * (i + 0.5) / 8 for i in range(8)]
    task = task_text(root, 0)
    if re.search(r"\d+\s*[:\-]\s*\d+|anomal|normal test|wrong", task, re.I):
        raise SystemExit(f"LEAK GUARD: task text looks like label notes -> {task!r}")
    content = [{"type": "text", "text": PROMPT.format(task=task)}]
    ims = []
    for t in times:
        im = grab_frame(video, t)
        if im is None: continue
        ims.append((t, im))
        content += [{"type": "text", "text": f"t={t:.1f}s"},
                    {"type": "image_url", "image_url": {"url": img_url(im.resize((448, 336)))}}]

    sheet_path = f"results/frames/{row.dataset.split('/')[-1]}_ep{ep}.jpg"
    contact_sheet(ims).save(sheet_path)

    ans = chat(MODEL, [{"role": "user", "content": content}], max_tokens=300, think=False,
               tag=f"vision:{row.dataset}:{ep}")
    m = re.search(r"\{.*\}", ans or "", re.S)
    v = json.loads(m.group()) if m else {"raw": ans}
    v.update(dataset=row.dataset, episode_index=ep, fail=int(row.fail), task=task, frames=sheet_path)
    out.append(v)
    print(f"[{'FAIL' if row.fail else 'GOOD'}] {row.dataset.split('/')[-1]} ep{ep}: "
          f"anomaly={v.get('anomaly')} type={v.get('failure_type')} conf={v.get('confidence')} | {v.get('reason')}")
    print(f"      task given to model: {task}")
    print(f"      frames: {sheet_path}")

res = pd.DataFrame(out)
res.to_csv("results/vision_check_BotFails.csv", index=False)
if "anomaly" in res:
    pred = res.anomaly.astype(str).str.lower().eq("true")
    acc = (pred == (res.fail == 1)).mean()
    tp = (pred & (res.fail == 1)).sum(); fp = (pred & (res.fail == 0)).sum()
    print(f"\nVision accuracy: {acc:.0%} | caught {tp}/{(res.fail == 1).sum()} failures | false alarms {fp}/{(res.fail == 0).sum()}")