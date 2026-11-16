# Research session 2 — 16 November 2026

Start 04:55:23 UTC, branch `research/waypoint-guidance`; no paid calls/push/merge.
Session 1 code and artifacts preserved. Development and validation splits retained;
previous test cases are not used for tuning. Plan fresh procedural test seeds after
selection, clearly separating fixture hints from real cached model responses.

## Baseline profiling

120 fixed development cases (query indices 0,5 on each of 60 maps), five repeats,
fresh LazyGridGraph every time. Mean total 2.841ms, preprocessing 1.525ms,
search 1.300ms; median total 1.489ms. 568 visibility unit-edge probes cause ~1,138
geometry neighbor checks per case. cProfile: 0.899s/120 queries, 0.690s cumulative
lazy adjacency, 0.576s collision, 0.413s shortcut; heaps ~0.007s combined. These
nested cumulative numbers overlap and must not be added. Lower-bound computation
~0.001s, ~0.1% of instrumented total. Heap count is not the main runtime bottleneck.
Degenerate walls switch entire maps to repeated Shapely construction/intersection.

## Iteration 1: indexed unit-grid geometry

Hypothesis: integer axis-aligned walls intersect unit integer grid edges only at
endpoints. Index intervals by row/column and cache point occupancy. Check individual
shortcut edges directly instead of constructing all eight neighbors. Preserve
installed Shapely handling for degenerate walls near the degenerate point; use
unchanged legacy geometry on noninteger maps. All index/cache setup charged per
query. No reuse across variants or queries. Test all unit edges on 20 random maps
with both wall orientations and degeneracies; compare certificate outputs and
noninteger fallback. Three new tests passed. Compare both guided and unguided
search on old/new engines to isolate geometry engineering from LLM contribution.

Iteration 1 result: old certificate 2.765ms -> indexed certificate 1.187ms mean
per-query median; matched WA2 1.761 -> 0.604ms. Outputs unchanged. Main speedup
is generic geometry engineering, not evidence that guidance pays for itself.

## Iteration 2: reachable-prefix DAG and selective gates

Avoid validating links whose source cannot yet be reached; process the layered
DAG topologically; cache octile-to-goal distances; stop when a verified exact
certificate is found. Discard links that cannot meet the certificate bound given
the actual known prefix cost. Compare early goal-link ordering, raw hints only,
and cheap gates (short query / dense hints / no bound detour). Also implement
independent controls for accepting a nonoptimal but bound-2 candidate and for
using an uncertified valid route as an incumbent upper bound with admissible pruning.

120 development cases, five interleaved repeats: reachability-first 0.894ms
versus indexed old certificate 1.163ms, same unique expansions/certificates on
these cases. Probes 568 ->341. Goal-first and detour gate negligible differences.
Dense-list gate 0.720ms and raw-only 0.684ms; both lose some certificate savings.
Matched WA2 0.598ms. Uncertified acceptance 0.912ms worsens average cost versus
exact-only; incumbent pruning 0.917ms improves costs slightly but not runtime.
No winner over matched control yet. Gate thresholds are exploratory development
choices, not generalization claims. Preserve all options/configurations.

## Iteration 3: exact macro-segment validation

Hypothesis: each of the two shortest lattice-walk orderings is the union of at
most two straight continuous pieces. Verify those pieces against indexed integer
walls, rather than constructing and probing every unit edge of every candidate.
Only expand the final accepted route into unit moves. This is exact for these
lattice walks; it is not unrestricted continuous line-of-sight smoothing.
Separate segment-test/wall-test counters; do not count a segment predicate as one
heap pop or pretend zero unit-edge probes means zero work. Separate cap of 256
candidate segment attempts, alongside original unit-probe budget. Seven new
correctness tests pass, including 1,000 randomly sampled complete lattice links
with degenerate walls and unit-route equality against original Shapely semantics.

Iteration 3 result: macro-segment certificate 0.707ms, versus 0.903ms reachable
unit evaluation and 1.179ms indexed original. Same certificates and unique states
on 120 cases; segment-only shortcut control 0.596ms versus matched WA2 0.619ms.
Uncertified pruning 0.749ms adds runtime despite slightly improved path cost.

## Iteration 4: collinear compression, single-pivot and bounded-quality routes

Remove forward-collinear/duplicate raw hints in linear time before local repair.
Test a single-pivot candidate graph versus full adjacent-layer graph. Independently
test beta=1.02/1.05/1.1 quality-gated routes: U<=beta*L is beta-bounded, not an
optimal certificate. Logging now separates bounded acceptance from exact optimal
certification. Nine new tests passed, including backtracking preservation and
correct labels for loose gates.

120 cases, five repeats: compressed exact certificate 0.644ms (same 34.17% exact
certificates), single-pivot 0.628ms, compressed raw 0.617ms versus control 0.614ms.
Beta gates do not offer a convincing efficiency/quality win and sometimes take a
slightly longer early route instead of an exact certificate. Do not promote on
these small timing differences. Start full 600 development queries with nine
randomized repetitions before validation/selection. Current parameters remain
exploratory; no old held-out cases used for tuning.

## Full development confirmation and provenance correction

600 development queries, nine repeats: old CF 2.665ms, indexed CF 1.179ms,
compressed CF 0.683ms, raw compressed 0.667ms, pivot 0.672ms, indexed WA2 0.652ms.
Compression loses 13/600 exact certificates (30.17% versus 32.33%), so not a
behavior-preserving optimization. Quality beta1.05 0.680ms, modest cost regression;
uncertified pruning 0.989ms improves cost but not runtime. Negative result: no
robust matched runtime win from these methods on all development data.

Source provenance issue detected: the old harness hashed at completion while
new optional modes were being added on disk. A sidecar note preserves this fact
without altering historical result bytes. Harness now snapshots/hashes all source
files at run START. No final claim will depend on the affected source hash; selected
algorithms will be frozen and rerun. Changes during that exploratory run only added
unselected options, but exact old source identity should not be overstated.

## Iteration 5: search-effort scheduling and frontier-certified incumbents

Selective direction: try exact certification once only after 16/64 actual search
expansions, avoiding preparation on queries already solved quickly. Keep an
identical search-loop no-guidance control to isolate generic engine differences.
Alternative use of uncertified routes: retain a valid upper bound U; stop weighted
search only when U<=min live (g+2h), which supports weight-2 quality, not optimality.
Compare full DAG against compressed raw-chain-only preparation and pruning-only.
This revisits the earlier loose frontier bound only with the new measured fast
geometry/candidate machinery; its quality-tail limitation remains explicit.

A new procedural generator is fixed before test: disjoint seed bases 440000
(development), 550000 (validation), 660000 (fresh test); eight former families plus
4x larger random-wall and maze maps. Two start/goal pairs/map and four fixture
qualities. Helpful fixture is the complete compressed optimal-route corners;
this is an oracle-quality deterministic fixture, NEVER real LLM evidence. It
probes whether any method can exploit strong hints in difficult large maps.

Scheduling pilot (120 cached cases): scheduled64 0.565ms versus matched lean WA2
0.535ms and lean direct-only 0.526ms. So the apparent advantage versus old 0.6ms
control was a search-engine confound; retain the lean control explicitly. Chain
frontier 0.610ms, with worse mean path length. No broad guidance runtime win.
Add lean fallback to exact CF as an explicit configuration and remove redundant
fallback path validation where the same engine already validated its result.
Accepted macro routes remain collision-certified by construction; test geometry
independently and still calculate the returned unit-edge path cost.

Engineering correction: fractional wall coordinates disable integer-only wall-cut
bounds in new code (octile bound remains admissible); geometry falls back to the
original predicate. 77 tests pass. Procedural run encountered a JSON serialization
failure for an infinite disconnected-map bound; preserve failed partial archive
and note, apply existing finite_json normalization, journal completed cases, and
rerun under a new directory. No historical results overwritten.
