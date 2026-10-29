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

## E015 — Remote audit (no video download) · 2026-10-28
- `--remote`: ffmpeg reads frames from Hugging Face URLs; reference frames cached per task
- 1g0rrr/demo2_frame_holder (never downloaded before): **10 episodes in 66s at 8 workers, 2.4 MB on disk, $0.0112 ($1.12 per 1,000 episodes)**
- 8 clean, 2 review (incomplete), 0 retake
- Log: `evidence/logs/E015_remote_audit.txt`

## E016 — Integrity layer + corruption benchmark ($0) · 2026-10-28
- 9 deterministic checks: dropped_frames, timestamp_error, empty_episode, nan_values, dead_sensor, duplicate_episode, length_mismatch (motion data / v3 metadata), frozen_video, black_frames (from frames already grabbed for vision)
- **Corruption benchmark (injected into real clean BotFails expert data): 30/30 detected for each of 6 motion corruptions; 20/20 for frozen video and black frames**
- **False positives: 0/20 clean videos; 1/178 clean expert episodes** (setTheTable expert ep7: all 6 joints constant for the whole episode; under investigation in E016b)
- Log: `evidence/logs/E016_integrity_bench.txt`

## E017 — Integrity scan, community_dataset_v3 (2 sub-datasets) · 2026-10-28
- `--vision none`: all 133 episodes, 3 s, $0.0023 (summary only)
- 0 integrity issues; 6 motion-only review flags; health 95.5%
- BotFails regression with integrity wired in: unchanged (80% / 4/12 / 1/28)
- Log: `evidence/logs/E017_integrity_scan.txt`

## E016b — The "false positive" was real: motionless expert demo · 2026-10-28
- Investigated the 1/178 flag from E016: BotFails setTheTable **expert** ep7
- **35 frames (1.2 s); state and action standard deviation exactly 0.0 on all 6 joints; frames show the robot never moves.** An accidental start/stop recording saved as an expert demonstration.
- → Integrity layer false positives on clean expert data: **0/178**. This is a genuine broken episode in a published benchmark's expert set, found by a deterministic check.
- Label improved: all-joints-constant is now reported as `no_motion` ("robot never moves") rather than `dead_sensor`
- Log: `evidence/logs/E016b_setTheTable_ep7.txt`

## E018 — Full integrity scan: lerobot/community_dataset_v3 · 2026-10-29
- Overnight, resumable, laptop, 2 workers: **1,754 of 1,755 sub-datasets scanned** (1 skipped: no `observation.state` column), 488 contributors, **72,356 episodes, 38.1M frames, 364.6 hours of robot data, $0 model spend**
- v1 results: 3,277 episodes (4.53%) with a hard issue, dominated by `dead_sensor` (2,668)
- **Diagnosis: v1 `dead_sensor` was over-flagging.** Flagged joints were mostly `left_*`/`right_*` on two-arm robots: an idle arm legitimately reads constant. A constant reading is not a broken sensor.
- Log: `evidence/logs/E018_community_scan_report.txt`

## E019 — Sharper dead-sensor definition + local re-scan · 2026-10-29
- New rule: a sensor is dead only if its **reading is frozen while the robot is commanded to move that joint** (state constant, action varying). Idle joints have both constant and are no longer flagged.
- Corruption benchmark unchanged: dead_sensor 30/30; all other types 30/30 or 20/20; false positives on clean expert data 1/178 (the known motionless ep7, a true positive)
- Local re-scan of all 1,754 datasets (no network): **156 s**
- **v2 results: 1,221 of 72,356 episodes (1.69%) with a hard issue; 219 of 1,754 datasets (12.5%)**
  - dead_sensor 514 (23 datasets) · empty_episode 338 (111) · no_motion 219 (96) · duplicate_episode (within dataset) 138 (8) · length_mismatch 71 (34) · timestamp_error 15 (4)
- **Duplicates across datasets: 4,509 recordings appear in 2+ datasets → 5,049 extra copies (7.0% of all episodes); 777 span different contributors; 97 dataset pairs are ≥80% identical recordings**
- Status: findings NOT yet verified by eye (Phase 4 in progress)
- Logs: `evidence/logs/E019_*`

## E020 — Dead-sensor rule v3 + visual verification of scan findings · 2026-10-29
- Visual check of v2 `dead_sensor` flags: hamidkaloorazi bimanual ep0 shows the flagged LEFT arm idle in all frames while the right arm folds cloth; so101_test ep91's flagged wrist roll had 0.35° of commanded jitter. **Both were idle joints, not dead sensors → v2 still over-flagged.**
- v3 rule: commanded RANGE in the episode must be ≥ 20% of the joint's 90th-percentile range across the dataset (jitter on idle arms excluded)
- Benchmark: dead_sensor 30/30, all other types 30/30 / 20/20; clean false positives 1/178 (the known true-positive ep7)
- **Final scan (v3): 763 of 72,356 episodes (1.05%) with a hard issue, in 209 of 1,754 datasets (11.9%)**
  - empty_episode 338 · no_motion 219 · duplicate_episode (within dataset) 138 · length_mismatch 71 · dead_sensor 56 · timestamp_error 15
- **Duplicates across datasets: 4,585 recordings in 2+ datasets → 5,125 extra copies (7.1% of episodes); 777 span different contributors; 97 dataset pairs ≥80% identical**
- **Verified examples:**
  - no_motion: 1g0rrr/demo2_frames_grab ep11, 23.9 s, all joints constant, arm static in frames while the scene changes around it
  - empty_episode: 7jep7/rook_to_d4_v5 ep4, 1 frame
  - dead_sensor: Arururu12/UR5e_Gello_Cube_bin_v3 ep1, 6 arm joints frozen for 52 s while commanded up to 0.31 rad std; gripper logged normally
  - duplicate (within): HuaihaiLyu/hamburger0509 ep84 = ep91 (max difference 0.000000, frames identical); a 7-episode block saved twice
  - duplicate (cross-contributor): Dangvi/soarm100_data ep0 = s20000s/soarm100_data ep0 (max difference 0.000000)
  - timestamp_error: kevin510/so-100-draw-smiley ep0, 415 non-increasing timestamps
  - length_mismatch: 1lyz123576/so101_test-1 ep10, video 11.3 s vs motion 18.6 s
- Logs: `evidence/logs/E020_*`

## E021b — Constrained Ultra checklists (single change vs E012), dev 40 · 2026-10-29 · ❌ REGRESSION
- Same as E021, but the checklist may only restate requirements literally written in the task text, plus "not a problem" guidance. Verified in output: e.g. "Dishes are placed in a dish rack".
- **Retake precision 60% (E012: 80%), caught 3/12 (4/12), false alarms 2/28 (1/28); retake+review false alarms 11/28 (9/28)**
- Fails the pre-set rule (precision ≥ 80% AND an improvement). Differences on 40 episodes are small, but none favor the checklist.
- **Insight: extra prompt text degrades the vision model even when accurate; the reference frames already carry the task context.**
- **Decision: freeze at the E012 configuration.** `--checklist` remains available, off by default. No further tuning on the dev set (overfitting risk).
- Cost $0.057 · Log: `evidence/logs/E021b_constrained_checklists_dev.txt`

## E022 — FROZEN TEST SET (run once, pipeline tagged v1.0-frozen beforehand) · 2026-10-29
- 50 BotFails episodes (25 real failures, 25 good), frozen in `evidence/splits/botfails_TEST_frozen.csv` before any tuning; never used in development
- Configuration: vision v2 (Nemotron 3.5 Super VL, 8 frames: 2 reference + 6 episode), reference = lowest-index expert demo from the dev split, two-tier verdicts, integrity layer, remote frames
- **RETAKE list: precision 100% (13/13; Wilson 95% lower bound ≈ 77%), caught 13/25, false alarms 0/25**
- **RETAKE + REVIEW: precision 82% (18/22), caught 18/25 (72%), false alarms 4/25**
- Retake flags by type: wrong_placement 5, spill 5, dropped_object 2, human_intervention 1
- Cost $0.0546 → **$1.09 per 1,000 episodes** · runtime 389 s for 50 episodes (8 workers, remote)
- No re-runs; no changes after seeing results.
- Log: `evidence/logs/E022_frozen_test_set.txt` · Report: `reports/botfails_TEST/`

## E023 — Full pipeline on a community sample (integrity + motion + vision) · 2026-10-29
- 52 episodes from 22 sub-datasets of `lerobot/community_dataset_v3`: 12 integrity-flagged (2 per issue type, from the scan) + 40 random episodes from 10 random datasets with no integrity issues
- `--remote --workers 8`: **280 s, $0.0572 → $1.10 per 1,000 episodes**
- **All 12 integrity-flagged episodes → retake** with code-check reasons
- 40 random episodes: 31 clean, 5 review, **4 retake (vision: human_intervention)**
- **Visual verification: 4/4 human-intervention flags confirmed** (hand/arm in the workspace)
  - campa-rabb/so100_50ep ep6 (mid-task, t=11.9 s) · jclinton1/smol_start_toaster_3 ep8 (start) · kevin-nd/so100_test_2 ep19 (start) · kevin-nd/so100_test_2 ep8 (final frame)
- Small sample; reported as verified examples, not as a rate
- Logs: `evidence/logs/E023_*` · Report: `reports/community_sample/`

## E024 — Tavily + Ultra fix guidance, v1 (runtime, inside `retake audit`) · 2026-10-29
- For each issue type in a report: Tavily web search → Nemotron 3 Ultra writes ≤3 causes/fixes citing only returned sources → code drops items citing non-existent sources
- Community sample: 7 issue types, 32 cited points, 7 fresh Tavily calls (runtime), cost $0.012
- **Manual review of relevance:** good for empty_episode, duplicate_episode, timestamp_error (LeRobot docs + GitHub issues #533, #1875, #2163); mixed for length_mismatch and no_motion; **wrong for dead_sensor** (UR5 MoveL forum post) and **human_intervention** (dexterous hand-tracking teleop papers)
- Diagnosis: generic queries; no rule against off-system sources; citation check verified source *numbers*, not *support*
- Side finding: Voxel51 publishes LeRobot curation metrics (incl. video_window_mismatch), an adjacent competitor
- Next (one tightening pass, as pre-set): LeRobot-specific queries + domain filter, off-system sources ignored, and **each point must carry a verbatim quote that code verifies exists in the cited source**

## E024b–d — Tightening fix guidance (three passes, then locked) · 2026-10-29
- **b:** LeRobot-specific queries + domain filter; off-system sources ignored; **each point must carry a 6–30-word verbatim quote that code verifies is in the cited source** → 17 kept, 4 removed. dead_sensor still off-topic (UMI blog); human_intervention correctly "no verifiable guidance"
- **c:** the cited source must itself describe the symptom (code keyword check) → 13 kept, 9 removed. dead_sensor now cited another dataset's README (timing offsets): keywords matched, topic didn't
- **d:** for LeRobot issue types, only official/maintained LeRobot sources count (LeRobot GitHub, official docs, phospho docs, DeepWiki LeRobot); deterministic robot choice for queries. **Locked here, no further passes.**
- Strongest surviving guidance: timestamp errors (LeRobot #2163, #2158), duplicates (#4982), length mismatch (#3177 from_timestamp vs video PTS drift, #2547), no motion (#2000 actions recorded as zero)
- Positioned in reports as **leads, not certainties**; "no verifiable guidance" is shown when nothing survives
- Also surfaced: `lerobot-doctor` (LeRobot's own metadata validator), adjacent tooling
- Logs: `evidence/logs/E024b_*`, `E024c_*`, `E024d_*`
- **Final (d) result:** 10 points kept, 14 removed. dead_sensor and human_intervention → "no verifiable guidance". Timestamp guidance now cites only LeRobot #2158 (non-monotonic DTS, single-shot v3 write, monotonic re-encode). empty_episode guidance (episode_time_s, official docs) is the weakest surviving item; kept, labeled as a lead.

## E025 — Post-hoc diagnosis of the frozen test set (no pipeline changes) · 2026-10-29
- Purpose: understand the 7 missed failures and 4 false alarms from E022. **Diagnosis only; nothing was tuned on these episodes.** Labels from `results/signals_BotFails.csv`, same as E022.
- Confirmed counts: 25 failures → 13 retake, 5 review, **7 missed**; 25 good → 21 clean, **4 false alarms (all review, all "incomplete")**
- **Missed failures, by eye (6 saved frames each):**
  - 2 visible sorting errors (vegetablesAndFruitsSorting ep6, ep9): items in the wrong box. The model checked that objects were sorted, not which box each went into.
  - 1 likely visible (soldering ep5): iron ends on the table rather than in its holder
  - 3 not judgeable from the camera used (robothon_buttons ep6, hatchAndProbe ep6, screws_sorting ep1): side view hides the relevant state
  - 1 unclear (dishTidyUp ep5)
- **Every miss gives the same reason, "matches the reference end state":** the vision layer mostly judges end-state similarity, so fine-grained rule violations pass. E021/E021b showed that adding the rules to the prompt does not fix this.
- **Model confidence does not separate misses (mean 0.93) from correct flags (0.95):** it cannot be used for triage.
- **All 4 false alarms are "incomplete" verdicts**, independently supporting E011 (incomplete → review, not retake).
- **Possible label noise:** 2 episodes from "_anomaly" folders are labeled good but look like failures (setTheTable ep2: knife and fork appear swapped; makingCoffee ep3: powder reportedly never poured). Scores keep BotFails' labels unchanged.
- Roadmap implications (to test on new data, not this test set): focused per-rule questions, camera choice / multiple cameras, denser frames.
- Log: `evidence/logs/E025_missed_failures.txt` · Frames: `reports/botfails_TEST_misses/`
