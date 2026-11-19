# Frozen held-out benchmark

All methods reuse the same raw model outputs. Native timing excludes API latency. Whole-map paired bootstrap, 4,000 resamples. Work/path means exclude incomplete audits; capped timings and timeout counts are disclosed.

## team_maps

| Method | Valid audits | Mean ms | Mean unique | Total heap pops | Queue operations | GM cost/opt | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|
| geometry_consensus_quality | 200/200 | 6.81 | 629.7 | 1036.9 | 2229.9 | 1.00051 | 0 |
| cut105 | 200/200 | 5.42 | 656.1 | 1059.4 | 2296.8 | 1.00049 | 0 |
| hybrid_quality | 200/200 | 6.88 | 630.1 | 1037.2 | 2233.3 | 1.00047 | 0 |
| all_endpoints_quality | 200/200 | 7.02 | 631.0 | 1036.6 | 2234.8 | 1.00044 | 0 |
| geometry_best_quality | 200/200 | 6.81 | 629.7 | 1036.8 | 2229.3 | 1.00051 | 0 |

## challenging

| Method | Valid audits | Mean ms | Mean unique | Total heap pops | Queue operations | GM cost/opt | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|
| all_endpoints_quality | 20/20 | 9.44 | 849.9 | 1372.5 | 2899.3 | 1.00000 | 0 |
| hybrid_quality | 20/20 | 9.07 | 860.3 | 1382.2 | 2930.6 | 1.00000 | 0 |
| cut105 | 20/20 | 6.83 | 881.4 | 1398.5 | 2984.4 | 1.00000 | 0 |
| geometry_best_quality | 20/20 | 9.06 | 878.0 | 1400.0 | 2986.2 | 1.00000 | 0 |
| geometry_consensus_quality | 20/20 | 8.98 | 872.9 | 1394.7 | 2967.2 | 1.00000 | 0 |
