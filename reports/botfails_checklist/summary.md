# Retake audit: kantine/BotFails

## Verdict
The dataset has a health score of 35.0% with 14 clean, 17 review, and 9 retake episodes out of 40 audited.

## Caveats
This is an automated audit; on a labeled benchmark the vision layer agreed with human labels about 72% of the time, so a human should check the flagged frames before any episode is removed or re-recorded.

## What we found
**Retake flags**
- **wrong_placement** (5): `domotic_setTheTable_expert ep16` (knife/fork swapped), `domotic_setTheTable_anomaly ep1` (knife/fork swapped).
- **spill** (3): `domotic_pouringCoffee_anomaly ep1` (coffee spilled on table), `domotic_pouringCoffee_anomaly ep5` (liquid spilled, cup empty).
- **dropped_object** (1): `domotic_makingCoffee_anomaly ep12` (spoon dropped, task incomplete).

**Review flags** (possible issues)
- **incomplete** (16): `domotic_makingCoffee_expert ep2` (no coffee powder in filter), `industrial_robothon_hatchAndProbe_anomaly ep13` (probe never inserted).
- **motion_only** (1): `industrial_screws_sorting_anomaly ep4` (much shorter than typical demos).

## Hotspots
- **domotic_setTheTable**: 3 retake, 1 review (of 4 audited) - possible recurring issue: **wrong_placement** in 3 episodes
- **domotic_pouringCoffee**: 3 retake, 0 review (of 4 audited) - possible recurring issue: **spill** in 3 episodes
- **domotic_vegetablesAndFruitsSorting**: 2 retake, 0 review (of 4 audited)
- **domotic_makingCoffee**: 1 retake, 3 review (of 4 audited)
- **industrial_robothon_hatchAndProbe**: 0 retake, 4 review (of 4 audited)
- **industrial_soldering**: 0 retake, 3 review (of 4 audited)
- **industrial_robothon_buttons**: 0 retake, 2 review (of 4 audited)
- **industrial_screws_sorting**: 0 retake, 2 review (of 4 audited)
- **domotic_dishTidyUp**: 0 retake, 1 review (of 4 audited)
- **domotic_groceriesSorting**: 0 retake, 1 review (of 4 audited)
- Review flags are unconfirmed and are not, on their own, evidence of a problem with the data.

## Recommended actions
Check retake episodes first: `domotic_setTheTable_expert ep16`, `domotic_setTheTable_anomaly ep1`, `domotic_setTheTable_expert ep2`, `domotic_vegetablesAndFruitsSorting_anomaly ep10`, `domotic_vegetablesAndFruitsSorting_anomaly ep1`, `domotic_pouringCoffee_anomaly ep1`, `domotic_pouringCoffee_anomaly ep5`, `domotic_pouringCoffee_anomaly ep10`, `domotic_makingCoffee_anomaly ep12`. Then review `domotic_makingCoffee_expert ep2`, `industrial_robothon_hatchAndProbe_anomaly ep13`, `industrial_screws_sorting_anomaly ep4`, and `industrial_soldering_expert ep2` to confirm task completion.