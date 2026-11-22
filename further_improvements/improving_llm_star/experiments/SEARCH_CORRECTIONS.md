# Corrections: waypoint-only adaptation and duplicate handling

## Explicit scoring and reproduction controls

The untouched `llm-astar/` tree remains the original baseline. In the improvement
copy, constant-alpha calls default to `robust_search=False` and retain the legacy
score and expansion behavior. Default adaptive calls use `robust_search=True`.

Let h be Euclidean goal distance and d the active-target distance:

| Mode | Intermediate target | Final target | Closed-state handling |
|---|---|---|---|
| Original alpha=1 | g+h+d | g+2h | Original permanent CLOSED |
| Constant alpha=0.5 | g+h+0.5d | g+1.5h | Original permanent CLOSED |
| Corrected adaptive | g+h+alpha*d | g+h | Cost snapshots and reopening |
| Standard A* | g+h | g+h | Standard stale-entry rejection |

Adaptive mode does not reset/change the stored alpha on entering the final
goal; the effective waypoint coefficient becomes zero and the controller stops
updating. `alpha_history` records a `final_goal` event and `effective_alpha=0`.
There are no later stagnation/recovery updates during that phase. A new search
resets the controller. Intermediate-target switches still reset it to the
configured maximum, normally 1.0.

This g+h final score is an explicit design change. It is not attributed to
dynamic alpha or silently applied to the original and constant controls.

## Corrected search engine

The new heap entry is `(f, state, saved_g)`. The legacy engine retains its
`(f, state)` entries. For corrected entries, before any expansion/progress work:

1. Reject an entry if its saved cost differs from current g(state).
2. Reject an already-expanded state unless its new g is strictly lower than
   the g used at its previous expansion.
3. Otherwise accept the state. A lower-cost repeated expansion is a legitimate
   reopen, not an obsolete duplicate.

The historical expansion order remains in the CLOSED list for inspection. A
separate dictionary records the cost at which each state last expanded. Better
paths can update g and PARENT even when a state expanded before. On the fixed
Euclidean grid, closed neighbors whose geometric lower-bound cost cannot improve
g are skipped before expensive collision checking. Potential improvements still
pass the actual collision test and are queued for reopening.

On alpha/target changes, OPEN is filtered for current cost versions and eligible
unexpanded/reopened states. Identical live entries are consolidated. Priorities
are recalculated using current scores, with immutable saved_g preserved, then
heapified. Pending lower-cost reopens survive rebuilding. No extra model calls,
waypoint generation changes, or collision-semantic changes are introduced.

## Metric definitions

- `operation` / `heap_pops`: every heap extraction, including rejected entries.
  This retains the original raw-operation definition across modes.
- `expanded_nodes`: actual accepted expansions, including useful reopens.
- `unique_expanded_nodes`: distinct states among accepted expansions.
- `duplicate_pops`: in legacy mode, already-expanded pops that are processed;
  in corrected mode, rejected pops of previously expanded states. Useful
  improved-cost reopens are reported separately.
- `stale_pops` / `closed_pops`: counts of skipped entries. Zero in legacy mode
  means those checks are disabled, not that its heap contains no obsolete data.
- `reopened_expansions`: accepted repeated expansions with strictly lower g.
- `pruned_open_entries`: entries removed during rebuilding, not heap pops.

Rejected entries never update progress or the adaptation interval. Legitimate
reopens count as actual work. Alpha event indices use accepted expansions and
also include raw `heap_pops`, so both timelines can be inspected.

The path cost is calculated from the reconstructed path and validated against
legal edges. The reopen regression uses a directed subset of legal grid edges
with Euclidean costs and a deliberately inconsistent heuristic: legacy returns
cost 3+sqrt(2), while reopening finds cost 3. The test checks g(goal), returned
length, and the actual edge sum agree.

## Comparison and ablations

```sh
source .venv/bin/activate
python -m pytest improving_llm_star/tests -q
python improving_llm_star/experiments/compare_adaptive_alpha.py \
  --include-controls --repeats 3 --warmups 1
```

All variants replay identical raw responses and deep-copied queries. The four
main modes remain original, constant, adaptive, and standard A*. Seven optional
controls isolate changes:

| Control | Purpose |
|---|---|
| adaptive_before | Exact historical adaptive policy and legacy engine |
| adaptive_engine_only | Old adaptive scoring with corrected engine |
| adaptive_goal_only | Intermediate-only adaptation/g+h final score, legacy engine |
| original_fixed_engine | Constant 1.0, legacy scoring, corrected engine |
| constant_fixed_engine | Constant 0.5, legacy scoring, corrected engine |
| constant_goal_only | Constant 0.5 intermediate weight, g+h final score, corrected engine |
| fixed_waypoints_goal_only | Constant 1.0 intermediate weight, g+h final score, corrected engine |

`intermediate_only=False` is available solely for historical controls. It
re-enables the old goal adaptation explicitly and is never used by the corrected
main mode. `final_goal_weight=0.0` enables the matched final score in constant
controls. These options make attribution inspectable rather than mixing an
engine change with an adaptive-weight claim.

Outputs: [corrected report](results/adaptive_alpha_corrected/report.md),
[full runs](results/adaptive_alpha_corrected/comparison.json),
[summary CSV](results/adaptive_alpha_corrected/summary.csv), and
[alpha events](results/adaptive_alpha_corrected/alpha_events.csv).
The earlier [adaptive report](results/adaptive_alpha/report.md) is preserved.

## Wrong-direction case: interpretation

The earlier adaptive case had 133 raw pops, 90 distinct states, 43 processed
duplicates, five alpha changes, and six rebuilds. The wrong intermediate target
was already replaced by the goal at expansion 9; all subsequent changes acted
on the goal heuristic. Historical evidence is archived in
[diagnosis.json](results/adaptive_alpha_diagnosis/diagnosis.json).

With both corrections, this case has 185 raw pops, 153 accepted/distinct
expansions, and 32 discarded stale duplicate pops. It finds the same cost
24.1421356237, performs zero alpha changes, and rebuilds OPEN once. The same
185 raw pops and path occur with the fixed-intermediate-weight/g+h-final control:
this case therefore provides no evidence of a dynamic-alpha benefit.

Changing only final-goal behavior also gives 185 pops, but processes all 185,
including 32 duplicates. The engine correction skips those 32 neighbor loops;
it does not remove their extraction cost from the raw-operation metric.
Engine-only correction with old adaptive scoring gives 177 raw pops, 144 actual
expansions, 86 distinct states, and 58 useful reopens. Correctness fixes need not
reduce raw operation counts, especially under an inconsistent heuristic.

The increase relative to 133 is mainly the deliberately weaker g+h final score,
which explores 153 distinct states rather than 90. The final path is unchanged.
Baseline constant 0.5 remains faster on this case. The independent A* reference
also expands 153 distinct states, with 175 raw pops and no waypoint phase.
See the CSV for local repeated timings; no speedup is claimed.

Positive intermediate-waypoint terms remain inadmissible. Reopening and a g+h
final phase do not establish a global optimality guarantee, because the goal may
be selected while an intermediate target is still active. Hidden-map evaluation
and matched-engine/scoring ablations remain necessary.
