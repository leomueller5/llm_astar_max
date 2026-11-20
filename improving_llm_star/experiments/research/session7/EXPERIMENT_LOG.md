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

## 7. Resume, validation, alternative architectures and freeze

Research resumed20November09:16:49UTC after interruption. Do NOT count the day
away as active work. All queued collections completed and old nine failureholds
remained unchanged. Incoming teammain53d5f39/dev21b09aa updates merged safely:
README+WW-local llama adapter, and deletion of three old reproduction artifacts.
All five prior files archived byte-exact underteam_before_53d5f39. Localmainnever
moved. The adapter is not used in exactGPT experiments; no newmaps were uploaded.

Independentvalidation30maps:rawimagecost1094.33pops versus1146noresidual;
development-fittedalphaimage1005.87,verifiedcalibrated1031.37. UniformCut1.05
remainsstrong953.03. Addingthe SAMEmodelresidual on topof1.05doesnothelp:
1020.27pops/calibratedimage,957.67text. Tightvariableinflation1..1.05 gives
917.73pops but748.1unique and2162.6push+pop versusfixed1.05's953.03pops,
587.1unique,2108.27operations. A pop-onlyclaim wouldhideworse expanded/queuework.
The tightprofile is better than OUR loose2profile (1005.87pops/821.77unique/
2385.6operations) and has a stronger bound; selected as primary NEWmethod,
not claimed bestoverall. Strongclassicalcontrols remainmandatory.

CostICL onexact16query evaluation subset:image659.88vszero-shot672pops,
text750.13vs774.69. Modestpilotdifferences, severalidenticalreplygroups
(6/16image,7/16text). No evidence that ICL solvesglobalspatialunderstanding.
Fixed/contrastive/retrievedmask examples allkept; no heldoutexamplesinprompts.

Landmarkremaining-cost alternatives beforepaidcalls:forced-via oracleworse
1792.55pops withoutvisibility,1147.75withvisibility versus774.15A*. A different
triangle-differenceextension (relatedtoALT,notanewinvention) gives711.25oracle
pops but18.43mspilot versus6.92A*, andpoorrobustness tonoisyestimates. No paid
landmark requests: modestoracleheadroomdoesnotjustifyit. Oracleadmissibility
fortruevaluesrequires VERIFIEDlocaldistanceupperbounds; subtractingunverified
geometricdistance doesnot preserve admissibility. Realmodelvaluesremainuntrusted.

VM integration: exactengineparity(pops,pushes,cost) againstfrozenVM percase,
weights2and1.05. Newcost-basedmacroallocation givesalmostnochange; validation
rank105real897.3vsgeometry897.57pops. Spatialfield+macros870.83tightpops,
694.73unique,1985.3queueoperations versusVM105899.87/531.07/1912.13.
Againfewerpopsbutmoretruework. Do notattributegeometricmacrobenefittomodel.

One evidence-triggeredrealcorrectionpilot: after128UNIQUEstates, inspectactual
legalfrontieredges; at leasttwo learnedtriangleviolations >2aboveanchor'sown
violation allowonecall. Only3/20eligible. Targetedfeedback3calls gives625.45
meanpops versus631.45initial; genericselfreview3calls givesEXACTLYsamepops.
Networkmeans8.65sand7.61s/call. Noadditionalfeedbackbenefitestablished.
Regionaloraclecorrectionworsens668.55;fineoracle605.85exceedscoarseoutput's
expressiveness. Initialclassicaldampingcontrol omittedglobalalpha; v1localrow
invalid,preservedwithsource. Correctedv2localcontrol654.9pops. Allothermethods
andrealpilotusecorrectedcode; no invalidrowusedforselection.

Canonicalgeometryaudit:6/20developmentgeometriesoccurredinprevioussessions,
so calltheseindependentlyseeded DEVELOPMENTinstances, not20newmapgeometries.
Thisdoesnotleakfinaltests. Validation30distinctgeometries,no prioroverlap.
Finaltestusespreviouslyunusedgenerator sizes97/131/163/197 and227/263:
80queries/40newgeometries plus20largerqueries/20newgeometries. Exhaustive
recognizablynamedprior-case/mapscan findsZEROoverlapwithpriororcurrenttraining
geometries. Equalgeometries, notcasecounts, arebootstrapunits.

Selectedconfiguration+sourcesfrozen BEFOREnewmapgeneration in
frozen_manifest.json:bound1.05,base1,alpha.22640953779865894,side4,imagecost
promptgroundedv2,exactmodel,temp0,seed20261119,completioncap1400,no macros.
Secondarybound2,rawalpha1,structuredtext,ICL,5shuffles,scalar/geometry/macro
ablationsprespecified. Neworiginal/VMresponsegeneration usesCOMMONSession7seed;
frozenSession6algorithm/promptunchanged. HistoricalSession6seed/resultsretained.
No further model/algorithm selection from heldout outcomes permitted.
