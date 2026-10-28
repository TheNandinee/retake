import os, io, json, time, base64, hashlib
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

# $ per token (input, output), from Token Factory /v1/models?verbose=true
PRICES = {
    "nvidia/Nemotron-3_5-Lightning":         (0.06e-6, 0.24e-6),
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": (0.06e-6, 0.24e-6),
    "nvidia/Nemotron-3.5-Super-VL":          (0.30e-6, 0.90e-6),
    "nvidia/nemotron-3-super-120b-a12b":     (0.30e-6, 0.90e-6),
    "nvidia/Nemotron-3-Ultra-550b-a55b":     (1.00e-6, 3.00e-6),
}
BUDGET = float(os.getenv("RETAKE_BUDGET_USD", "3.0"))
DRY_RUN = os.getenv("RETAKE_DRY_RUN", "0") == "1"
CACHE = Path("results/llm_cache"); CACHE.mkdir(parents=True, exist_ok=True)
LEDGER = Path("results/ledger.jsonl")

client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1/",
                api_key=os.environ["NEBIUS_API_KEY"])

def spent():
    if not LEDGER.exists(): return 0.0
    return sum(json.loads(l)["cost"] for l in LEDGER.read_text().splitlines() if l.strip())

def img_url(pil_image, quality=80):
    buf = io.BytesIO(); pil_image.save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def chat(model, messages, max_tokens=600, think=False, tag=""):
    """Cached, budget-guarded, cost-logged model call. Returns the text answer."""
    key = hashlib.sha256(json.dumps([model, messages, max_tokens, think],
                                    sort_keys=True).encode()).hexdigest()
    cached = CACHE / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text())["content"]

    if DRY_RUN:
        print(f"[dry-run] would call {model} ({tag})")
        return None
    if spent() >= BUDGET:
        raise RuntimeError(f"Budget cap ${BUDGET:.2f} reached. Raise RETAKE_BUDGET_USD in .env to continue.")

    t0 = time.time()
    r = client.chat.completions.create(
        model=model, messages=messages, max_tokens=max_tokens,
        extra_body={"chat_template_kwargs": {"enable_thinking": think}})
    u = r.usage
    p_in, p_out = PRICES.get(model, (1e-6, 3e-6))
    cost = u.prompt_tokens * p_in + u.completion_tokens * p_out
    content = r.choices[0].message.content

    cached.write_text(json.dumps({"model": model, "content": content}))
    with LEDGER.open("a") as f:
        f.write(json.dumps({"ts": time.time(), "model": model, "tag": tag,
                            "in": u.prompt_tokens, "out": u.completion_tokens,
                            "cost": round(cost, 8), "secs": round(time.time() - t0, 2)}) + "\n")
    return content