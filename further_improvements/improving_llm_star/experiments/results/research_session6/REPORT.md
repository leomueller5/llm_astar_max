# Session 6: Hybrid geometric and LLM-guided A*

**Conclusion.** The implemented verified-macro planner substantially improves on frozen LLM-A*, with valid paths and better average path quality. However, genuine GPT-4o-mini advice does **not** reliably improve on the strongest matched geometric controls. This session supports a safe integration mechanism and a rigorous empirical limitation, not a general claim that the LLM makes classical search faster.

Research branch: `research/waypoint-guidance`. Main and historical implementations/results are preserved. The assignment PDFs in the repository were reviewed: Table 1 reproduction, hidden-map evaluation, and a defensible improvement to LLM-A* remain the academic objectives. The exact model is `gpt-4o-mini-2024-07-18`, also explicitly used in the new reproduction notebook. Some older caches only record a model alias, so their historical snapshot cannot be independently established.

## Method and relationship to the original paper

The original uses `f=g+h_goal+d_active_target`; at the final goal this becomes `g+2*h_goal`. It globally switches waypoint when a generated neighbor equals the active target, before collision and CLOSED checks (`llm-astar/llmastar/pather/llm_a_star/llm_a_star.py:129`). Expanding the waypoint, or reaching it on the returned path, is not required. The original implementation and scoring were not edited.

The proposed **LLM-A*-VM (verified macro guidance)** changes the *role* of advice. Geometry creates a bounded portfolio and endpoint identifiers. Where its best route is incomplete, the LLM proposes up to three ordered endpoint strategies. Targets supported by a strict majority of these routes become optional macro-transition proposals. They never replace collision checking or remove ordinary grid edges.

```
Build query-local geometry, admissible cut lower bound, and small route portfolio.
If a complete geometric route exists, use its targets without a model call.
Otherwise request three structured endpoint-ID route hypotheses.
Select targets supported by a strict majority of the proposed routes.
Run robust Weighted A* with priority g + w*h_cut.
After each eight real expansions, test up to three selected macro targets.
For every collision-free shortest lattice segment, relax its exact path cost.
Retain all normal grid successors; skip stale entries and reopen cheaper labels.
Stop when the goal is popped; return the reconstructed dense grid path.
```

For a verified macro from `u` to `v`, `c(u,v)` is the length of an actual walk in the original lattice graph. Thus no fictitious shortcut is introduced. With admissible `h_cut`, all unit edges retained, correct reopenings and termination on goal pop, the usual Weighted-A* argument gives `C <= w*C*` (subject to floating-point tolerance). `w=1` is optimal; the default `w=2` is bounded-suboptimal. The independently prespecified quality profile uses `w=1.05`. No such guarantee is claimed for the frozen original or its direct heuristic-preserving macro extension.

This is an **integration/adaptation**, combining established safe search ideas with geometry-constrained model advice; absolute academic novelty is not claimed. The model selects optional transitions instead of adding an unverified distance penalty to every OPEN priority. Its targets are fixed for a search, so **zero OPEN rebuilds** are needed. Consensus from one response is correlated and is not calibrated confidence.

Implementation: `llmastar/research/hybrid_guidance.py`, `macro_guidance.py`, `geometric_advice.py`. Headless query/result compatibility includes `searching(query, filepath=...)` and the original four result keys. Original, constant-alpha, adaptive-alpha, WW, and historical research variants remain independently runnable. See [the mathematical treatment](../../research/session6/THEORY.md) and [commands](../../research/session6/README.md).

## Data and experimental protocol

Fetched GitHub and preserved both team contributions through merges `da51b28` (dev maps/notebook) and `8bc8a66` (main notebook). The new `environment_100_60.json` has 100 maps, 1,000 queries, domains `[0,101] x [0,61]`, and 10–17 walls/map. Map 0 was inspected before splitting and explicitly forced into development. The split is 60 development / 20 validation / 20 reserved test maps.

The primary held-out evaluation comprises **200 queries on the 20 reserved team maps**, plus **20 independent challenging maps** across ten families, including corridors, mazes, nested obstacles and detours. Their geometries do not overlap development/validation maps. Parameters, sources and prompt were frozen at **2026-11-19 05:48:06 UTC**, before test generation. One later EOF cleanup was AST-identical and is disclosed in `frozen_manifest.json`. A forty-query factorial subset was predetermined, not chosen by favorable outcomes.

Each method gets identical inputs and cached raw responses. Repeated native timing includes fresh geometry, route construction, bounds, advice decoding and actual search, with no free preprocessed cache. One warmup and five timed repetitions, randomized ordering, equal three-second caps; **no primary timeouts occurred**. Heap instrumentation is separate. The 220 x 14-method primary study contains 18,480 recorded timing/audit trials plus warmups. Frozen original code is loaded unchanged, with plotting suppressed and an equivalent indexed collision primitive applied to matched comparisons; native-original timing is separately runnable. Full computational time excludes network waiting; an additional live study measures actual API-inclusive latency.

Arithmetic means of per-case median runtime and work are reported. Path-quality aggregates are geometric means against exact A*. Confidence intervals use 4,000 paired **whole-map** bootstrap resamples, not 200 falsely independent team queries. Intervals are nominal, without correction for the multiple exploratory comparisons.

## Primary held-out results

All methods below solved **220/220** cases. Runtime is local full computational runtime in milliseconds, including fresh preprocessing; **not API-inclusive latency**.

| Method | Team ms | Team heap pops | Team unique | Team GM cost/opt | Challenging ms | Challenging pops | Challenging GM cost/opt |
|---|---:|---:|---:|---:|---:|---:|---:|
| Frozen original LLM-A* | 183.414 | 2050.9 | 1209.1 | 1.03604 | 481.892 | 3274.4 | 1.02398 |
| Original + robust search engine | 13.043 | 3494.1 | 1193.7 | 1.02403 | 21.714 | 5772.9 | 1.01425 |
| Standard A* | 8.688 | 2329.6 | 1725.0 | 1.00000 | 12.942 | 3519.9 | 1.00000 |
| Weighted A*, w=2 | 6.106 | 2742.1 | 894.3 | 1.02653 | 11.094 | 4666.1 | 1.02334 |
| Witness-First, no LLM | 5.17 | 2668.9 | 870.9 | 1.02572 | 8.97 | 4091.7 | 1.01583 |
| Cut search, no LLM, w=2 | **4.735** | 1166.5 | 474.9 | 1.01856 | **6.113** | 1851.5 | 1.00852 |
| VM, geometric best route | 5.595 | 1046.0 | 395.6 | 1.01805 | 8.169 | 1696.8 | 1.00852 |
| VM, geometric consensus | 5.499 | 999.4 | 393.0 | 1.01772 | 8.136 | 1691.5 | 1.00852 |
| VM, all geometric endpoints | 5.568 | **955.1** | **379.4** | 1.01881 | 8.581 | 1669.7 | 1.01062 |
| **VM, genuine hybrid advice** | **5.607** | **1007.4** | **393.0** | **1.01852** | **8.080** | **1658.5** | **1.00996** |
| VM, coordinate LLM only | 6.17 | 1249.1 | 473.6 | 1.02668 | 7.43 | 1666.4 | 1.01512 |
| VM quality profile, w=1.05 | 6.912 | 1037.2 | 630.1 | 1.00047 | 9.180 | 1382.2 | 1.00000 |
| Cut quality profile, w=1.05 | 5.453 | 1059.4 | 656.1 | 1.00049 | 6.895 | 1398.5 | 1.00000 |

On team maps, VM reduces unique expansions by **67.5%** and total pops by **50.9%** relative to original, while reducing GM excess path cost from 3.60% to 1.85%. Computational runtime falls about 96.9%. These are whole-system improvements: most runtime gain is attributable to classical engine/geometry changes. Profiling four team tasks places approximately 91% of original runtime in `searching`, consistent with linear CLOSED handling and repeated processing. Comparing robust-original and frozen-original timings demonstrates how large this confound is.

**The critical LLM ablation:** VM / geometric-best pop ratio is 0.963 [0.850,1.028]; VM / geometric-consensus is 1.008 [0.986,1.030]; VM / all-endpoints is **1.055 [1.004,1.108]**. VM is worse than the strongest control in team-map pops. Corresponding computational runtime ratios are 1.002 [0.961,1.028], 1.020 [1.007,1.031], and 1.007 [0.984,1.029]. No general LLM advantage is supported.

On challenging maps the geometric-consensus pop ratio is 0.981 [0.924,0.999], a small conditional signal, but runtime ratio 0.993 [0.953,1.024] does not establish a runtime gain. Against all endpoints, pop ratio 0.993 [0.950,1.020] also includes equality. Nominal intervals and twenty maps warrant caution. Classical Cut remains faster.

At comparable high quality, the separate w=1.05 matched block gives team VM 1037.2 pops versus 1036.9 geometric-consensus and 1036.6 all-endpoints. Challenging VM uses 1382.2 versus 1394.7 and 1372.5. This again does not show a general model advantage. Maximum primary team path ratios are 1.293 for VM and 1.016 for VM-quality; averages do not imply every path is near-optimal.

Complete tables, queue counts, original-paper OR/SR/RPL denominators, medians, per-family outcomes and paired intervals are in `final_analysis_corrected/analysis.json`, `summary.csv`, `RESULTS.md`; the quality block is in `quality_analysis_corrected`. Original-paper operation counts are kept distinct from unique states and audited push+pop totals.

## Prompt-only, direct-original, and structural ablations

The following uses the predeclared 40-query subset. It is not interchangeable with the 220-case primary means.

| Variant | Team pops (20 tasks) | Challenging pops (20 tasks) | Interpretation |
|---|---:|---:|---|
| Original, original prompt | 1696.9 | 3274.4 | Frozen baseline |
| Original + endpoint-ID prompt | 2026.2 | 3438.2 | Better prompt alone does not reduce work |
| Original + prompt and consensus processing | 1622.2 | 3391.2 | Mixed; not a reliable general gain |
| Original + true map bounds in prompt | 1766.5 | 3273.1 | Stronger prompt control; no rescue |
| Team WW implementation | 1177.4 | 2881.8 | Preserved, independently compared |
| VM, primary | 702.9 | 1658.5 | Includes verified macros and cut anchor |
| VM, no macro edges | 808.8 | 1704.8 | Macros can reduce work; CPU savings not automatic |
| VM, Euclidean anchor | 2089.5 | 4618.0 | Cut lower bound explains a major classical gain |
| VM, no shared bound preprocessing | 702.9 | 1658.5 | Same search work; higher CPU cost |
| VM, always ask LLM | 798.5 | 1361.7 | Contradictory by stratum; follow-up below |
| Existing adaptive alpha, final g+h | 2528.9 | 3900.2 | Different final heuristic must be disclosed |
| Adaptive alpha, matched final g+2h | 2528.4 | 5480.1 | Adaptation did not solve the problem |
| Constant alpha .5, final g+2h | 2578.2 | 5599.5 | Preserved baseline |

In the frozen original there are 710 switch events over 220 tasks: median active duration **10 pops**, 26.2% at most one, **71.8% below 30**, but a long tail raises the mean to 194.1. Original duplicate pops average 879.1/query. Therefore a 30-expansion stagnation detector is structurally too late for many targets, while raw duplicate pops contaminate the signal. Distances can also improve locally while a route is strategically bad, or worsen during a necessary detour. These observations explain why simply retuning alpha is inadequate.

The primary test gate skips the model when geometry already has a valid route; that does not certify the route's usefulness. The always-call result motivated a **separately frozen secondary hypothesis**, before generating twenty more independent maps of sizes 92/124. All controls bypass the same gate; the real model, geometric best/consensus and all endpoints receive identical engines/portfolio computation. Five bijective endpoint randomizations preserve model route votes/overlap.

| Secondary ungated control | Mean pops | Mean ms | GM cost/opt |
|---|---:|---:|---:|
| Real model | 1984.45 | 9.219 | 1.01449 |
| Geometry best | 1965.60 | 9.094 | 1.00977 |
| Geometry consensus | 1949.40 | 9.033 | 1.00977 |
| All endpoints | 1951.50 | 9.448 | 1.02652 |
| Random endpoints | 1982.59 | 9.419 | 1.01655 |

Real/all pop ratio 1.017 [0.986,1.059]; real/random 1.001 [0.937,1.028]. The apparent always-call advantage **did not generalize**. This secondary study never changed the primary algorithm or its claims.

## Guidance quality, dynamic intervention, and oracle ceiling

On the initial 16-task pilot, geometry supplied a complete collision-free route in 11 cases; model ranking/refinement produced only 2/16 and 1/16 complete valid proposed routes, and original coordinate proposals 0/16. These are *advice-route* rates, not final planner failures: fallback found valid final paths in all cases. The first original pilot had an unfair 384-token cap and is excluded; it was regenerated with the original 1000-token allowance. Truncations that remained at the fair cap were retained.

Strong full-factorial work controls on the forty fixed test tasks: real advice 1180.7 pops; geometry 1170.8; all endpoints 1162.1; shuffled real 1178.5; vote-preserving random endpoints 1159.3. Thus advice is generally weak, and the method also uses it weakly. All random-seed repetitions are averaged within a task before treating maps as statistical units.

Explicit **oracle** controls demonstrate the distinction. Optimal reference targets in the same VM engine still average 1098.0 pops, whereas a verified complete optimal incumbent in Cut search averages 85.1 pops and optimal cost. Computing the oracle is excluded from those labelled planning counters and recorded separately. No solved optimal path or oracle-derived information entered any real prompt. This shows significant potential in constructing useful complete routes, but neither current real advice nor this target-insertion architecture consistently realizes it.

Other genuinely different experiments were preserved rather than hidden:

- Real dynamic macro correction: six calls/16 tasks, mean search pops 382.0 versus 374.2 without correction; no reliable benefit.
- Interactive verified frontier selection: 20 calls/16 tasks, 752.2 grid pops versus 759.1 random and 775.3 classical, plus abstract search and API latency. Small pilot, no established model benefit.
- Sparse roadmap completion saved approximately 2.6% pops but added CPU cost.
- Immediate local Beta trust and priority-descent gates sometimes reject necessary detours; no robust gain.
- Image prompts improved work in five hard development tasks but required approximately 25,500 additional input tokens/image plus rendering.
- Repeated real sampling reduced within-case pop variation for consensus but slightly worsened path quality. Three routes from one response are not independent samples.
- Early portfolio metadata leakage and an inconsistent gate in exploratory rows were identified and explicitly excluded; corrected controls have regression tests. See the experiment log for affected directories.

## Runtime, memory, and API accounting

In the primary 220-query hybrid collection the model is actually invoked for **76** queries; remaining entries are explicitly marked geometry-only, never counted as model successes. Six live calibration tasks (different queries from the same generated map families, not used to select the algorithm) measured actual end-to-end mean latency: original **8.460 s**, hybrid **2.288 s** (four calls/six tasks), geometry-only **0.0092 s**, all endpoints **0.0158 s**. These few cases illustrate network dominance, not a population-level latency theorem. The hybrid can beat an always-call original largely by avoiding calls; it cannot claim API-inclusive superiority over no-call geometry.

Traced peak memory on fourteen fixed diagnostic tasks: original mean 628 KiB, VM 1079 KiB, all endpoints 1080 KiB. Medians are original 445 KiB and VM 296 KiB; VM's worst case reaches 4097 KiB. **There is no overall memory reduction claim**. These are separately instrumented planning allocations, including diagnostic structures, not complete native-process RSS.

Cumulative ledger: **$0.2679828 successful estimated charges + $0.1783152 unresolved worst-case exposure = $0.4462980**, safely below the unchanged $3 allowance. Remaining authorized exposure is $2.553702. Session 6 alone: 659 successful requests, 825,232 input and 195,319 output tokens, estimated $0.2392674, plus one HTTP 520 reservation of $0.0198. Eight Session 5 unknown-cost holds remain intact. All 659 new successful responses identify the exact requested snapshot; reported reasoning tokens are zero, and any reported reasoning tokens are billed as part of output, not added twice. Every transport attempt was separately reserved, bounded retries/backoff used, successes cached immediately. No key appears in source, logs or commits. See `BUDGET_REPORT.json` and the portable ledger; provider billing may differ from these token-price estimates.

## Correctness and limitations

Full automated tests: **158 passed**. Independently audited **3,080 saved primary paths and 242,757 unit edges**, with Shapely collision checking and recomputed costs; all valid. Map fingerprint audit found zero development/validation/test geometry overlap. Earlier prototype/production parity also matched 360 runs and independently checked 25,061 edges. Test hashes still match the frozen algorithm; original implementation remains unchanged.

Limitations: 20 team test maps and twenty independent challenging maps are modest; structured axis-aligned geometry is assumed by the strongest anchor; arbitrary maps use safe weaker fallbacks; nominal multiple comparisons must not be mistaken for confirmatory successes. The model sees a bounded candidate pool, which may omit the right strategy. Vote thresholds can erase useful minority targets. A valid geometric route is not an optimality certificate. Macros add preprocessing, allocation and collision costs. Current model latency dwarfs millisecond search savings. Query parsing latency is separate when natural-language input, rather than the structured benchmark query, is used.

## Academic recommendation

Present one central mechanism: **geometry-constrained model advice as verified optional A* transitions, with an independent complete anchor**. Explain its relationship to LLM-A*, proof conditions and ablations. Report the strong original-baseline improvement, but explicitly attribute most of it to classical engineering/geometry. The honest scientific outcome is that current real-model guidance has not surpassed strong matched controls, despite synthetic/oracle potential.

For the deadline, submit the frozen original reproduction, the bounded verified-guidance method, the high-quality w=1.05 configuration, and the negative LLM ablation. Use Cut-only as the recommended runtime control. The strongest next research direction is verified construction/repair of complete strategic route candidates, where the oracle experiment indicates headroom; another late alpha threshold sweep is poorly motivated. Do not claim that a language model improves classical planning on this evidence.

Reproduction instructions: [research README](../../research/session6/README.md). Charts: [standalone PDF](figures/SESSION6_FIGURES.pdf). Raw primary output: `final_heldout/`; per-family and interval data: `final_analysis/`; factorial: `factorial_analysis/`; secondary: `supplementary_matched/`.

## Final analysis correction and publication status

A final audit found floor-indexed percentiles misleading for two-case family summaries (p95 could lie below the median). Linear interpolation and a regression test fix this reporting error. Corrected outputs are in `final_analysis_corrected`, `factorial_analysis_corrected`, and `quality_analysis_corrected`; the earlier outputs remain preserved. All means, medians, counts, costs and validity conclusions are unchanged. `ANALYSIS_CORRECTION.json` records the exact scope. Minor bootstrap endpoint interpolation changes do not change the rounded conclusions above.

The final GitHub fetch found additional teammate notebook/figure/result updates on dev1020fe0. Byte-exact prior versions are archived in `team_before_1020fe0` before incorporating them; they are not Session6 measurements. Main remains unchanged. Publication is withheld because the configured author email could not be verified as associated with the authenticated GitHub account. No identity/authentication settings or historical commit metadata were changed, and no push to any branch was attempted.
