"""Fix guidance: Tavily finds public sources at audit time, Nemotron 3 Ultra summarizes ONLY what they
support, and code keeps a point only if its verbatim supporting quote is found in the cited source."""
import os, re, json, hashlib
from pathlib import Path
from tavily import TavilyClient
from retake.llm import chat

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b")
CACHE = Path("results/tavily_cache"); CACHE.mkdir(parents=True, exist_ok=True)
TAVILY_CALLS = {"fresh": 0, "cached": 0}
LEROBOT_DOMAINS = ["github.com", "huggingface.co", "docs.phospho.ai", "deepwiki.com"]
SRC_CHARS = 1500
# For LeRobot issue types, only official / maintained LeRobot sources may back a point.
OFFICIAL = ("https://github.com/huggingface/lerobot", "https://huggingface.co/docs/lerobot",
            "https://docs.phospho.ai", "https://deepwiki.com/huggingface/lerobot")

# issue type -> (plain-English definition, search query, restrict to LeRobot-ecosystem domains?)
ISSUES = {
    "timestamp_error":   ("timestamps go backwards or repeat inside an episode",
                          "LeRobot dataset timestamps not monotonically increasing error", True),
    "length_mismatch":   ("the episode video is a different length than the recorded motion data",
                          "LeRobot dataset video frames do not match number of episode frames", True),
    "empty_episode":     ("the episode is under one second long, sometimes a single frame",
                          "LeRobot record empty or very short episode saved re-record", True),
    "no_motion":         ("the robot never moves during a recorded teleoperation episode",
                          "LeRobot record teleoperation follower arm does not move during recording", True),
    "dead_sensor":       ("one joint's recorded position stays constant while the commanded action for that joint changes",
                          "LeRobot {robot} observation.state joint position not updating while action changes", True),
    "duplicate_episode": ("an episode's motion data is identical to another episode's",
                          "LeRobot dataset duplicate episodes after merging or re-uploading", True),
    "frozen_video":      ("the camera image stops changing while the arm moves",
                          "LeRobot record camera frames frozen", True),
    "black_frames":      ("camera frames are black or blank",
                          "LeRobot record camera black frames", True),
    "human_intervention": ("an operator's hand is visible in the robot's workspace during a teleoperated demonstration",
                           "robot teleoperation data collection operator hands visible in camera frame imitation learning dataset quality", False),
}
FIXABLE = set(ISSUES)

# The cited source itself must describe the symptom (all patterns must match its text).
SYMPTOMS = {
    "timestamp_error":   [r"timestamp|\bpts\b|\bdts\b"],
    "length_mismatch":   [r"tolerance|drift|\bpts\b|mismatch|out of sync|number of frames"],
    "empty_episode":     [r"empty episode|short episode|0 frames|zero frames|re ?record|no frames"],
    "no_motion":         [r"not mov|does not move|doesn t move|set to zero|zero action|no motion|not respond"],
    "dead_sensor":       [r"state|position|joint|encoder|reading",
                          r"stuck|frozen|not updat|constant|same value|does not change|doesn t change|not chang"],
    "duplicate_episode": [r"duplicat|overwrit"],
    "frozen_video":      [r"frozen|freez|stuck|same frame"],
    "black_frames":      [r"black|blank|empty frame"],
    "human_intervention": [r"hand|operator|human"],
}

PROMPT = """You help a robotics team fix a data-quality problem found in a LeRobot robot-demonstration dataset.

Problem: {definition}
Robot type: {robot}
Examples found by deterministic checks: {examples}

SOURCES (from a web search; each truncated):
{sources}

Using ONLY sources that discuss this same problem in LeRobot or in robot-demonstration recording,
answer with JSON:
{{"causes": [{{"text": "...", "source": 1, "quote": "..."}}], "fixes": [{{"text": "...", "source": 2, "quote": "..."}}]}}

Rules:
- At most 2 causes and 2 fixes, each "text" under 25 words.
- "quote" must be 6 to 30 words copied EXACTLY, word for word, from the cited source text above.
- Ignore sources about a different robot software stack or a different problem.
- If no source genuinely supports a cause or fix, return empty lists. Returning nothing is better than stretching.
- Do not invent facts, versions, commands, or URLs."""

def _norm(s):
    return " ".join(re.sub(r"[^\w]+", " ", str(s).lower()).split())

def _search(query, restrict):
    key = hashlib.sha256(f"{query}|{restrict}".encode()).hexdigest()[:24]
    f = CACHE / f"{key}.json"
    if f.exists():
        TAVILY_CALLS["cached"] += 1
        return json.loads(f.read_text())
    if os.getenv("RETAKE_DRY_RUN", "0") == "1":
        print(f"[dry-run] would call Tavily: {query}")
        return {"results": []}
    kw = {"include_domains": LEROBOT_DOMAINS} if restrict else {}
    res = TavilyClient(api_key=os.environ["TAVILY_API_KEY"]).search(
        query=query, search_depth="advanced", max_results=5, **kw)
    TAVILY_CALLS["fresh"] += 1
    f.write_text(json.dumps(res))
    return res

def fix_guidance(issue, robot, examples):
    definition, q, restrict = ISSUES[issue]
    query = q.format(robot=robot or "SO-100")
    srcs = [r for r in _search(query, restrict).get("results", []) if r.get("url")][:5]
    texts = [(s.get("content") or "")[:SRC_CHARS] for s in srcs]
    base = {"issue": issue, "query": query, "restricted_to_lerobot_domains": restrict, "causes": [], "fixes": [],
            "sources": [{"n": i + 1, "title": s.get("title"), "url": s["url"]} for i, s in enumerate(srcs)]}
    if not srcs:
        return {**base, "note": "no public sources found", "removed_unsupported": 0}
    src_txt = "\n\n".join(f"[{i + 1}] {s.get('title', '')} ({s['url']})\n{texts[i]}" for i, s in enumerate(srcs))
    out = chat(JUDGE_MODEL, [{"role": "user", "content": PROMPT.format(
        definition=definition, robot=robot or "unknown", examples="; ".join(examples) or "n/a", sources=src_txt)}],
        max_tokens=1500, think=False, tag=f"fixes-v2:{issue}")
    m = re.search(r"\{.*\}", out or "", re.S)
    try:
        data = json.loads(m.group()) if m else {}
    except json.JSONDecodeError:
        data = {}

    def validate(items):
        keep = []
        for it in (items or [])[:2]:
            try:
                n = int(it.get("source"))
            except (TypeError, ValueError):
                continue
            quote = str(it.get("quote", "")).strip()
            text = re.sub(r"https?://\S+", "", str(it.get("text", ""))).strip()
            if not (1 <= n <= len(srcs)) or not text or len(quote.split()) < 6:
                continue
            if _norm(quote) not in _norm(texts[n - 1]):      # the quote must really be in the cited source
                continue
            if not all(re.search(pat, _norm(texts[n - 1])) for pat in SYMPTOMS.get(issue, [])):
                continue                                      # the cited source must describe this symptom
            if restrict and not srcs[n - 1]["url"].startswith(OFFICIAL):
                continue                                      # LeRobot issues: official sources only
            keep.append({"text": text, "source": n, "quote": quote})
        return keep

    causes, fixes = validate(data.get("causes")), validate(data.get("fixes"))
    proposed = len((data.get("causes") or [])[:2]) + len((data.get("fixes") or [])[:2])
    return {**base, "causes": causes, "fixes": fixes, "removed_unsupported": proposed - len(causes) - len(fixes)}

def fixes_md(guide):
    lines = ["## How to fix it",
             "_Public sources found at audit time by **Tavily**, summarized by **Nemotron 3 Ultra**. "
             "Every point carries a verbatim quote that code verified exists in the cited source; "
             "anything unsupported was removed. Treat these as leads._", ""]
    for t, g in guide.items():
        lines.append(f"### {t.replace('_', ' ')}")
        url = {s["n"]: s["url"] for s in g["sources"]}
        if not g["causes"] and not g["fixes"]:
            lines += ["- No public source with verifiable guidance was found.", ""]
            continue
        for label, items in [("Likely cause", g["causes"]), ("Fix", g["fixes"])]:
            for it in items:
                lines.append(f"- **{label}:** {it['text']} [[{it['source']}]]({url[it['source']]})  \n"
                             f"  > \"{it['quote']}\"")
        lines.append("")
    return "\n".join(lines)