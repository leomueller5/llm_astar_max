# Adaptive alpha: implementation and experiments

Only the improvement copy is changed. Prompt templates, response parsing,
waypoint generation, filtering, edge costs, CLOSED policy, and target-switch
semantics are retained. No replanning/model calls are made inside the loop.

## Using the planner

```python
from llmastar.pather import LLMAStar

original_weighting = LLMAStar(alpha=1.0)
constant_weighting = LLMAStar(alpha=0.5)
adaptive_weighting = LLMAStar(
    adaptive_alpha=True,
    stagnation_threshold=30,
    alpha_update_interval=10,
    alpha_decrease=0.2,
    alpha_increase=0.1,
    alpha_min=0.2,
    alpha_max=1.0,
    progress_epsilon=1e-9,
)
```

The existing `searching(query, filepath)` signature and successful-result keys
are unchanged. `adaptive_alpha=False` is the default. Adaptive mode enables
progress measurement even when `track_progress` is false. Both `alpha` and
progress summaries are reset appropriately when an instance is reused.

Each adaptive search starts with alpha=1.0 and resets it to 1.0 on each target
switch with the default bounds. If a smaller `alpha_max` is explicitly chosen,
the initial/reset value is clipped to that configured maximum. The `alpha`
constructor argument controls constant mode; adaptive mode starts at its maximum.

## Update rule

The existing summary measures the best Euclidean distance among states popped
while a target is active. The first pop establishes a distance baseline. Later
decreases greater than `progress_epsilon` reset the stagnation counter. Small
decreases accumulate against the previous best accepted distance, so repeated
small advances can eventually count as meaningful progress.

At every `alpha_update_interval` pops for the current target:

1. If consecutive pops without progress >= `stagnation_threshold`, subtract
   `alpha_decrease`.
2. Otherwise, if the improvement count increased since the previous evaluation,
   add `alpha_increase`.
3. Otherwise keep the weight.
4. Clamp to `[alpha_min, alpha_max]`.

Only an actual weight change refreshes OPEN. A target switch refreshes it once
for both the new target and reset weight. Checks at the bounds do not trigger
rebuilds. New-target counters start at zero; a transition occurring during a
neighbor loop is not immediately followed by an adaptive update for that target.

Defaults are experimental. A completely stagnant target first becomes eligible
after 31 pops (the initial sample plus 30 non-improving pops); with interval 10,
the first reduction is at pop 40. Further reductions occur at later intervals
while stagnation persists. Recovery requires new progress in the latest interval,
not an old improvement repeatedly counted as evidence.

The default progress tolerance is the existing numerical tolerance (1e-9), not
a claim that this is the best semantic definition of progress. An absolute
Euclidean criterion can misread necessary detours and does not detect all bad
waypoints. Test scale-normalized tolerances on development maps before fixing
parameters for held-out evaluation.

## OPEN correctness

The heap stores numeric `(priority, state)` tuples. Changing a global alpha
without updating these tuples leaves priorities stale. On a weight/target
change, all queued entries are recalculated from current g, target, and alpha,
then `heapq.heapify` builds the queue in O(|OPEN|). Existing duplicates are kept
to preserve the baseline's search behavior and counting. Recalculating just a
popped entry would be insufficient when priorities elsewhere have decreased.

## Logging

After `planner.searching(...)`, inspect:

- `planner.search_metrics`: expanded and unique expanded states, path cost,
  validity, goal reached, search seconds, alpha adjustment count, final alpha,
  and actual OPEN rebuild count.
- `planner.alpha_history`: initial weight, every actual change, and target reset
  events. Each includes global pop index, target, reason, old/new weights, best
  target distance, current stagnation, improvements, and OPEN size. Weights are
  constant between events, so this is a complete compressed weight trace.
- `planner.waypoint_progress`: one distance/stagnation summary per target activation.
- `planner.path`: the reconstructed start-to-goal state sequence.

Alpha adjustment counts include resets that change the numeric value. Reset
events at an already maximal weight are logged but not counted as adjustments.
Search seconds include the loop, queue maintenance, reconstruction, and path
validation; exclude imports, environment initialization, LLM processing, and
plotting. Logging is enabled equally for all three LLM comparison modes.

Legacy `operation`/expanded counts include duplicate heap pops and the goal pop.
The unique counter makes that distinction visible. Instrumentation is not a
claim that CLOSED has been corrected or duplicates eliminated.

On exhausted OPEN, the improvement copy now returns an empty `planner.path`,
`length=inf` in the legacy result, and `path_valid=False`, `path_cost=None` in
metrics instead of attempting reconstruction through a missing parent. The
comparison records failures with null costs and never treats them as zero cost.

## Running a paired comparison

From the workspace root:

```sh
source .venv/bin/activate
python -m pytest improving_llm_star/tests -q
python improving_llm_star/experiments/compare_adaptive_alpha.py --repeats 3 --warmups 1
```

Defaults replay the existing six fixed cases, three weighting variants and a
standard A* reference. Five cases have hand-authored waypoints; one is from the
public prompt. These are smoke tests, not GPT-4o-mini results. No model or API is
called. An offline response adapter feeds identical strings to the unchanged
waypoint-processing pipeline. Queries are deep-copied because legacy setup
mutates the supplied range lists.

Modes are `original` (constant 1.0), `constant` (0.5), and `adaptive`. The original
control uses the same instrumentation as the other two. Outside timed runs its
operations, storage, length, and exact path are audited against the untouched
original source. The separately implemented standard A* uses an admissible
Euclidean heuristic and the same collision predicate and legal grid edges. It
skips stale entries and does not store infinite-cost states, so its operation and
storage counters have different semantics from legacy counters. Its path cost
is the reference for relative solution quality, not an attribution of search
bookkeeping gains to alpha.

Every case gets configurable warmups; mode order is shuffled using a recorded
seed for each repeat. Output contains every timed run and medians, rather than
only the best run. Short smoke timings are noisy and include instrumentation.

Outputs in `experiments/results/adaptive_alpha/`:

- `comparison.json`: raw responses, inputs, configuration, source hash, original
  audits, complete runs, paths, metrics, alpha events, and progress summaries.
- `summary.csv` and `report.md`: operations, storage, cost, cost relative to A*,
  valid-path fraction, median search time, weight changes, and rebuilds.
- `alpha_events.csv`: weight changes alongside expansion indices and progress.

Change parameters explicitly, keeping separate output directories:

```sh
python improving_llm_star/experiments/compare_adaptive_alpha.py \
  --stagnation-threshold 20 --alpha-update-interval 10 \
  --output-dir improving_llm_star/experiments/results/adaptive_threshold20
```

## Replaying cached GPT-4o-mini responses

Use `--cache path/to/cache.json` with this format:

```json
{
  "cases": [
    {
      "id": "map-id-query-id-sample-id",
      "source": "gpt-4o-mini cached response",
      "query": {
        "start": [5, 5], "goal": [20, 20],
        "range_x": [0, 51], "range_y": [0, 31],
        "horizontal_barriers": [[10, 0, 25], [15, 30, 50]],
        "vertical_barriers": [[25, 10, 22]]
      },
      "llm_response": "Generated Path: [[5, 5], [26, 9], [25, 23], [20, 20]]"
    }
  ]
}
```

The string above is an illustrative repository example, not a newly generated
model answer. Store actual raw outputs before filtering. Additional metadata
(model identifier, prompt hash, token usage, date, sample seed/settings) can be
included per case and is preserved in the JSON output. Do not include API keys.

## Optimality and recommended experiments

Positive `alpha * distance_to_waypoint` is generally inadmissible. At a goal
different from the active target it is even positive when true remaining cost
is zero. When target=goal the heuristic is `(1+alpha)*goal_distance`. Changing
alpha can introduce further inconsistency. The inherited permanent CLOSED
policy does not reopen improved states. Neither original nor adaptive LLM-A*
therefore has a shortest-path or fixed suboptimality guarantee. Queue refreshes
ensure correct ordering under the chosen score, not an A* optimality guarantee.

Keep waypoint quality, target advancement, collision semantics and reopening
changes out of the alpha experiment. The inherited target switch still occurs
on neighbor generation before collision checking, which can mask bad targets.
No regeneration or new LLM calls have been added.

Next: split by whole map; use cached outputs from several independent model
samples; include unseen map families; freeze settings before testing. Compare
fixed weights, decrease-only adaptation (a future ablation), recovery, and
different update intervals. Report failed attempts, tail expansions/costs, and
queue/runtime overhead. A decrease in expansions alone is not sufficient to
claim a faster or better planner. Do not choose a threshold solely from these
six cases.
