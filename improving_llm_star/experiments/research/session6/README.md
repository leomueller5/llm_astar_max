# Session 6 — geometry-gated verified waypoint search

The implemented candidate is **LLM-A*-VM**, exposed as
`llmastar.research.hybrid_guidance.HybridWaypointPlanner`. It uses a geometric
route portfolio, optionally requests three compact endpoint-ID strategies from
the exact GPT-4o-mini snapshot, applies route consensus, and inserts only
physically verified macro transitions into a complete grid search.

The original, constant-alpha and adaptive-alpha planners remain unchanged.
Promising development numbers did **not** establish a reliable additional LLM
benefit over strong matched geometric controls. Consult the final report before
making any performance claim. Low-level search-work reductions are distinct
from preprocessing costs and API latency.

## Run the implementation

The structured query and the four original result keys (`operation`, `storage`,
`length`, `llm_output`) are preserved. Additional fields contain the dense path,
validity, queue work and timing. `searching(query, filepath=...)` is accepted;
plotting is intentionally separate from headless search. Dictionaries and JSON
strings work offline. Natural-language strings require a provider parser, as in
the original model-backed interface.

```python
from llmastar.research.hybrid_guidance import HybridWaypointPlanner

# No API call: geometry fallback, or supply previously generated coordinate routes.
planner = HybridWaypointPlanner(weight=2.0, selection="consensus")
result = planner.searching(query, routes={"routes": [route1, route2, route3]})
```

The native package requires NumPy and Shapely. The complete historical benchmark
also imports the repository's existing model/plotting dependencies. The exact
tested environment is recorded in `requirements-tested.txt` and
`../../results/research_session6/environment.json`. No new runtime dependency was
needed for the proposed algorithm.

```sh
PYTHONPATH=improving_llm_star .venv/bin/python improving_llm_star/experiments/research/session6/run_hybrid.py \
  --query-file /path/to/query.json --routes-file /path/to/routes.json \
  --output /tmp/llm-astar-vm-result.json
```

Only `--online` enables real requests. The provider always uses
`gpt-4o-mini-2024-07-18`, loads the authorized credential into process memory,
and uses the existing cumulative ledger. It never prints the key. One logical
guidance request is allowed per query, with at most two separately reserved
transport attempts. Natural-language parsing is a separate bounded request.

```sh
.venv/bin/python improving_llm_star/experiments/research/session6/api.py status
.venv/bin/python improving_llm_star/experiments/research/session6/run_hybrid.py \
  --query-file /path/to/query.json --online --output /tmp/llm-astar-vm-online.json
```

Do not reset/delete the Session 5 SQLite ledger or either portable export to
obtain a fresh allowance. Historical unknown-cost failures retain their full
reservations. Reasoning tokens are counted within completion tokens, never
double charged.

## Reproduce without API costs

All published search comparisons reuse stored raw model responses. These
commands make no network requests. Output directories must be new so historical
results cannot be overwritten.

```sh
.venv/bin/python -m pytest improving_llm_star/tests -q

.venv/bin/python improving_llm_star/experiments/research/session6/final_benchmark.py \
  --cases improving_llm_star/experiments/results/research_session6/heldout_all.json.gz \
  --original improving_llm_star/experiments/results/research_session6/heldout_original_a/responses.json.gz \
             improving_llm_star/experiments/results/research_session6/heldout_original_b/responses.json.gz \
  --hybrid improving_llm_star/experiments/results/research_session6/heldout_hybrid/responses.json.gz \
  --repeats 5 --output /tmp/llm-astar-session6-replay

.venv/bin/python improving_llm_star/experiments/research/session6/analyze_final.py \
  --results /tmp/llm-astar-session6-replay/results.json.gz \
  --paper improving_llm_star/experiments/results/research_session6/heldout_paper_denominator/results.json.gz \
  --output /tmp/llm-astar-session6-analysis
```

Exact deterministic work/path outputs are the reproducibility target. Runtime is
machine dependent. Every timed trial creates fresh geometry, candidate routes
and a goal-specific anchor; no cached preprocessing is free. Warmups are
excluded, method order is randomized, and each method receives the same
three-second trial cap. Heap instrumentation runs separately from native timing.
Timeout records are censored and are not treated as zero work or solved paths.

The final test comprises 200 tasks on 20 reserved team maps and 20 newly generated
tasks from ten challenging families. Report those two strata separately. The
40-query factorial subset was fixed as the first query on each team map plus all
20 synthetic tasks. `frozen_manifest.json` records the selected parameters and
source hashes before those test tasks were prepared. Only an AST-identical EOF
whitespace cleanup was made afterward and is recorded explicitly.

## Ablations and controls

`source="geometry_best"`, `"geometry_consensus"` and `"all_endpoints"` are three
strong no-model controls with the identical search engine. `source="goal_only"`
omits candidate-route generation. `source="llm_only"` uses an appropriate
coordinate provider without geometric candidate guidance. `hybrid_always`
disables the geometric call gate for the explicit prompt/call-policy ablation.

`selection="first"` removes consensus. `probe_budget=0` removes advisory macro
edges. `share_anchor=False` isolates preprocessing reuse. `heuristic="euclidean"`
isolates the stronger geometric anchor. `weight=1.05` is the tighter-quality
profile; `weight=1` retains optimality under the verified-edge conditions.

The alpha subset distinguishes the existing adaptive default (final `g+h`) from
the explicit matched final-goal setting (final `g+2h`). In the old class,
`final_goal_weight=1.0` denotes the **additional** goal coefficient, so its total
coefficient is two. The frozen original's final heuristic is never silently
changed. The WW team implementation is loaded unchanged as a separate baseline.

## Research record and known invalid pilots

`EXPERIMENT_LOG.md` records successful and rejected hypotheses. `CHECKPOINT.md`
contains the resumable state. The first 384-token original-prompt pilot is
excluded from fair comparisons; original outputs were regenerated with the
original 1,000-token allowance. Three original responses still hit that cap in
the initial 16-case development set; those outcomes were retained.

The early `macro_portfolio_geometry` comparisons in `validation_search` and
`portfolio_regret_development` inherited LLM route metadata and are invalid.
Corrected controls replace all model metadata, and regression tests enforce
independence. Early portfolio-only rows in `opportunity_pilot` used inconsistent
easy-case gating and are exploratory, not confirmatory. The later full studies
use identical easy-case geometric advice. Main `macro_cut_geometry` and random
controls were unaffected by the metadata bug.

The first interactive-frontier pilot's exact source is preserved as
`frontier_development/source_frontier_v1.py`; later alias deduplication changes
its context hashes. Replay that pilot with its preserved source and context
archive rather than pretending a changed search state has the same response.

## Research contribution and limits

The defensible contribution is a **verified integration** of uncertain LLM
waypoint hypotheses with bounded A* search, plus a controlled empirical study.
Macro edges, visibility graphs, consensus and lazy evaluation are established
ideas. This project adapts them to the original LLM-A* failure modes; it does not
claim to invent those techniques or prove absolute academic novelty.

The model never supplies an admissible bound, a trusted edge cost, or permission
to cross an obstacle. Its proposals only select optional transitions. A complete
unit-edge fallback remains available. CPU gains from indexing, cut lower bounds
and shared preprocessing must be credited to geometry. A claim about the LLM
requires superiority to the matched geometric controls, not just to the original
implementation.

References and a full guarantee are in `THEORY.md`. Scientific figures and the
held-out results are generated under `experiments/results/research_session6/`.

## Additional final controls and diagnostics

```sh
.venv/bin/python improving_llm_star/experiments/research/session6/heldout_controls.py \
  --root improving_llm_star/experiments/results/research_session6 \
  --output /tmp/llm-astar-guidance-controls --seeds 10

.venv/bin/python improving_llm_star/experiments/research/session6/always_study.py \
  --cases improving_llm_star/experiments/results/research_session6/supplementary_cases.json.gz \
  --responses improving_llm_star/experiments/results/research_session6/supplementary_guidance/responses.json.gz \
  --output /tmp/llm-astar-ungated-controls

.venv/bin/python improving_llm_star/experiments/research/session6/final_diagnostics.py \
  --root improving_llm_star/experiments/results/research_session6

.venv/bin/python improving_llm_star/experiments/research/session6/plot_results.py \
  --root improving_llm_star/experiments/results/research_session6 \
  --output /tmp/llm-astar-session6-figures
```

The supplementary hypothesis was separately frozen before preparing twenty new
maps (`supplementary_frozen_manifest.json`). It changes no primary algorithm:
all model and geometric controls use `source="hybrid_always"`, with identical
preprocessing, three-target probes, lower bound, and budget. Five endpoint
bijections preserve the real response's full vote/overlap pattern. The apparent
always-call advantage in the first factorial subset did not replicate.

Final results: [full report](../../results/research_session6/REPORT.md),
[team explanation](../../results/research_session6/TEAM_BRIEF.md),
[figures PDF](../../results/research_session6/figures/SESSION6_FIGURES.pdf),
[budget audit](../../results/research_session6/BUDGET_REPORT.json).
The budget export and portable response caches are sufficient for offline
reproduction; no credentials or network access are needed.
