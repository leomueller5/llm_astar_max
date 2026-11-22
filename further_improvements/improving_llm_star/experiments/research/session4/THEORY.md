# Session 4: correctness, scope and relation to known search

## Common graph semantics

The frozen repository searches an eight-neighbor integer lattice with unit axial
cost1 and diagonal cost sqrt(2), bounded by closed axis-aligned wall segments.
This project does not introduce a no-corner-cutting rule. At integer wall
coordinates a unit edge can meet a nondegenerate wall only at an integer endpoint.
Indexed occupancy therefore matches that geometry; degenerate barriers retain
the installed predicate behavior. Fractional geometry uses the legacy predicate.
Continuous straight-line paths are NOT silently substituted for lattice paths.
Every returned candidate is expanded to actual unit moves and collision checked.

## Monotone cut relaxation (MCR)

For one axis let c1,...,ck be integer cuts separating state s from goal t, ordered
in their traversal direction. At cut i retain the orthogonal coordinate y. Let
Fi contain free lattice vertices on that cut, including intersections with
perpendicular walls. Define

    Dk(y) = octile((ck,y),t), y in Fk
    Di(y) = min(z in F(i+1)) [octile((ci,y),(c(i+1),z)) + D(i+1)(z)]
    Hx(s) = min(y in F1) [octile(s,(c1,y)) + D1(y)]
    H(s) = max(Hx(s), Hy(s)).

When no separating cut exists, the axis bound is ordinary octile distance.
States lying on a cut use its masked table. Additional geometry between cuts is
ignored. We do NOT sum independent x/y or per-wall bounds.

Proof sketch: every real integer path has a first visit to each separating cut;
these visits occur in the stated order, even if the path later backtracks. Each
subpath costs at least octile distance between its endpoints. Its crossing
vertices belong to Fi. Minimizing these sums relaxes the real path; taking a
maximum of admissible bounds remains admissible. Advice may select a subset of
real cuts but cannot invent free vertices or provide numeric lower bounds.
Dropping cuts weakens the relaxation; it cannot make it overestimate.

The octile kernel is piecewise linear in orthogonal displacement. Four sliding
minimum/prefix/suffix expressions compute each min-plus transform in O(H), where
H is the orthogonal map height. Preprocessing costs O(kH), plus occupancy masks
(current implementation scans wall lists for masks). Lazy per-column transforms
and Python list allocation are timed and reported; they are not free cache hits.
Two axes have separate costs O(kx*height + ky*width), with potential further
O(width*height) cached values if every column/row is eventually queried.

## Advice is primal, not a certificate

A coordinate chain, bypass proposal, relaxed gate route or roadmap path supplies
only an upper bound U after actual lattice-edge validation. Preference masks in
primal gate generation NEVER enter admissible anchor tables. An impossible
bypass may fail or waste a bounded proposal budget; it cannot certify a false
route. Verified prefix seeds have real accumulated g costs; the start remains
in OPEN and improved ordinary grid paths replace macro parents.

Let w>=1 be the requested quality factor. If U<=w*H(start), U<=w*C*. Otherwise
complete Weighted A* orders OPEN by g+wH, skips stale snapshots, and reopens on
improved g. If the cheapest live key is F and U<=F, then U<=w*C*: an optimal-path
frontier exists with key <= g*+w*h* <= w*C*. Goal-pop has the same bound. Pruning
only g+H>=U cannot remove a cheaper-than-incumbent solution. We do not require
heuristic consistency because improved CLOSED states can reopen. Floating-point
comparisons use small tolerances; tests use corresponding numerical tolerances.
This is a bounded-suboptimal guarantee, NOT an optimality claim when w>1.
At w=1 the complete bounded variants are optimal subject to those tolerances.

CutStrategySearch keeps the anchor heuristic fixed during interventions. New
advice changes only candidate upper bounds and verified g seeds; existing heap
keys therefore do not require rebuilds. This avoids the adaptive-alpha stale-key
problem while retaining event-driven advice. Static cached providers cannot
pretend to produce a second distinct reply. Simulated provider delays are ledger
entries, never sleeps or measured API latency.

PrimalFirstSearch first tries cheap certificates and deferred cut construction.
Its weighted fallback is complete. Selecting a shorter verified incumbent than
the fallback result preserves the fallback quality bound. LazyRoadmap alone is
NOT complete on the full grid and provides no global approximation guarantee;
it is always a bounded-work candidate generator inside these complete wrappers.
Its valid edges are shortest lattice links, not unchecked Euclidean shortcuts.
The local ordered-route diagnostic from Phase1 has validity only; it is excluded
from bounded-winner claims.

## Hierarchical bound and deferred corridors

Tile components represent exact local connectivity. Portal free-run sets relax
movement by their minimum octile distances; moving within a portal may be free.
Thus portal-graph distances are optimistic. Singleton portals tighten this bound
but still ignore internal obstacles between boundary points. Their preprocessing
and query Dijkstra costs belong to the algorithm. A soft region corridor retains
outside successors in a deferred frontier, and activates them if proposals fail,
exceed effort budget or cannot meet the independent anchor certificate. All
advice has a global fallback; no path is accepted solely because it lies in a
recommended region. Coarse portal teleportation explains weak observed bounds.

## Relation to prior work and limits of contribution

Hierarchical decomposition, roadmap search, anchor heuristics and bounded search
are established ideas, not new inventions here. Relevant primary sources:

- Botea et al., Near Optimal Hierarchical Path-Finding (2004):
  https://webdocs.cs.ualberta.ca/~mmueller/ps/2004/hpastar.pdf
- Aine et al., Multi-Heuristic A* (RSS2014):
  https://ai.dmi.unibas.ch/research/reading_group/aine-et-al-rss2014.pdf
- Thayer and Ruml, Bounded Suboptimal Search: A Direct Approach Using
  Inadmissible Estimates (IJCAI2011): https://ijcai.org/proceedings/2011/119
- Meng et al., LLM-A*, arXiv2407.02511:
  https://arxiv.org/pdf/2407.02511

This project investigates a concrete cut relaxation for the repository's wall
model, a verifiable strategy interface, and controlled comparisons isolating
advice quality, classical geometry and real runtime. It does not assert that
these combinations constitute a novel research-paper contribution. Purely
synthetic/oracle strategic responses demonstrate potential, never real-model
performance. New prompts are untested until separately authorized real calls
are made. Public caches alone cannot establish unseen-map LLM generalization.
