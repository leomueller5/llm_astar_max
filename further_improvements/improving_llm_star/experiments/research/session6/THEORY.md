# Verified macro guidance: method and guarantees

## Original limitation

The frozen class scores a node as

\[
 f_{\mathrm{original}}(n)=g(n)+\|n-g\|_2+\|n-t\|_2.
\]

When the target is the goal, this becomes `g+2*h_E`. An intermediate target is
advanced when it appears among a generated state's neighbors, before collision
and CLOSED checks. A global queue rekey follows. This is not a path-local claim
that the eventual returned path reached the target. In prior cached experiments,
the median target lifetime was one queue pop; a 30-expansion stagnation trigger
was usually incompatible with this behavior. Neither the intermediate heuristic
nor the frozen CLOSED handling supplies an A* optimality guarantee.

## Proposed integration: LLM-A*-VM

1. Build a bounded geometric route portfolio from free wall endpoints, x/y cut
   relaxation proposals, and a small conflict-repair tree.
2. If it already contains a fully checked route, use that geometric guidance and
   skip the model. This gate is a resource decision, not a proof of optimality.
3. Otherwise request up to three endpoint-ID strategies from the exact model.
4. Select points supported by a strict majority of the returned strategies, in
   first-occurrence order. One occurrence per strategy counts as one vote.
5. Run Weighted A* with an admissible geometric anchor. At sparse expansion
   events, test optional links to the goal and selected targets. Insert a link
   only after constructing a valid shortest lattice walk with its actual cost.

For routes `R_1,...,R_m`, the advisory support of target `t` is

\[
 v(t)=\sum_{j=1}^m \mathbf1[t\in R_j],\qquad
 T=\{t:v(t)>m/2\}.
\]

These strategies are generated in one response and are correlated. Their votes
are not calibrated probabilities or independent self-consistency samples.

The queue score is

\[
 f(n)=g(n)+w h_{\mathrm{cut}}(n),\qquad w\ge1.
\]

The model changes which optional edges are tested, not the anchor. The anchor is
the maximum of independent x/y separating-cut relaxations. At each cut, dynamic
programming permits only free crossing coordinates, while ignoring intervening
obstacles. Any real path must cross the separating cuts; the relaxation is
optimistic even when the actual path backtracks. Unsupported noninteger cut
geometry falls back to the admissible octile distance.

A macro from `a` to `b` is accepted only if its emitted unit grid edges are valid.
Its cost is the sum of those edges; for the constructed shortest lattice walk,

\[
 c(a,b)=\max(|\Delta x|,|\Delta y|)
       +(\sqrt2-1)\min(|\Delta x|,|\Delta y|).
\]

The default proposal budget is 256 tests, at events every eight true expansions,
with up to three advisory targets plus the goal. These values are experimental
defaults, not claimed optimal settings.

## Completeness and quality argument

Let `G` be the finite original unit grid and `G'` its augmentation with accepted
macros. All edges of `G` remain. Every added edge expands into a path of the same
cost in `G`, hence the optimal costs in `G` and `G'` are equal. The anchor remains
admissible for the augmented graph. Immutable parent labels retain the actual
verified prefix if another branch improves an ancestor.

Cheaper paths reopen closed states; stale labels do not count as expansions.
The usual Weighted-A* argument therefore gives

\[
 C_{\mathrm{returned}}\le w C^*.
\]

Before the selected goal, OPEN contains a frontier label on an optimal path with
correct accumulated cost. Its weighted key is at most `w*C*`; the selected goal
has no larger key. With `w=1` the solution is optimal. Implemented comparisons
use floating-point tolerances, checked numerically to `1e-7`. No consistency
claim beyond admissibility is required because cheaper labels reopen states.

An infinite separating-cut lower bound can certify unreachability without an API
call. No approximate LLM prediction is used for this certificate.

The direct frozen-class macro extension in `session6/direct.py` deliberately
retains the original heuristic and CLOSED rules. It does **not** inherit this
bound and is documented separately.

## Report pseudocode

```text
HYBRID-VERIFIED-ASTAR(query, provider, w):
    graph, anchor <- fresh verified grid geometry and admissible cut bound
    if endpoints invalid or anchor proves no path: return failure
    candidates <- bounded geometric route proposals
    if a complete candidate exists:
        targets <- its intermediate points
    else:
        strategies <- provider(query, candidates), or geometric fallback
        targets <- majority-supported free points
    OPEN <- {(start, 0 + w * anchor(start))}
    best[start] <- immutable label(start, 0)
    CLOSED <- empty cost table
    while OPEN nonempty:
        label <- pop minimum priority
        if stale or no better than closed cost: continue
        close/reopen label
        if label.node == goal: expand immutable macro pieces and return path
        if a proposal event and budget remains:
            for goal and a few advisory targets:
                if an actual shortest lattice walk is clear:
                    relax target with true walk cost and immutable parent
        for every ordinary legal unit neighbor:
            relax with true unit cost
    return failure
```

## Why adaptive trust was not selected

A tested alternative estimates local edge availability using

\[
 \alpha_{c,t}=\frac{1+S_{c,t}}{2+S_{c,t}+F_{c,t}},
 \quad U(n,t)=\alpha_{c,t}
 \max(0,w h(n)-c_{\mathrm{oct}}(n,t)-w h(t)).
\]

`c` is a local 8×8 position bucket; `S,F` count actual successful/failed geometric
probes. Trust affects probe allocation only, so OPEN requires no rebuilding.
A failed shortest interpolation is not treated as proof of unreachability.
Nevertheless, local availability did not reliably predict global usefulness,
and requiring positive priority descent also rejected useful temporary detours.
These mechanisms are preserved as negative experiments, not silently included
in the selected method.

## Complexity and attribution

The complete grid fallback has the ordinary heap-search costs plus a fixed
number of extra proposals. Accepted macros introduce only checked transitions;
failed tests consume their budget too. Cut tables and cached heuristic columns
add memory, and immutable labels can retain more objects than a state-count
metric suggests. Actual traced memory must accompany storage ratios.

Reusing the same query/goal cut tables for candidate generation and search saves
classical preprocessing. It does not constitute an LLM-specific gain. Likewise,
reduced Python CLOSED membership costs are search-engine fixes. The matched
geometry/all-endpoint controls isolate the additional contribution of model
information.

## Related primary sources

- [Meng et al., LLM-A*, arXiv:2407.02511](https://arxiv.org/abs/2407.02511): the
  original waypoint-attraction method. Our change replaces uncertain attraction
  with optional physically verified transitions and bounded fallback.
- [Uras, Koenig and Hernández, ICAPS 2013](https://ojs.aaai.org/index.php/ICAPS/article/view/13568):
  subgoal graphs use obstacle-corner abstractions for efficient grid planning.
  Macro/subgoal transitions themselves are established ideas.
- [Dellin and Srinivasa, LazySP](https://personalrobotics.cs.washington.edu/publications/dellin2016lazysp.pdf):
  choosing which unknown geometric edges to validate is an established planning
  problem. Our sparse-roadmap control is inspired by this framework, not a new
  invention of lazy evaluation.
- [Wang et al., self-consistency](https://arxiv.org/abs/2203.11171): combines
  independently sampled reasoning paths. Our same-response route support is a
  weaker correlated consensus heuristic and must not be equated with its claims.
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs):
  the exact approved snapshot supports strict schemas. Schema adherence constrains
  IDs and formats, not physical route correctness.
