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
