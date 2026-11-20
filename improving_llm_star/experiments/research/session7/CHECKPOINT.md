# Session 7 persistent checkpoint

Started2026-11-19 07:25:52UTC; target~180productive minutes if available.
Branchresearch/waypoint-guidance, initial86c8c88, clean tree. Session6 and original
frozen implementations preserved. No subagents. No main edits or pushes.

Budget start:charged$.2679828,held$.1783152,remaining$2.553702.
Use Session7Client from common.py: SAME Session5SQLite ledger, restores portable
Session6 then7 exports, writes ONLY Session7 cumulative export. Exact snapshot,
strictschemas, per-attempt worst-context reservation, boundedbackoff/retries,
reasoning counted inside completion. Never printread/config contents or key.

Hypotheses: spatial residual-cost fields and route-probability fields may contain
information missed by coordinate waypoints. FIRST oracle control on development
maps; only pursue representations showing real headroom. Safe integration via
bounded heuristic envelope and/or anchor-protected focal/dual queues. Separately
measure regional prediction quality, actual search work, and processing costs.

Plan: review/sync/research; implement oracle/prediction primitives; evaluate
coarse regional residuals versus fine oracle; real text/image/ASCII comparisons;
few-shot+contrastive examples from development only; policy-controller oracle
ceiling; optional targeted feedback; freeze on validation; freshheldout;
independentverification+tests+report+plots+PDF+localcommits. No positiveclaim
unless matched no-LLM controls support it.

Publication identity unresolved fromSession6: authenticatedloginleomueller5,
configured emailnotverified. Do not changeidentity/auth to bypass. If unresolved,
no push; give user exact manual research-branch push command at end.

## First oracle finding
Coarse4x4 exact residual costs can HURT cut-anchor search:1320vs774pops.
Fine exact residual helps342pops, exact route membership242vs839. Increasing
resolution materially changes the information content:binarycorridor8x8oracle
631pops vs839matchedweighted1.5;16x16oracle401pops. Smoothing residuals adds
cost and remains weak. Therefore prioritize compact corridor-ID masks (8x8),
not an untested assumption that coarse scalar costs must help. Real paired
representations collecting20maps x6forms undercumulativeledger.

## Resume20November09:16:49UTC

Interruption was over a day; exclude it from productive time. Last verified
previous clock08:06:26 on19November (~40.6active minutes then, plus a few closing
operations). Resume for roughly140additional productive minutes if environment
allows. All nine ambiguous old failures remain held, no reserved request in flight.
Budget now$.71209395charged+$.1783152held, remaining$2.10959085.
Completedactualresponses:v1representations120,cost40,grounded48,ICLmask48,
costICL32,controller40,validationcost60,plus connectivity/sanity. Exactmodel.
Milestone9bdcd40 preserves code+initialfindings;rawresultsnotcommittedyet.
Fullsuite189passed before interruption. Do not reset ledger/export.

New production sources:spatial_guidance.py (bounded envelope, pointwise envelope,
focal,dual,staticandone-revision fields,optional verified macros),
spatial_calibration.py (verifiedsamplebounds+regionalalphaclip,bilinearfield).
NoSession6source changed. Portaloracle alreadynegative -> no paidportaltests.
Policycontrollerchoosesfixedcut105forwardall40;semanticcheckhonorsrequested
otherenumvalues,so no evidence of a schema/transport substitution bug.

Next:inspect validation and costICL; evaluate all-dev-frozen alpha/VRC profiles
against constant-weight controls; test one search-aware correction and contrastive
policy/example alternatives only if meaningful. Then freeze selectedcandidate,
newheldout maps,original+VM+strongmatchedclassical controls,independentpathaudit,
actualnative timings+predictionerrors+mapbootstrap+plots+PDF,finaltests/localcommits.
Publicationstillrequiresverifiedemail/account;otherwisegive manualpushcommand.

## Frozen finalphase20November~09:40UTC

Mainalgorithm/prompt/calibrationfrozen before heldoutmapgeneration.
PrimarySpatialResidualAStar,bound1.05,base1,alpha.22640953779865894,side4,
source=model,macrosFalse,groundedimagecostprompt. Secondarybound2. Simpler
calibratedcostfieldretainedoverextraVRCpreprocessing. Itdoesnotbeatstrongfixed
weight1.05invalidationqueueoperations,so no generalLLMadvantageclaim.
Allsourceshashedinfrozen_manifest.json. Neverchange/tunethoseaftertestopening.

Freshdataheldout_main80queries/40geometries,heldout_large20/20,all100queries.
Fortymorequeriesreservedonlyforlatencycalibration. Prior+train geometryaudit
findszerooverlap. Developmentactually6overlapswitholdgeometries (allowedonly
asdevelopment);validation30distinctfresh. Do notcallall20devgeometriesnew.

APIcollections running, eachbudget-reserved/cached:
heldout_baselines (original+geometrygatedfrozenVM), heldout_cost(image+text),
heldout_icl(image). Commonexactmodel,temp0,seed20261119 acrossnewrequests.
Sharedauthoritativeledger,ownSession7export. No costsreset. BaselineplainAPI
adapteriscollect_baselines.py; strictspatialclientcommon.py staysfrozen.

native_benchmark.py implementsfreshpreprocessing,warmup,5native repeats,
separateheap audit,5shuffle seedsaveragedwithinquery,5seconduniformcap,
fullpathsave,primarytraces,label-basedclosed/stalepopclassification. Incoming
cachedadvice isnotfirst-usepromptgeneration; independentlymeasureprompt/image
CPU andliveAPI-inclusivecalibration. Smoke usesexplicitSYNTHETICbaseline
fixturesin/tmp, neverasrealmodelbenchmark. No APIcallsinnativeharness.

Latest fulltests195passed beforefinalfreeze. Needfullpost-checktests,sourcehash
verification,independentallpathaudit,memory/CPUprofiling,statistics+CI+perfamily,
figures+PDF+README,exactreplaycommands,Gitsecret/metadata/artifactreview.
Latestteammergepreserved5priorversions;mainstill66baa31. Publicationemail
unverified=>doNOTpush;provide manualgitpushoriginresearch/waypoint-guidance.
