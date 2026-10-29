# Retake audit: kantine/BotFails

## Verdict
Health score 47.5%; 40 episodes audited, 19 clean, 16 flagged for review, 5 flagged for retake.

## Caveats
This is an automated audit. On a labeled benchmark the vision layer agreed with human labels about 72% of the time, so a human should check the flagged frames before any episode is removed or re-recorded.

## What we found
**Retake flags**
- spill (3): `domotic_pouringCoffee_anomaly ep5` (coffee spilled on table, no filled cup), `domotic_pouringCoffee_anomaly ep10` (cup knocked over, coffee spilled).
- wrong_placement (2): `domotic_setTheTable_anomaly ep1` (knife left, fork right, reversed), `domotic_setTheTable_expert ep16` (knife left, fork right, reversed).

**Review flags (possible issues)**
- incomplete (14): `domotic_makingCoffee_expert ep2` (powder remains in can, not in filter), `industrial_robothon_buttons_expert ep11` (starts with slider at top, red button not pushed).
- vision_error (1): `domotic_setTheTable_expert ep2`.
- motion_only (1): `industrial_screws_sorting_anomaly ep4` (much shorter than typical demos, -2.2 sd).

## Hotspots
- **domotic_pouringCoffee**: 3 retake, 0 review (of 4 audited) - possible recurring issue: **spill** in 3 episodes
- **domotic_setTheTable**: 2 retake, 2 review (of 4 audited)
- **domotic_makingCoffee**: 0 retake, 4 review (of 4 audited)
- **industrial_robothon_buttons**: 0 retake, 4 review (of 4 audited)
- **domotic_dishTidyUp**: 0 retake, 2 review (of 4 audited)
- **domotic_groceriesSorting**: 0 retake, 1 review (of 4 audited)
- **industrial_robothon_hatchAndProbe**: 0 retake, 1 review (of 4 audited)
- **industrial_screws_sorting**: 0 retake, 1 review (of 4 audited)
- **industrial_soldering**: 0 retake, 1 review (of 4 audited)
- Review flags are unconfirmed and are not, on their own, evidence of a problem with the data.

## Recommended actions
Check retake episodes first: the three spill episodes (`domotic_pouringCoffee_anomaly ep5`, `domotic_pouringCoffee_anomaly ep10`, `domotic_pouringCoffee_anomaly ep1`) and two wrong_placement episodes (`domotic_setTheTable_anomaly ep1`, `domotic_setTheTable_expert ep16`) show visible task failures. Then check review episodes starting with `domotic_makingCoffee_expert ep2` and `industrial_robothon_buttons_expert ep11` (possible incomplete task execution), `domotic_setTheTable_expert ep2` (possible vision error), and `industrial_screws_sorting_anomaly ep4` (possible cutoff).