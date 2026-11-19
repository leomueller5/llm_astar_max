# Session 7 experiment log

## 1. Research question and initial review

Can a general-purpose LLM supply useful instance-specific regional cost or
search-priority information beyond a strong geometric anchor? This extends
LLM-A* by replacing transient waypoint attraction with persistent spatial advice.
Session6 demonstrates why comparison only against the frozen original is
insufficient. Preserve VM as fallback, include matched geometry/random controls.

Relevant primary work: TransPath(arxiv2212.11730) predicts correction factors and
path probabilities using supervised transformers; focal integration preserves
bounded quality. Multi-HeuristicA*(Aineetal2016) uses independent anchor and
inadmissible queues. Greco/Baier learned-focal work warns direct learned-value
ranking can perform poorly compared with discrepancy ranking. These are
established architectures, not inventions we can claim. Our research concerns
zero-shot/few-shot general-purpose model spatial advice and safe integration.

Budget reconciled with prior report exactly. Initial snapshot86c8c88. New maps
must be independently seeded: openedSession6 tests cannot be untouchedSession7
heldout. Development examples/oracle references NEVER enter evaluation prompts.

## 2. Oracle spatial information / compression (development20newmaps)

Full reverse-Dijkstra references computed offline and never passed to a model.
Cut+A*:774.15pops/643.6unique; cutWA1.5:839.5/359.05,GMcost1.00230.
Fine-oracle residual:342.3pops; fine path-membership potential:242.2pops.
Coarse4x4oracle residual worsens1320.15pops; coarse8x8:780.15;16x16:498.5.
Binary corridor mask8x8:631.3pops versus839.5 matchednone;16x16:400.65.
Inverse-distance smoothing worsens cost and overhead. Information resolution,
not only model quality, is an actual bottleneck. Retain easy maps in all means.

Three safe engines implemented separately from frozenSession6: bounded-key
priority envelope; exact-eligibility focal (accounts for threshold decreases);
two-queue anchor-eligibility gate. All best-g labels reopen; stale pops excluded
from expansion/feedback counts; every physical heap push/pop counted. Goal
priority/cost untouched. Static advice cached; one optional actual revision
clears cache and rebuilds ONLY live labels. No claim to invent Focal/MHA*.

## 3. Genuine paired representations

20developmentmaps x6representations=120successful actual responses,exactmodel.
Coordinates,structuredtext,exactfullASCII,512x512image,image+16candidate labels,
image+structuredmap. Image token usage around8500image tokens+text, measured
actual usage; unlike prior large figures it fits one512tile. Axes and region
labels independently visually checked: xright,yup,R0lowerleft. No path/cost
references in images. No train/test examples in this zero-shot pilot.

Envelopemask priorities:matchednone839.5pops. Real coordinate1576.0,
structured1559.0,ASCII1695.2,image1785.6,labeledimage1295.9,hybrid1662.5.
Pathcost GM worsens from1.00230 to about1.01–1.02. Canonicalpath regionrecall
only.37–.57;many missingstart/goal regions,overlap preferred/avoid. Canonical
reference is ONE optimum, so this metric is not an exhaustive validity label.

Explicit groundingv2 supplies exact start/goal region IDs, everyregion bounds
and free sample; start/goal removed fromavoid schema. Evaluated16maps disjoint
from4fixed ICLteacher maps. Stillworse:structured1256.1pops,ASCII1137.9,
hybrid1050.9 vs642.6none. Preservev1 andv2; do not retrospectively substitute.

## 4. Genuine remaining-cost prediction, scalar controls

20maps xtext/imagecost predictions,16regions. Raw MAEtext39.21,image38.85 versus
cutbound15.48:predictions numerically worse. Yet residual envelopes reducepops:
image650.75 vs774.15none, structured732.9. Image shuffle1150pops. This suggests
some spatial correlation but is not enough:classicalfixedWA1.05 gives565.35pops
and no observed excess cost. Query-mean residual and fixeddiagonal residual do
NOT reproduce all spatial gain (~777pops), but strongestweightedcontrol wins.

MSE-derived globalalpha (not search-outcome tuning),leave-one-MAP-out:
image644.55pops,structured663.8,bothobservedGMcost1.0. Full-development fitted
alphaimage.22640954,text.07056526 savedforvalidation; do not refit onvalidation.
Relative scaling andbilinear interpolation mixed; twoqueue usuallysame expansions
plusmoreheap work. Pointwise heuristic envelope testedseparately fromfull-key
cap; onthese cases no outcome difference. Retain both for explicit guarantees.

## 5. Different strategic hypotheses and negative controls

Persistent obstacle-side potential stays active until crossing that wall's plane,
not until transient target-switch. Its ORACLE is alreadyworse901.95pops vs839.5
none,geometry865.65. Reject BEFORE making any paid portal-policy requests.

Policy/direction oracle ceiling20maps:cut105forward565.35pops,reverse725.1;
bestdirectionoracle495.8. Broaderpolicyoracle377.9pops. Actual20maps xtext/image
controller nevertheless selects cut105/forward inALL40responses. Two tiny
semantic/schema checks correctly return explicitly requested lastenum/reverse,
so no schema/transport substitution bug is established. Constantcontroller
provides no query-specific benefit. Nativepilotpolicy timings exploratory only.

## 6. In-context learning and verified residual trust (ongoing)

4teacher maps fixed(open,rooms,treemaze,Utraps,firstseed);16otherdevelopmentmaps
for evaluation. Fixedtwoexamples,contrastivesuccess/failureexamples,feature-based
retrieval of2from4:allgenuinecached. Teachers derivedfromverifieddevelopment
search/optimalpaths only; explicitmapleakageguard. Numericcost ICL usesopen+
treemaze examples to distinguish additionaldetour fromtotalremainingcost.

VerifiedResidualField computes per-sample [L,U] using only admissibleCut and
collisionchecked direct/single-endpoint walks (atmost4trials),nooptimalsolver.
Clipconfidence-weightedmodeldelta toU-L whenfinite. This defines regionalalpha
fromactualgeometricevidence without waiting30expansions. It does NOT prove
coarsefieldadmissible; independent envelopeproves finalbound. Matchedmidpoint,
uppergap,zerocontrols useidentical geometricwork. Developmentimage model623pops
vs757midpoint,774zero, but stillworse thanWA1.05 and extraCPU~8ms. Scaledvariant
616.65 usesall-dev coefficient and is IN-SAMPLE exploratory; not confirmatory.
Thirtyindependentvalidationmaps nowcollectcostsusingfrozenzeroshotcostprompt.
