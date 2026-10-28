# Retake audit: kantine/BotFails

## Verdict
Health score 52.5% across 40 audited episodes: 21 clean, 14 flagged for review, 5 flagged for retake.

## Caveats
This is an automated audit; on a labeled benchmark the vision layer agreed with human labels about 72% of the time, so a human should check the flagged frames before any episode is removed or re-recorded.

## What we found
**Retake — spill (3):** `domotic_pouringCoffee_anomaly ep1`, `domotic_pouringCoffee_anomaly ep5` — liquid spilled on table during pouring; `domotic_pouringCoffee_anomaly ep10` — liquid spilled and cup knocked over.
**Retake — wrong_placement (2):** `domotic_vegetablesAndFruitsSorting_expert ep15` — pink box holds vegetables, yellow box holds vegetables; `domotic_vegetablesAndFruitsSorting_anomaly ep10` — fruits placed in green vegetable box.

**Review — incomplete (13, possible):** `domotic_makingCoffee_expert ep2`, `domotic_makingCoffee_expert ep13` — robot never transferred coffee powder into filter; `industrial_robothon_buttons_expert ep11`, `industrial_robothon_buttons_expert ep14` — slider not moved, no button pushes; `industrial_soldering_expert ep6` — iron never moved to board; `domotic_dishTidyUp_anomaly ep13` — one plate remains on table; `domotic_groceriesSorting_anomaly ep3` — basket not emptied; `domotic_makingCoffee_anomaly ep12` — powder not transferred, spoon left on table; `domotic_setTheTable_anomaly ep9` — green plate missing, utensils not arranged; `industrial_robothon_buttons_anomaly ep8` — final state differs from reference; `industrial_robothon_hatchAndProbe_anomaly ep14` — no evidence hatch/probe/plug manipulated; `industrial_screws_sorting_expert ep19` — only one screw moved to left bowl; `domotic_vegetablesAndFruitsSorting_anomaly ep1` — green vegetable remains in central bowl.
**Review — motion_only (1, possible):** `industrial_screws_sorting_anomaly ep4` — final state matches reference but episode much shorter than typical.

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
Check retake episodes first: the three pouring spills (`domotic_pouringCoffee_anomaly ep1`, `ep5`, `ep10`) and two sorting misplacements (`domotic_vegetablesAndFruitsSorting_expert ep15`, `domotic_vegetablesAndFruitsSorting_anomaly ep10`) show visible failures. Then review the incomplete episodes, prioritizing the two `domotic_makingCoffee` expert episodes (`ep2`, `ep13`) and two `industrial_robothon_buttons` expert episodes (`ep11`, `ep14`) where the task appears entirely unfinished, plus `industrial_screws_sorting_anomaly ep4` for the anomalously short duration.