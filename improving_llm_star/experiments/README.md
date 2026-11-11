# Offline waypoint progress measurement

Adaptive weighting and the paired comparison are described in
[ADAPTIVE_ALPHA.md](ADAPTIVE_ALPHA.md). Run
`python improving_llm_star/experiments/compare_adaptive_alpha.py` from the
workspace root after activating `.venv`.

Run from the workspace root with Python's standard library (isolated mode):

```sh
python3 -B improving_llm_star/experiments/measure_waypoint_progress.py
```

With the project environment installed, use real package imports and Shapely:

```sh
source .venv/bin/activate
MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.venv/matplotlib" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -B improving_llm_star/experiments/measure_waypoint_progress.py --backend installed
python -m pytest improving_llm_star/tests -q
```

Installed-mode results go to `results/waypoint_progress_installed/`. Integration
tests also exercise the real plotting code and compare the installed-mode
results against the earlier isolated measurements. They block network access.

This measures the actual planner's search with six fixed waypoint fixtures at
constant alpha values 0, 0.5, and 1. No network or real model calls are used.
Five fixtures are hand-authored; the sixth uses the first public map/query and
the corresponding waypoint example in the repository prompt. These are not
saved GPT-4o mini responses or evidence of generalization.

The isolated backend loads the planner class through Python's AST. This was
initially needed because of a syntax error in `model/__init__.py` and missing
dependencies. The syntax error has since been fixed in the improvement copy,
and the dependencies are installed in the workspace `.venv`. Environment,
prompt formatting, parsing, filtering, search, queue rebuilding, and path
reconstruction come from the repository. Model responses and plotting are
substituted. Closed-segment intersection on these integer fixtures replaces
Shapely in isolated mode. Installed mode uses the actual imported planner and
Shapely; model answers and plotting remain substituted for the paired runs.

`LLMAStar(alpha=1.0, track_progress=True)` records summaries in the instance's
`waypoint_progress` list; the existing returned result dictionary is unchanged.
Tracking defaults to off. Each target activation has one summary, so recording
does not keep a full node trace. The first heap pop for a target establishes its
distance baseline. Later decreases beyond 1e-9 count as progress and reset the
stall counter. Equal distances, duplicate pops, and increasing distances count
as no progress. Counts include the goal pop, matching legacy `operation`.
The original neighbor-generation target-switch behavior is retained.

Outputs are `results/waypoint_progress/measurement.json` and `summary.csv`.
The JSON includes raw inputs, source labels, processed waypoints, search results,
and per-target summaries. `max_stagnation` is the longest consecutive run of
heap pops without a new best Euclidean distance to the active target.

The runner checks that tracking on/off preserves search results, exact paths,
parent maps, and pop order; that alpha=1 matches the frozen original; and that
measurements reset on progress, target transitions, and repeated searches.
No adaptive weight updates or changes to baseline bookkeeping are included.
