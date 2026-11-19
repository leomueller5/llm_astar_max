# Frozen held-out benchmark

All methods reuse the same raw model outputs. Native timing excludes API latency. Whole-map paired bootstrap, 4,000 resamples. Work/path means exclude incomplete audits; capped timings and timeout counts are disclosed.

## team_maps

| Method | Valid audits | Mean ms | Mean unique | Total heap pops | Queue operations | GM cost/opt | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|
| wa2 | 200/200 | 6.11 | 894.3 | 2742.1 | 5737.8 | 1.02653 | 0 |
| original | 200/200 | 183.41 | 1209.1 | 2050.9 | 4681.2 | 1.03604 | 0 |
| hybrid_quality | 200/200 | 6.91 | 630.1 | 1037.2 | 2233.3 | 1.00047 | 0 |
| all_endpoints | 200/200 | 5.57 | 379.4 | 955.1 | 2038.3 | 1.01881 | 0 |
| cut2 | 200/200 | 4.74 | 474.9 | 1166.5 | 2483.3 | 1.01856 | 0 |
| geometry_consensus | 200/200 | 5.50 | 393.0 | 999.4 | 2122.2 | 1.01772 | 0 |
| geometry_best | 200/200 | 5.59 | 395.6 | 1046.0 | 2218.0 | 1.01805 | 0 |
| hybrid_first | 200/200 | 5.61 | 392.9 | 1006.2 | 2140.1 | 1.01935 | 0 |
| hybrid | 200/200 | 5.61 | 393.0 | 1007.4 | 2142.1 | 1.01852 | 0 |
| witness | 200/200 | 5.17 | 870.9 | 2668.9 | 5578.7 | 1.02572 | 0 |
| robust_original | 200/200 | 13.04 | 1193.7 | 3494.1 | 7269.4 | 1.02403 | 0 |
| cut105 | 200/200 | 5.45 | 656.1 | 1059.4 | 2296.8 | 1.00049 | 0 |
| astar | 200/200 | 8.69 | 1725.0 | 2329.6 | 4871.0 | 1.00000 | 0 |
| llm_only | 200/200 | 6.17 | 473.6 | 1249.1 | 2657.8 | 1.02668 | 0 |

## challenging

| Method | Valid audits | Mean ms | Mean unique | Total heap pops | Queue operations | GM cost/opt | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|
| geometry_consensus | 20/20 | 8.14 | 555.5 | 1691.5 | 3542.2 | 1.00852 | 0 |
| cut105 | 20/20 | 6.89 | 881.4 | 1398.5 | 2984.4 | 1.00000 | 0 |
| geometry_best | 20/20 | 8.17 | 560.6 | 1696.8 | 3561.0 | 1.00852 | 0 |
| original | 20/20 | 481.89 | 2021.2 | 3274.4 | 7230.7 | 1.02398 | 0 |
| wa2 | 20/20 | 11.09 | 1730.5 | 4666.1 | 9549.4 | 1.02334 | 0 |
| all_endpoints | 20/20 | 8.58 | 534.3 | 1669.7 | 3477.1 | 1.01062 | 0 |
| robust_original | 20/20 | 21.71 | 1991.1 | 5772.9 | 11789.7 | 1.01425 | 0 |
| hybrid_quality | 20/20 | 9.18 | 860.3 | 1382.2 | 2930.6 | 1.00000 | 0 |
| hybrid | 20/20 | 8.08 | 537.7 | 1658.5 | 3463.6 | 1.00996 | 0 |
| llm_only | 20/20 | 7.43 | 559.0 | 1666.4 | 3504.8 | 1.01512 | 0 |
| cut2 | 20/20 | 6.11 | 596.8 | 1851.5 | 3868.7 | 1.00852 | 0 |
| hybrid_first | 20/20 | 8.13 | 544.1 | 1665.0 | 3482.9 | 1.00996 | 0 |
| witness | 20/20 | 8.97 | 1613.7 | 4091.7 | 8347.5 | 1.01583 | 0 |
| astar | 20/20 | 12.94 | 2584.4 | 3519.9 | 7230.0 | 1.00000 | 0 |

