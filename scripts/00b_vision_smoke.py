import os, io, base64, time
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw

load_dotenv(override=True)
client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1/",
                api_key=os.environ["NEBIUS_API_KEY"])
MODEL = os.environ["VISION_MODEL"]

def make_img(label, color):
    im = Image.new("RGB", (320, 240), "white")
    d = ImageDraw.Draw(im)
    d.ellipse([100, 60, 220, 180], fill=color)
    d.text((10, 10), label, fill="black")
    return im

def b64(im):
    buf = io.BytesIO(); im.save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

colors = ["red", "blue", "green", "orange", "purple", "black", "pink", "gray"]
content = [{"type": "text", "text": "8 frames follow. Reply with ONLY a JSON list of the circle colors in order."}]
for i, c in enumerate(colors):
    content.append({"type": "text", "text": f"Frame {i+1} (t={i*0.5:.1f}s):"})
    content.append({"type": "image_url", "image_url": {"url": b64(make_img(f"t={i*0.5:.1f}s", c))}})
msgs = [{"role": "user", "content": content}]

variants = {
    "A: reasoning ON, big budget": dict(),
    "B: enable_thinking=False": dict(extra_body={"chat_template_kwargs": {"enable_thinking": False}}),
    "C: /no_think system prompt": dict(system="/no_think"),
}

for name, opt in variants.items():
    m = ([{"role": "system", "content": opt.pop("system")}] if "system" in opt else []) + msgs
    t0 = time.time()
    try:
        r = client.chat.completions.create(model=MODEL, messages=m, max_tokens=2000, **opt)
        msg = r.choices[0].message
        reasoning = getattr(msg, "reasoning_content", None) or ""
        print(f"\n=== {name}  ({time.time()-t0:.1f}s)")
        print("answer:", msg.content)
        print("reasoning tokens:", r.usage.completion_tokens_details.reasoning_tokens,
              "| total out:", r.usage.completion_tokens, "| in:", r.usage.prompt_tokens)
        if reasoning: print("reasoning preview:", reasoning[:200].replace("\n", " "))
    except Exception as e:
        print(f"\n=== {name} FAILED:", str(e)[:200])