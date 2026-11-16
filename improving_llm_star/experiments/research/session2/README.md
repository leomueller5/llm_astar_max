# Session 2 — Fast exact geometry certificates and honest LLM ablations

Research started 16 November 2026 at 04:55:23 UTC. Session-1 code/results remain
unchanged. The policy was frozen before the new test maps were generated; see
[selection](selection.json) and [experiment log](EXPERIMENT_LOG.md). No paid API
calls, pushes, or merges. All new work is on `research/waypoint-guidance`.

## Implemented mechanisms

The original certificate method spent most time repeatedly creating eight
neighbors for a single queried edge and scanning every obstacle; degenerate walls
could force whole maps into repeated Shapely object creation. Its optimality bound
and heap operations were minor costs. We implemented and tested:

1. Query-local wall interval indices by row/column and cached point occupancy.
   On integer axis-aligned maps, a unit lattice edge intersects a nondegenerate
   integer wall only at an endpoint. Individual edge queries no longer construct
   eight neighbors. Noninteger geometry retains the old unit-edge predicates;
   zero-length barriers preserve actual installed Shapely behavior.
2. Exact macro verification: either shortest-walk ordering between two lattice
   points consists of a diagonal and an axial piece. Verify these pieces against
   indexed walls; expand only the final route into unit moves. This does not
   permit continuous paths that cannot be emitted on the original grid.
3. Reachability-first layered DAG evaluation, prefix-cost certificate sieving,
   early termination, and collinear raw-hint compression. Compression can lose
   some certificates; it is an algorithmic tradeoff, not an equivalence refactor.
4. **Witness-first certificates:** the admissible single-wall lower bound also
   identifies candidate integer crossings immediately beyond wall endpoints.
   Try actual checked routes through those witnesses before using LLM hints.
5. Optional exact LLM candidate stage; or a separate frontier-incumbent variant
   that uses valid, uncertified hints as upper bounds. The latter has weight-2
   quality, not an optimality certificate.
6. Explicit lean no-guidance controls with identical fallback scores, tie order,
   stale-g checks and reopening. Generic engine speedups are not LLM contributions.

Public interface: `WitnessFirstLLMAStar` in
`llmastar/pather/llm_a_star/witness.py`. Original `LLMAStar` and Session-1
`CertifiedLLMAStar` remain separately available. Successful return keys remain
`operation`, `storage`, `length`, `llm_output`; inspect `.path`, `.research_result`
and `.search_metrics` for details. On failure external length is infinity, internal
records use null. Structured input is copied and never modified.

```python
from llmastar.pather import WitnessFirstLLMAStar

# Fastest selected configuration: geometric witnesses, no LLM use or model call.
planner = WitnessFirstLLMAStar(use_waypoints=False)
result = planner.searching(query_dict)

# Optional existing response: exact certificates from remaining LLM hints.
planner = WitnessFirstLLMAStar(waypoint_response=cached_raw_response)
result = planner.searching(query_dict)

# Independently runnable experimental weight-2 incumbent policy.
planner = WitnessFirstLLMAStar(waypoint_response=cached_raw_response,
                              policy='frontier')
```

Set `PYTHONPATH=improving_llm_star` when running from repository root. The normal
initial model adapter is inherited and was not modernized; use cached responses
for offline GPT-4o mini comparisons. No-guidance mode skips the initial model
request. No variant makes a request during search.

## Pseudocode and guarantees

```text
L = max(octile(start, goal), independent_integer_wall_cut_bounds)
P = checked_shortest_lattice_walk(start, goal)
if P absent:
    for endpoint crossing q with octile(start,q)+octile(q,goal) <= L:
        P = checked_lattice_walk(start,q) + checked_lattice_walk(q,goal)
        if P exists: return P
if P exists: return P
if optional_exact_LLM_stage:
    P = reachable_verified_DAG(compressed_raw_hints, radius_one_candidates)
    if P exists and cost(P) <= L: return P
return robust_Weighted_A_star(weight=2)
```

`L <= C* <= cost(P)`: accepted exact routes are optimal up to floating tolerance.
Wall bounds take a MAX, never a sum. Fractional maps use the universally admissible
octile bound rather than applying the integer wall proof outside its domain.
All emitted edges have original unit Euclidean costs and collision semantics.
The fallback is not optimal A*: with admissible Euclidean h and reopening it is
weight-2 bounded. The complete method therefore has a global factor-2 bound,
with exact optimality only on certificates.

For optional frontier incumbents, maintain a valid route U and stop only when
`U <= min_OPEN(g+2h)`, after stale checks. An optimal-path frontier state bounds
that weighted minimum by `2*C*`; pruning uses admissible `g+h >= U`. Thus this
policy remains factor-2 bounded but can worsen paths relative to the matched
control. Directly accepting a nonoptimal candidate is never labelled optimal.

For B wall segments, query-local index construction is O(B); point occupancy
queries examine only intervals on the queried row/column and are cached. A
macro-piece checks the indexed wall coordinates it crosses, so its cost depends
on intersected wall intervals, not a universal O(1). A raw list of m hints gives
O(m) candidates and links with fixed layer width; cap candidate attempts at256.
The original experimental unit-probe cap4096 is a separate counter. Unit probes,
continuous segment tests, wall interval tests and heap pops are never equated.
Geometry/index/DAG memory is additional to the historical storage counter.

## Evidence boundaries

Primary fresh protocol: 80 independently seeded maps /640 fixture cases; ten
families, including large maps; two start-goal pairs and four hint qualities.
Seed660000 is separate from development440000 and validation550000 and all
session-1 seeds. The helpful fixture is a full compressed optimal route created
by an offline oracle **only for fixture generation**; no runtime algorithm sees
its cost or a reference search. These fixtures are not actual LLM outputs.

Real cached responses use the established whole-map split. Selection uses only
development/validation. A replay of the previously opened Session-1 test split is
labelled opened confirmation, not independent fresh held-out evidence. Three
prompt styles share map/query clusters and are not stochastic model repetitions.
No new model sampling, token pricing, or API latency is measured; actual new
model calls/tokens/costs are zero.

Fresh timing stages run serially. Within a stage, methods are randomized and
interleaved for every case/repetition; each pays fresh index/cache/geometry cost.
Four-case warmups are excluded. Repetitions are reduced by median within case,
then map-clustered bootstrap intervals are computed. Report arithmetic mean
case medians, paired geometric ratios, raw means and tail regressions, rather
than conflating these statistics. Public interface timing additionally includes
query parsing/copying and normal initialization; imports, network and plotting
are excluded for every variant. Independent post-timer path checks are uniform.

Original-indexed keeps frozen scoring/OPEN/switching source but supplies the same
new geometry; its counts isolate algorithm behavior. Native original uses its
actual old collision implementation and is separately measured through the same
public-query boundary on a predetermined map-balanced sample. These are distinct
controls. Disconnected original exceptions are reported, not hidden as graceful
no-path returns. Primary new methods return failure cleanly.

The fastest selected method does not require LLM guidance. Any LLM-specific
claim must compare against `witness_only`, not just original or unoptimized WA2.
The exact stage may save a few additional states while adding CPU overhead;
frontier routes may help ideal fixtures without proving usefulness of real model
outputs. Do not attribute geometric witness gains to LLM intelligence.

## Reproduce (repository root)

All commands are offline; use installed `.venv`. Do not run timing commands
concurrently. Output directories refuse overwrites; choose a new path for reruns.

```bash
.venv/bin/python -m pytest -q improving_llm_star/tests

.venv/bin/python -B improving_llm_star/experiments/research/session2/run.py --split development --repeats 11 --variants scheduled_wa2 witness_only witness_cf witness_frontier --output /private/tmp/llm-astar-session2-dev

.venv/bin/python -B improving_llm_star/experiments/research/session2/cases.py --split fresh_test --maps-per-family 8 --output /private/tmp/llm-astar-session2-fresh.json.gz

.venv/bin/python -B improving_llm_star/experiments/research/session2/run.py --cases /private/tmp/llm-astar-session2-fresh.json.gz --repeats 11 --variants original_indexed indexed_astar scheduled_wa2 old_cf indexed_cf lean_cf witness_only witness_cf witness_chain witness_frontier --output /private/tmp/llm-astar-session2-fresh

.venv/bin/python -B improving_llm_star/experiments/research/session2/native.py --cases /private/tmp/llm-astar-session2-fresh.json.gz --repeats 7 --output /private/tmp/llm-astar-session2-native

.venv/bin/python -B improving_llm_star/experiments/research/session2/run.py --split test --prompts standard cot repe --repeats 7 --variants original_indexed indexed_astar scheduled_wa2 old_cf indexed_cf lean_cf witness_only witness_cf witness_chain witness_frontier --output /private/tmp/llm-astar-session2-opened-confirmation

.venv/bin/python -B improving_llm_star/experiments/research/session2/verify.py
.venv/bin/python -B improving_llm_star/experiments/research/session2/report.py
```

`final_evaluate.py` runs/resumes the canonical three stages sequentially, skipping
already completed stages. A partially failed output directory requires explicit
inspection and a new directory; no partial result is silently overwritten.
Each core result archive includes complete configurations, source hashes and
source snapshots, case hash, platform/version and per-trial metrics. Archives
preserve prior phases and negative experiments. Source snapshots intentionally
retain original baseline whitespace; check modified production source separately.

Known exploratory infrastructure issues are recorded in the log: a late-source
hash before snapshots were added, and strict JSON rejecting infinity on a
no-path case. Failed artifacts are not evidence. Final release/selection occurs
in commit87c3310 before any new test generation. No algorithm tuning follows.

## Final measured interpretation and native protocol deviation

The new fixture suite confirms a small mean-time improvement for witness-only
versus identically optimized WA2, with regressions in some families (notably maze).
Raw-chain incumbents help the oracle-corner fixture mixture but do not establish
an actual-model speedup. In opened real caches, the exact LLM extension accepted
no additional route, while witness geometry explains the improvement.

The first native-interface attempt was interrupted after a mistaken diagnosis of
buffered parent output; it had no saved measurements and is NOT used. Full core
results were already saved and unchanged. The repeated native stage now journals
every trial and applies the SAME two-second cap to every method. Native-original
has 35 censored trials; its reported aggregate is only a lower runtime bound,
not a complete mean. No other native method timed out. This is a documented
measurement-protocol deviation, not an algorithm/parameter change. The original
core/indexed evaluation has no such cutoff.
