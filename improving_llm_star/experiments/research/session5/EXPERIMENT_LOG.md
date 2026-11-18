# Session5 experiment log

## Framing and model provenance

Start2026-11-18 06:22:51UTC. Original paper Algorithm1 explicitly uses global
neighbor-triggered target changes and full OPEN rekeys; scoreg+h_goal+d_target,
finaltargetgoal givesg+2h_goal. RePE in the paper performs intrinsic evaluation,
not environment feedback. A real geometry/search feedback loop is a relevant
integration extension, not an unrelated classical speed tweak.
No exact university rubric file was found. Use the user's stated academic
objective; do not invent grading criteria.

Historical Table1 notebook cells5/7/44 namegpt-4o-mini, caches lack model metadata.
User temporarily requestedo4-mini, then explicitly corrected to exact
`gpt-4o-mini-2024-07-18`. ALL new requests use that snapshot. Authenticated model
listing and minimal paid probe confirm it works. No o4 requests were made.
Official Nov18 rates:$0.15/M input,$0.075/M cached input,$0.60/M output.
`api_ledger.sqlite3` authoritative; full context-window cost reserved atomically
before each call, failures retain holds, no implicit retries. No credential values
are printed/cached/copied; only user-authorized .env loaded in process memory.

## Hypothesis1: lineage-consistent waypoint progress

Original global switching credits a target to every frontier branch even if only
an unrelated neighbor points at it. New immutable path labels inherit resolved
waypoint stages from their actual parents. Better-g reopenings and optional
same-g/higher-stage labels preserve path provenance; no mutable ancestor can
silently invalidate a reached-waypoint claim. Branch-only switches require no
OPEN rekey. Alternatives: original score, normalized trust preserving final2h,
bounded funnelH=2h-alpha*max(0,h-d_target), and path-length credit rather than
distance stagnation. Trust uses verified neighboring lattice links and detour
excess; unresolved guidance can be skipped under a configurable actual path-cost
budget. These are integrations/adaptations, not claims to invent labelled A*.

Six new tests cover reservation/cache/failure cap, real immutable ancestry,
bounded quality and dynamic rekey, final-goal weighting. Original baseline frozen.

## Pilot1: original/coords/endpoint/ASCII prompts

10 new development maps,10 families, sizes40/56. One query/map, same exact mini
snapshot,temp0,seed20261118,1024 completion cap, concurrent3 requests.40 successful
responses+$0.00000285 connectivity probe, total$0.00832170. No reasoning tokens
reported; framework records them as completion-token subset if present.

Matched replay on identical responses,14 methods×3 repeats=1680 searches. All
paths valid. Original prompt frozen original230.8 unique states, costGM1.0249;
matched corrected neighbor229.2/cost1.0157; unguided same-label engine208.5/
1.0163. Lineage341.6/1.0082, boundedlineage258.6/1.0166; full244.3/1.0123.
Branch consistency alone increases work despite improving some costs; retain as
negative structural experiment, not a winner.

Compact coordinates original249.7states,cost1.0319. Endpoint IDs original384.7/
1.0190; ASCII350.7/1.0219. Endpoint trust can reduce this to~208.8 but then matches
unguided208.5: apparent improvement over bad guidance is not a useful LLM benefit.
IDs remove coordinate-generation errors but model often lists irrelevant wall
ends (even walls beyond the goal) and fails route order. Original prompt has
truncated dense answers in some maze cases. Choosing good route topology remains
the main problem; merely changing response syntax does not solve it.

## Iteration2: external feedback and smaller strategic decisions

One targeted correction on17 contradicted original/endpoint proposals; total58
successful requests,$0.01418805. Feedback identifies an actual invalid point or
first invalid edge of a specified interpolation; explicitly NOT unreachable
claims and never supplies an optimal path. Self-review control on the exact same
contradicted initial subset receives no external failure fact; same extra cap.
Currently collecting/replaying. Next hypothesis: choose ONE verified reachable
endpoint from a small candidate list with cheap local facts, rather than invent
an entire route. Compare classical candidate ranking and random/shuffled controls.

## Iteration2 result / iteration3 direct original extension

Targeted feedback improves frozen original on the SAME contradicted pilot
subset: original prompt8 cases281.25→264.38 unique states,429.75→400.12pops,
arithmetic cost ratio1.0290→1.0223. Endpoint9 cases424.44→411.56states,
618.33→595.78pops,cost1.0214→1.0098. Generic self-review is worse (314.38 and
552.00states). This is a small exploratory positive feedback signal; not a
confirmed generalization result and not a latency improvement.

Verified single-candidate prompt: frozen original206.9states/317.7pops,
costGM1.0299 vs original-prompt230.8/349.6/1.0249. Quality worsens slightly;
not a strict improvement. Branch-specific prefix seeding makes it worse
(seed bounded275.7states,cost1.0524), so reject that candidate. Exact reachable
candidate IDs eliminate invalid target coordinates but do not ensure usefulness.

Two exploratory evaluation attempts aborted on their source-hash guard after
unrelated budget-code changes. Their directories contain source snapshots only,
no accepted results. Reran sequentially into candidate_search_v2 and
self_review_search_v2. Do not use incomplete directories. Final timings will be
serial; exploratory selection uses deterministic counts/quality, not those noisy
parallel attempts.

New direct extension: Evidence-Gated Online Repair (EGOR). Subclass the actual
frozen LLMAStar; keep heuristic/CLOSED/neighbor switching unchanged. If a factual
geometric contradiction exists AND search remains unresolved after16 expansions,
issue at most ONE correction containing the failed interpolation and observed
search state. Accept a correction only if its empirical evidence tuple improves:
(invalid coordinate count,failed shortest-link fraction,octile chain length).
This tuple is NOT a proof of reachability/usefulness; original classical search
still constructs actual paths. Rekey original OPEN only when the plan changes.
This isolates an LLM-integration contribution from search-engine fixes and relates
directly to the paper's RePE, which did not receive external environment feedback.
Live dynamic pilot running; original/candidate prompts retained for validation.

Session5 split seed ranges corrected BEFORE generating validation/fresh:
development5510000..5600000,validation6610000..6700000,fresh7710000..7800000.
No cross-split case-ID collisions. Exact geometry disjointness will be audited.

## Closure and execution limits

At08:20 the requested~120min wall window was nearly reached; active time was not
metered and an extended approval/transport interruption occurred. No more paid
requests after113 successful calls and8 uncertain transport failures. A free
connectivity check's automatic approval review timed out (not a safety denial).
Do not claim network health or a successful online-self control from that run.
Known estimated billed$0.02871540 plus retained worst-case$0.15851520=$0.18723060
accounted exposure; remaining$2.81276940. Actual failed-request billing unknown.
All113 successful responses explicitly match the approved exact model snapshot.

Milestoneb928a02 freezes candidate code and real response archive before fresh
OFFLINE correctness checks. SQLite remains local/ignored; committed portable
api_export.json restores the ledger on a fresh checkout so budget is not reset.
Credential-value scan passed227 tracked session files, including decompressed
archives; no keys persisted. No Codex auth configuration was changed.

Controlled replay of exact successful EGOR responses: original349.6pops,
EGOR-gated330.1,costGM1.02491→1.02789; no-guidance ORIGINAL engine320.8/cost1.01997.
Unconditional correction422.2/cost1.02167; evidence gate protects against one
harmful proposal here, not a guaranteed property. Restart with the same accepted
correction340.2/cost1.01959, charging the actual16-prefix expansions. Retaining
CLOSED saves operations but can preserve worse paths; matched controls expose
that tradeoff. Corrected shuffle/random controls preserve start/goal and target
count:332.2/365.4pops. Initial replay incorrectly shuffled boundary endpoints;
repair_replay_controls_v2 supersedes only those controls, not raw observations.

4000 map-bootstrap samples (development only): EGOR/original mean-pop ratio0.9442,
CI[0.7423,1.0728]; EGOR/no-guidance1.0290,[0.9307,1.4376]. No reliable victory,
no held-out confirmation. Mean initial API7.679s; extra correction API2.093s/query;
actual online loop2.131s; derived initial+loop9.810s excludes initial setup.
Latency gain is NOT claimed. Preflight self-review17 successful outputs can be
analyzed only separately; all8 online-self requests failed.

Fresh offline audit20 cases/10 maps,80 bounded random-target paths and6312
independent Shapely edges passed; geometry disjoint from Session5 dev/validation
and Session4 dev/fresh. This is correctness only, NOT fresh LLM performance.
First audit attempt completed checks but hit argparse-variable shadowing while
writing output; fixed audit-only variable and reran into fresh_offline_audit_v2.
No algorithm change based on fresh cases. No Session5 real-model holdout exists.
