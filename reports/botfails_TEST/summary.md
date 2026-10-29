# Retake audit: kantine/BotFails

## Verdict
The health score is 56.0% with 28 clean, 9 review, and 13 retake episodes out of 50 audited.

## Caveats
This is an automated audit; on a labeled benchmark the vision layer agreed with human labels about 72% of the time, so a human should check the flagged frames before any episode is removed or re-recorded.

## What we found
**Retake (13 episodes):**
*   **Spill (5):** `domotic_pouringCoffee_anomaly ep3` (liquid spilled on table), `domotic_pouringCoffee_anomaly ep12` (liquid spilled, cup and pitcher knocked over); `domotic_makingCoffee_anomaly ep6` (coffee powder spilled), `domotic_makingCoffee_anomaly ep10` (coffee powder spilled).
*   **Wrong placement (5):** `domotic_setTheTable_anomaly ep11` (glass not in front of plate), `domotic_setTheTable_anomaly ep14` (knife on left, glass misplaced); `domotic_groceriesSorting_anomaly ep8` (objects in incorrect boxes), `domotic_vegetablesAndFruitsSorting_anomaly ep11` (fruit/vegetable boxes reversed).
*   **Dropped object (2):** `domotic_makingCoffee_anomaly ep13` (spoon dropped, scoop separated), `domotic_setTheTable_anomaly ep12` (gray cup lying on side).
*   **Human intervention (1):** `industrial_soldering_anomaly ep10` (human hand in workspace at 6.0s).

**Review (9 episodes, possible incomplete):**
*   **Domotic tasks (4):** `domotic_dishTidyUp_expert ep16` (green plate on table), `domotic_dishTidyUp_anomaly ep10` (two green plates on table); `domotic_makingCoffee_anomaly ep3` (coffee powder not transferred to filter).
*   **Industrial tasks (5):** `industrial_robothon_hatchAndProbe_expert ep6` (probe not inserted); `industrial_robothon_hatchAndProbe_anomaly ep0` (laptop open, hatch not closed), `industrial_robothon_hatchAndProbe_anomaly ep3` (probe/plug not placed); `industrial_screws_sorting_expert ep11` (screws remain in bowl/on table); `industrial_robothon_buttons_anomaly ep4` (slider at start position).

## Hotspots
- **domotic_makingCoffee**: 3 retake, 1 review (of 4 audited)
- **domotic_pouringCoffee**: 3 retake, 0 review (of 7 audited) - possible recurring issue: **spill** in 3 episodes
- **domotic_setTheTable**: 3 retake, 0 review (of 6 audited)
- **industrial_screws_sorting**: 1 retake, 1 review (of 5 audited)
- **domotic_groceriesSorting**: 1 retake, 0 review (of 4 audited)
- **domotic_vegetablesAndFruitsSorting**: 1 retake, 0 review (of 7 audited)
- **industrial_soldering**: 1 retake, 0 review (of 5 audited)
- **industrial_robothon_hatchAndProbe**: 0 retake, 4 review (of 5 audited)
- **domotic_dishTidyUp**: 0 retake, 2 review (of 5 audited)
- **industrial_robothon_buttons**: 0 retake, 1 review (of 2 audited)
- Review flags are unconfirmed and are not, on their own, evidence of a problem with the data.

## Recommended actions
Check retake episodes first: verify spills in `domotic_pouringCoffee_anomaly ep3`, `ep7`, `ep12` and `domotic_makingCoffee_anomaly ep6`, `ep10`; confirm dropped spoon in `domotic_makingCoffee_anomaly ep13` and cup in `domotic_setTheTable_anomaly ep12`; validate human hand in `industrial_soldering_anomaly ep10`. Then review incomplete flags, prioritizing `industrial_robothon_hatchAndProbe` episodes (`expert ep6`, `anomaly ep0`, `ep3`, `ep8`) which account for 4 of 9 review flags.