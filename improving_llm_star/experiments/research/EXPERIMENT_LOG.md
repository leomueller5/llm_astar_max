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
