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

## 10. Final evaluation execution and baseline-provider compatibility

All fresh collections completed:100 original responses,100 VM records (some
geometry-gated without a call),200 zero-shot cost responses (image/text),100
fixed-ICL image responses,20 supplementary original-bounds responses. Exact
snapshot/temperature/seed preserved. No model or coefficient selection uses
these final outcomes. Native randomized25-method comparison started20November
~10:17UTC, five measured repetitions plus warmup and independent heap audit.

Frozen VM's candidate-ID enum exceeds the provider's supported schema size on
some newly large maps. Preserve literal provider-failure/fallback asvm_strict2;
add separately labelledvm_hybrid2 compatibility control: SAME full prompt,
search, candidates and decoder, removing ONLY unsupported enum restriction.
Never truncate candidates or silently substitute compatible responses into the
literal baseline. The diagnosed400 reservation remains held conservatively.
See BASELINE_COMPATIBILITY.md. This baseline adapter is an explicitly documented
protocol addendum, not a change to the frozen primary algorithm.

Additional diagnostics selected by fixed ID hashes, never performance: three
genuine seeds on ten validation maps; six reserved third-query live latency
cases; one case/family plus four extra Python-allocation profiles. API-inclusive
live latency is separate from offline replay. Image/prompt construction CPU,
tracemalloc and cProfile run separately after native timings to avoid measurement
interference. A switch event records the NEW target, while active_pops belongs
to the PREVIOUS intermediate target, including switches TO the final goal.

Latest full correctness suite198passed; random stress1120runs/240maps and8164
independent Shapely edge checks. Full saved-path verification and final source
hash audit still required after native completion. Cumulative API estimates at
10:20UTC:charged$1.4581956,held$.1977456,remainingauthorized$1.3440588.
Unknown-cost holds are never released merely to improve reported expenditure.

## 11. Separate new hypothesis while frozen comparison runs

Established discrepancy-search literature suggests that numerical heuristic
ranking and a learned local policy are different information uses. A new
ISOLATED prototype uses region cost predictions to identify locally preferred
legal successors, accumulating a unit discrepancy for other choices. Exact
Focal eligibility remains `g+h<=w*min_OPEN(g+h)`, with threshold-decrease checks,
stale handling/reopenings and all ordinary transitions retained. The model never
prunes edges. This does not modify any frozen source or test configuration.

Test first on existing development/validation responses against identical
no-model discrepancy engine, shuffled advice and strong fixed1.05. Multi-queue
overhead is fully counted. No paid request justified before a convincing
matched-control result. If rejected, retain code/results as a negative study;
do not tune it on the already generated final evaluation.

## 12. Publication identity verification

Read-only GitHub account/email API verification with existing credentials
succeeded. Authenticatedloginleomueller5matchesintendedremoteandconnectedGitHub
profile. ConfiguredcommitidentityLeo/leonard.mueller2005@gmail.com has no matching
VERIFIED email in the returned account email records. No credential values were
printed or saved; only verification booleans/account metadata are recorded.
Under the user's explicit condition, publication is WITHHELD, without changing
identity/authentication or attempting a push. Preserve local commits and provide
`git push -u origin research/waypoint-guidance` for manual publication.

## 13. Search-aware regularization and safety-envelope headroom

Separate bounded-pathmax prototype addresses descending discontinuities of coarse
regional fields. Accepted successor labels use
`H_child=min(w*h_child,max(H_raw_child,H_parent-edge_cost))`. All usual grid edges
remain, better g reopens, parent labels immutable. The upper clip preserves the
existing w argument but can prevent full heuristic consistency; no consistency
claim is made. Compare pathmax on/off with actual, shuffled, zero and uniform
advice on development/validation only. Off variant must exactly reproduce the
frozen engine's search work. If regularization merely approaches uniform WA*,
that is not evidence of additional LLM information.

A further explanatory oracle experiment compares the selected pointwise envelope,
full-key envelope and Focal eligibility at1.05and2on validation, using none,
actual frozen-calibrated, exact-at4x4samples and exact-every-node fields. A trusted
perfect-admissible oracle is explicitly unattainable for unchecked model outputs.
This tests whether a tight safety envelope discards otherwise useful strategic
information. Exact-reference generation is recorded, never billed as free model
knowledge or online runtime. No held-out tuning/new paid request follows from
this explanatory experiment without a separate new freeze and fresh dataset.

## 14. Floating-point confound caught in the late pathmax prototype

Full206tests passed after correcting an overly exact path-cost equality test
(~1e-14 roundoff); physical queue counts stayed exact on those fixtures. Broader
pilot diagnostics then showed pathmax-none changed work despite ZERO meaningful
reported raises. Cause: copying `g+min(H...)` instead of the frozen engine's
`min(g+upper,max(g+lower,g+base+advice))` changes floating plateau tie ordering.
Even a last-bit change can alter many expansions. This is a confound, not evidence
of useful regularization. Preserve pathmax_source_v1.py and original pilot files;
DO NOT use their apparent benefits as results. Newv2uses exactly the frozen key
arithmetic when disabled, and applies only raises>1e-12 to prevent phantom updates.
Added unsaturated-guidance parity/no-phantom-update regressions. Rerun v2ondev/val
in NEW result files after timing blocks. Frozen primary sources/results unchanged.

## 15. Stronger VM contribution control after unblinding

Primary RH is slower/more work than strong uniform control. Frozen VM2shows a
small aggregate main-set time difference versus all-endpoints geometry2while
queue work is slightly worse; large-set time is essentially equal. A shorter
model-selected macro list could explain this without useful spatial reasoning.
Add a transparent POST-UNBLINDING robustness block, no candidate/prompt tuning:
same frozen VM2with actual model, all endpoints, geometric consensus, abstaining
provider (same portfolio retained), and bijectively shuffled model route targets.
Bijection preserves route overlaps, consensus votes, unique target cardinality
and fixed start/goal; three seeds averaged within query. No new paid calls.
This is a stronger negative/causal check, not a newly pre-registered success.

## 16. Final results and correctness correction (20–21November)

Frozen final main100tasks/60geometries completed. All new variants return paths;
original26/100audits exceed5s. MainRH34.53ms/Q8161.9 versusuniform27.18ms/Q7274.8;
largeRH191.42ms/Q43443.7 versusuniform124.68ms/Q34251.4. Map intervals are wide:
primaryqueue ratio1.122[.881,1.684],large1.268[.898,3.488]. No reliable model gain.
Few-shot improves means but not matched classical superiority; all1600confidence
values become1and MAE worsens. This is not proof of improved spatial reasoning.

The classical original A* returns goal-to-start. The legacy adapter expected the
opposite and incorrectly marked completed paper paths invalid. Raw data retained;
newpaper_denominator_corrected normalizes69paths, all independently valid/optimal,
31timeouts unchanged. No algorithm/time/work/storage changes. OR/SR in
final_analysis_corrected uses completed denominators with explicit coverage.
Historical denominator validity summaries require review before reuse. Main
LLMA/VM/region comparisons are unaffected. Regression test added.

Correctedpathmaxv2validationQ2061.37 versusuniform2108.27,but shuffled2051.47,
anddevelopment1413.15 versusuniform1317.1: no general or LM-specific benefit.
DiscrepancyrealvalidationQ9039.77 versusno-model9562.33 butuniform2108.27,
so policy signal is overwhelmed by heap/expansion work. Confidence-placement
controls with equal mean residual show negligible/mixed effects. No promotion.

VM robustness block:100tasks,matchedweights/portfolios,three target-shuffle seeds.
Model/abstain pooledtime ratio.998[.983,1.010];model/shufflequeue.999[.993,1.003].
Primarysmall timegain versusall endpoints is absent versusabstention; it does
not establish useful model strategy. Nominalpost-hocQgain versusabstain~.4%,
not versusstrongergeometry/shuffle, withworse large-pathquality. Model targets
survive on43/100queries;44geometry-gated,13calledbutno-consensus-targetqueries.

Full209tests passed. Independently verified stored paths4217,edges1105593;
additional100Shapely-onlyreference maps/300bounded searches and retained240map
stress1120runs. All52historical/selected production dependencies match pre-test
hashes/tree;two new unselected prototypes labelled separately. Main unchanged.
A conditional weighted-search analysis of the original Euclidean formula is
recorded inWAYPOINT_BOUND.md,supportedby756synthetic checks on63reachablemaps;
this is not a novel theorem or real-LLM performance evidence.

Finalbudget:successfulestimated1.47216705USD+held.1977456=exposure1.66991265<3;
open0,Session7success905,input7442139,output281031,reasoning0. No paid calls on
21November. Source/experiment/PDF/secret/commit checks finish the release.
FinalfetchfoundonlyupstreamREADMEadditiondd6a2d9,safelymergedascb111efwithout
changingmain,productioncodeorresults. Verified commit-email association still
absent despite correctGitHubaccount;no push under the user's explicit condition.
