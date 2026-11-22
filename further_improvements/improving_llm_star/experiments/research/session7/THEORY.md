# LLM-RH*: calibrated spatial residual A*

## Research problem

LLM-A* treats uncertain route points as attraction targets. The frozen priority
is `g+h_goal+d_target`, becoming `g+2*h_goal` at the final target. A target advances
when generated as a neighbor, before collision/CLOSED checks. It can disappear
before a delayed trust controller reacts. These mechanics and the original
implementation are preserved; the new method has a separately named interface.

Our question is whether a general-purpose model can instead supply persistent
spatial information about remaining costs, and whether that information helps
beyond inexpensive geometric guidance and uniform heuristic inflation.

## Model output and calibration

Divide the interior integer map into a fixed4x4grid. Each region has a free
representative selected using geometry only. The model sees the original map,
representative coordinates, exact region identifiers and a geometric lower bound
at each representative. It predicts additional remaining cost `delta_r>=0` and
reported confidence `c_r in[0,1]`. Images show walls/start/goal/region IDs only,
never a solved route or offline reference costs. A text and few-shot variant are
separate experimental conditions. Confidence is not assumed probabilistically
calibrated.

For development samples with exact remaining costs computed offline, set
`x_r=c_r*delta_r/D`, `y_r=(C*_r-h_geo(r))/D`, where `D` is map diagonal.
The single global trust coefficient minimizes squared residual error:

\[
 a=\operatorname{clip}_{[0,1]}
       \frac{\sum_r x_r y_r}{\sum_r x_r^2}.
\]

Evaluation-map samples are excluded from any leave-one-map-out development fit.
The selected final image coefficient is0.22640953779865894, learned on development
only; no language-model weights are trained. This is a scalar supervised
calibration step, not a claim of a completely training-free overall system.

## Safe priority and effective alpha

Let `h(n)` be the admissible geometric cut lower bound, with octile fallback for
unsupported geometry. For region `r(n)`, the priority is

\[
 H(n)=h(n)+\min\{(w-1)h(n),\; a c_{r(n)}\delta_{r(n)}\},\qquad
 F(n)=g(n)+H(n).
\]

Equivalently, for positive predicted residual,

\[
 \alpha_{\mathrm{eff}}(n)=
 \min\left\{a c_{r(n)},\frac{(w-1)h(n)}{\delta_{r(n)}}\right\}.
\]

The influence changes with spatial region and the remaining geometric distance;
it does not wait for30stagnant expansions or transient waypoint switches. At the
goal the extra term is zero. Primary `w=1.05` and secondary `w=2` were frozen before
test generation. They are different quality profiles, not a silent modification
of original LLM-A*'s final-goal weight. Uniform1.05and2controls are essential:
model-free `a=0` is A*, so comparing only with that weaker/optimal control would
not establish a benefit beyond ordinary inflation.

## Guarantee

Predicted residuals are neither admissible nor consistent. The independent
pointwise envelope gives `h(n)<=H(n)<=w*h(n)<=w*C*(n)`. All ordinary grid edges
remain. Better-cost paths reopen states; outdated heap labels are skipped.
Immutable parent labels preserve the actual path when an ancestor improves.
Before termination, the frontier on an optimal path has correct `g*` and a key
at most `g*+w*h* <= w*C*`. The popped goal has no larger key and `H(goal)=0`.
Thus returned cost is at most `w*C*`, up to documented floating tolerances.
For `w=1` this reduces to optimal A*. The argument assumes finite original grid,
nonnegative actual edge costs, admissible anchor, retained transitions and
correct reopenings. A benchmark time cap can prevent completion; it is not part
of the uncapped completeness guarantee.

Optional macro transitions are accepted only as actual collision-checked lattice
walks with their real cost. They cannot reduce the underlying optimum, so the
same guarantee applies. Disabled/corrupt model advice yields neutral residuals,
never invented free-space transitions. No API call occurs per node.

## Pseudocode

```text
SPATIAL-RESIDUAL-ASTAR(query, cached_or_online_provider, a, w):
    construct original grid and admissible geometric lower bound
    construct geometry-only regional representatives
    request or replay one compact regional residual response
    validate values; missing or invalid regions receive neutral advice
    OPEN <- start with priority g+bounded_residual_heuristic(start)
    best <- immutable start label; CLOSED <- cost table
    while OPEN is not empty:
        pop label of minimum F
        skip stale label or already-closed label with no better g
        close/reopen current label
        if goal: reconstruct and validate actual grid path; return
        for each legal ordinary successor (and optional verified macro):
            if accumulated true path cost improves best g:
                create immutable parent label
                H <- h + min((w-1)h, a*confidence*predicted_residual)
                push with g+H
    return no path
```

The selected method has static predictions: no guidance-induced OPEN rebuild is
needed. The experimental single-feedback variant clears cached advice and
rebuilds only live labels once if a replacement is applied. Counts distinguish
logical rebuilds, heap operations, expanded states, improved reopenings and stale
pops. Raw heap pops are not interchangeable with distinct node expansions.

## Other investigated integrations

A full-key envelope clips within `[g+h,w(g+h)]`; an exact-eligibility focal set
uses `g+h<=w*min_OPEN(g+h)` and rechecks eligibility if the threshold decreases.
A two-queue version checks the proposed guided state's anchor eligibility,
otherwise expands the anchor minimum. These are adaptations of established
bounded-search ideas, not claimed new focal/MHA* algorithms.

Verified Residual Calibration computes sample intervals `[L_r,U_r]` using an
admissible bound and collision-checked direct/single-endpoint routes. It clips
`a*c_r*delta_r` to `U_r-L_r` when a finite upper witness exists. This is meaningful
geometric trust evidence, but it does NOT make a coarse interpolated whole-region
heuristic admissible. Extra preprocessing and matched geometry-only midpoint/
upper-gap controls must be counted. Validation did not justify selecting it.

Landmark cost differences connect to classical triangle-inequality heuristics.
For exact `C*(landmark)` and a VERIFIED route of cost `D(n,landmark)`,
`C*(landmark)-D <= C*(n)` follows from the triangle inequality. Subtracting an
unverified octile distance does not establish that lower bound. Real LLM costs
are approximate, so they still require the independent envelope. Oracle tests
showed only modest useful headroom and substantial visibility overhead; no paid
landmark experiment was justified.

## Related primary literature

- [LLM-A*, Meng et al.](https://arxiv.org/abs/2407.02511): model route proposals
  guide incremental heuristic search. We replace transient attraction with a
  persistent predicted cost field and explicitly separate numerical advice from
  the bound protecting search.
- [TransPath, Kirilenko et al., AAAI2023](https://arxiv.org/abs/2212.11730):
  supervised correction factors and path-probability predictions are established
  learned-heuristic representations. Our model is a general-purpose API model;
  prompting/scalar calibration differ from training a pathfinding transformer.
- [Aine et al., Multi-Heuristic A*, IJRR2016](https://cse.sc.edu/~mgv/csce580sp17/gradPres/multiHeuristicAstar_AineJRR2016.pdf):
  anchor-guided combination of inadmissible heuristics is established. Our
  two-queue pilot uses an explicit eligibility check; it is not claimed as a new
  theorem or faithful reimplementation of every MHA* detail.
- [Greco and Baier,2021](https://prl-theworkshop.github.io/prl2021/papers/PRL2021_paper_33.pdf):
  direct learned-value focal ranking can be weaker than discrepancy ranking.
  Prediction MAE alone therefore cannot demonstrate improved search.
- [Goldberg and Harrelson, SODA2005](https://www.microsoft.com/en-us/research/wp-content/uploads/2005/01/soda05.pdf):
  landmark/triangle-inequality A* bounds are established. Our sparse approximate
  model-cost extension is an experimental adaptation with separate safeguards.

## A limitation of the pointwise guarantee

The sufficient condition `H<=w*h_geo` is stronger than necessary for bounded
search. If a maze has true remaining cost far above `w*h_geo`, even a perfect
model correction is clipped. The model can then do little beyond small uniform
inflation. This is a limitation of the integration, not proof that the model has
no information. A full-key envelope permits extra slack `(w-1)*(g+h)` instead of
`(w-1)*h`; a Focal set instead gates eligibility with an independent anchor while
using unrestricted secondary priorities. Both were tested separately. Their
actual queue overhead and real/no-model outcomes remain essential. A trusted
perfect-admissible oracle is a different, unavailable assumption, never a real
model guarantee or free preprocessing trick.

The late bounded-pathmax prototype expresses inheritance in F-space:
`F_child=min(g_child+w*h_child, max(F_raw_child,F_parent))` for a meaningful
raise>1e-12. This preserves pointwise bounds but may not preserve nondecreasingF
when the upper clip intervenes. Arithmetic association must match the disabled
control: an algebraically equivalent `g+(h+advice)` can alter floating plateau
ties compared with `(g+h)+advice`. Archivedv1apparent gains from this confound are
excluded; v2has exact off-control parity and no-phantom-update tests. Pathmax is
established search machinery, not an original invention claimed here.
