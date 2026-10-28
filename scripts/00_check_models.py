import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1/",
                api_key=os.environ["NEBIUS_API_KEY"])

ids = sorted(m.id for m in client.models.list().data)
print(f"{len(ids)} models available\n")
for i in ids:
    tag = "  <-- NVIDIA" if "nemotron" in i.lower() or "nvidia" in i.lower() else ""
    print(i + tag)