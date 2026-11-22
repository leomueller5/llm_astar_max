# Adaptive alpha: paired offline comparison

Actual API calls: 0. Default cases use fixed fixtures, not new model responses.

| Case | Mode | Operations | Length | Relative to A* (%) | Median search (ms) | Alpha changes | Rebuilds | Valid |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| open_direct | original | 23 | 26.971 | 100.00 | 3.09 | 0 | 1 | 100% |
| open_direct | constant | 23 | 26.971 | 100.00 | 3.22 | 0 | 1 | 100% |
| open_direct | adaptive | 23 | 26.971 | 100.00 | 3.11 | 0 | 1 | 100% |
| open_direct | astar | 169 | 26.971 | 100.00 | 23.57 | 0 | 0 | 100% |
| open_detour | original | 243 | 22.828 | 103.77 | 16.75 | 0 | 1 | 100% |
| open_detour | constant | 299 | 22.000 | 100.00 | 22.97 | 0 | 0 | 100% |
| open_detour | adaptive | 243 | 22.828 | 103.77 | 16.70 | 0 | 1 | 100% |
| open_detour | astar | 23 | 22.000 | 100.00 | 3.38 | 0 | 0 | 100% |
| wall_bypass | original | 21 | 24.142 | 100.00 | 3.42 | 0 | 2 | 100% |
| wall_bypass | constant | 58 | 24.142 | 100.00 | 6.51 | 0 | 2 | 100% |
| wall_bypass | adaptive | 21 | 24.142 | 100.00 | 3.43 | 0 | 2 | 100% |
| wall_bypass | astar | 153 | 24.142 | 100.00 | 26.15 | 0 | 0 | 100% |
| wall_wrong_direction | original | 66 | 26.971 | 111.72 | 7.02 | 0 | 1 | 100% |
| wall_wrong_direction | constant | 74 | 24.142 | 100.00 | 7.80 | 0 | 1 | 100% |
| wall_wrong_direction | adaptive | 133 | 24.142 | 100.00 | 12.45 | 5 | 6 | 100% |
| wall_wrong_direction | astar | 153 | 24.142 | 100.00 | 27.02 | 0 | 0 | 100% |
| wall_unreachable_endpoint | original | 31 | 24.142 | 100.00 | 4.31 | 0 | 1 | 100% |
| wall_unreachable_endpoint | constant | 74 | 24.142 | 100.00 | 7.53 | 0 | 1 | 100% |
| wall_unreachable_endpoint | adaptive | 31 | 24.142 | 100.00 | 4.34 | 0 | 1 | 100% |
| wall_unreachable_endpoint | astar | 153 | 24.142 | 100.00 | 25.97 | 0 | 0 | 100% |
| public_prompt_example | original | 281 | 42.728 | 100.00 | 35.46 | 0 | 2 | 100% |
| public_prompt_example | constant | 402 | 42.728 | 100.00 | 50.45 | 0 | 2 | 100% |
| public_prompt_example | adaptive | 281 | 42.728 | 100.00 | 35.61 | 0 | 2 | 100% |
| public_prompt_example | astar | 323 | 42.728 | 100.00 | 72.69 | 0 | 0 | 100% |

These small, public/hand-authored cases are smoke tests, not generalization evidence.
Runtime includes measurement and queue maintenance. Alpha changes can reduce expansions while increasing runtime.
The original source is audited against the alpha=1 control outside timing. All three LLM variants use identical raw responses and progress logging.
The reference A* uses admissible Euclidean distance and identical legal edges, but rejects stale entries. Its operation/storage definitions differ from legacy LLM counters.
Positive waypoint weighting remains generally inadmissible; no optimality or fixed cost bound is guaranteed.
See comparison.json for full configuration, source hash, paths, and per-target progress; alpha_events.csv relates updates to progress.
