# Frozen Session 4 evaluation tables

Times are means of per-query medians; every query has randomized repeated trials and two fixed excluded warmups. All values include cold map setup and all method processing. Model generation and network latency are unavailable/excluded; actual API calls and costs are zero. Synthetic/oracle results are not real LLM performance.

## final_fresh

|Method|Mean ms|Median ms|Unique union|Heap pops incl. local|Cost/opt GM|Reachable valid|Timeout trials|
|---|---:|---:|---:|---:|---:|---:|---:|
|cut_none|18.1522|4.2115|1814.0681818181818|5019.022727272727|1.00798|40/40|0|
|weighted|45.1372|10.5489|4614.931818181818|16029.25|1.00854|40/40|0|
|local_raw|14.4577|1.9352|1402.3636363636363|3621.3636363636365|1.01414|40/40|0|
|cut_raw|17.4350|1.9444|1634.25|4264.454545454545|1.02218|40/40|0|
|cut_dynamic|13.6591|3.7092|1189.8863636363637|3032.0227272727275|1.00049|40/40|0|
|astar|45.7814|15.7081|6098.681818181818|8358.045454545454|1.00000|40/40|0|
|cut_wrong|19.4198|4.3976|1814.0681818181818|5019.022727272727|1.00798|40/40|0|
|cut_octile|44.6223|10.1784|4415.5|16038.59090909091|1.01260|40/40|0|
|witness|40.2874|8.4587|4486.818181818182|15733.75|1.00854|40/40|0|
|cut_noseed|19.1410|4.9806|1821.4772727272727|5018.931818181818|1.00885|40/40|0|
|witness_raw|41.3293|8.6330|4486.818181818182|15733.75|1.00854|40/40|0|
|local_none|19.6306|4.6597|1827.5454545454545|5063.045454545455|1.00798|40/40|0|
|local_portfolio|15.8153|2.0250|1353.909090909091|3518|1.01177|40/40|0|
|cut_random|19.8362|4.3888|1814.0681818181818|5019.022727272727|1.00798|40/40|0|
|cut_oracle|11.9810|1.2397|1033.8636363636363|2778.181818181818|1.00000|40/40|0|
|cut_nogeometry|17.4527|4.8218|1821.4772727272727|5018.931818181818|1.00885|40/40|0|

Timeout means are censored lower bounds on full completion time. Unique counts are component unions where available; roadmap/hierarchy exploratory work is separately accounted in its own artifacts. Heap pushes and rebuild details require the separate instrumented audit.

|Paired time ratio|Estimate|95% map CI|
|---|---:|---|
|cut_none/weighted|0.4022|[0.1396, 0.8407]|
|cut_none/witness|0.4506|[0.1574, 0.9333]|
|local_raw/cut_none|0.7965|[0.5160, 0.9304]|
|local_raw/local_none|0.7365|[0.4256, 0.9029]|
|cut_raw/cut_none|0.9605|[0.7130, 1.1097]|
|cut_dynamic/cut_none|0.7525|[0.4091, 0.9230]|
|cut_wrong/cut_none|1.0698|[0.9898, 1.2539]|
|local_none/cut_none|1.0814|[0.9731, 1.2976]|
|local_portfolio/local_none|0.8056|[0.5039, 0.9407]|
|local_portfolio/local_raw|1.0939|[0.9408, 1.3367]|
|cut_random/cut_none|1.0928|[0.9747, 1.2878]|
|cut_oracle/cut_none|0.6600|[0.2309, 0.8653]|

Intervals are exploratory and not corrected for multiple comparisons. See statistics.json for all comparisons and per-family results.

## final_cached_validation

|Method|Mean ms|Median ms|Unique union|Heap pops incl. local|Cost/opt GM|Reachable valid|Timeout trials|
|---|---:|---:|---:|---:|---:|---:|---:|
|cut_raw|0.3185|0.0421|18.331666666666667|35.315|1.00466|600/600|0|
|cut_octile|0.4375|0.0419|58.41|123.85|1.00443|600/600|0|
|cut_none|0.3215|0.0421|19.46|38.13|1.00474|600/600|0|
|astar|1.4157|0.9981|275.065|350.485|1.00000|600/600|0|
|witness|0.3436|0.0407|59.885|129.175|1.00362|600/600|0|
|weighted|0.7735|0.3512|127.7|267.38|1.01607|600/600|0|
|cut_wrong|0.3191|0.0419|18.246666666666666|35.49|1.00469|600/600|0|
|witness_raw|0.3705|0.0404|59.695|128.985|1.00362|600/600|0|
|cut_random|0.3253|0.0417|18.826666666666668|36.473333333333336|1.00647|600/600|0|
|cut_oracle|0.1482|0.0419|0|0|1.00000|600/600|0|
|local_none|0.3556|0.0427|24.79|49.805|1.00474|600/600|0|
|local_raw|0.3398|0.0426|21.733333333333334|41.17|1.00507|600/600|0|

Timeout means are censored lower bounds on full completion time. Unique counts are component unions where available; roadmap/hierarchy exploratory work is separately accounted in its own artifacts. Heap pushes and rebuild details require the separate instrumented audit.

|Paired time ratio|Estimate|95% map CI|
|---|---:|---|
|cut_raw/cut_none|0.9904|[0.9630, 1.0168]|
|cut_none/weighted|0.4157|[0.2658, 0.5843]|
|cut_none/witness|0.9358|[0.6647, 1.2770]|
|cut_wrong/cut_none|0.9924|[0.9601, 1.0218]|
|cut_random/cut_none|1.0117|[0.9856, 1.0357]|
|cut_oracle/cut_none|0.4610|[0.3545, 0.6107]|
|local_none/cut_none|1.1060|[1.0377, 1.1598]|
|local_raw/cut_none|1.0568|[1.0249, 1.0907]|
|local_raw/local_none|0.9555|[0.8998, 1.0273]|

Intervals are exploratory and not corrected for multiple comparisons. See statistics.json for all comparisons and per-family results.

## final_native

|Method|Mean ms|Median ms|Unique union|Heap pops incl. local|Cost/opt GM|Reachable valid|Timeout trials|
|---|---:|---:|---:|---:|---:|---:|---:|
|original_matched|581.6679|96.5768|missing/censored|missing/censored|1.00885|17/20|12|
|original_native|1203.2935|2002.5670|missing/censored|missing/censored|1.00088|10/20|36|
|weighted|26.3656|9.4707|3248.090909090909|14258.772727272728|1.00636|20/20|0|
|witness|21.9606|8.5069|3193.5454545454545|14075|1.00636|20/20|0|
|cut_none|10.2984|4.0029|1057.2727272727273|3099.7272727272725|1.00415|20/20|0|
|local_raw|7.2510|1.6673|688.3636363636364|1964.2272727272727|1.01166|20/20|0|
|local_none|10.4808|4.4464|1069.1363636363637|3143.7272727272725|1.00415|20/20|0|
|local_portfolio|7.4221|1.7467|682.6363636363636|1961.7727272727273|1.01228|20/20|0|

Timeout means are censored lower bounds on full completion time. Unique counts are component unions where available; roadmap/hierarchy exploratory work is separately accounted in its own artifacts. Heap pushes and rebuild details require the separate instrumented audit.

|Paired time ratio|Estimate|95% map CI|
|---|---:|---|
|cut_none/weighted|0.3906|[0.1432, 0.9303]|
|cut_none/witness|0.4690|[0.1761, 1.0656]|
|local_raw/cut_none|0.7041|[0.3788, 0.9143]|
|local_raw/local_none|0.6918|[0.3706, 0.9029]|
|local_none/cut_none|1.0177|[1.0069, 1.0401]|
|local_portfolio/local_none|0.7082|[0.3910, 0.9140]|
|local_portfolio/local_raw|1.0236|[0.9644, 1.0819]|

Intervals are exploratory and not corrected for multiple comparisons. See statistics.json for all comparisons and per-family results.

## final_fresh_local_controls

|Method|Mean ms|Median ms|Unique union|Heap pops incl. local|Cost/opt GM|Reachable valid|Timeout trials|
|---|---:|---:|---:|---:|---:|---:|---:|
|local_noshortcut|13.4762|2.1537|1412.3636363636363|3638.068181818182|1.03053|40/40|0|
|local_random|17.1854|4.4460|1822.6363636363637|5039.204545454545|1.00798|40/40|0|
|local_wrong|17.0752|3.5449|1815.6136363636363|5010.636363636364|1.02067|40/40|0|
|local_shuffled|16.8627|3.5780|1802.8636363636363|4976.181818181818|1.00832|40/40|0|
|local_raw|13.6303|1.8718|1402.3636363636363|3621.3636363636365|1.01414|40/40|0|
|local_none|17.1832|4.6436|1827.5454545454545|5063.045454545455|1.00798|40/40|0|
|local_norepair|16.6344|1.8710|1767.7272727272727|4909.295454545455|1.01120|40/40|0|

Timeout means are censored lower bounds on full completion time. Unique counts are component unions where available; roadmap/hierarchy exploratory work is separately accounted in its own artifacts. Heap pushes and rebuild details require the separate instrumented audit.

|Paired time ratio|Estimate|95% map CI|
|---|---:|---|
|local_noshortcut/local_raw|0.9887|[0.9434, 1.0046]|
|local_random/local_raw|1.2608|[1.0689, 1.8987]|
|local_wrong/local_raw|1.2527|[1.0744, 1.8759]|
|local_shuffled/local_raw|1.2371|[1.0722, 1.7958]|
|local_raw/local_none|0.7932|[0.5280, 0.9309]|
|local_norepair/local_raw|1.2204|[1.0422, 1.7961]|

Intervals are exploratory and not corrected for multiple comparisons. See statistics.json for all comparisons and per-family results.

## final_cached_local_controls

|Method|Mean ms|Median ms|Unique union|Heap pops incl. local|Cost/opt GM|Reachable valid|Timeout trials|
|---|---:|---:|---:|---:|---:|---:|---:|
|local_noshortcut|0.3325|0.0367|22.183333333333334|42.49166666666667|1.00553|600/600|0|
|local_random|0.3278|0.0366|21.566666666666666|40.84166666666667|1.01294|600/600|0|
|local_wrong|0.3290|0.0367|21.733333333333334|41.458333333333336|1.00594|600/600|0|
|local_shuffled|0.3398|0.0368|22.913333333333334|43.971666666666664|1.00474|600/600|0|
|local_raw|0.3294|0.0367|21.733333333333334|41.17|1.00507|600/600|0|
|local_none|0.3485|0.0370|24.79|49.805|1.00474|600/600|0|
|local_norepair|0.3174|0.0365|19.163333333333334|37.75333333333333|1.00521|600/600|0|

Timeout means are censored lower bounds on full completion time. Unique counts are component unions where available; roadmap/hierarchy exploratory work is separately accounted in its own artifacts. Heap pushes and rebuild details require the separate instrumented audit.

|Paired time ratio|Estimate|95% map CI|
|---|---:|---|
|local_noshortcut/local_raw|1.0093|[0.9956, 1.0255]|
|local_random/local_raw|0.9951|[0.9705, 1.0231]|
|local_wrong/local_raw|0.9987|[0.9796, 1.0182]|
|local_shuffled/local_raw|1.0314|[0.9982, 1.0706]|
|local_raw/local_none|0.9452|[0.8901, 1.0187]|
|local_norepair/local_raw|0.9634|[0.9397, 0.9891]|

Intervals are exploratory and not corrected for multiple comparisons. See statistics.json for all comparisons and per-family results.

