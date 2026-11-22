# Session 3 — Verified waypoint prefixes and real-content controls

Start: 16 November2026,06:49:54UTC. Branch `research/waypoint-guidance`.
Algorithms/configurations frozen in commit79b96f3 before Session3 validation.
No old test split reused, no paid API calls, no pushes/merges. Prior source and
results preserved. See `selection.json`, `EXPERIMENT_LOG.md` and
`../../results/research_session3/REPORT.md` for measured results and limitations.

## Why earlier guidance fails

Original switching consumes a target when a generated neighbor equals it, before
collision/CLOSED filtering. Dense adjacent hints and already-searched neighborhoods
therefore consume targets rapidly. Median1 pop;93.45% live<30 pops. Simply retaining
targets longer was negative in prior work; we did not repeat it unchanged.

600 real development responses: Witness already solves467 cases without search.
In133 residual cases,99 contain at least one geometrically benign hint, yet old
matched guidance improves both cost and distinct states in only3. A benign point
is not necessarily an efficient search hint. Exact forced-route labels were used
only in offline audit, never for selection/scoring inside the planner.

## New strategy: verified prefix seeding

A complete LLM route is unnecessary. Validate a partial shortest lattice walk from
start to a useful intermediate point and put that point into OPEN with the actual
route cost. Start remains in OPEN. The main score stays exactly `g+2*h_goal`.

```text
if existing geometric Witness certificate succeeds: return its optimal route
L = admissible geometric start lower bound
T = free, integer, unique raw intermediate hints
T = {t in T: octile(s,t)+octile(t,g) <= 1.1*L}  # primary conservative filter
sort T by octile(s,t)+2*Euclidean(t,g)
for t in first8 ranked candidates:
    P = collision-checked actual shortest lattice walk s -> t
    if P exists:
        if cost(P)+2*h(t) < 2*h(s): seed t with g=cost(P), macro parent=P
        break  # sorted estimate equals actual priority for every verified link
OPEN also contains s with g=0
run Weighted A*; skip stale/closed duplicates, reopen improvements
replace a macro parent if a better ordinary path is found
expand the final macro prefix into original unit grid moves
```

Ranked/lazy and strict-detour variants are separately runnable. The1.1 bound is
an experimental predeclared guard, not a validated universal optimum. Raw-point,
occupancy-only, one/multiple seed, chain-prefix and geometric-only source ablations
are preserved. Lazy ranking exactly matches eager ranked seed choice/counts.

Every macro edge is an actual original-grid route with its real cost, so it adds
no artificial short path. Keeping start and supporting reopenings preserves the
optimal-path frontier argument: with `H<=2*h*`, goal-pop cost is <=2*C*. This is
bounded-suboptimal search, not optimal A*. Witness certificates remain optimal.

Also tested: fixed visible-waypoint funnel
`H(n)=min(2h(n),d(n,t)+1.5d(t,goal))`; immediate confidence bonus
`H(n)=2h-alpha*max(0,h-d(n,t))`, alpha in[0,1] from initial progress/detour;
and tie-breaking only. These avoid the old late-stagnation timer, but may spend
more work. Near-goal scoring reverts to2h; original baseline scoring is untouched.
A uniform1.5-weight control tests whether quality comes merely from weakening the
heuristic rather than informative waypoint locations.

## Public API

```python
from llmastar.pather import SeededLLMAStar
p = SeededLLMAStar(waypoint_response=cached_raw_response, strategy='cut')
r = p.searching(query_dict)
# Same operation/storage/length/llm_output keys; p.path and p.search_metrics.
control = SeededLLMAStar(guidance=False)
quality_candidate = SeededLLMAStar(waypoint_response=cached_raw_response,
                                  strategy='quality')
```

Use `PYTHONPATH=improving_llm_star` at repository root. Input is copied. No request
during search. Supply cached response for offline use; enabled live initial adapter
otherwise remains the inherited legacy adapter. Disabled mode skips initial model
processing. Historical storage counters exclude some auxiliary allocations.

## Evaluation and causal limits

Development:600 standard-response queries on60 maps. Validation:600 real cached
observations on20 different maps, three prompt styles,9 randomized interleaved
repeats. This historical validation split was used by previous sessions, so it is
not a completely new real-model holdout. No Session3 selection uses the old test
split. Prompt styles/repetitions are not independent map samples.

Fresh:30 independently seeded maps,240 cases,10 families with anisotropic integer
scaling,7 repeats. Exact canonical geometry disjointness is checked against all
100 cached maps and stored Session2 development/validation/fresh maps. Helpful
fixtures use oracle route corners; they are NOT real model outputs and are never
presented as LLM evidence. Reference costs are used only for fixture creation and
evaluation; planners receive query+points, not reference cost.

Controls: frozen original search with identical indexed unit geometry; standard A*;
optimized WA2; Witness without/with existing LLM stage; identical new disabled
engine; geometric seed candidates; same-map wrong-query actual responses; equally
sized random free-point lists; shuffled hint order; geometric/random potentials;
and uniform1.5-weight search. Ranking intentionally ignores hint order: shuffle
must match counts/costs. A wrong-query result as good as correct hints undermines
claims of task-specific LLM utility.

All graph/index construction, filtering, route checks, queue work and validation
are timed per query. Raw cache parsing is outside every core run; separate public
interface timing includes parsing/copying. No preprocessing cache is free for one
variant only. Candidate counts mean selected seeds/targets, not proof the seed was
used in the final path. Causal contribution comes from matched ablations.

Whole-map paired bootstrap,2000 resamples. Secondary comparisons are exploratory
and unadjusted; report costs, operations, means, medians, tails and acceptance as
well as runtime. A quality-only gain must also survive uniform-weight/random-point
controls. No post-validation parameter changes or favorable-subset headline claims.

## Reproduction (repository root)

```bash
.venv/bin/python -m pytest -q improving_llm_star/tests
.venv/bin/python -B improving_llm_star/experiments/research/session3/audit.py

.venv/bin/python -B improving_llm_star/experiments/research/session3/run.py --split development --repeats 9 --variants guide_off witness_only seed_raw seed_geo_filter seed_rank seed_multi seed_geometry seed_chain potential_visible immediate_trust --output /private/tmp/session3-dev

.venv/bin/python -B improving_llm_star/experiments/research/session3/run.py --split validation --prompts standard cot repe --repeats 9 --variants original_indexed indexed_astar scheduled_wa2 witness_only witness_cf guide_off seed_cut seed_lazy geometry_lazy seed_cut_wrong seed_cut_random seed_cut_shuffle potential_visible potential_geometry potential_random uniform15 --output /private/tmp/session3-validation

.venv/bin/python -B improving_llm_star/experiments/research/session3/evaluate.py
.venv/bin/python -B improving_llm_star/experiments/research/session3/public_timing.py
.venv/bin/python -B improving_llm_star/experiments/research/session3/verify.py
.venv/bin/python -B improving_llm_star/experiments/research/session3/report.py
```

`evaluate.py` uses canonical output paths and refuses overwrites; use new output
paths for reruns. It runs validation then generates/checks/runs the frozen fresh
suite. Run timing stages serially. Archives contain per-trial records, full
configurations, source snapshots/hashes, case hash and platform. Expanded journals
are retained locally but ignored by Git; gzip archives are canonical.
