# Session 4 persistent research checkpoint

Started2026-11-17 08:57:26UTC. Target~180min productive work, no artificial waits.
Branch research/waypoint-guidance; initial commit f8842ca. Main untouched. No paid
calls/push/merge; model credentials never inspected. Existing implementations and
all prior results preserved. No agent delegation requested or used.

Current phase:2 / exact components, relaxed portals, bounded strategy corridors.
Current hypothesis: coordinate-only integration discards route topology and often
caps/crops even oracle guidance; region strategies plus bounded corridor validation
may exploit genuine topology. First measure potential before committing to prompts.

Read: Session1-3 READMEs/logs, prior bounded/focal/certificate/seed implementations,
representative raw cached responses (all three styles), geometry and dataset code.
Raw caches contain verbose planning claims as well as coordinates; examples have
inconsistent above/below claims and routes on/through barriers. This is an observed
sample, not yet a quantified corpus result. No local model weights in workspace.

Research plan:
1. Fixed development oracle/cached/random/geometric/imperfect comparisons.
2. Structured strategic schema/provider with robust legacy parsing and prompts.
3. Hierarchical component/portal graph, same hierarchical no-LLM control, cold/warm
   costs separated. Persistent deferred frontier and effort-driven plan changes.
4. Multiple strategy hypotheses, independent anchor certification, quality1.1/2
   comparisons. Avoid repeating prior focal loops unchanged.
5. Freeze methods before fresh challenging maps; real-cache evidence separate
   from all oracle/simulated strategic responses. Latency break-even analysis.
6. Independent path/bound audits, map-cluster intervals, plots, notes, commits.

Completed: phase1_potential (120 development cases,5 repeats). Oracle verified-chain0.0713ms vs Witness0.3223ms; real0.3299ms, no real benefit. See log for quality caveats. Best verified production prior remains Witness-First. New schema/providers and hierarchy bounds tested; strategic planner in progress.
New files/results will live under research/strategic and experiments/session4.
Resume: read this checkpoint and EXPERIMENT_LOG.md; inspect git status/log before
continuing. Exact executable commands will be added with each completed stage.

Resume commands:
.venv/bin/python -m pytest -q improving_llm_star/tests/test_strategic.py
.venv/bin/python -B improving_llm_star/experiments/research/session4/oracle_potential.py --output /private/tmp/session4-oracle-rerun

10:03 UTC checkpoint: phase2 coarse/point portal pilots complete, no runtime win.
Phase3 CutStrategySearch implemented and 13 strategic tests pass. Cut pilot32
cases: geometric324.81 states vs weighted904.19; oracle266.63, valid28/28 reachable,
all4 disconnected correct. Cold mean medians3.497ms geometric,3.384ms oracle,
4.572ms weighted1.1. This is exploratory; no real advice in these new maps.
Cached120 pilot now running; source snapshots taken before launch. New cut bound
and primal strategy work remain uncommitted; save milestone after pilot/test.
Current best production recommendation remains Witness until broader timings.
Remaining: quantify cached real hint quality and bounds, optimize measured hot
spots, genuinely different strategy portfolio/dynamic architecture, larger dev,
freeze before new validation/fresh tests, CI/perfamily/plots, independent audits.

10:18 UTC checkpoint (earlier approximate10:03 entry was written around10:00).
Milestone commit d65c584 preserves phase1-3 foundation.132-case development
large pilot complete; cut geometry w1.1 is current strongest new large-map
candidate, but cached Witness remains faster. Legacy inference and prefix copying
were profiled; code now uses bounded opt-in inference and shared segment prefixes.
19 strategic tests pass (full suite last run115 before latest4 tests). Phase5
strategic-label/local-repair/portfolio pilot running serially; do not mutate
loaded production modules while its timing process runs. Read its source snapshot
for exact provenance. No held-out Session4 maps opened yet.
Remaining: parse robustness edge cases; profile preservation; phased budgeted
candidate policy; final benchmark with warmups/native original/total work and
per-map paired CIs; freeze before fresh seeds/sizes; independent geometry/bound
and memory checks; plots, docs, commits. Target session end11:57 UTC if useful.

13:19UTC: candidates frozen at0c462d6; all118 tests pass. Wall elapsed already
~4h22; active duration not separately metered. Complete final deliverables now.
Phase5 shows corrected oracle and local portfolio potential; stronger classical
local-repair control added before freeze. Fresh44 cases generated only AFTER
freeze, sizes96/192,11 families,2 maps and2 pairs per family. Final serial run
currently active (seven repeats,16 modes); DO NOT alter frozen algorithms or
existing session4 Python files until source-integrity checks complete. New
postprocessing/audit files may be added; they are not imported by timed code.
Next: cached validation with matched noLLM/random/wrong controls; uniform-capped
native/matched original fixed fresh query0 subset; bootstrap/per-family reports,
independent Shapely/cost/bound/disjointness audits, memory profile and plots.
No parameter/algorithm refinement based on fresh output. No paid calls/push/main.

## Session complete — 2026-11-17 13:43 UTC

Observed wall window08:57:26–13:43UTC, approximately4h46min. Active CPU/model
work was not separately metered; do not claim a measured180-minute active run.
All launched research/timing/audit processes completed. No paid calls or idle
waits to consume a time budget. No required implementation work left pending.

Best supported large-map classical engine: CutStrategySearch, bound2, no provider.
Guidance research candidate: same engine + single LocalRouteProvider, total local
budget128/per-link32. Synthetic/oracle guidance helps; real cache evidence remains
negative. Portfolio, hierarchy, roadmap and primal variants preserved. No universal
winner across families; retain Witness as small-map control. All algorithms remain
unchanged from candidate freeze0c462d6. Foundationd65c584; final commit adds
post-freeze artifacts, reports and analysis tooling only.

Final tests118/118 pass (6.45s final run); compileall succeeds. Independent audit
44 reference distances/833196 bounds/4480 paths/949396 edges.70 separate exact
heap/memory trials match path/counter expectations. Final datasets have no source
changes during timing, and fresh map hashes are disjoint from generated dev maps.
Main ref remains66baa31d2fc2b658b501dcd4b34e09d31af66cb4. Original utils/env imports
are byte-identical between frozen and current packages. No push/merge/main edits.

Start here to review or resume:
- experiments/results/research_session4/REPORT.md
- experiments/research/session4/README.md (all commands)
- final_analysis/TABLES.md, SUPPLEMENT.md, statistics.json, diagnostics.json
- final_analysis/*.pdf and *.png
- final_audit/audit.json
- EXPERIMENT_LOG.md and THEORY.md

Only future research direction: independently authorize new strategic model
outputs, freeze the prompt/cost budget before collection, reserve an unopened
map-disjoint test set. Do not continue tuning this opened fresh set or relabel
synthetic guidance as real LLM evidence. Keep current raw results immutable.
