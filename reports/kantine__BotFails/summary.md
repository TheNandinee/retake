# Retake audit: kantine/BotFails

## Verdict
The dataset health score is 52.5% based on 40 audited episodes (21 clean, 14 flagged for review, 5 flagged for retake).

## Caveats
This is an automated audit; on a labeled benchmark the vision layer agreed with human labels 72% of the time. A human should verify the flagged frames before any data is deleted or re-recorded.

## What we found
**Retake (5 episodes):** 3 spills, 2 wrong placements.
*   *domotic_pouringCoffee::0, test ep. 5:* Dark liquid spilled on table at 17.9s.
*   *domotic_vegetablesAndFruitsSorting::0, normal_train ep. 15:* Pink box holds vegetables; yellow box holds vegetables, contradicting reference state.
*   *domotic_pouringCoffee::0, test ep. 10:* Liquid spilled and cup knocked over at 23.9s.
*   *domotic_vegetablesAndFruitsSorting::0, test ep. 10:* Fruits placed in green vegetable box instead of pink fruit box.
*   *domotic_pouringCoffee::0, test ep. 1:* Liquid spilled on table during pouring at 17.9s.

**Review (14 episodes):** 13 incomplete, 1 false positive.
*   *domotic_makingCoffee::0, normal_train ep. 2:* Robot never transferred coffee powder into filter.
*   *industrial_robothon_buttons::0, normal_train ep. 11:* Episode ends in start state; slider not moved, no button pushes.
*   *domotic_makingCoffee::0, test ep. 12:* Powder not transferred; spoon left on table (motion: +4.0 SD duration).
*   *industrial_screws_sorting::0, test ep. 4:* Final state matches reference, but episode much shorter than typical (-2.2 SD).
*   *industrial_soldering::0, normal_train ep. 6:* Soldering iron never moves to board.

## Hotspots
*   **domotic_pouringCoffee::0 (3 retake, all spill):** Systematic collection problem—every audited anomaly episode shows a spill.
*   **domotic_vegetablesAndFruitsSorting::0 (2 retake, both wrong_placement):** No clear systematic pattern (only 2 matching retake episodes).
*   **domotic_makingCoffee::0 (4 review, all incomplete):** Systematic collection problem—4 episodes show missing powder transfer step.
*   **industrial_robothon_buttons::0 (3 review, all incomplete):** Systematic collection problem—3 episodes end without slider/button manipulation.

## Recommended actions
1.  **Re-check the 3 `domotic_pouringCoffee` retake episodes (test ep. 1, 5, 10)** first: consistent visual evidence of spills makes these high-confidence deletes or re-records.
2.  **Re-check the 4 `domotic_makingCoffee` review episodes (normal_train ep. 2, 13; test ep. 12; anomaly ep. 12)** next: unanimous "incomplete" flags across splits suggest a procedural gap in the demonstration script.
3.  **Re-check the 3 `industrial_robothon_buttons` review episodes (normal_train ep. 11, 14; test ep. 8)**: consistent failure to manipulate slider/buttons indicates a possible task definition or execution issue.
4.  **Verify the 2 `domotic_vegetablesAndFruitsSorting` retake episodes (normal_train ep. 15; test ep. 10)** for box-label confusion.
5.  **Inspect `industrial_screws_sorting` test ep. 4**: flagged "review/none" but duration is -2.2 SD; confirm if episode was truncated.