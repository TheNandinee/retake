# Retake audit: kantine/BotFails

## Verdict
The audited 40-episode sample (12.4% of 323) scored 52.5% health: 21 clean, 14 flagged for review, and 5 flagged for retake.

## Caveats
This is an automated audit; on a labeled benchmark the vision layer agreed with human labels about 72% of the time. A human should check the flagged frames before any episode is removed or re-recorded.

## What we found
**Retake (5 episodes)**
- Spill (3): `domotic_pouringCoffee_anomaly ep1` (liquid spilled on table at 17.9s), `domotic_pouringCoffee_anomaly ep10` (liquid spilled and cup knocked over at 23.9s).
- Wrong placement (2): `domotic_vegetablesAndFruitsSorting_expert ep15` (vegetables in pink fruit box at 39.0s), `domotic_vegetablesAndFruitsSorting_anomaly ep10` (fruits placed in green vegetable box at 39.0s).

**Review (14 episodes, unconfirmed — possible issues)**
- Incomplete (13): `domotic_makingCoffee_expert ep2` (no coffee powder transferred at 34.1s), `industrial_robothon_buttons_expert ep11` (slider not moved, no button pushes at 29.3s).
- Motion only (1): `industrial_screws_sorting_anomaly ep4` (final state matches reference but duration much shorter than typical, -2.2 sd).

## Hotspots
- **domotic_pouringCoffee**: 3 retake, 0 review (of 4 audited) - possible recurring issue: **spill** in 3 episodes
- **domotic_vegetablesAndFruitsSorting**: 2 retake, 1 review (of 4 audited)
- **domotic_makingCoffee**: 0 retake, 3 review (of 4 audited)
- **industrial_robothon_buttons**: 0 retake, 3 review (of 4 audited)
- **industrial_screws_sorting**: 0 retake, 2 review (of 4 audited)
- **domotic_dishTidyUp**: 0 retake, 1 review (of 4 audited)
- **domotic_groceriesSorting**: 0 retake, 1 review (of 4 audited)
- **domotic_setTheTable**: 0 retake, 1 review (of 4 audited)
- **industrial_robothon_hatchAndProbe**: 0 retake, 1 review (of 4 audited)
- **industrial_soldering**: 0 retake, 1 review (of 4 audited)
- Review flags are unconfirmed and are not, on their own, evidence of a problem with the data.

## Recommended actions
Check retake episodes first due to visible evidence: the three `domotic_pouringCoffee` spill episodes (`anomaly ep1`, `anomaly ep5`, `anomaly ep10`) and the two `domotic_vegetablesAndFruitsSorting` wrong-placement episodes (`expert ep15`, `anomaly ep10`). Then review the incomplete episodes, prioritizing `domotic_makingCoffee_expert ep2` and `industrial_robothon_buttons_expert ep11` (both show unfinished tasks at ~30s), and `industrial_screws_sorting_anomaly ep4` for the motion-only timing anomaly.