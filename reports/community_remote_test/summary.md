# Retake audit: lerobot/community_dataset_v3 [1g0rrr/demo2_frame_holder]

## Verdict
Health score 80% with 8 clean, 2 review, and 0 retake out of 10 audited episodes; 2 episodes are flagged for review.

## Caveats
This is an automated audit; on a labeled benchmark the vision layer agreed with human labels about 72% of the time, so a human should check the flagged frames before any episode is removed or re-recorded.

## What we found
**Retake flags:** None.

**Review flags — possible incomplete (2 episodes):**
- `1g0rrr/demo2_frame_holder ep53`: possible incomplete — the frame may not have been placed into the holder by the end of the recording (evidence at 13.7 s).
- `1g0rrr/demo2_frame_holder ep59`: possible incomplete — the frame may not have been transferred from the right mat to the left holder (evidence at 12.9 s).

## Hotspots
- **1g0rrr/demo2_frame_holder**: 0 retake, 2 review (of 10 audited)
- No clear recurring pattern: no task has 3+ retake episodes with the same visible issue.
- Review flags are unconfirmed and are not, on their own, evidence of a problem with the data.

## Recommended actions
Check the two review episodes first: `ep53` and `ep59`. Both show possible incomplete task execution near the end of the trajectory; confirm whether the frame reaches the holder before deciding to keep or re-record.