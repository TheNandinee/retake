# Retake: community_dataset_v3 audit (verified)

Retake scanned all 1,754 datasets in `lerobot/community_dataset_v3`: 72,356 episodes,
364.6 hours of robot data from 488 contributors. On a laptop, overnight, $0 model spend.

- **7.1% of episodes (5,125) are exact motion duplicates** (every joint, every frame) of episodes elsewhere in the collection.
  777 duplicated recordings span different contributors.
  e.g. `Dangvi/soarm100_data` ep0 == `s20000s/soarm100_data` ep0 (max difference 0.000000)
- **763 episodes (1.05%) are objectively broken:** 338 empty fragments, 219 where the robot
  never moves, 138 duplicated within the same dataset, 71 with video/motion length mismatch,
  56 with a frozen joint sensor on a commanded arm, 15 with timestamps running backwards.
- Every finding comes from a deterministic check (no AI judgment) and is reproducible from this repo.
- Each finding type was verified by hand; see EXPERIMENTS.md E018–E020.
