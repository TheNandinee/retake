# Retake audit: kantine/BotFails

## Verdict
The dataset scores **47.5% health** (19 clean / 40 audited episodes), with 20 episodes requiring retake and 1 needing review.

## What we found
- **Incomplete (14 episodes):** Task ended before the goal state was reached.  
  - *domotic_dishTidyUp::0 ep. 2 (normal_train):* Two green plates left on the table instead of stored in the dish rack.  
  - *domotic_makingCoffee::0 ep. 2 (normal_train):* Spoon never used to transfer powder into the coffee maker.  
  - *industrial_robothon_buttons::0 ep. 11 (normal_train):* Slider not moved to top and blue button not pushed.  
  - *domotic_dishTidyUp::0 ep. 13 (test):* Not all dishes stored in the rack.  
  - *domotic_makingCoffee::0 ep. 12 (test):* Spoon removed from can but never used to add powder to filter.  
  - *domotic_setTheTable::0 ep. 9 (test):* Green plate not placed on the table in final state.  
  - *industrial_robothon_buttons::0 ep. 10 (normal_train):* Episode ends before required sequence (red button, slider to top, blue button) is completed.  
  - *industrial_robothon_hatchAndProbe::0 ep. 1 (normal_train):* No required object interactions performed; ended in start state.  
  - *domotic_dishTidyUp::0 ep. 14 (normal_train):* Two plates left on the table instead of stored.  
  - *industrial_robothon_hatchAndProbe::0 ep. 14 (test):* Probe remains outside the black plug.  
  - *industrial_soldering::0 ep. 8 (test):* Circuit board in same state as start; soldering not completed.  
  - *domotic_makingCoffee::0 ep. 10 (normal_train):* Spoon never placed into the coffee machine filter.  
  - *domotic_vegetablesAndFruitsSorting::0 ep. 1 (test):* Yellow fruit remains in central basket at end.  
  - *industrial_robothon_buttons::0 ep. 14 (normal_train):* None of the three required actions completed.

- **Wrong placement (3 episodes):** Objects placed in incorrect locations.  
  - *domotic_groceriesSorting::0 ep. 3 (test):* Red pepper in pink-sign vegetable box but on central plate; banana (fruit) in pink vegetable box; fruit missing from yellow box.  
  - *domotic_vegetablesAndFruitsSorting::0 ep. 4 (test):* Vegetables placed in pink box and fruits in yellow box, contradicting task rule.  
  - *domotic_setTheTable::0 ep. 1 (test):* Knife on left side of plate instead of right; fork on right instead of left.

- **Spill (3 episodes):** Liquid spilled during pouring.  
  - *domotic_pouringCoffee::0 ep. 5 (test):* Liquid spilled on table while pouring.  
  - *domotic_pouringCoffee::0 ep. 10 (test):* Robot knocked over small glass and spilled liquid.  
  - *domotic_pouringCoffee::0 ep. 1 (test):* Liquid spilled onto table around the glass during pouring.

- **Review (1 episode):** Motion statistics anomaly only.  
  - *industrial_screws_sorting::0 ep. 4 (test):* Ends with screws in correct left plate matching reference, but episode is much shorter than typical (-2.2 sd), possibly cut off.

## Hotspots
- **domotic_dishTidyUp::0:** 3/4 audited episodes are retakes (all *incomplete* — plates left on table).  
- **domotic_makingCoffee::0:** 3/4 audited episodes are retakes (all *incomplete* — spoon/powder step missed).  
- **domotic_pouringCoffee::0:** 3/4 audited episodes are retakes (all *spill* — liquid on table).  
- **industrial_robothon_buttons::0:** 3/4 audited episodes are retakes (all *incomplete* — sequence not finished).  
- **industrial_robothon_hatchAndProbe::0:** 2/4 audited episodes are retakes (both *incomplete* — no interactions performed).  
- **domotic_setTheTable::0:** 2/4 audited episodes are retakes (*incomplete* + *wrong_placement*).  
- **domotic_vegetablesAndFruitsSorting::0:** 2/4 audited episodes are retakes (*wrong_placement* + *incomplete*).  

**Pattern:** Three domestic tasks (*dishTidyUp*, *makingCoffee*, *pouringCoffee*) and one industrial task (*robothon_buttons*) show systematic failure modes — specific sub-steps (storing plates, spooning powder, pour control, button sequence) are consistently omitted or botched across both `normal_train` and `test` splits, suggesting the collection protocol did not enforce or verify completion of these sub-tasks.

## Recommended actions
- **Re-record (20 episodes):** All `retake` episodes listed above. Priority: the 14 *incomplete* episodes (missing goal-critical steps) and the 3 *spill* episodes (safety/cleanliness violation).  
- **Review before use (1 episode):** `industrial_screws_sorting::0 ep. 4 (test)` — verify it is not truncated; if complete, keep; otherwise re-record.  
- **Drop from training until fixed:** Do not include any of the 20 `retake` episodes in training until re-recorded and verified clean.  
- **Collection process changes:**  
  1. Add explicit “completion checks” for the four hotspot sub-tasks (plate storage, spoon-to-filter, pour-no-spill, button sequence) — either a human spotter or an automated end-state validator.  
  2. Require a minimum episode duration threshold per task (e.g., *makingCoffee* > 30 s) to catch early cutoffs like the *screws_sorting* anomaly.  
  3. For *pouringCoffee*, enforce a “no liquid on table” visual check before accepting a demo