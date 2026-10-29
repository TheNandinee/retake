import os
from retake.llm import chat

PLANNER_MODEL = os.environ.get("JUDGE_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b")

PROMPT = """You are helping an inspector judge robot demonstration videos.
Task description: "{task}"

Write a short checklist with exactly two parts.

REQUIRED (at most 3 lines): restate ONLY requirements that are explicitly written in the task description above.
Do NOT add objects, quantities, orientations, or completeness criteria that the description does not state.
If the description is vague, write fewer lines.

NOT A PROBLEM (at most 3 lines): normal variation an inspector should NOT flag for this kind of task, for example:
start and end frames looking alike when the result is not visible at the end, a different order of steps,
a different path or speed, objects in slightly different exact positions.

Return only the two parts."""

def make_checklist(task):
    out = chat(PLANNER_MODEL, [{"role": "user", "content": PROMPT.format(task=task)}],
               max_tokens=4000, think=True, tag=f"checklist-v2:{task[:40]}")
    if not out:
        return None
    lines = [l.strip() for l in out.strip().splitlines() if l.strip()][:9]
    return "\n".join(lines)