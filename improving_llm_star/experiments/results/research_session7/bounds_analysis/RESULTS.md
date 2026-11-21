# Frozen Session7 results

Planning CPU uses cached advice, fresh preprocessing, five native trials. First-use prompt/image and actual API latency reported separately. Native timeouts are right-censored; their measured cap contributes to the mean, never treated as zero. Work/path means use completed audits with coverage shown. Whole-geometry paired bootstrap4000, nominal intervals without multiplicity correction.

## primary

| Method | Valid | Mean ms | Pops | Push+pop | Unique | GM cost/opt | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|
| matched_uniform105 | 10/10 | 109.93 | 7789.6 | 16067.9 | 4688.6 | 1.00000 | 0 |
| original | 5/10 | 2673.11 | 1519.8 | 3628.8 | 1046.8 | 1.01922 | 5 |
| original_bounds | 5/10 | 2755.75 | 1649.0 | 4020.6 | 1220.8 | 1.02671 | 5 |
| rh_image105 | 10/10 | 153.42 | 7025.7 | 15891.7 | 6185.0 | 1.00000 | 0 |
| robust_original | 10/10 | 253.16 | 34732.0 | 69918.4 | 9818.8 | 1.01084 | 0 |
| vm_geo105 | 10/10 | 108.30 | 7682.8 | 15656.1 | 4574.0 | 1.00000 | 0 |

## large

| Method | Valid | Mean ms | Pops | Push+pop | Unique | GM cost/opt | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|
| matched_uniform105 | 10/10 | 333.09 | 23099.7 | 46820.3 | 10484.9 | 1.00070 | 0 |
| original | 3/10 | 3618.78 | 1801.3 | 4205.0 | 1261.0 | 1.03110 | 7 |
| original_bounds | 4/10 | 3369.84 | 3400.0 | 8785.8 | 2108.8 | 1.04650 | 6 |
| rh_image105 | 10/10 | 403.32 | 23419.6 | 51655.9 | 15159.8 | 1.00035 | 0 |
| robust_original | 10/10 | 492.59 | 72259.0 | 145263.1 | 19212.3 | 1.01377 | 0 |
| vm_geo105 | 10/10 | 243.53 | 22899.5 | 46049.2 | 10278.3 | 1.00070 | 0 |
