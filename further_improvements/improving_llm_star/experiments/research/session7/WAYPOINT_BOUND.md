# A conditional weighted-search interpretation of original LLM-A*

This is a derived analytical relationship, not a claim to invent Weighted A*,
nor a claim that the original algorithm is optimal. It assumes the actual
Euclidean distances, nonnegative true grid-edge costs dominating Euclidean
movement, finite targets, exact global OPEN refreshes, and the frozen monotone
CLOSED behavior. Floating-point implementations require numerical tolerances.

For a fixed current target t and global alpha>=0, define

```text
H_t(n) = distance(n,goal) + alpha*distance(n,t)
H'_t(n) = H_t(n) - alpha*distance(goal,t)
```

Subtracting the same constant from every OPEN key does not change expansion
order. For project values0<=alpha<=1, triangle inequality gives
`(1-alpha)*distance(n,goal)<=H'_t(n)<=(1+alpha)*distance(n,goal)`.
Moreover `H'_t/(1+alpha)` is consistent, has value0at the goal, and is admissible:
it is a convex combination of two Euclidean distance functions minus a constant.
Thus a fixed target is recognizable as weighted heuristic search, even though
its unnormalized heuristic is neither goal-zero nor admissible.

For changing GLOBAL target/alpha with alpha<=A, let L=1+A>=1. At every queue pop,
`H_t(u)-H_t(v)<=L*cost(u,v)` for all legal transitions, independently of target
location and reachability. A state-cost induction handles changing targets:

1. Previously CLOSED states have `g(p)<=L*g*(p)`; initially this holds for start.
2. Before a new n is closed, choose the first not-yet-CLOSED q on an optimal
   start-to-n path. Its predecessor p was expanded, so OPEN has a fresh best-g
   label with `g(q)<=L*g*(q)`. Costs only improve, and q was never closed.
3. Current queue ordering gives `g(n)+H_t(n)<=g(q)+H_t(q)`. A stale popped key can
   only exceed its node's current key, while a fresh q entry remains available.
   Global rekeying is essential when target or alpha changes.
4. Consistency along q-to-n gives
   `H_t(q)-H_t(n)<=L*(g*(n)-g*(q))`. Combining yields `g(n)<=L*g*(n)`.
5. Duplicate pops of an already CLOSED state do not change that state's bound.
   At goal termination the same L bound applies. With the frozen parent behavior,
   the actual returned chain has the recorded cost.

Consequently constantalpha0.5has a conditional1.5bound, originalalpha1a2bound,
and changing global alpha up to1has the conservative global2bound from this
monotone-CLOSED argument. Lowering the FINAL alpha alone does not establish a
smaller bound by this induction. A separate argument with full reopenings may
yield stronger current-heuristic guarantees; that is not ruled out here. This interpretation
explains why complete queue updates matter and why lack of optimality does not
itself imply arbitrarily unbounded path cost in this specific distance setting.

This argument does NOT automatically apply to node-dependent alpha, arbitrary
regional model costs, stale heuristic keys after changes, different motion-cost
models, malformed inputs, or a benchmark interrupted by its time cap. Regional
predictions can be discontinuous. LLM-RH* therefore uses a different sufficient
pointwise envelope plus correct reopenings, with its separately proved1.05bound.
Ordinary A* optimality is still not guaranteed by positive waypoint weighting.

`waypoint_bound.py` executes the actual frozenalpha1and current legacyconstant
alpha0/.5engines with synthetic adversarial targets, against independent Shapely
Dijkstra. These are implementation falsification checks, never real-LLM results
or substitutes for the proof and its stated assumptions. Review assumptions when
reusing the argument for another implementation.
