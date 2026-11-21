# Session7: spatial residual heuristics and bounded A*

Primary research candidate: `llmastar.research.spatial_planner.SpatialResidualAStar`
(LLM-RH*). Original and frozenSession6 implementations remain unchanged. See
`THEORY.md` for equations/proof/pseudocode and `EXPERIMENT_LOG.md` for negative
findings. All final settings are recorded before test generation in
`../../results/research_session7/frozen_manifest.json`.

No general extra LLM benefit is established by the development/validation work.
Strong fixed-weight and geometric-macro controls are essential. Do not present
fewer stale heap pops as fewer actual expansions or lower total computation.

## Offline use

```python
from llmastar.research.spatial_planner import SpatialResidualAStar
planner = SpatialResidualAStar(bound=1.05, alpha=0.22640953779865894, side=4)
result = planner.searching(query, predictions=cached_json_response)
# Original keys: operation, storage, length, llm_output (compatibility endpoints).
# New fields: path, validity, stale/reopened states, heuristic/guidance timing,
# coverage, regional trust, heap work, and optional trace.
```

The query is the original structured dictionary or its JSON representation.
No API call occurs unless an explicit provider object is supplied. A provider
implements `predict(query, region_descriptions)` and returns the prediction object
or JSON string. Failures retain complete geometric search with neutral advice.
Natural-language query parsing is not silently charged as another model call;
convert to the original structured input first, as done by the benchmark.

Control: `SpatialResidualAStar(source="none", bound=1.05, base_weight=1.05)`.
This is uniform Weighted A* with the same engine. With base_weight1and no advice
it is A*. Geometry-only interval controls use source`geometry_midpoint` or
`geometry_upper`. Optional `macros=True` reuses the verified geometric transitions;
its no-model control has exact work/cost parity against frozen VM.

## Budget policy

Exact model: `gpt-4o-mini-2024-07-18`; temperature0,seed20261119 for all new
collections. Original-waypoint cap1000, frozenVM cap384, regional-cost cap1400.
Caps differ because outputs differ; actual tokens, image usage, cost and latency
are recorded. Model confidence is not a calibrated probability.

Session7Client uses the SAME Session5SQLite ledger, restores Session6and7portable
exports, writes only Session7's export, and reserves the entire128kcontext cost
plus max output BEFORE each attempt. Bounded retries/backoff; unknown failures
remain held. Reasoning is counted within output, never double-billed. The secret
is loaded only inside the process from the authorized configuration, never printed
or copied. Do not reset/delete the ledger to obtain another allowance.

Collections are explicitly paid and are not part of offline reproduction. Search
replay imports no online provider and makes zero requests. Existing tested `.venv`
and repository dependencies suffice; no new runtime dependency was needed.

## Reproduce the frozen comparison without API calls

Run from repository root; use a NEW output directory to preserve past results.

```sh
.venv/bin/python -m pytest improving_llm_star/tests -q

.venv/bin/python improving_llm_star/experiments/research/session7/native_benchmark.py \
  --cases improving_llm_star/experiments/results/research_session7/heldout_all.json.gz \
  --baselines improving_llm_star/experiments/results/research_session7/heldout_baselines/responses.json.gz \
  --costs improving_llm_star/experiments/results/research_session7/heldout_cost/responses.json.gz \
  --icl improving_llm_star/experiments/results/research_session7/heldout_icl/responses.json.gz \
  --repeats 5 --shuffle-seeds 5 --timeout 5 --output /tmp/session7-replay
```

The native test uses fresh query-local geometry, regional parsing, calibration,
optional portfolio and search in every trial; cached advice is incoming data.
Prompt/image CPU and actual online latency are separate measured quantities, not
free first-use computation. One warmup, five native repetitions, randomized
method order, separate heap audit. Every method gets the same five-second cap;
timeouts are censored, not zero-cost successes. Five shuffle seeds are averaged
within query; confidence intervals resample whole canonical map geometries.

Main test:80queries/40freshgeometries at generator sizes97/131/163/197.
Large stress:20queries/20freshgeometries at227/263. No geometry overlaps with
recognized prior or current training/validation sets. Data integrity and source
hashes are recorded. Development contains6previously seen geometries (permitted
only as development); it is not represented as wholly untouched data.

Some analyses use explicitly labelled oracle information. Optimal remaining
costs are computed offline only; model prompts never receive test solutions.
Teacher examples are fixed on separate development maps, never evaluation maps.

## Independent audits and diagnostic studies

The full-path checker uses Shapely segments independently of the search geometry.
`independent_reference.py` additionally builds successors itself for independent
Dijkstra on negative/nonsquare/fractional-wall maps. These are correctness checks,
not performance benchmarks. Run after native measurements to avoid interference.

```sh
.venv/bin/python improving_llm_star/experiments/research/session7/audit_paths.py \
  --cases improving_llm_star/experiments/results/research_session7/heldout_all.json.gz \
  --paths /tmp/session7-replay/paths.json.gz --output /tmp/session7-path-check.json
.venv/bin/python improving_llm_star/experiments/research/session7/independent_reference.py \
  --maps 100 --output /tmp/session7-independent-reference.json.gz
```

The late `discrepancy_pilot.py` and `pathmax_pilot.py` accept `--cases`,
`--responses`, `--output`, and run only cached development/validation advice.
They are distinct information-use hypotheses, not changes to the frozen method.
`resource_audit.py`, `prediction_audit.py` and `guidance_audit.py` separate prompt
CPU, Python peak allocations, prediction accuracy, effective alpha, waypoint
lifetimes and genuine response-seed sensitivity. Instrumented times are never
substituted for native measurements.

Original target-lifetime events store the NEW target but the previous target's
duration. In particular, the switch TO the final goal still describes the last
intermediate waypoint lifetime. Never discard that duration as final-goal work.

Additional controls are explicit: `matched_uniform2`, `rh_macro_zero105`,
`rh_macro_uniform105`, `original_goal_only` and `robust_goal_only`. They are run
with `native_benchmark.py --methods ...` into a NEW directory. Counts-only runs
may use `--repeats 0 --skip-warmup`; timing runs always require warmup.

Completed main replay can be followed by the resumable **offline-only** audit
pipeline below. It runs additional timing blocks sequentially and reuses existing
completed outputs. Partial artifacts are preserved on failure. Do not start this
while another native timing process is running.

```sh
.venv/bin/python improving_llm_star/experiments/research/session7/finish_offline.py
```

Optional `live_latency.py` makes real requests and is deliberately excluded from
the offline pipeline. It uses the same persistent cumulative budget, preserves
all unknown-cost holds, and never resets expenditure. The configured key is
loaded only inside the authorized process, never copied into repository files.

Regional advice is recorded in `field_predictions`/`guidance_type`. The legacy
`llm_output` endpoint list is not model-generated coordinate guidance and must
not be used to claim a waypoint-validity advantage.

## Corrected paper denominators and quick analysis

The frozen classical A* returns its path from goal to start. The historical
shared adapter expected start to goal; stored raw paper records are preserved.
`paper_denominator_corrected` reverses only this presentation convention and
normalizes validity: 69 completed optimal paths, 31 capped trials. No search,
operation count, storage count, score or runtime is changed. The current native
adapter includes this normalization. Use **final_analysis_corrected**, not the
initial final_analysis, for paper OR/SR. Main means/paired comparisons are unchanged.

```sh
.venv/bin/python improving_llm_star/experiments/research/session7/analyze_native.py \
  --results improving_llm_star/experiments/results/research_session7/combined_results.json.gz \
  --cases improving_llm_star/experiments/results/research_session7/heldout_all.json.gz \
  --paper improving_llm_star/experiments/results/research_session7/paper_denominator_corrected/results.json.gz \
  --output /tmp/session7-analysis-review
```

This reads cached measurements and takes seconds; it does not rerun the long
native experiment or make model calls. Statistics use map-cluster bootstrap,
not timing repetitions as independent observations.

## Reproduce the stronger VM guidance-contribution check

This is explicitly post-unblinding robustness analysis, not a selected method
or a pre-registered positive result. All methods are frozen; no prompt tuning.
The shuffled control preserves target cardinality, route overlaps and majority
votes while permuting free candidate positions. Three seeds are averaged within
query; no additional model generation is required.

```sh
.venv/bin/python improving_llm_star/experiments/research/session7/native_benchmark.py \
  --cases improving_llm_star/experiments/results/research_session7/heldout_all.json.gz \
  --baselines improving_llm_star/experiments/results/research_session7/heldout_baselines/responses.json.gz \
  --costs improving_llm_star/experiments/results/research_session7/heldout_cost/responses.json.gz \
  --icl improving_llm_star/experiments/results/research_session7/heldout_icl/responses.json.gz \
  --methods vm_hybrid2 vm_geo2 vm_consensus2 vm_abstain2 vm_shuffled2 \
  --repeats 5 --shuffle-seeds 3 --timeout 5 --output /tmp/session7-vm-replay
.venv/bin/python improving_llm_star/experiments/research/session7/vm_controls.py \
  --output /tmp/session7-vm-replay
```

The ordinary model source and all-endpoints controls are repeated in this block
so comparisons are made within the same timing window. Do not pool absolute
wall times across the main and robustness blocks. `VM_UTILIZATION.json` measures
how often actual model proposals survive frozen majority selection.

## Late hypotheses and mathematical interpretation

Use NEW output files. The old pathmax_pilot_* artifacts and pathmax_source_v1.py
are intentionally preserved failed prototypes: arithmetic regrouping perturbed
floating ties. Corrected pathmax_v2_* matches the frozen disabled-control key
arithmetic and suppresses meaningless raises. Do not cite v1 apparent gains.

```sh
.venv/bin/python improving_llm_star/experiments/research/session7/pathmax_pilot.py \
  --cases improving_llm_star/experiments/results/research_session7/validation.json.gz \
  --responses improving_llm_star/experiments/results/research_session7/validation_cost/responses.json.gz \
  --output /tmp/session7-pathmax-v2-review.json.gz
.venv/bin/python improving_llm_star/experiments/research/session7/confidence_ablation.py \
  --cases improving_llm_star/experiments/results/research_session7/validation.json.gz \
  --responses improving_llm_star/experiments/results/research_session7/validation_cost/responses.json.gz \
  --output /tmp/session7-confidence-review.json.gz
.venv/bin/python improving_llm_star/experiments/research/session7/waypoint_bound.py \
  --maps 100 --output /tmp/session7-waypoint-bound-review.json.gz
```

`WAYPOINT_BOUND.md` derives the conditional1+alpha interpretation for the original
Euclidean-distance formula. This is analysis of established weighted search,
not a new theorem claim. Arbitrary node-dependent costs need a separate bound.
Oracle and synthetic checks never count as evidence of real-model usefulness.

## Report and PDF

The complete research report is supporting material, not the five-page final
ACL submission. TEAM_BRIEF.md is the short German explanation for the team.
Export the final Markdown, including standalone scientific figures, to a NEW PDF:

```sh
.venv/bin/python improving_llm_star/experiments/research/session7/report_pdf.py \
  --report improving_llm_star/experiments/results/research_session7/REPORT.md \
  --output /tmp/session7-report-review.pdf
```

Publication is withheld: the intended authenticated GitHub account is verified,
but the existing configured commit email has no matching verified association.
No identity/authentication settings were changed. All work remains on the research
branch. Manual publication command, after reviewing identity and the results:

```sh
git push -u origin research/waypoint-guidance
```
