# Retake — Experiment Log

Every result below is reproducible from the scripts in this repo.
Raw outputs: `evidence/logs/` · Result files: `evidence/snapshots/`

---

## E000 — Token Factory vision model check · 2026-10-28
- Model: `nvidia/Nemotron-3.5-Super-VL` via Nebius Token Factory
- Limit: max 8 images per request
- 8-frame color test: correct in all 3 configurations
- `enable_thinking=False`: 0.9s, 27 output tokens, 0 reasoning tokens
- Reasoning on: 2.4s, ~247 output tokens, same answer
- **Decision:** thinking off by default for vision; ~$0.0007 per 8-frame call

## E001 — Motion-signal baseline, BotFails · 2026-10-28
- Data: `kantine/BotFails`, 10 tasks, 323 episodes (145 anomaly-folder, 178 expert)
- Labels: folder name (`_anomaly` vs `_expert`). Superseded by true per-frame labels in a later entry.
- Six hand-built motion signals, z-scored within each task
- **Result: every signal at AUROC 0.46–0.53, i.e. coin-flip.** Max-|z| combo 0.598. Duration (per-task z) 0.343, so about 0.66 flipped.
- **Interpretation:** BotFails anomalies are visual/semantic; arm motion looks normal. Motion alone can't detect them → motivates the vision layer.
- Log: `evidence/logs/E001_botfails_motion_baseline.txt`

## E002 — Motion-signal baseline, ViFailback · 2026-10-28
- Data: `sii-rhos-ai/vifailback-dataset-lerobot`, first 1,000 episodes (848 failure, 152 success)
- Labels: `is_failure_episode` flag
- **Result (flipped where < 0.5):** duration (per-task z) 0.905 · idle_ratio 0.691 · grip_closes 0.69 · track_err 0.675 · jerk 0.65
- **Caveat:** the duration signal likely reflects how the dataset was built (failure episodes may be cut off at the failure point). Reported as an "incomplete demo" detector; later results are also reported without duration.
- Max-|z| combo 0.402: the combination method is flawed (mixes signal directions). Replaced by a learned model in E003.
- Log: `evidence/logs/E002_vifailback_motion_baseline.txt`

---
<!-- Next: E003 learned signal model (held-out tasks), E004 true BotFails labels, E005 vision on BotFails -->

## ⚠️ E005 INVALIDATED — label leakage · 2026-10-28
- Found on inspection: for anomaly-folder episodes, the "task" text sent to the model came from the dataset's anomaly-folder metadata, which **describes the recorded anomalies and their episode ranges** (e.g. "5:9 put items in the wrong box").
- The model was therefore primed on what to look for in anomaly episodes but not in expert episodes. **E005's 65% accuracy is invalid.**
- Fix: task text now always comes from the matching expert folder, plus a guard that aborts if label-like text reaches the prompt.
- Side benefit: those metadata notes document the anomaly type per episode range, so they become ground truth for grading failure-type classification, never shown to the model.

## E006 — Vision layer on BotFails, leak-free re-run · 2026-10-28
- Same 20 episodes and settings as E005, clean expert task text for all episodes
- Result: _fill in after run_
- Log: `evidence/logs/E006_botfails_vision_clean.txt`
- **Result: 60% accuracy, 6/10 anomalies caught, 4/10 false alarms.** This is the real, leak-free baseline.
- Episodes previously "caught" only via leaked notes are now missed (groceries ep5, dish ep7, dish ep12); in dish ep12 the model saw plates left on the table and still judged success.
- Total spend to date: $0.026
## E007 — Manual review of vision errors · 2026-10-28
Human review of the contact sheets from E006:
- setTheTable expert ep9, ep16: fork IS on the robot's left. **False alarm** caused by camera viewpoint (left/right mirrored).
- groceriesSorting expert ep17: items are in the correct boxes. **False alarm** (hallucination).
- pouringCoffee ep19 (documented by dataset authors as a "normal sample"): **a spill is visible.** Either a benchmark label error or a dirty scene left over from earlier spill takes. Both are real data-quality issues.
- soldering ep14: human hand visible in workspace. Model noticed it but didn't treat it as an anomaly → prompt gap.
- hatchAndProbe ep2: reviewer couldn't judge from 8 frames → needs final-state comparison against a reference.
**Conclusion:** most errors come from the model not knowing what "correct" looks like for each task → vision v2 adds reference frames from a known-good demo.
- **Follow-up on pouringCoffee ep19:** spill is NOT present at the start; it occurs during the episode, but is small, off to the side, and doesn't interfere with the task. → A genuine minor spill in an episode the dataset documents as normal. Not claimed as a label error: the authors evidently considered it acceptable.
- **Product implication:** detections need a severity level (minor / major / critical) so users can set their own tolerance. Planned for vision v3.

## E008 — Vision v2: reference-conditioned audit, dev set · 2026-10-28
- Each request: 2 frames (start/end) of a known-good expert demo of the same task (dev split only) + 6 episode frames (always includes first and last moments). Prompt adds human-in-workspace rule, viewpoint guidance via the reference, describe-then-decide output.
- **Same 20 as E006: 70% (was 60%), caught 6/10, false alarms 2/10 (was 4/10)**
- **20 new dev episodes: 75%, caught 7/10, false alarms 2/10**, so the improvement holds on unseen episodes (no overfitting to the E006 set)
- **All 40: 72%, caught 13/20, false alarms 4/20.** Cumulative spend $0.066
- Fixed: setTheTable left/right false alarms; human hand in soldering ep14 now caught as `human_intervention`; minor spill in pouring ep19 no longer flagged (consistent with dataset label)
- **Remaining error pattern:** tasks whose result isn't visible in the final frame (buttons, hatch/probe). End-state comparison misses mid-task errors (wrong hole, red plug) and wrongly flags correct demos ("start = end, so nothing happened").
- **Next (v3):** pick episode frames at gripper grasp/release moments from the motion data, so motion tells vision where to look. Add severity levels.
- Log: `evidence/logs/E008_vision_v2_reference_dev.txt`

## E009 — Vision v3: gripper-event keyframes + severity, dev set · 2026-10-28 · ❌ REGRESSION
- Changed two things at once (a methodology mistake): episode frames chosen just after gripper grasp/release events, AND a revised prompt (mid-task target checks, "start = end is normal", severity levels)
- **ALL-40: 55% (v2: 72%), caught 9/20 (v2: 13), false alarms 7/20 (v2: 4).** Worse on both.
- Buttons and hatch tasks (the target of the change) did not improve
- Likely cause: post-grasp frames are often occluded by the arm, and the evenly spaced coverage of the episode is lost. Not isolated, because two variables changed.
- **Decision: v2 remains the vision layer. Prompt tuning stops; remaining effort goes to the pipeline.** Severity output is still a good product idea; to be re-added later as a separate change, tested in isolation.
- Cumulative spend: $0.108
- Log: `evidence/logs/E009_vision_v3_keyframes_dev.txt`

## E010 — First end-to-end `retake audit` run · 2026-10-28
- `uv run python -m retake.audit kantine/BotFails --limit 40 --exclude <frozen test split>`, 40 dev episodes stratified across 10 tasks
- **Runtime 39s, model cost $0.047 → $1.17 per 1,000 episodes** (4 parallel vision calls + 1 Ultra summary)
- Verdicts vs labels: caught 8/12 failures, **12/28 false alarms** (worse than E008's 4/20)
- Diagnosis: 14 of 20 "retake" verdicts are `incomplete`, and at least 8 of those are expert demos. "Incomplete" means the model is judging that a result is *absent* from the last frame, which it does unreliably (also seen in E008 for buttons/hatch). Visible-evidence types (spill, wrong placement, human) look much more reliable.
- Possible extra factor: the reference demo is now chosen by "most typical motion" instead of lowest episode index (E008). Not isolated.
- **Summary (Ultra) problems:** built a "systematic collection failure" narrative on false alarms; invented a threshold ("makingCoffee > 30 s"); hit the 1,500-token limit so the Caveats section was cut off.
- **Key product insight:** the re-record list must be high-precision. Missing some failures is acceptable; telling a team to delete good data is not. → Optimize retake-list precision; route uncertain verdicts to "review".
- Log: `evidence/logs/E010_first_audit_run.txt` · Report: `evidence/snapshots/E010_report_BotFails/`

## E011 — Verdict-rule analysis on saved answers ($0) · 2026-10-28
- Re-scored the cached vision answers from E008 and E010 under 4 verdict rules
- **"Visible evidence only" (spill, wrong placement, human, dropped object, wrong object/target, collision) → retake:** E008 precision 100% (9/20 caught, 0 false alarms); E010 precision 50% (3/12, 3/28)
- "Incomplete" verdicts were right only 9 of 22 times across both runs → never enough on their own for the retake list
- Adding motion corroboration (short duration) or a confidence ≥ 0.9 filter changed nothing
- The E008/E010 gap points at the reference-selection change, tested in E012
- Log: `evidence/logs/E011_verdict_rules.txt`

## E012 — Audit with two-tier verdicts + "first" reference · 2026-10-28
- Same 40 dev episodes as E010 (same seed); only change from E011's rule: reference = lowest-index expert demo (E008 setting) instead of "most typical motion"
- **RETAKE list: precision 80% (4/5), caught 4/12, false alarms 1/28** (E010: 40%, 12 false alarms)
- **RETAKE + REVIEW: caught 10/12 real failures**, 9/28 false alarms, so the review list does its job of surfacing for humans
- Single-variable comparison with E011: reference choice moved precision 50% → 80%. "first" becomes the default.
- Health score 52.5% · cost $0.045 ($1.12 per 1,000 episodes) · 37s
- Caution: precision based on 5 retake verdicts; the defended number will come from the frozen test set
- Log: `evidence/logs/E012_audit_fixed.txt`

## E013 — Summary guardrails: code decides facts, LLM writes prose · 2026-10-28
- Problem (E012): Ultra ignored prompt rules, calling "review" flags a "systematic collection problem", citing a duplicate episode, mislabeling a motion-only flag as "false positive"
- Fix: (1) Hotspots computed in Python; a "possible recurring issue" requires 3+ retake episodes with the same visible issue in one task. (2) Validator scans Ultra's text for banned claims (systematic / procedural / protocol / delete / require) → one retry with offending lines quoted → remaining lines removed. (3) Unique episode ids. (4) Motion-only flags labeled `motion_only`.
- **Result: 0 rule violations after retry; verdicts unchanged (retake precision 80%, 4/12, 1/28).** Only recurring issue reported: pouringCoffee spill ×3 (visible evidence).
- Bug found: cost-per-1,000 reported as $0.10 on a fully cached run. Fixed: cache hits are counted, and no per-1,000 figure is reported unless the run was uncached. True figure: $1.12 per 1,000 episodes (E012).
- Log: `evidence/logs/E013_summary_guardrails.txt`

## E014 — LeRobot v3 support + remote frame access · 2026-10-28
- `lerobot/community_dataset_v3`: 488 contributor folders, all sub-datasets LeRobot **v3.0** (many episodes per video file), varied robots (so100, so101, sam_two) and camera names. Previous pipeline would have silently fallen back to motion-only.
- Added: targeted per-sub-dataset fetch (listing the whole repo hung for 30+ min), v3 episode offsets from `meta/episodes`, `tasks.parquet` support, per-path task groups (contributors reuse dataset names), third-person camera preference.
- **Offset verification (00ri/so100_battery, 50 episodes, 2 cameras): video segment length vs motion length max |diff| 0.00s; offsets monotonic.**
- First v3 audit: 10 episodes, 0 errors, all clean, $0.0106 ($1.06 per 1,000 episodes, consistent with BotFails' $1.12)
- BotFails regression check: identical verdicts (80% / 4/12 / 1/28)
- **Remote frame access:** ffmpeg reads frames directly from Hugging Face URLs via range requests: **~4–5 s per frame, no download** (vs 509 s to download one dataset's video). Makes a multi-dataset audit feasible.
- Logs: `evidence/logs/E014_*`
