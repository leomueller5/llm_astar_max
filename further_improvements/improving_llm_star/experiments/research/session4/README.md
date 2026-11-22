# Session 4 — Verified strategic guidance and monotone cut search

Research on `research/waypoint-guidance`; no main edits, pushes, paid calls or
model credentials. Existing sources/results remain intact. Candidate freeze:
`0c462d6`, before the fresh map file was created. `d65c584` preserves the first
oracle/hierarchy milestone. Full findings and limitations are in the final
[report](../../results/research_session4/REPORT.md), with
[theory and guarantees](THEORY.md), [log](EXPERIMENT_LOG.md), and
[checkpoint](CHECKPOINT.md).

## What is implemented

- Strict strategic JSON/legacy parsing with explicit abstention; coordinates,
  ordered obstacle bypass IDs, regions and up to three prompted alternatives.
- Offline static/scripted guidance providers with event context and separate
  actual/simulated latency ledgers. No network/model client exists in this path.
- Component/portal hierarchy with a soft corridor, persistent deferred frontier,
  effort-triggered revisions and an independent bounded anchor.
- **Monotone Cut Relaxation (MCR)**: admissible wall-column/row crossing dynamic
  programs with O(height) octile transforms. Cheap Witness runs first.
- **Verified Strategic Route Refinement**: actual lattice shortcut checks and
  bounded local A* links (128 expansions total,32 per link), followed by independent
  candidate certification or complete bounded grid fallback. Helpful proposals
  can seed OPEN with shared, real-cost path prefixes. No adaptive-alpha rekeying.
- Lazy endpoint roadmap and Primal-First alternatives retained as independent
  experimental configurations; not silently substituted into the frozen baseline.

At factor `w>1` the bounded variants guarantee at most `w` times optimal cost;
they do not claim optimality. At `w=1` they are optimal under floating tolerances.
All returned routes use the repository's original eight-neighbor lattice and
closed wall geometry. Unsupported fractional cut geometry falls back to complete
weighted search. Unsuccessful local/corridor/roadmap attempts never remove the
unrestricted fallback. Advice cannot supply trusted numerical lower bounds.

The strongest real-model finding remains a **negative** one: cached answers do
not establish a reliable benefit beyond matched geometry. Positive synthetic/
oracle findings are upper-potential diagnostics, not real-model results. New
prompts have not been evaluated by a live model. See final tables for exact
runtime/path-quality tradeoffs and family-level regressions.

## Offline public interface

From the repository root:

```python
import sys
sys.path.insert(0, 'improving_llm_star')
from llmastar.research.strategic.api import StrategicLLMAStar

planner = StrategicLLMAStar(waypoint_response=cached_response, bound=2.0)
result = planner.searching(query_dict)
# Existing keys: operation, storage, length, llm_output; plus valid.
path = planner.path
metrics = planner.research_result
```

`query_dict` has the original `range_x`, `range_y`, `start`, `goal`,
`horizontal_barriers`, `vertical_barriers` fields. Input is not mutated.
Use a new provider per independent run; provider objects deliberately retain
request/event state. `llm_output` is an empty compatibility list for this richer
interface; inspect the provider/event metrics rather than interpreting it as the
original target list. Rendering and natural-language parsing are not performed.
Direct experimental API: `CutStrategySearch(bound=2).search(query, provider)`.
Without a provider this is the exact matched no-guidance engine.

Structured advice, with traversal order preserved:

```json
{"version":1,"strategies":[{"id":"upper_route","confidence":0.7,
"bypasses":[{"obstacle_id":"v0","side":"above"}],
"waypoints":[],"regions":[]}],"abstain":false}
```

For horizontal `hN` use `left/right`; vertical `vN` use `below/above`. IDs refer
to original wall-list indices. Confidence is stored as metadata; current variants try the supplied order. It
never proves feasibility or cost. `prompts.build_prompt` returns system/user strings;
`guidance.schema.json` documents the format. No function sends those strings.

## Reproduction

Run from workspace root with the existing `.venv`. Every results folder must be
new: runners refuse to overwrite historical artifacts. Put reruns under `/tmp`.
Matplotlib can use writable caches:

```sh
export MPLCONFIGDIR=/tmp/llmastar-matplotlib
export XDG_CACHE_HOME=/tmp/llmastar-cache
.venv/bin/python -m pytest -q improving_llm_star/tests
```

Reproduce the frozen fresh-map comparison from the stored raw maps:

```sh
.venv/bin/python improving_llm_star/experiments/research/session4/evaluate.py \
  --cases improving_llm_star/experiments/results/research_session4/fresh_maps_frozen.json.gz \
  --repeats 7 --bound 2 \
  --modes astar weighted witness witness_raw cut_octile cut_none cut_raw local_none local_raw local_portfolio cut_oracle cut_random cut_wrong cut_noseed cut_nogeometry cut_dynamic \
  --output /tmp/session4-fresh
```

The exact fresh-generation command was:

```sh
.venv/bin/python improving_llm_star/experiments/research/session4/maps.py \
  --split fresh --maps-per-family 2 --queries 2 --output /tmp/session4-fresh-maps.json.gz
```

Real cached validation (600 observations,200 distinct queries,20 maps,three styles):

```sh
.venv/bin/python improving_llm_star/experiments/research/session4/evaluate.py \
  --split validation --prompts standard cot repe --repeats 7 --bound 2 \
  --modes astar weighted witness witness_raw cut_octile cut_none cut_raw local_none local_raw cut_oracle cut_random cut_wrong \
  --output /tmp/session4-cached
```

Frozen original native vs matched geometry on predetermined fresh query0/map:

```sh
.venv/bin/python improving_llm_star/experiments/research/session4/evaluate.py \
  --cases improving_llm_star/experiments/results/research_session4/fresh_maps_frozen.json.gz \
  --stride 2 --repeats 3 --timeout 2 --bound 2 \
  --modes original_native original_matched weighted witness cut_none local_none local_raw local_portfolio \
  --output /tmp/session4-native
```

A uniform timeout is a censored trial, NOT a completed runtime or evidence of
path invalidity. Native and matched original retain scoring, switching, duplicate
behavior and queue rebuilds; only matched geometry is replaced by the exact
indexed graph. Synthetic original and improved single-route methods receive the
same imperfect coordinate sequence. Portfolio has three alternatives and is
explicitly a more-information ablation, not an equal-output-token comparison.

Secondary source/repair diagnostics reuse the exact stored prepared fixtures:

```sh
.venv/bin/python improving_llm_star/experiments/research/session4/local_controls.py \
  --cases improving_llm_star/experiments/results/research_session4/final_fresh/cases.json.gz \
  --repeats 7 --output /tmp/session4-local-controls
```

Independent geometry/reference/bound checks and separate Python memory/heap audit:

```sh
.venv/bin/python improving_llm_star/experiments/research/session4/audit_final.py \
  --evaluation improving_llm_star/experiments/results/research_session4/final_fresh \
  --development-cases improving_llm_star/experiments/results/research_session4/development_maps_v1.json.gz \
  --output /tmp/session4-audit
```

Tables/plots (add secondary/native result directories to `--inputs` as available):

```sh
.venv/bin/python improving_llm_star/experiments/research/session4/report.py \
  --inputs /tmp/session4-fresh /tmp/session4-cached /tmp/session4-native \
  --output /tmp/session4-analysis
```

## Interpretation rules

Cold timing includes fresh geometry, witness, DP construction, lazy transforms,
parsing, validation, local search, fallback, path construction and internal checks.
Common independent post-timer auditing is applied uniformly. Imports, plotting,
fixture/reference generation and model response production are excluded for all
methods; excluded oracle generation is unavailable information, not free LLM
inference. Two fixed warmup cases are excluded. Seven repeated shuffled trials
are collapsed to per-query medians, not counted as independent maps. Map-cluster
bootstrap intervals are exploratory and unadjusted for multiple comparisons.

`unique_total` is the union of local/global expanded states. `operation` retains
global heap-pop meaning; `total_heap_pops` includes local search. Geometric DP,
collision and preprocessing work are separately timed. Instrumented heapq pushes,
pops and heapify item counts belong to a separate untimed audit. Tracemalloc
measures Python allocations, not total native RSS. Operation/storage ratios use
the same recorded definitions; state-count ratios cannot substitute for memory
bytes. Simulated latency scenarios are calculations, never measured API timings.

Post-freeze diagnostics also run on `final_cached_validation/cases.json.gz`.
They compare identical local refinement on real/synthetic raw, random,
wrong-query and shuffled hints; named no-repair/no-shortcut settings isolate
local-search versus shortcut contribution. These are secondary diagnostics,
not a second round of tuning on fresh data.

Profiler reproduction (diagnostic times only; archived source remains intact):

```sh
.venv/bin/python improving_llm_star/experiments/research/session4/profile_search.py \
  --cases improving_llm_star/experiments/results/research_session4/development_maps_v1.json.gz \
  --oracle --legacy --family tree_maze serpentine --size 256 \
  --snapshot improving_llm_star/experiments/results/research_session4/phase4_development_large/source_snapshot \
  --output /tmp/session4-profile-before
```

Omit `--snapshot` and use a new output folder for the frozen optimized version.
To generate additional ratios, latency scenarios, exact heap/memory summaries and
family plots after `report.py` and the audit:

```sh
.venv/bin/python improving_llm_star/experiments/research/session4/diagnostics.py \
  --root improving_llm_star/experiments/results/research_session4
```

This last command refreshes only current derived analysis files; it does not
change raw measurements or historical experiment artifacts.

Timing boundary detail: final benchmarks use the outer `seconds` measurement.
A supplied-graph core method's `total_seconds` begins after the caller constructed
that graph, so do not treat that field alone as public end-to-end latency.
Final outer timings include graph construction and all parsing; pre-created
static/scripted response-holder objects and unavailable fixture generation are
excluded. Those holders only store metadata/response references; parsing happens
inside the timed provider call. This small setup distinction matters when
interpreting microsecond-scale cache differences. The final reports make no
positive claim from such differences.

Region-only strategies are consumed by the hierarchical `StrategicSearch`; the
cut/public adapter uses coordinates and ordered bypasses. Unsupported advice
forms safely leave the complete fallback active.
