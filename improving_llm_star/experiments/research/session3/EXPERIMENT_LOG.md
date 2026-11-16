# Session 3 — Real waypoint contribution, 16 November 2026

Start 06:49:54 UTC; branch research/waypoint-guidance, clean at start. Main and
old code/results preserved. No paid calls/push/merge. All new methods use the same
SegmentGridGraph, fresh per query, plus a matched identical disabled-guide loop.

## Development audit

Existing lifetime audit: median1 pop, p90=15; 93.45% of switched targets live<30
pops; switching is on generated neighbor before collision/closed filtering, so
dense adjacent lists and already-explored neighborhoods consume guidance quickly.
298 zero-lifetime switches;1.15% blocked triggers. Prior delayed alpha cannot act
on most targets. Persisting a target is not by itself beneficial (prior pop-switch
study was negative); we do not repeat that unchanged experiment.

600 real standard development responses: geometry already certifies467 cases.
472/600 have an intermediate with <=10% forced optimal detour;99/133 residual
cases do. Benign-point existence is not sufficient evidence of computational
usefulness. Matched old robust g+h+d guidance uses fewer states in84/600, shorter
paths in90/600, both in34. Among geometry-residual cases:15/133 fewer states,
22 shorter paths, only3 improve both. These are observational labels; exact
forced-route costs are used only offline, never by any algorithm.

## Iteration 1: multiple genuinely different guidance mechanisms

1. Verified prefix seeding: collision-check routes from start to selected raw hints,
   seed OPEN with their actual g and compressed parent link; keep ordinary start.
   Complete LLM route need not exist. Raw, valid-point filter, ranked-detour filter,
   one versus three seeds, chain-prefix, and geometric-only candidate controls.
2. Fixed waypoint funnel H(n)=min(2h(n), d(n,t)+1.5*d(t,goal)), including visible-point
   selection. This survives short target lifetimes without blindly forcing visits.
3. Confidence initialized immediately from goal progress and geometric detour;
   H(n)=2h-alpha*max(0,h-d(n,t)), alpha in[0,1]. Continuous state bonus, no delayed
   stagnation rule, final near-goal region naturally reverts to2h.
4. Waypoint tie-breaking, with original primary g+2h score unchanged.

All new scores are <=2*admissible Euclidean goal distance and goal score0. With
reopening they have a global factor2 bound, not optimality. Seed shortcuts are
verified real grid walks and add no cheaper edges than the underlying graph;
start remains OPEN and improved paths replace macro parents correctly.

120 fixed development cases,7 interleaved repetitions: raw/ranked seeds~0.323ms
vs matched disabled0.330ms, but old lean witness0.311ms. Seeds save~2.5 distinct
states/case. Potential0.512ms, visible-potential0.435ms, immediate confidence0.534ms,
tie0.344ms: rejected as runtime candidates in this pilot. Some reduce costs but
increase work. Geometry-only seed0.344ms shows location quality may matter, but
small timing differences are not conclusive.

## Iteration 2: reduce avoidable shared engine overhead, full development

Use identical 3-tuple weighted queue for seeded/disabled variants; inline base
priority, reconstruct a single macro prefix plus normal tail rather than allocating
one list per parent edge. Cache target-to-goal distance and activation confidence
once. These are shared engineering fixes, not LLM effects; retain matched off
and prior witness baselines. Full600 development cases,9 repeats, all promising
seed/filter controls plus negative potential modes. No old held-out test cases.
Source snapshots are saved at start; do not edit algorithm while measuring.

Full-development result: matched off0.3426ms, existing witness0.3362ms, rank-seed
0.3394ms, geometric seeds0.3373ms. Rank-seeds reduce states58.7->57.0 but raise
mean cost34.1225->34.1491. Soft confidence gives slightly shorter paths but more
work; visible potential improves mean cost to34.0599 at0.4324ms. Quality-only
candidate, not runtime winner.

## Iteration 3: provably lazy ranking and conservative filtering

For independent shortest lattice prefixes the ranking estimate equals actual
seed priority. Stop after the first valid sorted link (or first k valid for k
seeds); eager/lazy must select identical seeds. Regression test confirms this.
Test a conservative prefix+goal octile bound <=1.1*admissible start wall bound;
and a separate continuous goal-visibility filter (feature only, not a path).
600 cases,11 repeats: lazy0.3346ms vs matched off0.3364ms and old witness0.3322ms.
Cut-filter0.3358ms, costs34.1282 vs off34.1225 (smaller regression than raw rank).
Geometry-only0.3307ms, fewer states55.26 vs LLM-rank57.00. Therefore no supported
LLM runtime win on development; retain exact comparisons rather than cherry-pick.

Freeze primary cut-seed, rank-seed secondary, visible-potential quality secondary.
Add strong nulls before evaluation: map-matched wrong-query responses, equally
sized random free-point lists, order shuffle (rank is intentionally invariant),
geometric-only potential, and uniform goal weight1.5 to detect mere goal-weight
weakening. Original final-goal scoring remains untouched. No Session3 use of old
held-out test split. Fresh procedural geometry is independently seeded and
anisotropically scaled; oracle fixtures are not real-model evidence.
