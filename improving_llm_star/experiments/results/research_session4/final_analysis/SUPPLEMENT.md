# Additional diagnostics

## final_fresh

|Method|Mean pop ratio / A*|Mean global g-entry ratio / A*|Mean cost / optimal|
|---|---:|---:|---:|
|weighted|1.0835|0.5991|1.00874|
|witness|0.8986|0.4524|1.00874|
|cut_none|0.5468|0.2884|1.00845|
|local_none|0.5606|0.2884|1.00845|
|local_raw|0.2831|0.1527|1.01469|
|local_portfolio|0.2500|0.1230|1.01193|
|cut_oracle|0.1731|0.0846|1.00000|

The g-entry ratio excludes local transient structures and DP/cache bytes; it is not a claim of byte-memory reduction.

## final_cached_validation

|Method|Mean pop ratio / A*|Mean global g-entry ratio / A*|Mean cost / optimal|
|---|---:|---:|---:|
|weighted|0.5833|0.5981|1.01686|
|witness|0.1922|0.1625|1.00376|
|cut_none|0.0530|0.0775|1.00516|
|local_none|0.0877|0.0680|1.00516|
|local_raw|0.0642|0.0705|1.00549|
|cut_oracle|0.0000|0.0102|1.00000|

The g-entry ratio excludes local transient structures and DP/cache bytes; it is not a claim of byte-memory reduction.

## Separate instrumented memory/heap pass

Ten predetermined fresh query0 cases: open, random walls, rooms, tree mazes and bottlenecks at both sizes. Traced allocations include Python objects and any native buffers exposed to tracemalloc; this is not total native memory or process RSS. No instrumented times enter native runtime tables.

|Method|Mean peak MiB|Max peak MiB|Heap pushes|Heap pops|Heapify items|
|---|---:|---:|---:|---:|---:|
|cut_none|1.877|14.047|3093.2|2991.2|1.3|
|cut_oracle|1.424|13.200|2489.1|2485.0|0.1|
|local_none|1.874|14.047|3165.2|3029.6|1.3|
|local_portfolio|1.529|14.070|2792.5|2692.8|0.1|
|local_raw|1.649|14.055|2840.1|2730.2|1.1|
|weighted|2.403|11.845|4682.1|4439.1|0.0|
|witness|2.372|11.979|4527.3|4393.7|0.0|
