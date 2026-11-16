# Session 3: real waypoint contribution

Algorithms frozen in commit79b96f3 before Session3 validation. No old held-out test reuse. Real validation is the established20-map split used by prior sessions; fresh30-map/240-case fixtures are new geometry, but helpful points are oracle fixtures, not actual model responses. No paid calls. CIs:2000 whole-map bootstrap resamples, secondary comparisons exploratory/unadjusted.

## validation

All times include fresh graph construction, guidance preprocessing and search. Cached response parsing excluded equally from core variants; see separate public-API timings. Medians within query first; arithmetic mean across queries.

| Method | Mean ms | Median ms | Distinct | Pops | GM cost / optimal | Valid / solvable | Hint queries accepted |
|---|---:|---:|---:|---:|---:|---:|---:|
| original_indexed | 5.5859 | 0.9883 | 165.70 | 256.87 | 1.02698 | 600/600 | 0 |
| indexed_astar | 1.4099 | 0.9821 | 275.06 | 350.49 | 1.00000 | 600/600 | 0 |
| scheduled_wa2 | 0.6827 | 0.3118 | 127.70 | 267.38 | 1.01607 | 600/600 | 0 |
| witness_only | 0.3378 | 0.0364 | 59.88 | 129.18 | 1.00362 | 600/600 | 0 |
| witness_cf | 0.3572 | 0.0364 | 59.70 | 128.99 | 1.00362 | 600/600 | 0 |
| guide_off | 0.3436 | 0.0373 | 59.88 | 129.18 | 1.00362 | 600/600 | 0 |
| seed_cut | 0.3434 | 0.0370 | 58.87 | 126.40 | 1.00451 | 600/600 | 58 |
| seed_lazy | 0.3412 | 0.0376 | 58.67 | 126.04 | 1.00465 | 600/600 | 58 |
| geometry_lazy | 0.3469 | 0.0376 | 58.04 | 127.40 | 1.00527 | 600/600 | 114 |
| seed_cut_wrong | 0.3393 | 0.0374 | 58.30 | 122.04 | 1.00487 | 600/600 | 18 |
| seed_cut_random | 0.3443 | 0.0376 | 58.58 | 129.23 | 1.00526 | 600/600 | 54 |
| seed_cut_shuffle | 0.3421 | 0.0373 | 58.87 | 126.40 | 1.00451 | 600/600 | 58 |
| potential_visible | 0.4338 | 0.0375 | 78.07 | 135.90 | 1.00276 | 600/600 | 64 |
| potential_geometry | 0.5276 | 0.0375 | 97.36 | 136.71 | 1.00196 | 600/600 | 132 |
| potential_random | 0.4645 | 0.0372 | 82.19 | 141.35 | 1.00308 | 600/600 | 90 |
| uniform15 | 0.3708 | 0.0376 | 68.98 | 124.36 | 1.00135 | 600/600 | 0 |

| Candidate | Time / matched off (95% CI) | Time / geometric seeding (95% CI) | Fewer / more states | Shorter / longer paths |
|---|---:|---:|---:|---:|
| seed_cut | 0.9993 [0.9680,1.0253] | 0.9897 [0.9617,1.0305] | 22/11 | 2/14 |
| seed_lazy | 0.9929 [0.9635,1.0184] | 0.9834 [0.9550,1.0238] | 23/10 | 2/15 |
| potential_visible | 1.2626 [1.1442,1.4428] | 1.2505 [1.1258,1.4512] | 0/63 | 14/2 |
| potential_geometry | 1.5354 [1.3445,1.8233] | 1.5207 [1.3219,1.8348] | 3/129 | 30/3 |
| potential_random | 1.3520 [1.2232,1.5269] | 1.3390 [1.2012,1.5474] | 0/86 | 17/11 |
| seed_cut_wrong | 0.9875 [0.9403,1.0212] | 0.9780 [0.9394,1.0183] | 15/0 | 0/9 |
| seed_cut_random | 1.0022 [0.9656,1.0262] | 0.9925 [0.9708,1.0158] | 24/6 | 3/15 |

Worst-case cost ratios, candidate acceptance counts, search-only/preparation times and per-family numbers are in report_statistics.json. A lower heuristic can improve quality without demonstrating informative LLM content; compare uniform15 and randomized/geometric potentials. Ranking deliberately ignores input order; shuffle must match counts/costs exactly.

## fresh

All times include fresh graph construction, guidance preprocessing and search. Cached response parsing excluded equally from core variants; see separate public-API timings. Medians within query first; arithmetic mean across queries.

| Method | Mean ms | Median ms | Distinct | Pops | GM cost / optimal | Valid / solvable | Hint queries accepted |
|---|---:|---:|---:|---:|---:|---:|---:|
| original_indexed | 138.0725 | 1.5571 | 694.66 | 1113.33 | 1.01054 | 216/216 | 0 |
| indexed_astar | 5.8478 | 3.1787 | 1182.88 | 1562.22 | 1.00000 | 216/216 | 0 |
| scheduled_wa2 | 4.0195 | 0.6174 | 685.15 | 2193.67 | 1.00823 | 216/216 | 0 |
| witness_only | 3.8710 | 0.0641 | 652.57 | 2150.40 | 1.00721 | 216/216 | 0 |
| witness_cf | 3.8974 | 0.0634 | 651.44 | 2148.99 | 1.00702 | 216/216 | 0 |
| guide_off | 3.9199 | 0.0655 | 652.57 | 2150.40 | 1.00721 | 216/216 | 0 |
| seed_cut | 3.9182 | 0.0645 | 652.22 | 2149.75 | 1.00721 | 216/216 | 5 |
| seed_lazy | 3.9244 | 0.0635 | 652.16 | 2149.69 | 1.00721 | 216/216 | 5 |
| geometry_lazy | 4.0030 | 0.0640 | 650.20 | 2138.15 | 1.00685 | 216/216 | 44 |
| seed_cut_wrong | 3.9627 | 0.0637 | 650.43 | 2173.67 | 1.00778 | 216/216 | 24 |
| seed_cut_random | 3.7706 | 0.0663 | 651.48 | 1929.89 | 1.00859 | 216/216 | 21 |
| seed_cut_shuffle | 3.9326 | 0.0644 | 652.22 | 2149.75 | 1.00721 | 216/216 | 5 |
| potential_visible | 3.9522 | 0.0636 | 659.34 | 2155.95 | 1.00714 | 216/216 | 6 |
| potential_geometry | 3.5588 | 0.0650 | 682.62 | 1222.87 | 1.00612 | 216/216 | 44 |
| potential_random | 3.9030 | 0.0641 | 718.05 | 1609.35 | 1.00621 | 216/216 | 44 |
| uniform15 | 3.7244 | 0.0643 | 714.58 | 1641.53 | 1.00258 | 216/216 | 0 |

| Candidate | Time / matched off (95% CI) | Time / geometric seeding (95% CI) | Fewer / more states | Shorter / longer paths |
|---|---:|---:|---:|---:|
| seed_cut | 0.9996 [0.9970,1.0043] | 0.9788 [0.9562,0.9924] | 2/0 | 0/0 |
| seed_lazy | 1.0011 [0.9983,1.0067] | 0.9803 [0.9594,0.9947] | 3/0 | 0/0 |
| potential_visible | 1.0083 [1.0001,1.0341] | 0.9873 [0.9698,1.0049] | 0/6 | 1/0 |
| potential_geometry | 0.9079 [0.7591,1.1741] | 0.8890 [0.7516,1.1363] | 0/20 | 8/0 |
| potential_random | 0.9957 [0.8172,1.2939] | 0.9750 [0.8096,1.2526] | 0/31 | 9/5 |
| seed_cut_wrong | 1.0109 [0.9690,1.0533] | 0.9899 [0.9387,1.0245] | 12/0 | 4/4 |
| seed_cut_random | 0.9619 [0.9071,1.0093] | 0.9419 [0.8983,0.9796] | 4/5 | 3/4 |

Worst-case cost ratios, candidate acceptance counts, search-only/preparation times and per-family numbers are in report_statistics.json. A lower heuristic can improve quality without demonstrating informative LLM content; compare uniform15 and randomized/geometric potentials. Ranking deliberately ignores input order; shuffle must match counts/costs exactly.

## Cached public interface

40 fixed validation queries,7 randomized interleaved repeats; query parse/copy, initial cached response processing, fresh geometry, guidance and search included. Construction/imports/network/rendering excluded uniformly. Guidance-disabled methods skip model parsing. No paid calls.

```json
{
  "witness": {
    "mean_case_median_ms": 0.3743010573089123
  },
  "seed_off": {
    "mean_case_median_ms": 0.37119268672540784
  },
  "seed_cut": {
    "mean_case_median_ms": 0.4353312135208398
  },
  "quality": {
    "mean_case_median_ms": 0.5353406595531851
  }
}
```

## Independent verification

```json
{
  "validation": {
    "seed_cut": {
      "independently_valid_paths": 600,
      "correct_no_path": 0
    },
    "seed_lazy": {
      "independently_valid_paths": 600,
      "correct_no_path": 0
    },
    "potential_visible": {
      "independently_valid_paths": 600,
      "correct_no_path": 0
    }
  },
  "fresh": {
    "seed_cut": {
      "independently_valid_paths": 216,
      "correct_no_path": 24
    },
    "seed_lazy": {
      "independently_valid_paths": 216,
      "correct_no_path": 24
    },
    "potential_visible": {
      "independently_valid_paths": 216,
      "correct_no_path": 24
    }
  }
}
```

The global bound of new methods is2, not optimality. Exact geometry certificates remain optimal. Verified seeds only add real grid paths; start remains OPEN, stale snapshots are skipped, improved paths reopen, and macro parents are replaced on improvements. Original source/scoring preserved. No claim of LLM-specific efficiency is allowed if matched no-guidance/geometric/random controls are competitive.
