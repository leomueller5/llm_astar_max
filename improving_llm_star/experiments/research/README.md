# Certificate-First Waypoint Search

Research branch: `research/waypoint-guidance`. All runs are offline. Original code
in `llm-astar/` and historical Table 1 outputs remain unchanged. The existing
corrected/constant/adaptive planner is independently runnable. Research variants
live in `llmastar/research/`; the public wrapper is `CertifiedLLMAStar`.

## What the original actually does

The original score is `g+h(goal)+d(active_target)`, hence `g+2h` at the final goal.
It advances when a **generated neighbor equals the target**, before rejecting
collision/closed neighbors, rather than after expanding that target. In the 600
map-disjoint development queries, median target lifetime is one legacy pop,
p90=15; 93.45% of switched targets live fewer than 30 pops. Multiple switches
within one neighbor loop produce 298 zero-lifetime targets. The existing corrected
adaptive mode changes alpha in 205/600 queries, but these short lifetimes undermine
its delayed feedback. Its final-goal `g+h` also makes it explore more than the
original final `g+2h`; this is a confound, not an alpha-only effect.

14.91% of 5,118 distinct intermediate points are invalid/unreachable; 41.62% are
invalid/unreachable or impose a >10% optimal detour if **required** to pass through.
This offline topological label does not establish causal harm from a soft heuristic.
Whole-map splits use seed 20261113: 60 development / 20 validation / 20 test maps.
Raw caches contain 3,000 outputs; notebook labels indicate GPT-4o mini, but raw
cache metadata alone cannot verify the model/version/temperature. All malformed
responses remain in evaluation with explicit empty-waypoint parsing fallback.

## Selected algorithm

Reactive weighting was not the strongest method found. Selected policy converts
uncertain guidance into a **verified route or no guidance at all**:

1. Try a direct shortest lattice path, testing every unit edge for collisions.
2. Compute an admissible lower bound `L` on the optimal grid cost. Start with
   octile distance, `max(dx,dy)+(sqrt(2)-1)*min(dx,dy)`. For each separating wall,
   compute the minimum octile detour via either adjacent free-side integer
   crossing at its endpoint. Take the **maximum**, never sum, across wall bounds.
   Other walls are ignored, so each individual bound remains optimistic.
3. Around each raw intermediate waypoint propose itself and four axial neighbors.
   Only free integer candidates remain. Do not repair start or goal.
4. Discard points/links whose octile start-to-link-to-goal lower bound exceeds L.
   Build a forward layered DAG: adjacent waypoint layers, start-to-all and
   all-to-goal links. Each link is an actual checked shortest lattice route
   (diagonal-first or excess-axis-first), not continuous line of sight.
5. Compute its best verified route of cost U, limiting all successful **and failed**
   visibility probes to 4,096 unit-edge checks. Accept only if `U <= L + 1e-10`.
6. Otherwise discard the candidate completely and run the same robust Weighted A*
   control `f=g+2*Euclidean(goal)`, with stale-g checks and reopening.

```text
L <- max(octile(start, goal), independent_single_wall_bounds)
P <- checked_direct_lattice_route(start, goal)
if P is absent:
    V <- free_radius_one_candidates(raw_intermediate_waypoints)
    E <- certificate_sieve(forward_layered_links(V), L)
    P <- shortest_route_in_verified_DAG(E, edge_probe_budget=4096)
if P exists and cost(P) <= L + tolerance:
    return P
return robust_weighted_A_star(start, goal, weight=2)
```

For integer axis-aligned wall maps and 8-connected unit Euclidean grid edges,
`L <= C* <= U`; accepted routes are optimal up to floating-point tolerance.
Each wall crossing must contain an integer state on its row/column outside the
closed interval; minimizing octile costs over that half-line is attained at the
adjacent endpoint (or the direct lower bound already suffices). Taking max retains
admissibility. Degenerate zero-length walls follow original Shapely semantics and
are excluded from the bound. Tests compare these bounds against exact A*.
Fallback has the usual weight-2 bounded-suboptimal guarantee with admissible
Euclidean h and reopening. **The whole method is not optimal A*.** It returns an
optimal certificate or the matched WA2 result; it cannot worsen fallback path
cost/expansion count, but can worsen runtime through preprocessing.

With m raw points there are O(m) candidates (at most five per point), O(m) links
under this fixed layer width, sorting O(m log m), and at most B=4096 geometric
edge probes. DAG storage additionally retains verified link paths, bounded by
successful probe work. Fallback uses ordinary graph-search memory. The number
of walls affects collision-check and lower-bound cost; no constant-time geometry
claim is made. The production wrapper uses lazy adjacency; benchmark shared
precomputation and its costs are recorded separately.

## Evidence and limitations

See [aggregate results](../results/research/REPORT.md),
[figures](../results/research/expansions.pdf), and [experiment log](EXPERIMENT_LOG.md).
Selection was frozen in `selection.json` after development and validation and
before either held-out suite. No policy/parameter changes followed test inspection.

On 600 cached test responses (200 start/goal pairs, 20 unseen maps, three prompt
styles), distinct expansions average 215.98 original / 168.99 selected (-21.76%).
Geometric-mean cost/optimal improves 1.02254 to 1.01035. All paths are valid.
**Raw heap pops increase 343.92 to 365.68 (+6.33%)**. Selected mean distinct count is
5.36% below common-engine WA2 and 3.25% below direct-shortcut-only; this smaller
increment measures actual added waypoint benefit. 137/600 routes have exact
zero-expansion certificates versus 75/600 direct-only. Zero expansions still
requires geometry/preprocessing and does not mean zero computation.

On the independent 192-case procedural suite, all 168 solvable cases succeed and
all 24 disconnected cases are correctly rejected. Solvable mean distinct counts
78.33 original / 63.19 selected (-19.33%). Extra waypoint benefit over direct-only
occurs in only two cases; much of the synthetic improvement is shortcut/fallback
geometry, not LLM content. Maze-family mean expansions slightly regress. Synthetic
useful points are generated from reference paths strictly as benchmark fixtures,
not as actual LLM responses and not available as a runtime oracle.

No per-case dominance versus original: 113/600 cached cases expand more distinct
states, 45/600 return longer paths. Maximum selected test path ratio is ~1.334,
higher than original ~1.310 despite better average and p95. Report tail tradeoffs.
Fresh-query timings (40 predetermined test queries, three shuffled repetitions)
are 38.57ms original / 1.57ms matched WA2 / 1.42ms direct-only / 2.24ms selected.
The large original speedup combines engine/collision engineering with guidance;
**the selected guidance adds CPU cost to matched controls**. No RAM reduction
claim: historical storage counters omit DAG and geometry allocations.

No live paid model calls were made. Cached prompt styles are not independent LLM
sampling replicates; generalization evidence is limited to 20 real held-out maps
and eight procedural families. More maps/seeds and fresh model caches are needed.
The contribution is combining certified selective LLM route use, a cheap map lower
bound and controlled ablations, not inventing Weighted A*, DAGs, or certificates.

## Offline API

```python
from llmastar.pather import CertifiedLLMAStar
planner = CertifiedLLMAStar(waypoint_response=cached_raw_response)
result = planner.searching(query_dict)
# result retains operation, storage, length, llm_output; inspect planner.path
# and planner.search_metrics / research_result for detailed instrumentation.
```

Set `PYTHONPATH=improving_llm_star` if importing from the repository root.
No waypoint generation/prompt changes. Without `waypoint_response`, the inherited
legacy initial model adapter is used; this work does not modernize its SDK/model.
Internal CLOSED/OPEN attributes of the inherited class are not research metrics.

## Reproduction (repository root)

Use installed `.venv` dependencies. No API credentials are needed for these commands.

```bash
.venv/bin/python -m pytest -q improving_llm_star/tests

.venv/bin/python -B improving_llm_star/experiments/research/benchmark.py --split development --variants original robust_original wa2 pop_switch budget_skip confidence focal11 focal11_goal --output /private/tmp/research-development

.venv/bin/python -B improving_llm_star/experiments/research/benchmark.py --split validation --variants original wa2 direct_only sieved_cert sieved_no_repair sieved_no_cut --output /private/tmp/research-validation

.venv/bin/python -B improving_llm_star/experiments/research/benchmark.py --split test --prompts standard cot repe --variants original alpha05 current_adaptive astar wa2 direct_only sieved_cert sieved_no_repair sieved_no_cut --output improving_llm_star/experiments/results/research/heldout_cached

.venv/bin/python -B improving_llm_star/experiments/research/benchmark.py --suite synthetic --split test --maps-per-family 3 --variants original alpha05 current_adaptive astar wa2 direct_only sieved_cert sieved_no_repair sieved_no_cut --output improving_llm_star/experiments/results/research/heldout_synthetic

.venv/bin/python -B improving_llm_star/experiments/research/audit_guidance.py
.venv/bin/python -B improving_llm_star/experiments/research/native_timing.py
.venv/bin/python -B improving_llm_star/experiments/research/verify_results.py
.venv/bin/python -B improving_llm_star/experiments/research/verify_native.py
.venv/bin/python -B improving_llm_star/experiments/research/report.py
```

Detailed gzip JSON stores every variant configuration, input/cache/source hashes,
case manifest hash, seed, costs, heap metrics, alpha/switch traces and preprocessing.
Original frozen operations/costs match existing Table 1 records on all 600 dev and
600 test observations checked. Independent vectorized Shapely audit validates all
768 successful held-out selected paths and confirms all 219 certificates optimal.
Earlier variants and negative results remain independently runnable by the exact
configurations embedded in their result files. Confidence intervals resample whole
maps; repeated prompt styles and waypoint fixtures are clustered together.

## Next steps for the assignment

Present the initial alpha hypothesis, its measured lifetime limitation, and the
certificate alternative as an evidence-led pivot. Separate engine fixes, goal-only
WA2, direct geometric shortcuts, candidate repair, wall bound, and waypoint content.
Benchmark a future cheap confidence gate for whether DAG preprocessing is worthwhile,
using new validation maps rather than retuning on this test set. Investigate bounded
suboptimal certificates (e.g. 1.02) only as separate future policies. Add peak RSS
measurement and more independently seeded maps before claiming memory/robustness wins.

References: original [LLM-A* paper](https://arxiv.org/abs/2407.02511),
[Explicit Estimation Search](https://www.ijcai.org/Proceedings/11/Papers/119.pdf),
[Anytime Focal Search](https://www.ijcai.org/proceedings/2018/199).

Production lazy geometry was independently replayed on all 792 held-out cases and exactly matched precomputed search costs, validity, distinct states and heap pops. A final exhaustive small-grid audit checks the wall-cut lower bound on every free start/goal pair for both wall orientations and all nondegenerate integer intervals on 100 wall maps.
