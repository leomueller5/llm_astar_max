# Session4 research log — fundamental strategic redesign

Start08:57:26UTC on17November2026. Three-hour target if environment permits.
No main edits, historical-result overwrites, pushes, paid API calls, or key access.

## Prior evidence and literature boundary

Sessions1-3: delayed alpha misses short waypoint lifetimes; raw coordinate guidance,
static corridor retries, focal loops and prefix seeding did not prove real-model
benefit. Witness improvements were geometric. Session3 random/wrong-response and
uniform-weight controls refuted weaker success claims. Do not retune those methods.

Primary technical references consulted:
- Aine et al., Multi-Heuristic A*, RSS2014:
  https://ai.dmi.unibas.ch/research/reading_group/aine-et-al-rss2014.pdf
- Botea et al., Near Optimal Hierarchical Path-Finding,2004:
  https://webdocs.cs.ualberta.ca/~mmueller/ps/2004/hpastar.pdf
- Thayer/Ruml, Explicit Estimation Search, IJCAI2011:
  https://ijcai.org/proceedings/2011/119
Established anchors/abstraction/focal methods are not claimed as novel inventions.
The project contribution must be the representation, integration, measured
tradeoffs and controlled ablations, with genuine versus simulated evidence clear.

## Phase1: information-potential experiment

120 fixed development queries,5 repeats, original real standard responses versus
random/geometric/oracle/imperfect-oracle inputs, same fresh geometry each run.
Existing verified-chain: Witness0.3223ms/54.73states; real0.3299ms/54.73states;
oracle0.0713ms/3.49states with GMcost1.0; perturbed oracle0.2732ms/36.53states,
GMcost1.01605. Prefix method oracle0.2959ms/46.26states: its first8-point policy
underuses full-route information. Full ordered refinement oracle0.0769ms/zero
search states, GMcost1.0, versus real0.6264ms and GMcost1.2194. Ordered refinement
has validity-only guarantee and is NOT a deployable bounded winner. Naive random
or unordered endpoint sequences are bad controls for route quality, not strong
classical planners. All source sizes recorded; oracle generation charged separately
as an unavailable-information diagnostic, not claimed as real-model performance.

Interpretation: useful coordinate routes have substantial potential. Poor hint
quality and integration/budget restrictions both matter; this is not proof that
coordinate representations are fundamentally incapable. Strategic advice remains
promising, but must beat strong topology-aware classical controls. Latency matters:
sub-millisecond savings cannot pay for per-query real model latency of seconds.

Schema/provider foundation: strict versioned strategy, regions, bypasses and
legacy Generated Path support. Malformed text initially exposed the old parser's
(0,0) fallback; replaced by explicit marker+JSON decoding with abstention on errors.
No new parser treats the default coordinate as advice. Provider responses are
untrusted data, with separate actual processing versus simulated latency ledger.
Three schema/provider tests pass; no provider performs network requests.

## Phase2 start: component/portal abstraction

Build exact 8-connected components inside tiles. Boundary free-run portals yield
an admissible relaxed graph: local costs are minimum octile distance between port
sets, and real cross-tile edge costs. Teleportation within portal sets only relaxes
cost, never certifies an actual path. Low-level corridor search must construct and
validate a real grid route. Start bound and optional per-state bound are checked
against exact grid shortest costs. Preprocessing visits every map cell; report this
work, time and memory separately, never call it free node-expansion savings.
Rasterization and hierarchy are classical components with matched no-LLM controls.
Four tests pass, including all free starts on24 small random maps vs exact costs.

## Phase2 result: hierarchy provides bounds, not a runtime win

32 new development queries, eight families, size64, four queries per map,
three randomized method-order repeats. Coarse portals: start LB/opt0.2682;
flat weight1.1 mean query1.545ms,904.19 distinct states; geometric corridor
2.309ms/648.94; oracle corridor2.341ms/645.66. Including per-map setup actually
amortized over four queries:1.553ms flat,4.952ms geometric,4.079ms oracle.
The different single setup samples are noisy: do NOT infer a guidance benefit
from their timing differences. Point portals tighten LB/opt to0.94099 and reduce
oracle states to418.72, vs classical419.75, but query3.128ms and amortized8.823ms.
Decision: retain as a correct strategic/dynamic baseline, reject cold runtime
winner. Oracle contributes almost nothing beyond this topology-aware classical
control. Build costs and portal Dijkstra dominate. These first exploratory
pilots did not snapshot sources at launch; portal-span config is saved and all
later timed pilots snapshot sources before execution. No final quantitative
claim should depend on reproducing bit-exact early exploratory source state.

Reproduce:
```
.venv/bin/python improving_llm_star/experiments/research/session4/hierarchy_pilot.py --cases improving_llm_star/experiments/results/research_session4/pilot_maps.json.gz --repeats 3 --output /private/tmp/hierarchy-coarse
.venv/bin/python improving_llm_star/experiments/research/session4/hierarchy_pilot.py --cases improving_llm_star/experiments/results/research_session4/pilot_maps.json.gz --portal-span 1 --repeats 3 --output /private/tmp/hierarchy-point
```

## Phase3 hypothesis: monotone cut relaxation with proof-checked strategies

A path must first cross every separating integer wall column/row. Keep its
crossing coordinate but relax all intervening geometry: dynamic programming
across cuts yields a lower bound even when the true route backtracks. O(H)
octile min-plus transforms avoid dense portal-edge graphs. Actual route proposals
are separately collision checked; advice never changes the lower bound. Verified
prefixes can initialize g with real costs, and an anchor start remains present.
Full incumbents terminate only under admissible/weighted frontier certificates.
Provider can intervene on candidate failure or effort; static cached responses
are never spuriously counted as newly generated replies. Multiple candidate
strategies are tested under one segment budget. All latency in simulated ledger;
no sleeping/network/API. Bounds/transform tests and adversarial bounded-search
tests pass on small exhaustive/random maps. Cold pilot now running.

## Phase3/4 result: stronger geometry, weak real advice

120 fixed cached development queries, five/seven repeats, fresh graph per query.
After measuring redundant heuristic calls, avoid computing h before a failed g
relaxation; cache h values per state. Counter/path regression unchanged. Cold
cut geometric time fell from0.442ms in first pilot to0.359ms in subsequent pilot
(time samples from different runs, not a paired estimate of optimization alone).
Witness0.322ms, cut real0.387ms, cut oracle0.214ms. Cut geometric27.48 states,
real27.48, oracle8.33; cost GM1.00085/1.00085/1.0. Real advice has no established
benefit. Roadmap-augmented geometry0.276ms, real0.312ms, oracle0.355ms. Adding
oracle vertices to a bounded roadmap can spend its fixed probe budget badly;
more supplied information is not automatically used effectively. Roadmap work
must be reported separately from low-level grid states/pops.

New lazy roadmap: edge-event A* over a capped geometric endpoint set plus advice
vertices. Edges are checked only when useful. It only generates candidates; the
complete bounded wrapper remains responsible for quality and fallback. Distinct
from earlier single-pivot Witness and one-shot coordinate filtering. Primal-first
variant defers cut construction until a valid candidate needs it; cheap single-
wall certificates precede expensive checks. It preserves a complete weighted
fallback and returns the shorter verified route. On120 cached dev queries at
w1.1: geometry0.298ms, real0.327ms, oracle0.294ms; no general LLM-specific win.

132 independently generated DEVELOPMENT queries,11 families, sizes64/128/256,
three maps/family, four pairs/map, five repeats.120 reachable,12 disconnected.
At w1.1: weighted43.265ms/6557.27states, Witness46.146ms/5359.98states,
cut geometry20.753ms/2406.79states, oracle24.443ms/2126.92states. GMcost ratios
1.000019,1.01377,1.000086,1.0 respectively. Oracle saves states but costs more
mean time. This confirms why expansions alone do not establish runtime success.
Point-free octile control46.487ms/6209.33states: cut improvement is not explained
just by replacing Euclidean h with octile h. No advice exists from real models on
these new maps; every non-geometric source is explicitly synthetic/oracle.

Measured eight large maze/serpentine oracle queries with cProfile:2.964s total
instrumented time,0.851s legacy_bypasses all-walls/all-points interpretation,
0.228s record_prefix (repeated prefix sums),1.187s grid neighbor generation.
These are instrumented diagnostic costs, not native runtime estimates. Decision:
legacy inference no longer runs by default; explicit structured bypasses remain.
When enabled, skip inference after an already valid chain and cap pair work8192.
Maintain incremental prefix costs and share immutable segment lists with prefix
length indices; eliminate full-prefix copies without changing valid g seeds.
This addresses measured quadratic overhead rather than tuning map parameters.

## Information audit (development only, v2 supersedes initial audit)

1800 real cached responses:600 distinct queries on60 maps, standard/cot/repe.
Witness solves467/600 before needing advice. On133 residual queries, cleaned
nonempty route chains valid only2/4/4 for standard/cot/repe; their GM cost ratios
1.1600/1.2063/1.2666. Raw polyline crossing violations in120/127/122 residual
responses; abstentions12/5/8 are excluded from that violation count. This says
raw straight connections are unsafe, not that every detour between targets is
impossible. All600 samples: point-on-wall rates11.10%/14.35%/8.73%.

Important parser finding: some long answers contain a complete Generated Path
followed by a truncated duplicate. Recover the last COMPLETE marked2-D array,
otherwise abstain. Never manufacture the old default(0,0) coordinate. Standard
abstentions52/600, cot18, repe41; differences from legacy include genuine old
fallbacks and recovered format differences. Initial audit counted direct routes
for empty advice among cleaned-chain successes; v2 now reports nonempty-guided
counts separately and excludes abstentions from raw crossing violations.
Historical audit retained, v2 is the authoritative interpretation.

## Phase5: strategic labels and bounded local planning

Ordered obstacle ID/side lists compile to integer endpoint gates, removing the
need for a model to calculate endpoint offsets. Oracle extractor is offline and
labelled unavailable information; imperfect controls flip/drop strategic labels.
Local refinement runs small bounded A* links only when checked geometric
shortcuts fail. All local expansion and heap costs are recorded as preprocessing
search work, not hidden. Three imperfect alternatives exercise a strategy
portfolio; complete global fallback and independent certificate remain. Current
large development pilot compares these with the same no-advice cut engine atw2.
