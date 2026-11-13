# Adaptive alpha: paired offline comparison

Actual API calls: 0. Default cases use fixed fixtures, not new model responses.

| Case | Mode | Heap pops | Expansions | Distinct | Duplicate pops | Reopens | Length | Relative to A* (%) | Median search (ms) | Alpha changes | Rebuilds | Valid |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| open_direct | original | 23 | 23 | 23 | 0 | 0 | 26.971 | 100.00 | 3.22 | 0 | 1 | 100% |
| open_direct | constant | 23 | 23 | 23 | 0 | 0 | 26.971 | 100.00 | 3.28 | 0 | 1 | 100% |
| open_direct | adaptive | 205 | 169 | 169 | 36 | 0 | 26.971 | 100.00 | 14.52 | 0 | 1 | 100% |
| open_direct | astar | 203 | 169 | 169 | 34 | 0 | 26.971 | 100.00 | 24.33 | 0 | 0 | 100% |
| open_direct | adaptive_before | 23 | 23 | 23 | 0 | 0 | 26.971 | 100.00 | 3.27 | 0 | 1 | 100% |
| open_direct | adaptive_engine_only | 23 | 23 | 23 | 0 | 0 | 26.971 | 100.00 | 3.24 | 0 | 1 | 100% |
| open_direct | adaptive_goal_only | 205 | 205 | 169 | 36 | 0 | 26.971 | 100.00 | 15.63 | 0 | 1 | 100% |
| open_direct | original_fixed_engine | 23 | 23 | 23 | 0 | 0 | 26.971 | 100.00 | 3.23 | 0 | 1 | 100% |
| open_direct | constant_fixed_engine | 23 | 23 | 23 | 0 | 0 | 26.971 | 100.00 | 3.25 | 0 | 1 | 100% |
| open_direct | constant_goal_only | 205 | 169 | 169 | 36 | 0 | 26.971 | 100.00 | 14.25 | 0 | 1 | 100% |
| open_direct | fixed_waypoints_goal_only | 205 | 169 | 169 | 36 | 0 | 26.971 | 100.00 | 14.28 | 0 | 1 | 100% |
| open_detour | original | 243 | 243 | 171 | 72 | 0 | 22.828 | 103.77 | 17.01 | 0 | 1 | 100% |
| open_detour | constant | 299 | 299 | 230 | 69 | 0 | 22.000 | 100.00 | 23.27 | 0 | 0 | 100% |
| open_detour | adaptive | 255 | 179 | 172 | 76 | 7 | 22.000 | 100.00 | 14.90 | 0 | 1 | 100% |
| open_detour | astar | 23 | 23 | 23 | 0 | 0 | 22.000 | 100.00 | 3.45 | 0 | 0 | 100% |
| open_detour | adaptive_before | 243 | 243 | 171 | 72 | 0 | 22.828 | 103.77 | 16.97 | 0 | 1 | 100% |
| open_detour | adaptive_engine_only | 254 | 178 | 171 | 76 | 7 | 22.828 | 103.77 | 14.75 | 0 | 1 | 100% |
| open_detour | adaptive_goal_only | 246 | 246 | 172 | 74 | 0 | 22.000 | 100.00 | 17.26 | 0 | 1 | 100% |
| open_detour | original_fixed_engine | 254 | 178 | 171 | 76 | 7 | 22.828 | 103.77 | 14.80 | 0 | 1 | 100% |
| open_detour | constant_fixed_engine | 299 | 230 | 230 | 69 | 0 | 22.000 | 100.00 | 18.10 | 0 | 0 | 100% |
| open_detour | constant_goal_only | 299 | 230 | 230 | 69 | 0 | 22.000 | 100.00 | 18.13 | 0 | 0 | 100% |
| open_detour | fixed_waypoints_goal_only | 255 | 179 | 172 | 76 | 7 | 22.000 | 100.00 | 14.81 | 0 | 1 | 100% |
| wall_bypass | original | 21 | 21 | 21 | 0 | 0 | 24.142 | 100.00 | 3.53 | 0 | 2 | 100% |
| wall_bypass | constant | 58 | 58 | 47 | 11 | 0 | 24.142 | 100.00 | 6.62 | 0 | 2 | 100% |
| wall_bypass | adaptive | 185 | 153 | 153 | 32 | 0 | 24.142 | 100.00 | 15.67 | 0 | 2 | 100% |
| wall_bypass | astar | 175 | 153 | 153 | 22 | 0 | 24.142 | 100.00 | 26.51 | 0 | 0 | 100% |
| wall_bypass | adaptive_before | 21 | 21 | 21 | 0 | 0 | 24.142 | 100.00 | 3.55 | 0 | 2 | 100% |
| wall_bypass | adaptive_engine_only | 21 | 21 | 21 | 0 | 0 | 24.142 | 100.00 | 3.55 | 0 | 2 | 100% |
| wall_bypass | adaptive_goal_only | 185 | 185 | 153 | 32 | 0 | 24.142 | 100.00 | 17.91 | 0 | 2 | 100% |
| wall_bypass | original_fixed_engine | 21 | 21 | 21 | 0 | 0 | 24.142 | 100.00 | 3.53 | 0 | 2 | 100% |
| wall_bypass | constant_fixed_engine | 53 | 49 | 47 | 4 | 2 | 24.142 | 100.00 | 6.02 | 0 | 2 | 100% |
| wall_bypass | constant_goal_only | 187 | 158 | 153 | 29 | 5 | 24.142 | 100.00 | 16.12 | 0 | 2 | 100% |
| wall_bypass | fixed_waypoints_goal_only | 185 | 153 | 153 | 32 | 0 | 24.142 | 100.00 | 15.67 | 0 | 2 | 100% |
| wall_wrong_direction | original | 66 | 66 | 54 | 12 | 0 | 26.971 | 111.72 | 6.93 | 0 | 1 | 100% |
| wall_wrong_direction | constant | 74 | 74 | 55 | 19 | 0 | 24.142 | 100.00 | 7.57 | 0 | 1 | 100% |
| wall_wrong_direction | adaptive | 185 | 153 | 153 | 32 | 0 | 24.142 | 100.00 | 15.47 | 0 | 1 | 100% |
| wall_wrong_direction | astar | 175 | 153 | 153 | 22 | 0 | 24.142 | 100.00 | 26.14 | 0 | 0 | 100% |
| wall_wrong_direction | adaptive_before | 133 | 133 | 90 | 43 | 0 | 24.142 | 100.00 | 12.20 | 5 | 6 | 100% |
| wall_wrong_direction | adaptive_engine_only | 177 | 144 | 86 | 33 | 58 | 24.142 | 100.00 | 13.59 | 5 | 6 | 100% |
| wall_wrong_direction | adaptive_goal_only | 185 | 185 | 153 | 32 | 0 | 24.142 | 100.00 | 17.64 | 0 | 1 | 100% |
| wall_wrong_direction | original_fixed_engine | 97 | 78 | 49 | 19 | 29 | 26.385 | 109.29 | 8.27 | 0 | 1 | 100% |
| wall_wrong_direction | constant_fixed_engine | 77 | 67 | 55 | 10 | 12 | 24.142 | 100.00 | 7.35 | 0 | 1 | 100% |
| wall_wrong_direction | constant_goal_only | 182 | 157 | 153 | 25 | 4 | 24.142 | 100.00 | 15.76 | 0 | 1 | 100% |
| wall_wrong_direction | fixed_waypoints_goal_only | 185 | 153 | 153 | 32 | 0 | 24.142 | 100.00 | 15.44 | 0 | 1 | 100% |
| wall_unreachable_endpoint | original | 31 | 31 | 30 | 1 | 0 | 24.142 | 100.00 | 4.38 | 0 | 1 | 100% |
| wall_unreachable_endpoint | constant | 74 | 74 | 55 | 19 | 0 | 24.142 | 100.00 | 7.63 | 0 | 1 | 100% |
| wall_unreachable_endpoint | adaptive | 185 | 154 | 153 | 31 | 1 | 24.142 | 100.00 | 15.70 | 0 | 1 | 100% |
| wall_unreachable_endpoint | astar | 175 | 153 | 153 | 22 | 0 | 24.142 | 100.00 | 26.34 | 0 | 0 | 100% |
| wall_unreachable_endpoint | adaptive_before | 31 | 31 | 30 | 1 | 0 | 24.142 | 100.00 | 4.38 | 0 | 1 | 100% |
| wall_unreachable_endpoint | adaptive_engine_only | 35 | 34 | 31 | 1 | 3 | 24.142 | 100.00 | 4.72 | 0 | 1 | 100% |
| wall_unreachable_endpoint | adaptive_goal_only | 184 | 184 | 153 | 31 | 0 | 24.142 | 100.00 | 17.89 | 0 | 1 | 100% |
| wall_unreachable_endpoint | original_fixed_engine | 35 | 34 | 31 | 1 | 3 | 24.142 | 100.00 | 4.70 | 0 | 1 | 100% |
| wall_unreachable_endpoint | constant_fixed_engine | 80 | 67 | 55 | 13 | 12 | 24.142 | 100.00 | 7.45 | 0 | 1 | 100% |
| wall_unreachable_endpoint | constant_goal_only | 180 | 155 | 153 | 25 | 2 | 24.142 | 100.00 | 15.81 | 0 | 1 | 100% |
| wall_unreachable_endpoint | fixed_waypoints_goal_only | 185 | 154 | 153 | 31 | 1 | 24.142 | 100.00 | 15.68 | 0 | 1 | 100% |
| public_prompt_example | original | 281 | 281 | 182 | 99 | 0 | 42.728 | 100.00 | 35.44 | 0 | 2 | 100% |
| public_prompt_example | constant | 402 | 402 | 266 | 136 | 0 | 42.728 | 100.00 | 50.76 | 0 | 2 | 100% |
| public_prompt_example | adaptive | 462 | 367 | 323 | 95 | 44 | 42.728 | 100.00 | 46.94 | 8 | 10 | 100% |
| public_prompt_example | astar | 468 | 323 | 323 | 145 | 0 | 42.728 | 100.00 | 72.31 | 0 | 0 | 100% |
| public_prompt_example | adaptive_before | 281 | 281 | 182 | 99 | 0 | 42.728 | 100.00 | 35.23 | 0 | 2 | 100% |
| public_prompt_example | adaptive_engine_only | 311 | 257 | 213 | 54 | 44 | 42.728 | 100.00 | 33.49 | 9 | 10 | 100% |
| public_prompt_example | adaptive_goal_only | 473 | 473 | 321 | 152 | 0 | 42.728 | 100.00 | 59.81 | 0 | 2 | 100% |
| public_prompt_example | original_fixed_engine | 330 | 234 | 182 | 96 | 52 | 42.728 | 100.00 | 30.57 | 0 | 2 | 100% |
| public_prompt_example | constant_fixed_engine | 384 | 281 | 266 | 103 | 15 | 42.728 | 100.00 | 36.57 | 0 | 2 | 100% |
| public_prompt_example | constant_goal_only | 467 | 338 | 323 | 129 | 15 | 42.728 | 100.00 | 43.84 | 0 | 2 | 100% |
| public_prompt_example | fixed_waypoints_goal_only | 513 | 375 | 323 | 138 | 52 | 42.728 | 100.00 | 48.29 | 0 | 2 | 100% |

These small, public/hand-authored cases are smoke tests, not generalization evidence.
Runtime includes measurement and queue maintenance. Alpha changes can reduce expansions while increasing runtime.
The original source is audited against the alpha=1 legacy-engine control outside timing. All LLM variants use identical raw responses and progress logging.
Original final score: g+2h; constant 0.5: g+1.5h; corrected adaptive: g+h at final goal. Controls isolate these scoring and engine differences.
Operations count every heap pop. Distinct states, accepted expansions, skipped stale entries, and legitimate reopens are reported separately. Standard A* does not store infinite-cost states, unlike legacy storage counting.
Positive waypoint weighting remains generally inadmissible; no optimality or fixed cost bound is guaranteed.
See comparison.json for full configuration, source hash, paths, and per-target progress; alpha_events.csv relates updates to progress.
