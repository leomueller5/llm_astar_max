# Frozen held-out benchmark

All methods reuse the same raw model outputs. Native timing excludes API latency. Whole-map paired bootstrap, 4,000 resamples. Work/path means exclude incomplete audits; capped timings and timeout counts are disclosed.

## team_maps

| Method | Valid audits | Mean ms | Mean unique | Total heap pops | Queue operations | GM cost/opt | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|
| always_hybrid | 20/20 | 5.24 | 349.9 | 798.5 | 1741.5 | 1.02680 | 0 |
| original | 20/20 | 123.43 | 996.8 | 1696.9 | 4394.4 | 1.03731 | 0 |
| constant05_goal2 | 20/20 | 10.14 | 1151.6 | 2578.2 | 5489.0 | 1.00303 | 0 |
| euclidean_anchor | 20/20 | 6.91 | 615.2 | 2089.5 | 4358.4 | 1.02670 | 0 |
| ww | 20/20 | 84.45 | 670.7 | 1177.4 | 2595.8 | 1.03217 | 0 |
| no_sharing | 20/20 | 4.99 | 307.8 | 702.9 | 1523.1 | 1.02558 | 0 |
| no_macros | 20/20 | 5.32 | 374.1 | 808.8 | 1800.0 | 1.01394 | 0 |
| adaptive_goal2 | 20/20 | 11.22 | 1259.0 | 2528.4 | 5456.9 | 1.00120 | 0 |
| adaptive | 20/20 | 11.95 | 1500.3 | 2528.9 | 5466.6 | 1.00000 | 0 |
| hybrid | 20/20 | 4.65 | 307.8 | 702.9 | 1523.1 | 1.02558 | 0 |
| original_hybrid_prompt | 20/20 | 186.81 | 1317.7 | 2026.2 | 4504.6 | 1.02053 | 0 |
| robust_original | 20/20 | 10.75 | 973.5 | 2824.6 | 5950.9 | 1.02349 | 0 |
| original_hybrid_consensus | 20/20 | 142.88 | 1072.4 | 1622.2 | 3674.7 | 1.01797 | 0 |
| original_bounds_prompt | 20/20 | 131.75 | 1050.0 | 1766.5 | 4479.1 | 1.04342 | 0 |

## challenging

| Method | Valid audits | Mean ms | Mean unique | Total heap pops | Queue operations | GM cost/opt | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|
| adaptive | 20/20 | 18.72 | 2589.3 | 3900.2 | 8116.6 | 1.00000 | 0 |
| no_macros | 20/20 | 8.45 | 591.5 | 1704.8 | 3650.4 | 1.00852 | 0 |
| original | 20/20 | 478.38 | 2021.2 | 3274.4 | 7230.7 | 1.02398 | 0 |
| original_hybrid_prompt | 19/20 | 642.23 | 2286.3 | 3438.2 | 7310.6 | 1.01919 | 1 |
| hybrid | 20/20 | 8.32 | 537.7 | 1658.5 | 3463.6 | 1.00996 | 0 |
| always_hybrid | 20/20 | 7.29 | 474.0 | 1361.7 | 2861.7 | 1.01181 | 0 |
| no_sharing | 20/20 | 8.59 | 537.7 | 1658.5 | 3463.6 | 1.00996 | 0 |
| euclidean_anchor | 20/20 | 14.97 | 1700.2 | 4618.0 | 9402.1 | 1.01195 | 0 |
| robust_original | 20/20 | 21.52 | 1991.1 | 5772.9 | 11789.7 | 1.01425 | 0 |
| ww | 20/20 | 451.01 | 1758.7 | 2881.8 | 5980.6 | 1.02688 | 0 |
| constant05_goal2 | 20/20 | 20.69 | 2027.1 | 5599.5 | 11459.0 | 1.00938 | 0 |
| original_hybrid_consensus | 19/20 | 663.24 | 2263.3 | 3391.2 | 7113.5 | 1.01687 | 1 |
| adaptive_goal2 | 20/20 | 21.90 | 2048.8 | 5480.1 | 11281.8 | 1.01072 | 0 |
| original_bounds_prompt | 20/20 | 492.09 | 2069.4 | 3273.1 | 7380.3 | 1.02104 | 0 |
