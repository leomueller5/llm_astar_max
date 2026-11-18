# Session 6 experiment log

## 10:43–11:07 UTC — synchronization, infrastructure, first prototypes

Merged team maps and analyses with both conflicting notebooks retained. Local
main untouched. Authenticated Git owner verified; author-email verification
failed, so publication is blocked under the explicit user condition.

Free models request and 8-token reserved probe succeeded. Exact GPT-4o-mini
snapshot confirmed. Historical unknown-cost reservations retained. New bounded
retry/circuit implementation tested; no old budget export overwritten.

New map split fixed at 60/20/20 maps. Initial development uses first eight maps
under a hash permutation, first two existing tasks each. No performance-based
selection. All 16 tasks solvable by optimal A*.

### Iteration 1 — discrete route ranking, geometric repair, policy selection

Hypothesis: geometry-supported choices reduce coordinate errors. Geometry builds
a small conflict-branching portfolio plus x/y cut-relaxation proposals. LLM ranks
one, repairs its endpoint sequence, or selects guide/goal policy. Original prompt
comparison uses exactly the same model. No reference path reaches the prompt.

64 development responses collected (16×4), then original prompt repeated with
its proper original 1,000-token allowance. Initial 384-token original pilot was
truncated in 11/16 cases and is EXCLUDED from baseline comparisons. Its files
remain as prompt-feasibility evidence. Even at original 1,000 cap, 3/16 responses
finish by length; this is retained as a baseline limitation, not cherry-picked.

Geometry fully verified routes: 11/16. LLM rank: 2/16. LLM repair: 1/16. Original
coordinate output: 0/16. Policy outputs contain object-valued targets in 14/16,
contrary to the requested ID-list format; decoder safely abstains rather than
using unchecked coordinates. Ranking often chooses the shorter but blocked R0
while a verified detour exists. Confidence mostly copies example value 0.8.
These are pilot observations, not evidence that all strategic prompting fails.

### Iteration 2 — verified macro neighbors

New direct subclass retains frozen original g+h_goal+d_target score, switching,
CLOSED and duplicates, adding only verified longer neighbors and dense extraction.
Matched robust implementation always retains unit edges, reopens cheaper labels,
and has an admissible Weighted-A* anchor; weight-w guarantee follows because
macro edges correspond to actual original-grid paths. New tests verify 36 random
weighted runs, dense original-subclass output, unreachable/trivial cases, caps.
134 existing+infrastructure tests passed, then 9 Session-6 tests passed after
macro additions. Full suite will be rerun.

First unbounded benchmark stopped after ~2 min because one large-map response
was taking disproportionately long across repeated frozen-original trials. No
summary was produced and no partial timing result is claimed. Rerun applies the
same 3-second per-trial limit to every method and saves checkpoints. Expanded
counts on timeouts are unknown, never interpreted as zero search effort.

Native trials exclude heap instrumentation, use fresh geometry, randomized method
order, warmups and repeated medians. Geometric portfolio generation is INCLUDED
for hybrid route/rank replay and geometry controls. API latency is reported apart.

The first pilot predates source-snapshot support. It uses macro v1 with uncached
Euclidean h. Later prototype adds optional cut anchors and h-cache; final runs
will snapshot all sources and freeze configurations before held-out evaluation.
