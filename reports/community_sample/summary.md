# Retake audit: lerobot/community_dataset_v3 [00ri/so100_battery_bin_center,1g0rrr/demo2_frames_grab,1lyz123576/so101_test-1,7jep7/rook_to_d4_v5,Aadhavan/so101_test1,Arururu12/UR5e_Gello_Cube_bin_v2,Arururu12/UR5e_Gello_Cube_bin_v3,Beegbrain/moss_open_drawer_teabox,HuaihaiLyu/hamburger0509,HuaihaiLyu/hamburger_heti,Jinheng0130/Push,LeRobot-worldwide-hackathon/91-AM-PM-pouring-liquid,campa-rabb/so100_50ep,deepinsand/so100_test2,gxy1111/so100_close_drawer,jclinton1/smol_start_toaster_3,julyfun/so100_pick_and_place_v2_50,kevin-nd/so100_test_2,kevin510/so-100-draw-smiley,lt-s/rsj2025_train_lift_the_stacked_red_dish_and_set_it_down_on_the_table_flip,lt-s/rsj2025_train_relocate_any_blue_block_in_the_red_dish_to_the_blue_dish,masato-ka/so100_lego_sort]

## Verdict
Health score 59.6% across 52 audited episodes (1,868 in scope): 31 clean, 5 review, 16 retake.

## Caveats
This is an automated audit; on a labeled benchmark the vision layer agreed with human labels about 72% of the time, so a human should check the flagged frames before any episode is removed or re-recorded.

## What we found
**Retake — empty_episode** (2): `00ri/so100_battery_bin_center ep3` (1 frame, 0.0 s), `7jep7/rook_to_d4_v5 ep4` (1 frame, 0.0 s).  
**Retake — no_motion** (2): `1g0rrr/demo2_frames_grab ep11` (robot static 23.5 s), `Aadhavan/so101_test1 ep25` (robot static 3.1 s).  
**Retake — length_mismatch** (2): `1lyz123576/so101_test-1 ep10` (video 11.3 s vs motion 18.6 s), `Arururu12/UR5e_Gello_Cube_bin_v2 ep0` (video 57.8 s vs motion 59.5 s).  
**Retake — dead_sensor** (2): `Arururu12/UR5e_Gello_Cube_bin_v3 ep1` (six main motors never change), `Jinheng0130/Push ep4` (`main_shoulder_pan` never changes).  
**Retake — duplicate_episode** (2): `HuaihaiLyu/hamburger0509 ep84` (identical to ep91), `HuaihaiLyu/hamburger_heti ep119` (identical to ep126, ep133).  
**Retake — human_intervention** (4): `campa-rabb/so100_50ep ep6` (hand at 11.9 s), `jclinton1/smol_start_toaster_3 ep8` (hand at 0.3 s), `kevin-nd/so100_test_2 ep8` (hand at 29.3 s), `kevin-nd/so100_test_2 ep19` (hand at 0.6 s).  
**Retake — timestamp_error** (2): `LeRobot-worldwide-hackathon/91-AM-PM-pouring-liquid ep59` (462 non-increasing timestamps), `kevin510/so-100-draw-smiley ep0` (415 non-increasing timestamps).  

**Review — motion_only** (4): `campa-rabb/so100_50ep ep21` (possible correct end state, motion divergence flag), `campa-rabb/so100_50ep ep30` (possible correct transfer, repeated grasps flag), `julyfun/so100_pick_and_place_v2_50 ep8` (possible correct placement, long pause flag), `kevin-nd/so100_test_2 ep3` (possible correct arrangement, short duration flag).  
**Review — incomplete** (1): `campa-rabb/so100_50ep ep22` (possible missing final placement at 58.3 s).

## Hotspots
- **kevin-nd/so100_test_2**: 2 retake, 1 review (of 4 audited)
- **campa-rabb/so100_50ep**: 1 retake, 3 review (of 4 audited)
- **00ri/so100_battery_bin_center**: 1 retake, 0 review (of 1 audited)
- **1g0rrr/demo2_frames_grab**: 1 retake, 0 review (of 1 audited)
- **1lyz123576/so101_test-1**: 1 retake, 0 review (of 1 audited)
- **7jep7/rook_to_d4_v5**: 1 retake, 0 review (of 1 audited)
- **Aadhavan/so101_test1**: 1 retake, 0 review (of 1 audited)
- **Arururu12/UR5e_Gello_Cube_bin_v2**: 1 retake, 0 review (of 1 audited)
- **Arururu12/UR5e_Gello_Cube_bin_v3**: 1 retake, 0 review (of 1 audited)
- **HuaihaiLyu/hamburger0509**: 1 retake, 0 review (of 1 audited)
- **HuaihaiLyu/hamburger_heti**: 1 retake, 0 review (of 1 audited)
- **Jinheng0130/Push**: 1 retake, 0 review (of 1 audited)
- **LeRobot-worldwide-hackathon/91-AM-PM-pouring-liquid**: 1 retake, 0 review (of 1 audited)
- **jclinton1/smol_start_toaster_3**: 1 retake, 0 review (of 4 audited)
- **kevin510/so-100-draw-smiley**: 1 retake, 0 review (of 1 audited)
- **julyfun/so100_pick_and_place_v2_50**: 0 retake, 1 review (of 4 audited)
- No clear recurring pattern: no task has 3+ retake episodes with the same visible issue.
- Review flags are unconfirmed and are not, on their own, evidence of a problem with the data.

## Recommended actions
Check retake episodes first: the six integrity failures (`empty_episode`, `no_motion`, `length_mismatch`, `dead_sensor`, `duplicate_episode`, `timestamp_error`) are deterministic; the four `human_intervention` episodes show a hand in frame. Then check review episodes: `campa-rabb/so100_50ep ep22` may be truncated; the other three `motion_only` episodes have anomalous motion statistics but appear to reach the goal.

## How to fix it
_Public sources found at audit time by **Tavily**, summarized by **Nemotron 3 Ultra**. Every point carries a verbatim quote that code verified exists in the cited source; anything unsupported was removed. Treat these as leads._

### empty episode
- **Likely cause:** Episode timer expires immediately if episode_time_s is set to very low value [[2]](https://github.com/huggingface/lerobot/blob/main/docs/source/il_robots.mdx)  
  > "Duration of each data recording episode default: 60 seconds"
- **Fix:** Increase episode_time_s parameter to allow sufficient recording duration [[2]](https://github.com/huggingface/lerobot/blob/main/docs/source/il_robots.mdx)  
  > "episode_time_s=60 Duration of each data recording episode"

### no motion
- **Likely cause:** Recorded actions incorrectly saved as all zeros. [[2]](https://github.com/huggingface/lerobot/issues/2000)  
  > "the action recorded are all set to zero"

### length mismatch
- **Fix:** Ensure from_timestamp matches actual video PTS to eliminate drift [[5]](https://github.com/huggingface/lerobot/issues/3177)  
  > "This ensures from_timestamp always matches the actual video PTS eliminating drift regardless of episode count"
- **Fix:** Increase tolerance_s to mask underlying inaccuracy [[5]](https://github.com/huggingface/lerobot/issues/3177)  
  > "Increase tolerance_s e.g. 0.04 for 30fps or 0.06 for 15fps"

### dead sensor
- No public source with verifiable guidance was found.

### duplicate episode
- **Likely cause:** Duplicate episode indices cause data loss during split [[2]](https://github.com/huggingface/lerobot/issues/4982)  
  > "the second occurrence of 0 overwrites the first dictionary entry"
- **Fix:** Remove duplicate episode IDs before splitting datasets [[2]](https://github.com/huggingface/lerobot/issues/4982)  
  > "Removing duplicate IDs from the input avoids the issue"

### timestamp error
- **Likely cause:** Video muxer receives non-monotonic DTS values [[3]](https://github.com/huggingface/lerobot/issues/2158)  
  > "Application provided invalid, non monotonically increasing dts"
- **Fix:** Write v3 dataset in single shot avoiding cache re-entry [[3]](https://github.com/huggingface/lerobot/issues/2158)  
  > "embodied-data convert writes v3 in a single shot rather"
- **Fix:** Re-encode video with monotonic PTS to satisfy muxer [[3]](https://github.com/huggingface/lerobot/issues/2158)  
  > "re-encodes video with bf=0 g=2 monotonic PTS"

### human intervention
- No public source with verifiable guidance was found.
