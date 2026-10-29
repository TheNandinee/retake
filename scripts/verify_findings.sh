#!/bin/bash
# Phase 4: visual verification of scan findings. Opens each image as it's made.
R=lerobot/community_dataset_v3

run() {
  echo; echo "================ $1 ================"
  uv run python -m scripts.11_inspect_episode "$R" "$2" "$3"
  img="results/inspect_${2//\//_}_ep$3.jpg"
  [ -f "$img" ] && open "$img" || echo "   (no image saved)"
}

run "1  no_motion"                      1g0rrr/demo2_frames_grab 11
run "2  empty_episode"                  7jep7/rook_to_d4_v5 4
run "3a dead_sensor"                    1lyz123576/so101_test 91

EP=$(uv run python -c "
import pandas as pd
h = pd.read_csv('evidence/scan_hard_issues.csv')
x = h[(h.type=='dead_sensor') & (h.dataset=='hamidkaloorazi/so100_bi_5s_gab_green_t')].iloc[0]
print(int(x.episode))")
echo; echo "   dead_sensor detail for biggest offender, episode $EP:"
uv run python -c "
import pandas as pd
h = pd.read_csv('evidence/scan_hard_issues.csv')
x = h[(h.type=='dead_sensor') & (h.dataset=='hamidkaloorazi/so100_bi_5s_gab_green_t')].iloc[0]
print('  ', x.detail)"
run "3b dead_sensor (biggest offender)" hamidkaloorazi/so100_bi_5s_gab_green_t "$EP"

run "4a duplicate within dataset (A)"   HuaihaiLyu/hamburger0509 84
run "4b duplicate within dataset (B)"   HuaihaiLyu/hamburger0509 85
run "5a cross-contributor (Dangvi)"     Dangvi/soarm100_data 0
run "5b cross-contributor (s20000s)"    s20000s/soarm100_data 0

echo; echo "================ 6  timestamp_error / length_mismatch (numbers are the evidence) ================"
uv run python -c "
import pandas as pd
h = pd.read_csv('evidence/scan_hard_issues.csv')
for t in ['timestamp_error', 'length_mismatch']:
    print(f'--- {t} ---')
    print(h[h.type==t][['dataset','episode','detail']].head(3).to_string(index=False)); print()
"
