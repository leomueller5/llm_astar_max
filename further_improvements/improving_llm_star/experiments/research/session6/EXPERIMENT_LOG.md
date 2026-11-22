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

## 11:21 UTC — validation rejects an early generalization claim

Development macro-cut + geometry-gated multi-route LLM first proposal: 385.5
heap pops versus 732.7 for matched geometric targets; cost GM 1.01859 versus
1.02282. Whole-map bootstrap (8 maps) pop ratio 0.526, CI [0.284,0.999]. Random
endpoint advice 742.8, shuffled same LLM advice 535.6. Strong pilot signal, but
not stable evidence yet: only three maps trigger real API use in this pilot.

On independent validation (20 tasks /10 maps), LLM 968.2 versus geometry839.9
pops, both cost GM1.00530. Regret-based dynamic target ordering reduces harm
(860.8 versus843.5), but does not reverse it. Do NOT claim generalization.

Detected evaluation bug: macro_portfolio_geometry inherited LLM routes from
metadata despite replacing the primary point list. Those portfolio-only matched
comparisons are INVALID, explicitly superseded by later corrected runs. Main
macro_cut_geometry and random controls never use metadata routes and remain
unaffected. Geometry control now replaces all route metadata with geometric
proposals too. Regression test required.

Image experiment: on five unresolved development tasks, visual guidance873.8
pops versus text1360.4, cost GM1.01899 versus1.02053. Not superior to the cheaper
text multi-strategy pilot on these tasks; each image adds~25,500 input tokens
and rendering overhead. Rendering was NOT included by the generic pilot search
runner, so its raw search times are NOT full computational runtime. Image total
cost will be reported separately. No image-based CPU speedup claimed.

Next genuinely different direction: event-driven, geometry-informed strategic
correction of failed macro guidance, with unchanged anchor priorities and a
matched deterministic correction using the same visible candidates.

## Execution interruption and resume

Clock jumped from 2026-11-18 11:27:46 UTC to 2026-11-19 04:58:44 UTC
while the next orchestration call was being handled. This interval is NOT
claimed as active research. Work, cumulative ledger and the running collection
were preserved; it completed with no additional unresolved failures.

Sparse-roadmap completion pilot (16 tasks): LLM848.6 mean heap pops vs k4
geometry871.9, but 5.81ms vs5.45ms and cut-only5.28ms. Equal optimal cost in this
small sample for those three variants; no runtime gain. Full visibility improves
work785.4pops but costs5.79ms and slightly worse allowed path quality. Lazy full
roadmap completion costs20.22ms/3120.6pops: repeated abstract graph search is
expensive; not an LLM win. Classical controls preserve all roadmap processing.

Next iteration broadens development from8 to60 maps, using the fixed split and
reusing identical old API requests. New hypothesis: allocate verified macro probes
by positive anchor-priority gain multiplied by a local Beta availability estimate.
After a failed geometric link, reduce its trust within the local8×8 cell bucket;
reconsider in a new region. This never asserts unreachable, never changes OPEN
priority, retains all unit edges and the same bounded search guarantee.

## Broad development, 60 maps /120 queries

The original 8-map pilot was too small: after expanding the predeclared development
split, given-order LLM macro advice690.8 total heap pops versus732.2 for geometric
advice, and698.6 for all geometric endpoints under the same engine and easy-case
gate. Cost GM1.01545 vs1.01515 (geometry) /1.01603 (all endpoints). Offline compute
4.775ms vs4.875ms /5.001ms; native noise needs paired analysis and serial final
timing. This is a modest effect, NOT the earlier~47% pilot improvement.

Regret ordering reduces the gain. Priority-descent gating and local Beta trust
produce virtually no extra LLM benefit; they reject useful temporary increases
in the anchor score as well as misleading targets. Unit fallback preserves
correctness but does not prevent performance regressions. The originally
requested adaptive idea remains an informative negative result.

Only23/120 tasks require real model advice; five identical prior requests hit the
persistent cache. Geometry supplies identical advice across matched advisory
sources on all easy cases. New source-gate regression tests enforce this even
for multiple-route configurations. Synthetic challenging development adds20
independently seeded maps across10 families at new sizes; hold-out seeds fixed
in the generator before generation and not opened.

Reproduction model evidence: Table1_new.ipynb explicitly names the exact approved
snapshot. Archived older notebook uses the gpt-4o-mini alias; plain old response
caches lack provider metadata, so exact historical snapshots cannot be verified
from those strings alone. All new paid comparisons use exactly the approved
snapshot and cached provider metadata.

## Confirmatory evaluation in progress (06:07 UTC)

All220 original-prompt and220 hybrid records are cached.40 forced improved-prompt
records and40 original+bounds records support the predeclared factorial subset.
Original+bounds is an additional stronger-baseline control motivated by the
verified absence of range_x/range_y in the original generation prompt, not by
held-out performance. Main algorithm/prompt parameters remain frozen.

Native final benchmark is serial, with5timed repeats,1warmup and separate heap
audit per query/method. No simultaneous API experiments or second timing runs.
All query-local preprocessing is rebuilt. Cached providers reconstruct input
prompts and decode actual outputs; no model request occurs during replay.

Sampling sensitivity (10hash-selected hard development cases,3real outputs at
temperature0.3): first-route mean2101.2heap pops,consensus2113.4; within-case SD
143.6→112.7, but path cost GM1.01390→1.01622. Not a universal improvement;
primary tests retain temperature0.

A git diff check flagged one redundant blank line at EOF after milestone85723de.
Removed without changing the parsed Python AST; both byte hashes and the reason
are recorded in frozen_manifest.nonsemantic_changes. No algorithm adjustment.

## Frozen final evaluation — 19 November 2026

Hypothesis: geometry-constrained consensus targets, inserted as verified macro
edges into a fixed complete anchor search, can improve original LLM-A* and
provide additional real-model benefit beyond matched geometry.

Parameters frozen05:48:06UTC: weight2, cut anchor, shared preprocessing,
portfolio12, three advice probes every8expansions, total256probes, consensus.
Secondary quality profile1.05 was prespecified. New prompt/models never tuned
on final outcomes. Primary raw result: final_heldout/results.json.gz.

220tasks:200queries/20reservedteam maps +20fresh challenging maps/10families.
14methods, one warmup+5timings+oneinstrumented audit, fresh preprocessing,
randomized order, equal3second cap. All220/220valid, zero timeouts.
Team original:183.414ms,2050.9pops,1209.1unique,GMcost1.03604.
Hybrid:5.607ms,1007.4pops,393unique,GMcost1.01852.
Allendpoints:5.568ms,955.1pops,379.4unique,GMcost1.01881.
Cutonly:4.735ms,1166.5pops,GMcost1.01856.
Paired whole-map bootstrap real/allpops1.055[1.004,1.108]. Real/geometrybest
0.963[.850,1.028]; real/geoconsensus1.008[.986,1.030]. Additional LLM benefit
not established; strongest control wins. Classical engine+geometry explains
most original-baseline improvement. Quality-matched1.05 control confirms
no general extra model advantage. Detailed per-family/variance/OR/SR in analysis.

Forty-query factorial: direct original+improvedprompt worsens work in both
strata; consensus has mixed effects. Original+bounds prompt, WW team code,
no-macro, no-share, Euclidean-anchor, alpha with explicit finalgoal variants
all retained. Cutanchor is a major classical contribution, not model reasoning.

Independent audit:3080savedpaths/242757unit edges, all valid/cost-consistent.
Zero geometry overlap with development/validation. Fullsuite157passed.
14fixedmemory cases:meanVM1079KiB vs original628KiB; do not claim RAM reduction.
Separate live6case API-inclusive means:Original8.460s,hybrid2.288s(4calls),
geometry.0092s,all.0158s. API avoidance explains original-latency reduction;
no advantage over no-call geometry. cProfile confirms original CLOSED handling
as large bottleneck. Instrumented profile times are not native benchmark results.

Oracle controls distinguish limited target integration from complete-route
potential:optimal targets1098.0pops,verifiedoptimalincumbent85.1. Reference
computation recorded separately, no optimal reference was ever sent to model.

### Secondary gate-policy hypothesis and independent negative replication

The always-call factorial looked better on challenging maps but worse on team
maps. A stricter test must ungate the classical controls too. Hypothesis and
unchanged source/prompt frozen separately BEFORE generating20independent maps,
sizes92/124,seeds11210000+. Actual20newresponses. Same underlying engine,
geometryportfolio/anchor, no primary parameter changes. Native5repetitions,
warmup, separateheap audit;5bijective endpoint randomizations preserve votes.
Real1984.45pops/9.219ms/GM1.01449;geometryconsensus1949.4/9.033/1.00977;
all1951.5/9.448/1.02652;random1982.59/9.419/1.01655.
Real/allpop1.017[.986,1.059],real/random1.001[.937,1.028]. Negative replication,
retain as evidence against overinterpreting the first subset. No post-test tuning.

Final cumulative charges$.2679828 + held$.1783152, remaining$2.553702.
Session6:659successes,oneHTTP520hold$.0198, exact snapshot for every response,
825232input/195319outputtokens,0reportedreasoning. Old eight holds preserved.
No further paid calls planned. Export/accounting in BUDGET_REPORT.json.

### Closing checks and teammate synchronization

A final reporting audit found that floor-indexed p95 can lie below the median
for two-map families. Corrected to linear interpolation; added a regression test.
Raw experiments, means, medians, work and path results are unchanged, verified
programmatically. Previous analysis JSONs remain preserved; authoritative
corrected files are in *_analysis_corrected. Bootstrap endpoint interpolation
changes slightly, with no material conclusion change. CSV CRLF/EOF presentation
cleanups do not change data. The complete post-merge suite passes158tests.

Fetched newerdev1020fe0: team notebook/figure/result revisions, no new algorithm
source or maps. Archived all13 prior versions byte-exact with SHA256+gzip before
mergec3b2e44. Team measurements remain distinct from Session6 experiments.
Main untouched, original baseline unchanged, all frozen source hashes match.
A fresh offline replay of4fixed cases x5methods exactly reproduced costs,
operations, unique states and all heap counters (20matches, no API calls).

Final output:REPORT.md,TEAM_BRIEF.md,SESSION6_REPORT_FINAL.pdf (7pages),
figures_final/SESSION6_FIGURES.pdf, exact prompt/schema example, budget report,
independent path and archive audits. A PDF preview and paired-CI figure were
visually inspected. No secret findings in actual-key and generic-pattern scan,
including decompressed archived artifacts. Commit metadata checked; no AI author
or co-author trailers introduced. Github account login verified, configured
commit email unverified => publication withheld under user's explicit condition.
No identity/auth changes, no force operations, no push or main update.
