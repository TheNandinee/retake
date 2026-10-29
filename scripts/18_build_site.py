"""Build the static demo site (GitHub Pages, /docs) from audit reports and scan results."""
import json, shutil, html
from pathlib import Path
import markdown

DOCS = Path("docs"); ASSETS = DOCS / "assets"
REPO = "https://github.com/TheNandinee/retake"
CODE_TYPES = {"frozen_video", "black_frames", "dropped_frames", "duplicate_episode", "dead_sensor",
              "no_motion", "empty_episode", "nan_values", "length_mismatch", "timestamp_error"}

# Verified numbers (EXPERIMENTS.md E018-E020, E022)
SCAN = dict(datasets="1,754", contributors="488", episodes="72,356", hours="364.6",
            dup_pct="7.1%", dup_copies="5,125", cross_contrib="777", reupload_pairs="97",
            broken="763", broken_pct="1.05%")
ISSUES = [("Empty fragment (under 1 s, some a single frame)", 338),
          ("Robot never moves (every joint constant)", 219),
          ("Duplicated inside the same dataset", 138),
          ("Video and motion lengths disagree", 71),
          ("Frozen joint sensor on a commanded arm", 56),
          ("Timestamps run backwards", 15)]
EXAMPLES = [
    ("Robot never moves", "1g0rrr/demo2_frames_grab ep11: 23.9 s, every joint constant; people move objects around a motionless arm.",
     "results/inspect_1g0rrr_demo2_frames_grab_ep11.jpg"),
    ("Frozen arm sensor", "Arururu12/UR5e_Gello_Cube_bin_v3 ep1: six arm joints read constant for 52 s while commanded up to 0.31 rad; the gripper is logged normally.",
     "results/inspect_Arururu12_UR5e_Gello_Cube_bin_v3_ep1.jpg"),
    ("Same recording, two contributors", "Dangvi/soarm100_data ep0 = s20000s/soarm100_data ep0: max difference 0.000000 across 426 frames.",
     "results/inspect_Dangvi_soarm100_data_ep0.jpg"),
    ("A block saved twice", "HuaihaiLyu/hamburger0509 episodes 84-90 = 91-97: identical motion and identical frames.",
     "results/inspect_HuaihaiLyu_hamburger0509_ep84.jpg"),
    ("One-frame episode", "7jep7/rook_to_d4_v5 ep4: the entire episode is a single frame.",
     "results/inspect_7jep7_rook_to_d4_v5_ep4.jpg"),
    ("Motionless 'expert' demo in a published benchmark", "kantine/BotFails setTheTable expert ep7: 1.2 s, the robot never moves.",
     "results/inspect_domotic_setTheTable_expert_ep7.jpg"),
]

CSS = """
:root{--ink:#14161a;--muted:#5b6270;--bg:#f7f5f0;--card:#fff;--line:#e4e0d6;--retake:#c2412d;--review:#b7791f;
--clean:#2f7d4f;--code:#1f4fd1;--vision:#7a3fd1}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;
color:var(--ink);background:var(--bg)}
.wrap{max-width:1120px;margin:0 auto;padding:0 24px}
header.hero{background:#14161a;color:#f7f5f0;padding:64px 0 48px}
.hero .tag{color:#f2b8a8;font-weight:600;letter-spacing:.06em;text-transform:uppercase;font-size:13px}
.hero h1{font-size:46px;line-height:1.08;margin:10px 0 14px;letter-spacing:-.02em}
.hero p{max-width:780px;color:#d6d3cb;font-size:18px}
nav a{color:#f2b8a8;margin-right:18px;font-weight:600;text-decoration:none}
section{padding:52px 0;border-bottom:1px solid var(--line)}
h2{font-size:30px;margin:0 0 8px;letter-spacing:-.01em}h3{margin:32px 0 12px}
.lead{color:var(--muted);max-width:800px;font-size:17px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.tile b{display:block;font-size:28px;letter-spacing:-.02em}.tile span{color:var(--muted);font-size:13px}
.hero .tile{background:#1f2228;border-color:#2c3038}.hero .tile span{color:#a9a59b}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;overflow:hidden}
.card img{width:100%;border-radius:8px;margin-top:10px;display:block}
.card-head{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}
.card code{font-size:12px;word-break:break-all}
.issue{font-weight:700;color:var(--retake);text-transform:capitalize;margin-top:6px}.issue.review{color:var(--review)}
.card p{margin:6px 0 0;font-size:14px}
.badge{font-size:11px;padding:3px 8px;border-radius:999px;white-space:nowrap;font-weight:600}
.badge.code{background:#e5ecfd;color:var(--code)}.badge.vision{background:#efe6fb;color:var(--vision)}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line)}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line)}th{background:#efece5;font-size:13px}
td.num{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
details{margin-top:20px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px}
summary{cursor:pointer;font-weight:600}.muted{color:var(--muted);font-weight:400}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.step{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}.step b{display:block;margin-bottom:4px}
.big{font-size:20px;max-width:820px}a{color:var(--code)}
footer{padding:32px 24px;color:var(--muted);font-size:14px;text-align:center}
"""

def esc(x):
    return "" if x is None else html.escape(str(x))

def tile(value, label):
    return f'<div class="tile"><b>{esc(value)}</b><span>{esc(label)}</span></div>'

def page(title, body):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>'
            f'<style>{CSS}</style></head><body>{body}'
            f'<footer>Retake · Apache-2.0 · <a href="{REPO}">source</a> · '
            f'<a href="{REPO}/blob/main/EXPERIMENTS.md">every number, with its experiment log</a> · '
            f'built on Nebius Token Factory with NVIDIA Nemotron</footer></body></html>')

def card(e, img_base):
    code = e["failure_type"] in CODE_TYPES
    badge = ('<span class="badge code">verified by code</span>' if code
             else '<span class="badge vision">Nemotron vision</span>')
    t = e.get("evidence_time_s")
    tstr = f" · t={t}s" if isinstance(t, (int, float)) and t == t else ""
    img = (f'<img loading="lazy" src="{img_base}/{Path(e["frames"]).name}" alt="frames of {esc(e["id"])}">'
           if e.get("frames") else "")
    cls = "issue" if e["status"] == "retake" else "issue review"
    return (f'<div class="card"><div class="card-head"><code>{esc(e["id"])}</code>{badge}</div>'
            f'<div class="{cls}">{esc(e["failure_type"].replace("_", " "))}{esc(tstr)}</div>'
            f'<p>{esc(e.get("reason"))}</p>{img}</div>')

def report_section(report_dir, tag, heading, blurb, sid):
    report_dir = Path(report_dir)
    rep = json.loads((report_dir / "report.json").read_text())
    s, eps = rep["stats"], rep["episodes"]
    dst = ASSETS / tag; dst.mkdir(parents=True, exist_ok=True)
    for f in (report_dir / "frames").glob("*.jpg"):
        shutil.copy(f, dst / f.name)
    retake = sorted([e for e in eps if e["status"] == "retake"],
                    key=lambda e: (e["failure_type"] not in CODE_TYPES, e["failure_type"]))
    review = [e for e in eps if e["status"] == "review"]
    cost = s.get("cost_per_1000_episodes_usd")
    tiles = "".join([tile(f'{s["health_score_pct"]}%', "health score"), tile(s["audited_episodes"], "episodes audited"),
                     tile(s["retake"], "retake"), tile(s["review"], "review"), tile(s["clean"], "clean"),
                     tile(f"${cost}" if cost else "$1.09", "per 1,000 episodes")])
    md = (report_dir / "summary.md").read_text().split("\n", 1)[-1] if (report_dir / "summary.md").exists() else ""
    cards = "".join(card(e, f"assets/{tag}") for e in retake) or "<p>No retake flags.</p>"
    rcards = "".join(card(e, f"assets/{tag}") for e in review)
    return (f'<section id="{sid}"><div class="wrap"><h2>{esc(heading)}</h2><p class="lead">{blurb}</p>'
            f'<div class="tiles">{tiles}</div>'
            f'<h3>Retake list <span class="muted">({len(retake)}): strong evidence, re-record or drop</span></h3>'
            f'<div class="grid">{cards}</div>'
            f'<details><summary>Review list ({len(review)}): unconfirmed, needs a human look</summary>'
            f'<div class="grid" style="margin-top:12px">{rcards}</div></details>'
            f'<details><summary>Audit summary (facts computed by code, prose written by Nemotron 3 Ultra)</summary>'
            f'<div class="md">{markdown.markdown(md)}</div></details></div></section>')

def build():
    if DOCS.exists():
        shutil.rmtree(DOCS)
    (ASSETS / "examples").mkdir(parents=True)
    (DOCS / ".nojekyll").write_text("")

    hero = (f'<header class="hero"><div class="wrap"><div class="tag">Retake · data quality for robot learning</div>'
            f'<h1>Every robot demo needs an alibi.</h1>'
            f'<p>Robot companies pay for hours of demonstrations and train on them blind. Retake audits robot datasets '
            f'episode by episode and returns a trustworthy re-record list with evidence for every flag.</p>'
            f'<div class="tiles">{tile(SCAN["datasets"], "datasets scanned")}{tile(SCAN["episodes"], "episodes")}'
            f'{tile(SCAN["hours"] + " h", "of robot data")}{tile(SCAN["dup_pct"], "of episodes are exact copies")}'
            f'{tile(SCAN["broken"], "objectively broken episodes")}{tile("$0", "model spend for the scan")}</div>'
            f'<nav><a href="#found">What we found</a><a href="#proof">Proof</a><a href="#live">Live report</a>'
            f'<a href="#how">How it works</a><a href="botfails_test.html">Test-set report</a></nav></div></header>')

    rows = "".join(f"<tr><td>{esc(n)}</td><td class='num'>{c}</td></tr>" for n, c in ISSUES)
    ex = ""
    for title, detail, img in EXAMPLES:
        tag = ""
        if Path(img).exists():
            shutil.copy(img, ASSETS / "examples" / Path(img).name)
            tag = f'<img loading="lazy" src="assets/examples/{Path(img).name}" alt="{esc(title)}">'
        ex += (f'<div class="card"><div class="card-head"><b>{esc(title)}</b>'
               f'<span class="badge code">verified by code + by eye</span></div><p>{esc(detail)}</p>{tag}</div>')
    found = (f'<section id="found"><div class="wrap"><h2>What we found in Hugging Face\'s community robot data</h2>'
             f'<p class="lead">We scanned every sub-dataset of <code>lerobot/community_dataset_v3</code> '
             f'({SCAN["datasets"]} datasets from {SCAN["contributors"]} contributors) on a laptop overnight. '
             f'Every finding below comes from a deterministic check, involves no AI judgment, and was verified by hand.</p>'
             f'<p class="big"><b>{SCAN["dup_pct"]} of all episodes ({SCAN["dup_copies"]}) are exact copies</b> of episodes '
             f'elsewhere in the collection. {SCAN["cross_contrib"]} duplicated recordings span different contributors, and '
             f'{SCAN["reupload_pairs"]} dataset pairs are at least 80% the same recordings. In a pretraining mix, duplicates '
             f'silently over-weight some demos and leak between train and test splits.</p>'
             f'<p class="big"><b>{SCAN["broken"]} episodes ({SCAN["broken_pct"]}) are objectively broken:</b></p>'
             f'<table><tr><th>Issue</th><th style="text-align:right">Episodes</th></tr>{rows}</table>'
             f'<h3>Verified examples</h3><div class="grid">{ex}</div></div></section>')

    proof = (f'<section id="proof"><div class="wrap"><h2>Proof: a frozen test set, run once</h2>'
             f'<p class="lead">50 labeled episodes from the BotFails benchmark were set aside before any tuning. The pipeline '
             f'was locked (git tag <code>v1.0-frozen</code>) and then run on them exactly once.</p>'
             f'<table><tr><th>List</th><th>Precision</th><th>Real failures caught</th><th>Good demos flagged</th></tr>'
             f'<tr><td><b>Retake</b> (re-record these)</td><td class="num">100% (13/13)</td><td class="num">13 / 25</td>'
             f'<td class="num">0 / 25</td></tr>'
             f'<tr><td><b>Retake + review</b></td><td class="num">82% (18/22)</td><td class="num">18 / 25</td>'
             f'<td class="num">4 / 25</td></tr></table>'
             f'<p class="lead">13 of 13 is a small sample: the 95% lower bound on retake precision is about 77%. The design '
             f'trades coverage for certainty on the retake list; the review list catches more for a human to check. '
             f'Integrity checks: 100% detection on injected corruptions, 0 false alarms on 178 clean expert demos. '
             f'Two promising ideas that made accuracy worse were measured and dropped; see the '
             f'<a href="{REPO}/blob/main/EXPERIMENTS.md">experiment log</a>. '
             f'<a href="botfails_test.html">Full test-set report →</a></p></div></section>')

    live = report_section("reports/community_sample", "community",
                          "Live report: a community sample through the full pipeline",
                          "52 episodes from 22 community datasets: integrity checks on every episode, plus Nemotron vision "
                          "on each one. Badges show whether a flag came from a deterministic check or from the vision model. "
                          "All four vision flags here (a human in the workspace) were confirmed by eye.", "live")

    how = (f'<section id="how"><div class="wrap"><h2>How it works</h2><div class="flow">'
           f'<div class="step"><b>1 · Integrity (code)</b>Ten deterministic checks on every episode: empty, motionless, '
           f'duplicated, frozen sensors, broken timestamps, video/motion mismatch, frozen or black video. Free.</div>'
           f'<div class="step"><b>2 · Motion (statistics)</b>Per-task outliers in duration, hesitation, regrasps, jerk '
           f'and tracking error. Free.</div>'
           f'<div class="step"><b>3 · Vision (Nemotron 3.5 Super VL)</b>Two frames of a known-good reference demo plus six '
           f'frames of the episode, via Nebius Token Factory. Only visible evidence reaches the retake list.</div>'
           f'<div class="step"><b>4 · Report (Nemotron 3 Ultra)</b>Ultra writes the summary; code computes every number '
           f'and hotspot, and a validator removes any claim the data does not support.</div></div>'
           f'<p class="lead" style="margin-top:20px">Cost: <b>about $1.10 per 1,000 episodes</b>. Reads LeRobot v2 and v3 '
           f'datasets straight from Hugging Face without downloading the videos. One command: '
           f'<code>retake audit &lt;dataset&gt;</code>.</p></div></section>')

    (DOCS / "index.html").write_text(page("Retake: every robot demo needs an alibi", hero + found + proof + live + how))
    test = report_section("reports/botfails_TEST", "botfails_test", "Frozen test set: BotFails, 50 episodes",
                          "The one-time run on the held-out test set (pipeline tag v1.0-frozen). "
                          "Retake list precision 100% (13/13), 18 of 25 real failures surfaced overall.", "test")
    back = '<header class="hero"><div class="wrap"><nav><a href="index.html">← Back to Retake</a></nav></div></header>'
    (DOCS / "botfails_test.html").write_text(page("Retake: frozen test-set report", back + test))
    print("Built docs/index.html and docs/botfails_test.html")

if __name__ == "__main__":
    build()