# Autonomous research log — 13 November 2026

Session start: 07:09:32 UTC. Local branch: `research/waypoint-guidance`.
No paid API calls, pushes, main edits, or historical-result modifications.

## Checkpoint 0 — Preserve existing corrections

Saved prior uncommitted adaptive corrections and documentation in a local commit.
Read the original paper, project notes, adaptive implementation and corrections.
Discovered 3,000 repository-cached responses, labelled GPT-4o mini by the notebook.
Raw cache provenance cannot independently establish the model version/settings.

## Iteration 1 — Switching, confidence, and bounded focal guidance

Hypotheses: (a) switching on actual expansion prevents premature acceptance;
(b) per-target expansion budgets avoid trapping search on poor points;
(c) geometric detour confidence and shortcut sparsification reduce harmful trust;
(d) focal eligibility can contain bad advice while controlling solution cost.

Data: 60 whole development maps, 10 start/goal pairs each, cached standard prompt.
The 20 validation and 20 test maps were not used. Map split seed: 20261113.
Compared 18 modes, including frozen source, common-engine baselines, current
adaptive, switching policies, confidence/sparsification, and focal controls.
53 tests passed at this checkpoint, including exact collision parity and focal bounds.

Results: `results/research/iteration1_development/`. Original GM cost ratio 1.02888.
Pop-switching had 2.263x original unique expansions: rejected as a standalone fix.
Focal variants reduced cost inflation, but incurred more expansions and multiple
heap operations. Focal w=1.1 used 1.526x original unique expansions: rejected as
primary efficiency improvement. Geometry+sparsification used 0.767x expansions
and cost ratio 1.01638, but goal-only weighted A* w=2 used 0.747x and cost ratio
1.01651. Therefore these preliminary gains do not establish an LLM-guidance benefit.
Timing comparisons with frozen code mix engine implementation effects; use
matched-engine controls for causal claims. Shared graph preprocessing is separate.

Infrastructure correction before recording results: serialize unobserved infinite
best distances as null; count focal waiting-heap removals in total heap pops;
use activation anchors for budgets; fix the shortest lattice shortcut ordering.

## Waypoint audit — Why reactive alpha often cannot act

Data: same 600 development queries, 5,118 distinct intermediate raw points.
Median active lifetime: 1 legacy pop; p90: 15. 93.45% of switched targets lasted
less than 30 pops; 94.34% less than 40. 298 targets had zero lifetime because
multiple targets advanced during one neighbor loop. 1.15% of switches occurred
through a blocked candidate edge. Current adaptive changed alpha on 205/600 cases.

14.91% of raw intermediate points were invalid/unreachable. 41.62% were invalid
or would increase the optimal path cost by more than 10% if forced through that
point. This is an operational potential-harm label, not causal proof that a soft
heuristic point harms search. Audit includes initial parsing fallback cases and
keeps them in the denominator. Exact shortest distances used only for offline
labels, not for algorithms' waypoint confidence.

Interpretation: the original neighbor switching often consumes dense waypoint
lists long before a 30-expansion feedback rule can activate. Corrected geometry
and pre-search trust decisions are more promising than simply lowering a timer.

## Iteration 2 — Certified waypoint incumbents (in progress)

Hypothesis: replace uncertain attraction with a verified candidate route constructed
from the cached waypoint sequence. Use valid route costs as upper bounds, and
accept immediately only when an admissible start lower bound certifies quality.
Otherwise retain a fast weighted goal search, pruning only states unable to beat
the incumbent. Compare with a goal-shortcut-only ablation to identify LLM contribution.

Iteration 2/3 development results: certified-path/weighted-incumbent use achieved
mean unique expansions 98.66 versus original 146.19 and common-engine WA2 108.47,
but candidate early acceptance based on the weighted frontier can degrade tails.
The tight start-certificate setting had little effect because the weighted
incumbent stop could subsequently accept a looser solution. This is not a
correctness failure (paths remain valid and the loose weighted bound holds), but
it defeats the intended quality-control interpretation. Preserve it explicitly
as `bound_stop=weighted`, and test admissible-anchor stopping instead.
Goal-shortcut-only was faster than full waypoint DAG preparation; genuine waypoint
contribution must be shown against this ablation. Only 5/600 extra DAG routes
were certified at the exact obstacle-free lower bound.

Bounded attractive heuristic bonus was also tested as a different trust strategy:
f=g+2h-alpha*max(0,h-d_target). It avoids penalizing goal proximity and defaults
to WA2 when trust vanishes. Geometry+sparsification version did not beat the
matched WA2 control reliably. Focal weights 1.5 and 2 reduced expansions but
inflated paths more than original: rejected for the primary efficiency/quality goal.

Validation: frozen-source operations and lengths matched the existing Table 1
JSON results on all 600 development queries (zero mismatches). This additionally
checks dataset/cache alignment and shared collision-graph equivalence.
Research record ratios now use (count+1)/(baseline+1), explicitly labelled, to
handle zero-expansion certificates without undefined or misleading log ratios.
Raw means and zero-expansion fractions are reported separately.

Large detailed research JSON files are preserved losslessly as `.json.gz`.
Expanded JSON/JSONL working copies are ignored, avoiding repository bloat.

## Iterations 3–4 — Better bounds and geometric repair

Development iterations retained independently in `iteration2_3_development/`,
`iteration4_development/`, and `iteration5_development/`. Anchor-based stopping
removed the misleading loose weighted-acceptance interpretation. Tight octile
certificates alone rarely accepted extra waypoint routes. Hypothesis: hints near
an obstacle corner are useful but offset by one cell. Radius-one axial candidate
repair increased certificates; endpoint repair was excluded because it would
credit start/goal geometry to the LLM. An admissible maximum of independent
single-wall crossing bounds certified obstacle detours beyond straight octile
cost. Compared against exact A* on randomized maps and mixed wall orientations.

Decision: test a certificate-only gate. If a verified route cannot meet the exact
admissible bound, discard it and run identical WA2 fallback. This sacrifices
soft waypoint effects but isolates safe positive guidance and prevents candidate
incumbents from worsening fallback quality. This is an explicit new algorithm;
the original final score and all earlier adaptive modes remain untouched.

## Iterations 5–6 — Preprocessing cost and validation

Lazy/incremental DAG certificate evaluation tested; fewer probes did not reliably
reduce CPU time. Rejected as default. Certificate-aware point and link sieve
proved safe: octile start/link/goal cost already above the admissible target bound
cannot participate in an accepted exact route. Retained this sieve, local repair,
wall-cut lower bound, and exact certificate-only WA2 fallback.

Validation: 200 standard-response queries on 20 map-disjoint validation maps.
Mean unique expansions original 160.485 / selected 114.605 / matched WA2 127.7.
GM cost ratio original 1.02663 / selected 1.01146 / WA2 1.01607. Preprocessing
remains slower than WA2. Selected mode `sieved_cert`, exact parameter object
and data protocol frozen at 07:45 UTC in `selection.json` **before test**.
No policy or parameter changes after test inspection. Subsequent edits only
add documentation, reports and audits. Production wrapper uses lazy geometry;
input query is copied and cached response avoids all API calls.

## Held-out evaluation and ablations

Real caches: 600 observations, 200 start/goal pairs, 20 unseen maps, all three
prompt styles. These are clustered observations, not 600 independent maps.
All 600 valid. Mean distinct expansions original 215.982 / WA2 178.560 /
direct-only 174.672 / selected 168.985. Selected/original reduction 21.76%;
whole-map bootstrap (2,000 resamples) ratio CI [0.6958,0.8512]. Against matched
WA2 ratio CI [0.9103,0.9705]; direct-only [0.9458,0.9825]. GM cost ratio
1.02254 original / 1.01035 selected; p95 improved, but maximum ratio worsens
(~1.310 original to ~1.334 selected). 113/600 selected runs expand more distinct
states and 45/600 return longer paths than original. No such regressions versus
matched WA2 or direct-only, as expected from certificate/fallback policy.

Ablation exact certificates: direct-only 75/600; no repair 105/600; no wall-cut
79/600; selected 137/600. This supports both repair and wall bound, with interaction.
These ablations are not all four factorial combinations, so no additive-effect
claim. Mean selected heap pops 365.677 versus original 343.917: **6.33% worse**.
Do not equate fewer unique states with fewer raw search operations.

Synthetic test: eight families, three independent map seeds each, two query
positions, four fixture qualities; 192 cases. 168 solvable paths valid; all 24
unreachable cases correctly rejected. Solvable mean distinct original 78.333 /
selected 63.190 (-19.33%); clustered CI [0.5447,0.9334] for ratio. Whole-suite
mean includes unreachable cases and differs (126.833 / 113.583). Extra LLM-fixture
benefit over direct-only occurs in only two cases; its clustered ratio CI reaches
1.0. Maze mean expansions slightly regress versus original. This is weaker
cross-family waypoint evidence than the cached-map result, explicitly retained.

## Native timing and independent correctness audit

40 fixed held-out standard queries (indices 0 and 5 per map), three shuffled
repetitions per method, fresh per-query geometry. Median CPU milliseconds:
original 38.565; matched WA2 1.570; direct-only 1.418; selected wrapper 2.239.
The native-original difference includes geometry/search-engine effects. Selected
is slower than efficient controls, so primary supported win is distinct-state
count and average path quality, not matched CPU efficiency. Shared graph timing
and preprocessing totals are also saved. No peak-RAM claim from storage counters.

Independent vectorized Shapely audit regenerated all held-out selected paths:
600 cached +168 synthetic valid paths; 137+82 exact certificates equal optimal
A* costs; 24 correctly rejected disconnected cases. Frozen original operations
and costs match existing Table 1 JSON for all 600 cached held-out observations
(additional to 600 development matches). Final full automated suite: 65 tests (65 passed in 5.54 seconds).
No API calls, pushes, merges, or modifications of historical original results.

Reproduce with exact commands in `README.md`; all exploratory configurations and
per-case metrics are stored in gzip JSON, with source/input hashes and case hash.
Time accounting: session began 07:09:32 UTC; final actual end time recorded in the
last status entry below. No artificial waits to meet the target duration.

Final strengthening: production on-demand geometry exactly reproduces all 792 held-out selected results (validity, cost, distinct count and heap pops). Exhaustive lower-bound test covers every free start/goal pair on 100 small integer-wall maps, both orientations. No algorithm policy was changed for these audits.

Final report validation at 08:07:21 UTC: 57 minutes 49 seconds since session start,
followed by final documentation/commit checks (approximately 58 minutes total).
Verified all report links and all 7,128 held-out result records. This is an
approximate one-hour session, not a claim of exactly 60 minutes. Selected policy
has a supported distinct-expansion/average-quality benefit; no universal win on
operations, runtime, path tails, or all synthetic families is claimed.
