# CURRENT STATUS — Session 7 complete, 21 November 2026

Research, implementation, offline/real-model experiments and final verification
are COMPLETE. No further paid calls or algorithm tuning are required for this
session. Earlier sections below are retained chronological checkpoints, not
pending instructions.

- Frozen new candidate: LLM-RH*, persistent regional cost residuals, explicit
  1.05 quality envelope. No reliable additional LLM advantage over strong controls.
- Keep frozen Session6 LLM-A-VM* as the practical submission fallback; disclose
  the geometry-only, abstaining and spatially shuffled controls.
- 100 fresh tasks/60geometries, 209tests passed, 4217stored paths and1105593edges
  independently checked. Source integrity:52old/selected modules unchanged;
  2new late prototypes separately labelled. main still66baa31d2fc2b658b501dcd4b34e09d31af66cb4.
- Correct final tables:results/research_session7/final_analysis_corrected.
  Classical A* raw paths are goal-to-start:69completed paths normalized,31caps.
  Historical raw files and initial summaries remain preserved, not authoritative.
- Correct pathmax:ONLYpathmax_v2_*;v1hadfloating-tie confounding and is excluded.
- VM robustness results:vm_controls/analysis.json. Real targets do not robustly
  beat abstention or count/overlap-preserving shuffled targets. No new API calls.
- Budget:1.47216705USDsuccessful estimated+.1977456held=1.66991265exposure<3.
  Zero open requests;905successful Session7responses,exactsnapshot,reasoning0.
- Reports:REPORT.md,15-pageREPORT.pdf,TEAM_BRIEF.md; exact commands inREADME.md.
  THEORY.md/WAYPOINT_BOUND.md include equations, assumptions and pseudocode.
- Final team README-only updatedd6a2d9safelymergedascb111ef. No main/dev push.
- Publication WITHHELD:existing commit email lacks verified association with
  authenticatedleomueller5,confirmed again21Nov. No identity/auth settings changed.
  Manual command:git push -u origin research/waypoint-guidance.
- Verified active research before final packaging is~200minutes over three dated
  intervals inEXECUTION_TIME.json; both overnight gaps excluded.

Final code/data/report checkpoint: 84f66bc5d118b418dc2cf5e3bd86d5fbf6f70834.
The final documentation/verification commit follows this checkpoint. Inspect
Git log for HEAD; no historical metadata is rewritten and no push is attempted.

---

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

## Continuation20November~10:47UTC

The overnight gap is NOT active work. Approx41min in first episode, second
active episode resumed09:16:49UTC. Main native timing process14699 running,
~87/100queriesdone. Do NOT run other heavy diagnostics/API collections until
it finishes. All final collections complete:base200records,cost200,ICL100,
bounds20. Ledgercharged1.4581956+held.1977456=exposure1.6559412,remaining1.3440588,
zeroopenrequests. No paid requests since collections completed.

After final_native/completion.json exists, run sequential OFFLINE pipeline:
`.venv/bin/python improving_llm_star/experiments/research/session7/finish_offline.py`
It reuses only completed outputs, creates auxiliary matched controls, goal-only
original/robust counts, paper denominators, bounds prompt factorial, independent
paths/references, late dev/validation pilots, analyses, CPU/memory/profile audits,
figures and full tests. No network/paid calls. Partial output dirs are preserved;
if a step fails, diagnose and use a new output directory rather than overwrite.
Do not run multiple timing blocks simultaneously.

New isolated late hypotheses: discrepancy_guidance.py converts model estimates
to local successor policy then bounded Focal discrepancy ranking; pathmax_guidance.py
regularizes descending heuristic cliffs via established pathmax, with independent
w*h upper clip (not globally consistent). No frozen source edited. Their pilots
use only existing20dev/30validation advice, no paid calls and no final-data tuning.
If weak, keep negative results. New correctness tests reference Shapely-only
Dijkstra, not the production successor engine. Await full suite after timings.

Aux control addenda declared before final-result inspection:matched_uniform2,
rh_macro_zero105, rh_macro_uniform105;original_goal_only/robust_goal_only replace
onlyreplyby[start,goal], same scoring. Explicit VM provider enum compatibility
control retained beside literal vm_strict2. All primary/prompt/model coefficients
still frozen. Final performance has NOT yet been inspected or used for changes.

Optional true online latency audit AFTER native phases:
`.venv/bin/python improving_llm_star/experiments/research/session7/live_latency.py --output improving_llm_star/experiments/results/research_session7/live_latency --limit 6`
Uses fixed-hash reserved third queries, actual original model.ask and actual
regional provider, warm imports/fonts but fresh query prep; caches/reserves every
request. Approximately12actual calls, still bound by same cumulative3USDledger.
Run separately from native/resource timings to avoid interference.

Finish results interpretation, root documentation, README exactcommands, TEAM_BRIEF,
fullREPORT and session7/report_pdf.py export. Newreport is currently full static
methods/negative-findings narrative with final-results placeholder. New helper
report_pdf supports embedded figures and correctSession7header. Verify figures,
PDF, frozen sources, fulltests, actual-key/genericsecret scan includinggzip,
artifactreview, gitdiff/metadata/mainunchanged/teamarchive checks. Commit under
existingLeoidentity only; do NOT push while configuredemail/accountassociation
remainsunverified. Manual `git push -u origin research/waypoint-guidance`.

## FINAL PHASE20November~11:22UTC

Mainnative COMPLETE:17400records,100queries/60geometries,25methods+5shuffle
seeds. Newvariants all100valid;original74/100audits complete,26five-sectimeouts.
Primarymain80meanms:RH34.53,matcheduniform1.05 27.18,VMgeo1.05 23.63,
ICL30.76. QopsRH8161.9vsuniform7274.8. Largestress20RH191.42ms/Q43443.7
vsuniform124.68ms/Q34251.4. No generalLM-specificbenefit. Do NOT compareoriginal
completed-onlypopmeanswithall100successes;reportcensoringandpairedcoverage.

Paidliveaudit COMPLETE12actualcalls,6reservedqueries,actualoldmodel.askandnew
provider,randomizedwithinqueryorder. No more paid calls needed. Finalbudget
BUDGET_REPORT.json:charged1.47216705+held.1977456=exposure1.66991265<3,
remaining1.33008735,open0. Session7success905,charges1.20418425,input7442139,
output281031,cached1076736subset,reasoning0. Allsnapshotsexact.API_METHODS.json
complete. Originaloutputtruncates29/100at1000cap;do notretunepromptafterobserving.
8VMschemacompatresponsesreturnedunknownIDs,decoderrejects;44geometrygatescallfree.

SequentialofflinepipelineNOWRUNNINGsession61169. Fulltests206passed beforelate
pathmaxfix. Auxnative3controlsCOMPLETE;goal-onlycountsCOMPLETE;paperdenominator
COMPLETE;bounds_native~2/20around11:21. Then analysis/audits/prediction/tradeoffs/
guidance_lifetimes/resources/figures. Do NOT run concurrentheavywork/native
benchmarks. Light code/doc editing okay. Pipelinemayfail;preserveallartifacts.

IMPORTANTlatepathmaxv1confound:usingg+min(H)vsfrozenmin(g+H,...) changedfloating
plateauties. Someapparentgainswithzeroactualraiseswereinvalid. Archived
pathmax_source_v1.pyandoriginalpathmax_pilot_* results. DO NOTusev1findings.
Correctedv2storesFdirectly, exactfrozenoff-controlarithmetic, onlyraises>1e-12.
Addedunsaturated25case/no-phantom-update regression; finalfullsuiteexpected207.
Runningpipelinecompiledolder script and alreadyranv1,so AFTERitfinishesrun:
  pathmax_pilot.py --cases R/development.json.gz --responses R/cost_pilot/responses.json.gz --output R/pathmax_v2_development.json.gz
  pathmax_pilot.py --cases R/validation.json.gz --responses R/validation_cost/responses.json.gz --output R/pathmax_v2_validation.json.gz
  confidence_ablation.py samecase/responsepairs ->confidence_development.json.gz/validation
  .venv/bin/python -m pytest improving_llm_star/tests -q
Do notmodifyfrozenprimarysources/newmethodselection. Discrepancynegative:
valrealQ9039.8vsnoLM9562.3vsstronguniform2108.3. Policyhasweaksignalbuttooexpensive.
Newenvelope_ceiling_validation.json.gzcompleted:pointwisefineoracle1.05Q2781.7
vsuniform2108.3;full-keyfineoracle2Q1715.6;trustedexactoracleQ1526.8. Tightcap,
coarseresolutionandmodelqualityareallbottlenecks. Noadditionalpaidclaims.

NEWfinalizationhelperswrittenbutNOTRUN:finalize_report.pyrequirescorrectedv2files,
resource/prediction/analysis/guidanceauditcomplete;fillsREPORT.mdplaceholderwith
actualtables/CI/budget/limits/recommendation. figures.pypipelinecreates6plots;
case_visuals.pycreateshash-selectedtree/nestedpathillustrations(optional).
report_pdf.pynewcorrectSession7header+embeddedimages. Needpolishreportspacing,
TEAM_BRIEF.md,updaterootPROJEKT_ERKENNTNISSE,READMEexactreplay/analysis/audit/
PDFcommands. Nativeanalyzerhandlescensoredcoverage,clusterCI,phase-native medians.

Publicationread-onlyverificationnowdefinitive:GitcredentialANDGitHubappaccount
leomueller5correct. GET/user/emailsavailablebutconfiguredLeo/GmailhasNOmatching
VERIFIEDassociation. PUBLICATION_AUDIT.json recordsbooleans. DO NOTPUSH,do not
changeidentity/auth.Exactmanualcommandgitpush-uoriginresearch/waypoint-guidance.
Needfetchfinalreadonly+preserveanynewteamchangeifclear;mainmustremain66baa31.

Nextafterpipeline:correctedv2/confidence+207tests,integrity_audit.py(checkentire
historicalresearch+originaldependenciesagainstpre-testGit tree,selectedmanifest),
independentpathsummary,budgetunchanged,figures/PDFpreview,secretactualkeyscan
includinggzip+genericpatterns,gitdiff/artifact/authorchecks,localcommitsunder
existingLeoidentityonly,noAItrailers.No push. Needrecordactualactiveintervals:
verifiedepisode1 19Nov07:25:52–08:06:26UTC(40m34s);episode2 20Nov09:16:49–finalUTC.
Overnightexcluded.Target~180active min reachesaround11:36:15UTC. Productivework
mayfinishlater;reportactualdurationtruthfully. Neveridlejusttomatchduration.
