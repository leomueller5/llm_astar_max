# Session5 measured tables

Exact model: `gpt-4o-mini-2024-07-18`. All algorithm comparisons reuse the same real response; repeated timing runs are not independent maps. These are development/validation results, not fresh held-out LLM evidence.

|Direct original variant|Mean heap pops|Mean distinct states|Cost/opt GM|Offline compute ms|
|---|---:|---:|---:|---:|
|original|349.6|230.8|1.02491|10.075|
|no_guidance|320.8|208.8|1.01997|9.781|
|noop|349.6|230.8|1.02491|10.105|
|egor_gated|330.1|225.3|1.02789|9.716|
|egor_ungated|422.2|294.4|1.02167|12.480|
|restart_gated|340.2|225.3|1.01959|9.822|
|shuffle_gated|332.2|226.8|1.03409|9.757|
|random_gated|365.4|244.3|1.03453|10.478|

|Paired development pop ratio|Estimate|95% map-bootstrap interval|
|---|---:|---|
|egor_gated/original|0.9442|[0.7422897140546336, 1.0727555905879607]|
|egor_gated/no_guidance|1.0290|[0.9306564669450331, 1.4376180492251598]|
|egor_gated/egor_ungated|0.7819|[0.36331254753702297, 1.0]|
|egor_gated/restart_gated|0.9703|[0.9299650132611027, 0.9868186698742912]|
|egor_gated/shuffle_gated|0.9937|[0.9404244966212976, 1.029157667386609]|
|egor_gated/random_gated|0.9034|[0.6488097221666339, 1.0805687744835215]|

All intervals exploratory/unadjusted. API latency excluded from offline compute times.

API usage: {"cap_usd": 3.0, "accounted_usd": 0.0287154, "held_worst_case_usd": 0.1585152, "remaining_authorized_usd": 2.8127694, "attempts": 121, "successes": 113, "prompt_tokens": 92696, "completion_tokens": 27693, "reasoning_tokens": 0, "cached_input_tokens": 24064}

Latency summary seconds: {"mean_initial_api_seconds": 7.679396295803599, "mean_correction_api_seconds_per_query": 2.0925623333780097, "mean_actual_online_loop_seconds": 2.130932620796375, "mean_derived_initial_plus_online_seconds": 9.810328916599975}
