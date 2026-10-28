# Retake audit: lerobot/community_dataset_v3 [00ri/so100_battery,1g0rrr/demo2_frame_holder]

## Verdict
Health score 95.5% across 133 audited episodes: 127 clean, 6 flagged for review, 0 flagged for retake.

## Caveats
This is an automated audit; on a labeled benchmark the vision layer agreed with human labels about 72% of the time. A human should check the flagged frames before any episode is removed or re-recorded.

## What we found
**Retake (0):** None.

**Review — motion_only (6):**
*   `00ri/so100_battery ep8`, `ep19` – Possible operator hesitation (unusually long pauses, +4.5 sd and +3.1 sd).
*   `00ri/so100_battery ep48` – Possible incomplete demo (-2.3 sd) and possible collision or blocked arm (commanded/actual motion diverge, +3.1 sd).
*   `1g0rrr/demo2_frame_holder ep9`, `ep10` – Possible repeated regrasping (unusually many grasps, +6.3 sd each); `ep10` also much longer than typical (+5.2 sd).
*   `1g0rrr/demo2_frame_holder ep23` – Possible jerky motion (+3.2 sd).

## Hotspots
- **00ri/so100_battery**: 0 retake, 3 review (of 50 audited)
- **1g0rrr/demo2_frame_holder**: 0 retake, 3 review (of 83 audited)
- No clear recurring pattern: no task has 3+ retake episodes with the same visible issue.
- Review flags are unconfirmed and are not, on their own, evidence of a problem with the data.

## Recommended actions
Check review episodes first. Prioritize `00ri/so100_battery ep48` (possible collision/incomplete) and `1g0rrr/demo2_frame_holder ep10` (possible struggling/retries with regrasping) as they show multiple simultaneous anomalies. Then check `ep8`, `ep19` (hesitation), `ep9` (regrasping), and `ep23` (jerky motion) to confirm if behavior is acceptable task variance.