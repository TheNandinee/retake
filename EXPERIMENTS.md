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
