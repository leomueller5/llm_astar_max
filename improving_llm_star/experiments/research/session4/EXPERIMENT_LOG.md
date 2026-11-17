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
