# Retake audit: lerobot/community_dataset_v3 [00ri/so100_battery]

## Verdict
The dataset scored 94.0% health with 47 clean episodes, 3 flagged for review, and 0 flagged for retake.

## Caveats
This is an automated audit; on a labeled benchmark the vision layer agreed with human labels about 72% of the time. A human should check the flagged frames before any episode is removed or re-recorded.

## What we found
**Retake:** None.

**Review — motion_only (3 episodes):**
*   **Unusually long pause / operator hesitation:** ep8 (+4.5 sd), ep19 (+3.1 sd) — possible extended hesitation during demonstration.
*   **Short duration & motion divergence:** ep48 (-2.3 sd duration, +3.1 sd commanded vs. actual divergence) — possible incomplete recording or arm collision/blockage.

## Hotspots
- **00ri/so100_battery**: 0 retake, 3 review (of 50 audited)
- No clear recurring pattern: no task has 3+ retake episodes with the same visible issue.
- Review flags are unconfirmed and are not, on their own, evidence of a problem with the data.

## Recommended actions
Check ep48 first due to combined short duration and motion divergence signals suggesting a possible collision or cutoff. Then check ep8 and ep19 for extended operator pauses that may inflate dataset variance.