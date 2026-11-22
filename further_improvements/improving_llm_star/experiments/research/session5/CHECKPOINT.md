# Session 5 persistent checkpoint

Start2026-11-18 06:22:51UTC; target~120min, approximately08:22UTC if useful.
Branch research/waypoint-guidance; initialc196b34; main66baa31 unchanged.
No delegation requested; work remains local/no push or merge.
User-authorized API cap$3, credential path ~/.config/llm-astar/.env loaded ONLY
inside processes. Never display/file-copy credential contents. No Codex auth edits.
Model clarification resolved: EXACT gpt-4o-mini-2024-07-18, all new methods share
snapshot/temp/seed/token cap. User temporarily said o4-mini then corrected it.
NotebookTable1 cells5/7/44 name gpt-4o-mini alias; historical response strings lack
model metadata, so exact historical snapshot cannot be proved. No relabelling.
Authenticated GET confirms exact requested snapshot is available, o4-mini absent.
Model/pricing verified official docs Nov18:$0.15/M input,$0.075/M cached,$0.60/M
output. Reasoning, if reported, is included in completion tokens, never double-bill.

Budget: experiments/results/research_session5/api_ledger.sqlite3 authoritative.
Integer nanoUSD, atomic BEGIN IMMEDIATE reservations BEFORE requests, reserve
FULL128k context plus output cap. Failed/unknown requests retain reservation;
no implicit retry. All responses cached in SQLite before cost reconciliation,
then atomically exported. Pricing/latency/usage/prompts/metadata saved, no headers.
Networking in sandbox gives URLError; authorized escalated Python CLI succeeds.
Minimal paid connectivity probe running. Inspect budget with api_budget.py status.
Three budget/cache/failure tests pass. No actual paid research results yet.

Reviewed original paper Algorithm1/lines175-244, actual LLMAStar source/prompt,
root project findings, Session3/4 docs and common engine. Exact university rubric
not found; use stated objective, don't invent assignment requirements.
Original f=g+Euclidean(goal)+Euclidean(target); finalgoal implies2h_goal.
Premature global neighbor switch and rekeys are genuine paper/code properties.

Current hypothesis: lineage-consistent waypoint progress (per-node stage inherited
along actual parent paths) avoids global target changes caused by unrelated
branches and eliminates retarget rekeys. Compare original-shaped scoring, goal-
normalized trust, bounded funnel, and matched global switch engines. Different
from prior global popped-target tweak. Validate nearby links for immediate trust,
not delayed distance stagnation. No pure classical-only optimization focus.

Plan: budget client -> real prompt pilots (original/sparse coords/endpoint IDs/
ASCII) -> novel branch-local guidance + trust ablations -> targeted error feedback
vs generic self-verification -> freeze prompts/engine -> independent fresh maps,
original prompt/mechanism2x2 factorial plus no-guidance/random/shuffle controls.
At least one direct extension of original A* required. Cut engine is a secondary
integration control. New actual LLM data clearly separate from old caches/oracles.
Resume commands will be written in README as each experiment is completed.

## Execution/network limit checkpoint

At08:18UTC approximately115min wall elapsed.113 successful requests, estimated
known$0.02871540;8 failed/uncertain requests retain$0.15851520 worst-case holds.
Known+held$0.18723060 <=$3. Do not retry failed requests implicitly or release
holds without authoritative evidence. Generic ONLINE self-control had8 transport
failures (6URLError,1RemoteDisconnected,1TimeoutError); it is NOT a successful
model-control experiment. Successful preflight self-review remains usable on its
small matched initial subset. A new free model-list check hit the automatic
approval review deadline, not a safety rejection. No further API calls this run.

Live EGOR pilot:349.6→330.1pops,230.8→225.3unique versus exact original,
arithmetic cost ratio1.02520→1.02821. Small exploratory effort/quality tradeoff;
no held-out confirmation. Validation10maps initial prompts: candidate original
548.1unique/824.1pops vs original617.6/914.3; GMcost1.01856 vs1.01598. Branch and
seeding variants still do not beat matched unguided search. No Session5 fresh
REAL responses collected. Do not claim real-model generalization.

Next independent work: offline counterfactual EGOR replay/gate/restart ablations,
source/credential audit, fresh-map bounded correctness with EXPLICIT synthetic
controls only, report/plots/pseudocode, final local commit. Network remains off.
Exact model staysgpt-4o-mini-2024-07-18. No original/main/push/merge changes.

## Final closure checkpoint (08:35UTC, no further API requests)

Research wall window06:22:51→~08:35UTC;~132min includes substantial tool approval/
network interruption. Active work was not separately metered. Do not claim120min
measured productive CPU work. The live-research loop stopped at its~120min target;
subsequent work completed offline audits/reports and preserved results.

128 tests pass; compileall passes. Fresh OFFLINE audit20queries/10maps,80 bounded
paths,6312 independent Shapely edges; no real-model held-out claim. Original
unchanged. Milestoneb928a02 preserves research code/real outputs before audit.
Later robustness-only wrapper patch handles trivial/unreachable original failures;
no change to valid distinct-endpoint comparison behavior. API usage estimate and
holds unchanged:known0.0287154,held0.1585152,totalexposure0.1872306,remaining2.8127694.
No pending requests/processes.8 failed requests remain held; generic online
control is invalid as model efficacy data. No implicit paid retries are permitted.

Authoritative offline sources:
- results/research_session5/REPORT.md
- research/session5/README.md and EXPERIMENT_LOG.md
- api_export.json (portable budget/cache; SQLiteignored)
- repair_replay_controls_v2/results.json.gz (correct endpoint-preserving controls)
- analysis/statistics.json,TABLES.md,repair_tradeoffs.pdf
- heap_audit.json,fresh_offline_audit_v2/audit.json

Exact conclusion: no reliable new winner. EGOR development pops349.6→330.1 but
costGM1.02491→1.02789, CI includes no gain; no-guidance320.8pops is better. Heap
push+pop API calls actually rise974.8→1077.0. Branch-local labels and seeding are
negative variants. Candidate prompt trades slightly worse path for lower original
operations on validation. No fresh real-model test or successful online generic
self-control; these gaps must remain visible.

Resume only after consciously restoring network access with a FREE model listing,
keeping same ledger/holds/exact snapshot and freezing a NEW real-model holdout.
Never recollect successful responses just to reproduce. Never reset/delete the
export/ledger to regain budget. No main edits,pushes,merges or auth changes.
