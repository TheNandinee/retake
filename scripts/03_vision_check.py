import os, sys, json, re, base64, io
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from retake.common import DATA, find_roots, load_info, load_frames, video_for_episode, frame_grid

load_dotenv()
client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1/", api_key=os.environ["NEBIUS_API_KEY"])
MODEL = os.environ["VISION_MODEL"]

PROMPT = """You are auditing a robot demonstration for a training dataset.
Task instruction: "{task}"
The image is a 3x3 grid of frames in time order (left-to-right, top-to-bottom), each stamped with its time.
Answer ONLY with JSON:
{{"task_completed": true|false, "matches_instruction": true|false,
  "failure_type": "none|missed_grasp|dropped_object|regrasp|wrong_object|incomplete|collision|other",
  "evidence_time_s": number|null, "confidence": 0-1, "reason": "one sentence"}}"""

def ask(grid, task):
    buf = io.BytesIO(); grid.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=400, messages=[{
        "role": "user", "content": [
            {"type": "text", "text": PROMPT.format(task=task)},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}])
    txt = r.choices[0].message.content
    m = re.search(r"\{.*\}", txt, re.S)
    return json.loads(m.group()) if m else {"raw": txt}

repo, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10
sig = pd.read_csv("results/signals.csv")
sample = pd.concat([sig[sig.fail == 1].sample(n, random_state=0), sig[sig.fail == 0].sample(n, random_state=0)])
path = DATA / repo.replace("/", "__")
out = []
for _, row in sample.iterrows():
    root = path / row.dataset; info = load_info(root)
    cam = next(k for k in info["features"] if k.startswith("observation.images."))
    video, off = video_for_episode(root, info, int(row.episode_index), cam)
    times = [row.duration_s * i / 8 for i in range(9)]
    grid = frame_grid(video, off, times)
    grid.save(f"results/grid_{row.dataset.replace('/', '_')}_{int(row.episode_index)}.jpg")
    task = "complete the manipulation task"  # TODO: map task_index -> text from meta/tasks
    v = ask(grid, task); v.update(episode=int(row.episode_index), fail=int(row.fail))
    out.append(v); print(v)

res = pd.DataFrame(out)
res.to_csv("results/vision_check.csv", index=False)
if "task_completed" in res:
    acc = ((res.task_completed == False) == (res.fail == 1)).mean()
    print(f"\nVision accuracy on {len(res)} episodes: {acc:.0%}")