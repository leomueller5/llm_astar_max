# Session 6 checkpoint

Started 2026-11-18 10:43:32 UTC. Target ~13:43 UTC if productive.
Branch: research/waypoint-guidance. Main is never moved.

## Completed

- Fetched team branches. Merged origin/dev (da51b28), preserving all six replaced
  reproduction files under table1_reproduction/archive_before_table1_new.
- Merged origin/main (8bc8a66). Notebook add/add conflict resolved by preserving
  both copies: WA_Variants.ipynb and WA_Variants_from_main.ipynb.
- Found actual assignment PDF. It explicitly values fair A*/LLM-A* comparisons,
  ablations, honest negative results, hidden-map generalization and reproducibility.
- New team dataset: 100 maps, 1,000 queries, 101×61 coordinate ranges, 10–17 walls.
  Fixed map-disjoint 60/20/20 split in results/research_session6/team_split.json.
  Map 0 inspected before splitting and explicitly allocated to development.
- Cumulative starting API spend $0.0287154, ambiguous holds $0.1585152.
  Never release old holds without billing evidence; never reset ledger.
- Git credential owner leomueller5 verified. Existing author Leo / Gmail matches
  repository history, but email is NOT verified for authenticated account.
  Publication currently prohibited by user's identity-verification condition.

## Current hypotheses

1. Multi-route geometric portfolios provide more useful decisions than the
   already-rejected single visible endpoint prompt. Compare learned selection
   against the identical portfolio with a cheap deterministic ranker.
2. Conflict feedback can ask for a small strategic repair of a geometric route,
   rather than complete coordinate generation (direct original LLM-A* extension).
3. Route uncertainty can control bounded waypoint influence immediately, without
   the old 30-expansion delay. Compare identical engines with guidance disabled.

## Next

Verify free API health, minimal reserved probe, tests for retries/restoration.
Characterize development maps. Prototype candidates, collect development-only
responses, evaluate matched controls. Freeze before opening held-out cases.

## Resume

`.venv/bin/python improving_llm_star/experiments/research/session6/api.py status`

Do not invoke Session 5 export after new requests: retain historical artifacts.

## Update 11:28 UTC

Milestone c270d4a preserves first four research directions and cached requests.
Development macro-cut first multi-route shows real search-work advantage versus
geometry controls, but independent validation reverses it. No success claim.
Random/shuffle controls saved; 10 seeds averaged per query before map bootstrap.
Dynamic real correction pilot: 6 requests/16 tasks; 382 mean search pops versus
374.2 without intervention, random380.4, classical462.6. Trigger/goal and geometric
preprocessing are retained; no reliable benefit. One trigger may be redundant
when a full geometric route exists, so a future gated provider must avoid this.

Macro-portfolio geometry ablation contained metadata leakage (ONLY that ablation,
not macro-cut). Fixed by replacing every metadata route with geometric routes,
and resetting metadata in disabled controls; regression test added. Old affected
comparisons explicitly marked invalid in experiment log.

Next: lazy sparse geometric roadmap completion, with exact graph-search controls
and LLM-proposed missing connections. This changes the information representation
substantively rather than retuning previously unsuccessful weights.
