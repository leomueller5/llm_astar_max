# Research session 2 — measured results

Policies frozen in commit `87c3310` before new test generation. Primary runtime policy: `witness_only`. Its gains are geometric; it does not use LLM guidance. All runs offline. Fresh final timing stages ran sequentially.

## fresh_core

Fresh: 80 new maps /640 deterministic fixture cases (helpful fixture is oracle-derived, not real LLM). Opened confirmation: 600 cached observations /20 maps already inspected in Session 1; not a new independent holdout. Mean times are arithmetic means of within-case repetition medians.

| Variant | Mean ms | Median ms | Distinct states | Heap pops | GM cost / optimum | Valid / solvable | Exact certs | LLM routes used |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| indexed_astar | 2.8371 | 0.8397 | 581.83 | 743.72 | 1.00000 | 576/576 | 0 | 0 |
| indexed_cf | 2.0321 | 0.3790 | 327.61 | 718.02 | 1.00535 | 576/576 | 254 | 22 |
| lean_cf | 1.6745 | 0.2804 | 327.61 | 718.02 | 1.00535 | 576/576 | 254 | 22 |
| old_cf | 12.1143 | 0.9579 | 327.61 | 718.02 | 1.00535 | 576/576 | 254 | 22 |
| original_indexed | 53.5733 | 0.8682 | 346.48 | 553.01 | 1.00781 | 576/576 | 0 | 0 |
| scheduled_wa2 | 1.7073 | 0.3622 | 341.11 | 733.10 | 1.00642 | 576/576 | 0 | 0 |
| witness_cf | 1.6531 | 0.1427 | 319.46 | 705.31 | 1.00438 | 576/576 | 317 | 1 |
| witness_chain | 1.5383 | 0.1155 | 294.71 | 650.51 | 1.00380 | 576/576 | 317 | 66 |
| witness_frontier | 1.6062 | 0.1389 | 302.35 | 667.04 | 1.00445 | 576/576 | 317 | 61 |
| witness_only | 1.6356 | 0.1237 | 319.49 | 705.35 | 1.00446 | 576/576 | 316 | 0 |

Mean-time ratio / matched WA2, 95% whole-map bootstrap intervals (2,000 resamples):

- old_cf: 7.0957 [3.9844, 8.9003]; paired GM ratio 2.2593.
- lean_cf: 0.9808 [0.9496, 0.9978]; paired GM ratio 0.4849.
- witness_only: 0.9580 [0.9051, 0.9873]; paired GM ratio 0.3877.
- witness_cf: 0.9682 [0.9179, 0.9963]; paired GM ratio 0.3969.
- witness_chain: 0.9010 [0.8298, 0.9439]; paired GM ratio 0.3614.
- witness_frontier: 0.9408 [0.8691, 0.9800]; paired GM ratio 0.3831.

LLM incremental runtime / identical witness-only geometry:

- witness_cf: 1.0107 [1.0058, 1.0184]; more-cost cases 0; more-distinct cases 0.
- witness_chain: 0.9405 [0.9017, 0.9682]; more-cost cases 1; more-distinct cases 0.
- witness_frontier: 0.9820 [0.9488, 1.0045]; more-cost cases 4; more-distinct cases 0.

| Variant | p95 cost ratio | Max cost ratio | Longer than original | More distinct than original |
|---|---:|---:|---:|---:|
| indexed_astar | 1.00000 | 1.00000 | 0 | 523 |
| indexed_cf | 1.03446 | 1.35270 | 10 | 84 |
| lean_cf | 1.03446 | 1.35270 | 10 | 84 |
| old_cf | 1.03446 | 1.35270 | 10 | 84 |
| original_indexed | 1.04482 | 1.41605 | 0 | 0 |
| scheduled_wa2 | 1.03446 | 1.35270 | 21 | 105 |
| witness_cf | 1.01856 | 1.35270 | 10 | 81 |
| witness_chain | 1.00676 | 1.38416 | 2 | 26 |
| witness_frontier | 1.01225 | 1.35632 | 5 | 33 |
| witness_only | 1.01856 | 1.35270 | 11 | 81 |

Per-family mean case-median ms (equal case weighting within family):

| Family | WA2 | Witness only | Exact LLM | Frontier LLM |
|---|---:|---:|---:|---:|
| corridors | 2.0779 | 1.9272 | 1.9804 | 1.9528 |
| dead_ends | 0.3950 | 0.4200 | 0.4352 | 0.3820 |
| dense | 0.4972 | 0.5134 | 0.5271 | 0.4739 |
| disconnected | 2.6211 | 2.6266 | 2.6272 | 2.6255 |
| enclosed | 0.1374 | 0.0366 | 0.0405 | 0.0406 |
| large_maze | 9.7567 | 9.8576 | 9.8964 | 9.6187 |
| large_random | 0.9834 | 0.4459 | 0.4541 | 0.3555 |
| maze | 0.3255 | 0.4548 | 0.4891 | 0.5485 |
| open | 0.1072 | 0.0125 | 0.0126 | 0.0125 |
| random_walls | 0.1714 | 0.0615 | 0.0679 | 0.0523 |

The frozen-original soft-guidance algorithm has no comparable route-acceptance counter; its zero in that column means not applicable. Frozen-original exceptions on unreachable cases are reported separately: 64. New methods must match A* reachability; see independent verification.

Tail cost ratios and fallback/source breakdowns are saved in `report_statistics.json`; no claim of per-case runtime dominance. `original_indexed` retains frozen algorithm logic with the new geometry; it is not native-original timing.

## opened_cached_confirmation

Fresh: 80 new maps /640 deterministic fixture cases (helpful fixture is oracle-derived, not real LLM). Opened confirmation: 600 cached observations /20 maps already inspected in Session 1; not a new independent holdout. Mean times are arithmetic means of within-case repetition medians.

| Variant | Mean ms | Median ms | Distinct states | Heap pops | GM cost / optimum | Valid / solvable | Exact certs | LLM routes used |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| indexed_astar | 1.7120 | 1.2512 | 339.74 | 433.13 | 1.00000 | 600/600 | 0 | 0 |
| indexed_cf | 1.4598 | 0.9264 | 168.99 | 365.68 | 1.01035 | 600/600 | 137 | 62 |
| lean_cf | 0.9455 | 0.4462 | 168.50 | 362.10 | 1.01090 | 600/600 | 128 | 53 |
| old_cf | 3.1204 | 1.7397 | 168.99 | 365.68 | 1.01035 | 600/600 | 137 | 62 |
| original_indexed | 7.8036 | 1.8906 | 215.98 | 343.92 | 1.02254 | 600/600 | 0 | 0 |
| scheduled_wa2 | 0.9223 | 0.4319 | 178.56 | 380.81 | 1.01447 | 600/600 | 0 | 0 |
| witness_cf | 0.5662 | 0.0443 | 100.66 | 209.68 | 1.00496 | 600/600 | 408 | 0 |
| witness_chain | 0.5481 | 0.0451 | 100.49 | 209.52 | 1.00520 | 600/600 | 408 | 3 |
| witness_frontier | 0.5643 | 0.0447 | 99.77 | 208.04 | 1.00463 | 600/600 | 408 | 9 |
| witness_only | 0.5421 | 0.0446 | 100.66 | 209.68 | 1.00496 | 600/600 | 408 | 0 |

Mean-time ratio / matched WA2, 95% whole-map bootstrap intervals (2,000 resamples):

- old_cf: 3.3835 [2.6093, 4.3611]; paired GM ratio 3.3753.
- lean_cf: 1.0253 [0.9854, 1.0589]; paired GM ratio 0.7993.
- witness_only: 0.5878 [0.4276, 0.7312]; paired GM ratio 0.2175.
- witness_cf: 0.6139 [0.4498, 0.7629]; paired GM ratio 0.2236.
- witness_chain: 0.5943 [0.4336, 0.7378]; paired GM ratio 0.2192.
- witness_frontier: 0.6119 [0.4454, 0.7616]; paired GM ratio 0.2226.

LLM incremental runtime / identical witness-only geometry:

- witness_cf: 1.0445 [1.0337, 1.0587]; more-cost cases 0; more-distinct cases 0.
- witness_chain: 1.0111 [1.0038, 1.0178]; more-cost cases 2; more-distinct cases 0.
- witness_frontier: 1.0410 [1.0284, 1.0546]; more-cost cases 2; more-distinct cases 0.

| Variant | p95 cost ratio | Max cost ratio | Longer than original | More distinct than original |
|---|---:|---:|---:|---:|
| indexed_astar | 1.00000 | 1.00000 | 0 | 526 |
| indexed_cf | 1.07745 | 1.33397 | 45 | 113 |
| lean_cf | 1.07745 | 1.33397 | 46 | 116 |
| old_cf | 1.07745 | 1.33397 | 45 | 113 |
| original_indexed | 1.10406 | 1.30985 | 0 | 0 |
| scheduled_wa2 | 1.08688 | 1.33397 | 62 | 134 |
| witness_cf | 1.04776 | 1.15408 | 24 | 46 |
| witness_chain | 1.04776 | 1.19411 | 25 | 45 |
| witness_frontier | 1.03829 | 1.15772 | 22 | 41 |
| witness_only | 1.04776 | 1.15408 | 24 | 46 |

Per-family mean case-median ms (equal case weighting within family):

| Family | WA2 | Witness only | Exact LLM | Frontier LLM |
|---|---:|---:|---:|---:|
| cached_public | 0.9223 | 0.5421 | 0.5662 | 0.5643 |

The frozen-original soft-guidance algorithm has no comparable route-acceptance counter; its zero in that column means not applicable. Frozen-original exceptions on unreachable cases are reported separately: 0. New methods must match A* reachability; see independent verification.

Tail cost ratios and fallback/source breakdowns are saved in `report_statistics.json`; no claim of per-case runtime dominance. `original_indexed` retains frozen algorithm logic with the new geometry; it is not native-original timing.

## Native public interface on fresh map-balanced sample

Public structured-query API, parsing/copying/geometry/certificates/search/validation included; object construction/imports/rendering/network excluded uniformly. Independent post-timer checking identical for all methods. Cached response only; native original has original collision code.

| Variant | Mean observed/censored ms | Median observed/censored ms | Maximum observed/censored ms | Timeout trials |
|---|---:|---:|---:|---:|
| original_native | 202.4151 | 24.9249 | 2008.1596 | 35 |
| astar_public | 2.9557 | 1.1598 | 25.6180 | 0 |
| wa2_public | 1.8557 | 0.5665 | 20.2547 | 0 |
| old_cf_public | 12.5600 | 1.5217 | 233.3498 | 0 |
| witness_exact_public | 1.8127 | 0.2356 | 20.5381 | 0 |
| witness_only_public | 1.7679 | 0.1737 | 20.4930 | 0 |
| witness_frontier_public | 1.8077 | 0.2340 | 20.5036 | 0 |

Uniform 2-second per-trial timeout for ALL native interface methods. If any trials are censored, the observed mean is only a runtime LOWER BOUND, not the complete mean. This native safeguard was added after an interrupted first attempt; the full core evaluation has no such cutoff and is unchanged.


## Profiling and allocation scope

120 fixed development cases. Profiling is separate from uninstrumented timing. 24 fixed tracemalloc cases, GC collected before each; imports/native-library allocations excluded. Python peak allocations are not process RAM.

| Mode | Mean peak Python KiB | Mean geometry init ms | Mean prep ms | Mean search ms |
|---|---:|---:|---:|---:|
| old_cf | 219.60 | 0.0064 | 1.5170 | 1.2697 |
| indexed_cf | 196.72 | 0.0058 | 0.6410 | 0.5796 |
| compressed_cf | 174.29 | 0.0066 | 0.0681 | 0.5903 |
| lean_cf | 171.04 | 0.0063 | 0.0715 | 0.5210 |
| witness_cf | 136.88 | 0.0059 | 0.0435 | 0.3241 |
| witness_only | 135.05 | 0.0058 | 0.0298 | 0.3183 |
| scheduled_wa2 | 183.53 | 0.0060 | 0.0000 | 0.5899 |

The original cProfile places most cumulative cost in adjacency and collision; heap primitives are under 1% of that instrumented profile. Cumulative times overlap and cannot be summed. Exact compare U<=L is a scalar operation too small to isolate reliably; it remains inside timed preprocessing. Phase dictionaries, source configurations, allocation data and full profile listings are preserved.

## Correctness and interpretation

```json
{
  "fresh_core": {
    "witness_only": {
      "independent_valid_paths": 576,
      "optimal_certificates": 316,
      "correctly_exhausted_unreachable": 64
    },
    "witness_cf": {
      "independent_valid_paths": 576,
      "optimal_certificates": 317,
      "correctly_exhausted_unreachable": 64
    },
    "witness_chain": {
      "independent_valid_paths": 576,
      "optimal_certificates": 317,
      "correctly_exhausted_unreachable": 64
    },
    "witness_frontier": {
      "independent_valid_paths": 576,
      "optimal_certificates": 317,
      "correctly_exhausted_unreachable": 64
    },
    "frozen_original_unreachable_exceptions": 64
  },
  "opened_cached_confirmation": {
    "witness_only": {
      "independent_valid_paths": 600,
      "optimal_certificates": 408,
      "correctly_exhausted_unreachable": 0
    },
    "witness_cf": {
      "independent_valid_paths": 600,
      "optimal_certificates": 408,
      "correctly_exhausted_unreachable": 0
    },
    "witness_chain": {
      "independent_valid_paths": 600,
      "optimal_certificates": 408,
      "correctly_exhausted_unreachable": 0
    },
    "witness_frontier": {
      "independent_valid_paths": 600,
      "optimal_certificates": 408,
      "correctly_exhausted_unreachable": 0
    },
    "frozen_original_unreachable_exceptions": 0,
    "frozen_Table1_matches": 600
  }
}
```

Witness certificates are optimal, otherwise fallback is weight-2 bounded. Frontier variants remain weight-2 bounded and can regress against the control. All probe, failed-preparation and fallback costs are charged. Unit-edge tests, continuous-piece tests, wall tests and heap pops are distinct counters.

The primary speed improvement is geometric, not an established LLM advantage. Oracle corner fixtures show best-case guidance potential; cached model outputs determine real-response evidence. Opened confirmation is never relabelled fresh test data. See session2/README.md and EXPERIMENT_LOG.md for rejected approaches, exact commands, frozen policy and limitations.
