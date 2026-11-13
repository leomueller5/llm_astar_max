# Held-out research results — 13 November 2026

Policy frozen before test; no paid API calls. Distinct expansions and raw heap pops have different definitions. Timings below use shared collision graphs; fresh-query timings follow separately.

## heldout_cached

All-case expansion means include correctly exhausted disconnected maps. Path ratios use solvable cases only.

| Variant | Mean distinct | Mean heap pops | GM cost / optimal | p95 cost ratio | Shared median ms | Mean preprocessing ms |
|---|---:|---:|---:|---:|---:|---:|
| original | 215.98 | 343.92 | 1.02254 | 1.10406 | 1.469 | 0.000 |
| alpha05 | 277.14 | 441.43 | 1.00408 | 1.02951 | 0.437 | 0.001 |
| current_adaptive | 344.38 | 494.72 | 1.00076 | 1.00000 | 1.356 | 0.000 |
| astar | 339.74 | 433.13 | 1.00000 | 1.00000 | 0.475 | 0.000 |
| wa2 | 178.56 | 380.81 | 1.01447 | 1.08688 | 0.205 | 0.000 |
| direct_only | 174.67 | 375.84 | 1.01177 | 1.07876 | 0.156 | 0.011 |
| sieved_no_repair | 171.47 | 368.10 | 1.01127 | 1.07745 | 0.224 | 0.072 |
| sieved_no_cut | 174.41 | 375.58 | 1.01177 | 1.07876 | 0.301 | 0.128 |
| sieved_cert | 168.99 | 365.68 | 1.01035 | 1.07745 | 0.419 | 0.258 |

95% bootstrap intervals for selected/control mean distinct-expansion ratios (2,000 whole-map resamples):

- original: [0.6958, 0.8512] (solvable cases).
- wa2: [0.9103, 0.9705] (solvable cases).
- direct_only: [0.9458, 0.9825] (solvable cases).

| Variant | Mean stale pops | Mean duplicate pops | Mean rebuilds | Mean storage counter | Mean alpha events | Mean switches |
|---|---:|---:|---:|---:|---:|---:|
| original | 0.00 | 127.94 | 3.60 | 330.20 | 0.00 | 3.60 |
| alpha05 | 146.40 | 146.40 | 3.56 | 351.81 | 4.77 | 3.77 |
| current_adaptive | 130.99 | 130.99 | 5.31 | 464.35 | 6.35 | 3.26 |
| astar | 93.39 | 93.39 | 0.00 | 411.13 | 1.00 | 0.00 |
| wa2 | 149.64 | 149.64 | 0.00 | 256.56 | 1.00 | 0.00 |
| direct_only | 148.91 | 148.91 | 0.00 | 244.81 | 0.00 | 0.00 |
| sieved_no_repair | 146.13 | 146.13 | 0.00 | 238.18 | 0.00 | 0.00 |
| sieved_no_cut | 148.91 | 148.91 | 0.00 | 243.81 | 0.00 | 0.00 |
| sieved_cert | 145.78 | 145.78 | 0.00 | 231.72 | 0.00 | 0.00 |

Alpha events include initial/reset events where recorded, not just value changes. Storage counters are historical algorithm outputs, not comparable byte-level peak memory; candidate DAG and geometry caches add memory outside these counters. Stale/duplicate labels may overlap; the original does not classify stale snapshots separately and its recorded zero is not proof of their absence. No claim of reduced RAM usage is supported.


Regressions, selected versus controls: `{"original": {"more_distinct": 113, "longer_path": 45, "solvable": 600}, "wa2": {"more_distinct": 0, "longer_path": 0, "solvable": 600}, "direct_only": {"more_distinct": 0, "longer_path": 0, "solvable": 600}}`.

| Condition | Original distinct | WA2 distinct | Selected distinct |
|---|---:|---:|---:|
| cot | 210.19 | 178.56 | 167.38 |
| repe | 225.71 | 178.56 | 171.53 |
| standard | 212.06 | 178.56 | 168.04 |
## heldout_synthetic

All-case expansion means include correctly exhausted disconnected maps. Path ratios use solvable cases only.

| Variant | Mean distinct | Mean heap pops | GM cost / optimal | p95 cost ratio | Shared median ms | Mean preprocessing ms |
|---|---:|---:|---:|---:|---:|---:|
| original | 126.83 | 186.69 | 1.00683 | 1.04828 | 0.203 | 0.000 |
| alpha05 | 163.85 | 238.49 | 1.00282 | 1.00000 | 0.147 | 0.001 |
| current_adaptive | 173.76 | 225.09 | 1.00058 | 1.00000 | 0.464 | 0.000 |
| astar | 173.25 | 213.08 | 1.00000 | 1.00000 | 0.168 | 0.000 |
| wa2 | 122.31 | 210.40 | 1.00532 | 1.03734 | 0.071 | 0.000 |
| direct_only | 113.83 | 199.77 | 1.00483 | 1.03734 | 0.050 | 0.010 |
| sieved_no_repair | 113.83 | 199.77 | 1.00483 | 1.03734 | 0.069 | 0.021 |
| sieved_no_cut | 113.83 | 199.77 | 1.00483 | 1.03734 | 0.062 | 0.022 |
| sieved_cert | 113.58 | 199.52 | 1.00483 | 1.03734 | 0.069 | 0.035 |

95% bootstrap intervals for selected/control mean distinct-expansion ratios (2,000 whole-map resamples):

- original: [0.5447, 0.9334] (solvable cases).
- wa2: [0.6688, 0.9394] (solvable cases).
- direct_only: [0.9808, 1.0000] (solvable cases).

| Variant | Mean stale pops | Mean duplicate pops | Mean rebuilds | Mean storage counter | Mean alpha events | Mean switches |
|---|---:|---:|---:|---:|---:|---:|
| original | 0.00 | 59.86 | 0.47 | 161.37 | 0.00 | 0.41 |
| alpha05 | 67.18 | 67.18 | 0.58 | 204.09 | 1.59 | 0.59 |
| current_adaptive | 50.11 | 50.11 | 0.63 | 264.41 | 1.64 | 0.41 |
| astar | 39.83 | 39.83 | 0.00 | 211.15 | 1.00 | 0.00 |
| wa2 | 68.42 | 68.42 | 0.00 | 162.88 | 1.00 | 0.00 |
| direct_only | 67.40 | 67.40 | 0.00 | 135.12 | 0.00 | 0.00 |
| sieved_no_repair | 67.40 | 67.40 | 0.00 | 135.12 | 0.00 | 0.00 |
| sieved_no_cut | 67.40 | 67.40 | 0.00 | 135.12 | 0.00 | 0.00 |
| sieved_cert | 67.40 | 67.40 | 0.00 | 134.33 | 0.00 | 0.00 |

Alpha events include initial/reset events where recorded, not just value changes. Storage counters are historical algorithm outputs, not comparable byte-level peak memory; candidate DAG and geometry caches add memory outside these counters. Stale/duplicate labels may overlap; the original does not classify stale snapshots separately and its recorded zero is not proof of their absence. No claim of reduced RAM usage is supported.


Regressions, selected versus controls: `{"original": {"more_distinct": 12, "longer_path": 2, "solvable": 168}, "wa2": {"more_distinct": 0, "longer_path": 0, "solvable": 168}, "direct_only": {"more_distinct": 0, "longer_path": 0, "solvable": 168}}`.

| Condition | Original distinct | WA2 distinct | Selected distinct |
|---|---:|---:|---:|
| corridors | 266.54 | 269.50 | 262.50 |
| dead_ends | 50.54 | 51.83 | 30.50 |
| dense | 21.33 | 21.50 | 14.83 |
| disconnected | 466.33 | 466.33 | 466.33 |
| enclosed | 61.96 | 19.17 | 8.17 |
| maze | 76.54 | 76.67 | 76.67 |
| open | 16.17 | 16.17 | 0.00 |
| random_walls | 55.25 | 57.33 | 49.67 |

## Fresh-query CPU timing

40 held-out standard-prompt queries, indices 0 and 5 per map; 3 shuffled repetitions; cached response only. Selected includes inherited initial processing and fresh lazy geometry. Controls include fresh geometry. No precomputed graph supplied to search. Imports/model network excluded.

| Variant | Median ms | Mean ms |
|---|---:|---:|
| original | 38.565 | 58.765 |
| wa2 | 1.570 | 2.995 |
| direct_only | 1.418 | 3.285 |
| selected | 2.239 | 3.692 |

Selected is slower than matched WA2 and direct-only controls. The larger speedup over native original combines search changes with geometry/engine engineering and cannot be attributed to waypoint selection alone.

Independent verification:

```json
{
  "heldout_cached": {
    "independently_valid_paths": 600,
    "exact_optimal_certificates": 137,
    "correct_no_path": 0,
    "frozen_Table1_matches": 600
  },
  "heldout_synthetic": {
    "independently_valid_paths": 168,
    "exact_optimal_certificates": 82,
    "correct_no_path": 24,
    "frozen_Table1_matches": 0
  }
}
```

Additional graph preparation CPU totals and clustered comparisons are in `report_statistics.json`. No confidence interval treats three prompt styles as independent map samples.
