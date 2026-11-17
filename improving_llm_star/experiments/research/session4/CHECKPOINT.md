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
