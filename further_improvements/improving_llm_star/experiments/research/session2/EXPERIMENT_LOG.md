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

## Iteration 6: map witnesses reveal the key confound

The single-wall lower bound itself identifies adjacent endpoint crossing states.
Test verified routes through these witnesses before consulting uncertain hints.
This is NOT an LLM contribution. Witness-only and witness+exact-LLM are controlled
ablations. On 600 cached development cases, 11 repeats: witness-only 0.3346ms
versus lean WA2 0.5624ms, 467/600 exact certificates versus old CF 194/600.
Mean unique 58.70; heap pops 127.24. Exact LLM stage adds ZERO accepted routes or
expansion savings on these 600 cases; it adds CPU overhead (0.3496ms). Strong
runtime result, but geometry alone explains it. Do not market as an LLM benefit.

## Iteration 7: alternative corridor search and hybrid incumbents

Attempt A* in a radius-1/2 waypoint tube with capped cells/expansions. Accept only
with a weight-2 admissible bound; otherwise run global fallback, optionally using
a valid corridor route as an incumbent. Count ALL pops, repeated expansions and
preparation. Corridors were slower on 160 development fixtures: 2.71/3.06ms versus
matched 2.08ms, with more operations and worse costs. Reject as default. Small
bookkeeping correction after pilot: a returned incumbent goal is not counted as
expanded unless actually popped; no effect on paths or the negative conclusion.

Hybrid witness+raw chain or DAG frontier incumbent can exploit strong oracle hints
on procedural maps, but cached development benefit is tiny: witness+chain saves
0.30 unique states/case and raises mean path length ~0.02, with 0.341ms versus
witness-only 0.336ms. Full DAG saves 0.75 states/case and costs 0.353ms. Preserve
as explicit weight-2 optional modes, not optimal-certification claims.

Validation protocol now begins: whole prior validation split, all three cached
prompt styles (600 observations /20 maps), 11 repeats, plus independently seeded
procedural validation. No old held-out test map used for tuning. After this one
selection round, freeze policy and evaluate new seed-660000 test maps once.

## Selection frozen before fresh evaluation

Validation cached: witness-only 0.3379ms versus lean WA2 0.6698ms; 447/600 exact
certificates, 59.885 unique versus127.7. Exact LLM extension adds 3 certificates
and saves 0.19 states/case, but costs 0.3552ms. Whole-map bootstrap shows extension
runtime ratio vs witness-only ~1.051, CI [1.035,1.075]. Frontier DAG accepts 10
hint routes, saves ~1.21 states/case, runtime1.045x and occasional path inflation.
Raw-chain frontier accepts5 and runtime1.009x. No cached-guidance runtime win.
Procedural validation: chain frontier 1.073ms vs witness-only1.152ms, mainly strong
oracle fixtures; this does not establish real-model usefulness. Keep as secondary.

Public interface validation (40 predetermined real cached queries,9 repeats):
original41.678ms, oldCF2.403ms, matchedWA2 0.646ms, witness-only0.409ms,
witness+exact0.447ms. Imports/network/rendering excluded uniformly, all query-copy,
parsing, geometry and search included. No paid API calls.

Profiling new pipeline: direct/each bound~3-4us; wall-witness stage~15us; optional
hint candidate/DAG stage~17us on fixed development cases. Python tracemalloc
mean peaks oldCF225kB, witness-only138kB, matched lean WA2 188kB on24 fixed cases.
Native-library memory/imports excluded; these are not RSS measurements. Profiling
is instrumented and separate from primary speed comparisons.

Final safety adjustment before freeze: arbitrary/fractional geometry and
zero-length barriers preserve actual installed unit-edge predicates even when
checking macro pieces. Integer-only cut bounds are disabled on fractional maps.
Fresh evaluation policy in selection.json: primary runtime method witness_only;
exact and frontier LLM variants retained as ablations. 80 new maps/640 cases,
seed base660000, ten families including large maps. No test generation/inspection
before selection. Cached prior test replay is explicitly opened confirmation,
not a new independent holdout. No policy/parameter changes after freeze.
Final primary timing runs will be sequential. Exploratory runs occasionally
shared CPU with other instrumentation; robust medians help but do not erase that
limitation, hence no final speed claims rely solely on those trials.

## Frozen final evaluation — results and protocol deviation

640 fresh cases /80 maps, 11 repeats per variant: all576 solvable cases valid and
64 unreachable correctly exhausted by new methods. Witness-only mean case-median
1.6356ms versus matched WA2 1.7073ms (ratio0.9580, clustered95%CI[0.9051,0.9873]).
Not uniform: maze and large-maze families regress; sparse/open/large-random maps
improve most. Exact hint stage1.6531ms, only one added certificate. Raw-chain
frontier1.5383ms; ratio to witness-only0.9405 CI[0.9017,0.9682], but this fixture
mixture includes oracle-quality hints, not real LLM sampling. One case has worse
cost than witness-only. Preserve and explain conditional utility.

Opened cached confirmation (600 observations,7 repeats): original-indexed7.8036ms,
oldCF3.1204ms, lean WA2 0.9223ms, witness-only0.5421ms, exact-LLM0.5662ms.
Witness-only distinct states100.655, pops209.68, GM cost/optimal1.00496, versus
original215.982 /343.917 /1.02254. Exact hint stage accepts zero extra routes.
Raw-chain uses3 and full frontier9 hint routes; neither produces a net cached
runtime improvement over witness-only. Do not call the large geometric gain an
LLM-specific result. Confirmation was already opened in Session1.

Native protocol incident: buffered output was misdiagnosed as slow JSON export;
interrupting parent at05:42:50 also interrupted the active native-original run
(after progress71/80). It had no saved native results; none are reported. Full
fresh_core timings were complete and untouched. Preserve interruption note.
Rerun native with per-trial journals and a uniform two-second cap for EVERY mode;
35 original-native trials censored, all other modes complete. Original observed
mean202.415ms is a LOWER BOUND, not a full mean. Public WA2 1.8557ms,
oldCF12.5600ms, witness-only1.7679ms, exact-LLM1.8127ms on80 fixed map-balanced
queries,7 repetitions. New algorithms unchanged. Core evaluation remains uncapped.
Gzip output now uses buffered JSON encoding; this affects export only, outside
all search timing boundaries. No core rerun or timing-record modification.

Independent vectorized Shapely validation: all4 selected variants on576 fresh
and600 cached successful cases; costs agree with emitted unit paths; every exact
certificate equals A* cost; global factor2 checked; every new method agrees on
reachability. Original-indexed operations and costs match existing Table1 data
for all600 cached cases. Primary/exact-hint never regress in path cost or unique
states versus their matched fallback controls. 82 automated tests passed.
Reports, whole-map CIs, source snapshots, cached/fixture provenance, Python peak
allocations and plots saved. Numerical claim scope remains distinct across fresh
fixtures, opened real caches, native censored timing and instrumented profiling.

Final integrity check at 05:54:31 UTC (59 minutes08seconds after session start):
70,400 fresh-core +42,000 opened-confirmation +3,920 native-interface trial records
verified. Every final-core source snapshot matches its recorded SHA-256 hash.
Production algorithm files remain byte-identical to the pre-test freeze87c3310;
post-freeze edits concern export safeguards, analysis, documentation and reports.
Original `llm-astar/` and historical `table1_reproduction/` unchanged versus main;
main still66baa31. Full canonical-source whitespace checks and compilation pass;
archived frozen source intentionally retains its original whitespace. Approximately
60 minutes elapsed including final artifact/commit checks; no artificial waits.
