# Session5 — Real model guidance and evidence-gated online repair

Exact model for every successful request: **gpt-4o-mini-2024-07-18**. Temperature0,
seed20261118 (pilot),1024 completion cap; minimal connectivity probe cap8.
No model comparisons or silent fallback to o4 occurred. The original reproduction
notebook names the gpt-4o-mini alias; its old plain-text caches cannot prove the
historical snapshot. All new comparisons have exact returned-model metadata.

[Report](../../results/research_session5/REPORT.md), [log](EXPERIMENT_LOG.md),
[checkpoint](CHECKPOINT.md). Original baseline, main and historical results remain
unchanged. Milestoneb928a02 preserves implementation and real-response provenance.
No pushes/merges. Exact university assignment rubric was not found.

## Research contribution and limitation

`repair.repaired_class(Original)` adds one event-triggered, externally grounded
waypoint correction to the actual frozen LLMAStar class. It preserves its scoring,
neighbor-triggered target switching and CLOSED behavior. Contradicted guidance
that remains unresolved after16 expansions can request one correction containing
an actual invalid coordinate/edge and the observed search state. A lexicographic
geometric evidence gate decides whether to apply it; OPEN is rekeyed only if the
filtered plan changes. No arbitrary recurring LLM calls. Network failures or
rejected corrections continue classical search; original no-path extraction
failure is handled with a robust no-LLM weighted fallback.

This is an adaptation/integration study, not a claim to invent feedback planning.
Small development results are promising but inconclusive. The same original
engine without guidance is better. A fresh real-model holdout and successful
online self-review control are MISSING because of transport/approval limits.
Do not describe the fresh random-target correctness audit as an LLM evaluation.

The independent `PathConsistentSearch` preserves branch-specific target progress
in immutable real-cost parent labels. Original/normalized/bounded scoring, trust,
path-cost budgets and verified seed alternatives are retained as negative
experiments. The bounded score stays within[h_goal,2h_goal] with better-g
reopenings and preserves factor2; EGOR itself preserves the original algorithm's
lack of a proved optimality/bounded-suboptimality guarantee.

## Offline reproduction — no API calls

From workspace root, using existing `.venv`:

```sh
.venv/bin/python -m pytest -q improving_llm_star/tests
.venv/bin/python improving_llm_star/experiments/research/session5/api_budget.py status

.venv/bin/python improving_llm_star/experiments/research/session5/replay_repair.py \
  --cases improving_llm_star/experiments/results/research_session5/development.json.gz \
  --initial improving_llm_star/experiments/results/research_session5/prompt_pilot/responses.json.gz \
  --dynamic improving_llm_star/experiments/results/research_session5/dynamic_pilot/results.json.gz \
  --output /tmp/session5-repair-replay

.venv/bin/python improving_llm_star/experiments/research/session5/evaluate.py \
  --cases improving_llm_star/experiments/results/research_session5/validation.json.gz \
  --responses improving_llm_star/experiments/results/research_session5/validation_responses/responses.json.gz \
  --methods original neighbor lineage_bounded lineage_full none seed_bounded wa2 cut_none cut_real \
  --output /tmp/session5-validation

.venv/bin/python improving_llm_star/experiments/research/session5/offline_audit.py \
  --output /tmp/session5-fresh-correctness

.venv/bin/python improving_llm_star/experiments/research/session5/heap_audit.py \
  --root improving_llm_star/experiments/results/research_session5 \
  --output /tmp/session5-heaps.json

.venv/bin/python improving_llm_star/experiments/research/session5/report.py \
  --root improving_llm_star/experiments/results/research_session5
```

Use new output directories; raw runs refuse overwrite. Last command refreshes
only derived tables/plots. `repair_replay_controls_v2` is the authoritative replay:
it preserves endpoints and target count in shuffle/random controls. Earlier
control version shuffled boundaries too and is retained with that caveat.
`candidate_search`/`self_review_search` aborted on hash guards; use their_v2 folders.
`fresh_offline_audit` failed at result serialization after checks; use_v2.

## API/budget accounting

Authorized absolute cap:$3.00, persisted across all subprocesses and retries.
Known usage estimate$0.02871540; eight uncertain failures retain$0.15851520;
known plus maximum held exposure$0.18723060. Remaining authorized$2.81276940.
113 successful calls include one probe; eight transport failures are not treated
as free. All successful responses/usage are immediately stored in SQLite, then
exported. Input92696 tokens(including24064 cached),output27693,reasoning0. Reasoning
would be counted inside completion tokens, never double billed.

Official pricing checked2026-11-18: input$0.15/M,cached$0.075/M,output$0.60/M:
https://developers.openai.com/api/docs/models/gpt-4o-mini
Full128k context cost plus maximum output is reserved before each call, rather
than trusting approximate character/token counts. Integer nanoUSD, atomic SQLite
transactions and conservative unknown-failure holds prevent overspending. No
automatic retries. Concurrent workers share the same authoritative ledger.

The local authoritative `api_ledger.sqlite3` is ignored by Git. Committed
`api_export.json` is portable and restores an empty ledger on checkout, including
all conservative holds. Do not delete/reset ledger/export to bypass the cap.
Credentials are loaded only inside the execution process from the user-approved
`~/.config/llm-astar/.env`; no values, auth headers or raw exception text enter logs.
Codex authentication is untouched. A credential scan passed tracked artifacts and
compressed content. Key material is never part of source or response fixtures.

Network is OFF for the rest of this session. The free reconnection check hit an
automatic approval-review deadline, not a safety denial. Six URLError,one timeout
and one remote-disconnect affected the online generic-self control; that run is
NOT usable as a completed LLM-control comparison.

## Resume paid work only as a conscious next research step

The API commands below use real paid requests. Keep the same ledger and budget;
do not run them as ordinary offline reproduction. First verify network access
with `api_budget.py models`; then freeze any next study before fresh collection.

Original collection commands used:

```sh
.venv/bin/python improving_llm_star/experiments/research/session5/collect.py \
  --cases improving_llm_star/experiments/results/research_session5/development.json.gz \
  --phase pilot --output /tmp/session5-collection

.venv/bin/python improving_llm_star/experiments/research/session5/collect_dynamic.py \
  --cases improving_llm_star/experiments/results/research_session5/development.json.gz \
  --responses improving_llm_star/experiments/results/research_session5/prompt_pilot/responses.json.gz \
  --prompt original --gated --output /tmp/session5-online-repair
```

Request hashes include full payload and phase metadata. Exact repeated requests
reuse cache; failed/unresolved same hashes do NOT retry silently. Changing phase
can cause another paid request, so do not do that merely to reproduce old results.
Prompts and all responses are in api_export; all inputs use map facts, never
optimal costs/paths. Verified candidate generation is classical preprocessing,
not model reasoning; compare against equally supplied geometric/random options.

## Remaining protocol before making a positive university claim

1. Freeze EGOR and a new map-disjoint real-model split before any further tuning.
2. Collect original/improved prompts and successful equal-call generic/targeted
   corrections with the same approved snapshot,cap,seed schedule.
3. Evaluate original prompt×mechanism factorial; no-guidance original engine,
   corrected shared engine, geometric/random/shuffle,gate/no-gate and restart.
4. Charge all parsing,candidate preprocessing,search,API latency and failed-call
   holds. Repeat actual model outputs, not just cached timing trials.
5. Report path quality and paired map uncertainty. A result that only avoids bad
   guidance but loses to no-guidance must not be sold as LLM-specific benefit.
