# Retake audit: kantine/BotFails

## Verdict
Health score 52.5% (21 clean, 14 review, 5 retake out of 40 audited episodes from 323 in scope across 10 task groups).

## Caveats
This is an automated audit; on a labeled benchmark the vision layer agreed with human labels about 72% of the time. A human should check the flagged frames before any episode is removed or re-recorded.

## What we found
**Retake — spill (3):** `domotic_pouringCoffee_anomaly ep1` (liquid spilled at 17.9s), `domotic_pouringCoffee_anomaly ep10` (liquid spilled, cup knocked over at 23.9s). **Retake — wrong_placement (2):** `domotic_vegetablesAndFruitsSorting_expert ep15` (pink box holds vegetables), `domotic_vegetablesAndFruitsSorting_anomaly ep10` (fruits placed in green vegetable box).

**Review — incomplete (13, possible):** `domotic_makingCoffee_expert ep2` (powder never transferred to filter), `industrial_robothon_buttons_expert ep11` (slider not moved, no button pushes). **Review — motion_only (1, possible):** `industrial_screws_sorting_anomaly ep4` (episode much shorter than typical, final state matches reference).

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
Check retake episodes first: `domotic_pouringCoffee_anomaly ep1`, `domotic_pouringCoffee_anomaly ep5`, `domotic_pouringCoffee_anomaly ep10` (confirmed spills); `domotic_vegetablesAndFruitsSorting_expert ep15`, `domotic_vegetablesAndFruitsSorting_anomaly ep10` (confirmed wrong placements). Then review incomplete flags with strongest evidence: `domotic_makingCoffee_expert ep2`, `domotic_makingCoffee_anomaly ep12` (motion flag: much longer), `industrial_robothon_buttons_expert ep11`, `industrial_soldering_expert ep6`.