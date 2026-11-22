# LLM-A*: Table 1 reproduction and LLM-A*-WW

This repository contains

1. the reproduction of **Table 1** of *LLM-A\*: Large Language Model Enhanced Incremental Heuristic Search on Path Planning* (Meng et al., 2024, [arXiv:2407.02511](https://arxiv.org/abs/2407.02511)) with GPT-4o mini,
2. our improved algorithm **LLM-A\*-WW** (LLM-A\* with weighted waypoints), and
3. additional experimental research on adaptive guidance, verified macro-edges, and LLM-generated spatial heuristics.

The original LLM-A\* code ([SilinMeng0510/llm-astar](https://github.com/SilinMeng0510/llm-astar)) is included unchanged in `llm-astar/`.

## Repository structure

```
llm-astar/                     original LLM-A* code and datasets (unchanged)
table1_reproduction/
    Table1_new.ipynb           Table 1 reproduction
    WA_Variants.ipynb          additional analysis: weighted A* variants
    antworten_<prompt>.json    stored GPT-4o mini answers (standard = Few-Shot, cot, repe)
    antworten_cot_abgeschnitten.json   CoT answers cut after the first line (truncation experiment)
    ergebnisse.json            per-sample results
    table1_*_new.csv           Table 1 (means, 95 % CIs, statistics, comparison with the paper)
improving_llm_star/
    llm_astar_ww/llmastar/     copy of the original llmastar package + LLM-A*-WW
        pather/llm_a_star_ww/llm_a_star_ww.py   implementation of LLM-A*-WW
        model/chatgpt.py       GPT wrapper updated for openai>=1.0 / GPT-4o mini
    LLM_AStar_WW.ipynb         evaluation of LLM-A*-WW (1000 samples, ablation, examples)
    results/                   result files of the notebook
    figures/                   report figures (created by the notebook)
further_improvements/          supplementary research (separate from the WW evaluation)
Team22_Report.pdf              team project report
requirements.txt
README.md
```

## Installation

Python 3.10 or newer (tested with Python 3.11).

```bash
pip install -r requirements.txt
```

No API key is needed to reproduce our numbers: all notebooks use the stored GPT-4o mini answers by default. An OpenAI API key is only needed to query the LLM again or to run LLM-A*-WW on new maps. Set it as environment variable `OPENAI_API_KEY` (in Colab: secret `OPENAI_API_KEY`). No keys or tokens are stored in this repository.

## Running the notebooks

Locally, start Jupyter in the folder llm_astar_max and open the notebook; it finds the project folder by itself. In Google Colab, upload the whole folder llm_astar_max (with exactly this name) to /content/ or to MyDrive/ in Google Drive, then open the notebook from there. The notebook finds the folder automatically. Cloning with the Colab secret GITHUB_TOKEN is only a fallback for team members with access to the private repository.
Run all cells from top to bottom. The settings are in the first cell of each notebook.

---

## Part 1: Table 1 reproduction

**Notebook:** `table1_reproduction/Table1_new.ipynb` (about 10–15 minutes on a laptop CPU).

* Dataset: `environment_50_30.json`, 100 maps × 10 start/goal pairs = 1000 samples
* Methods: A\*, Dynamic WA\* (initial weight 2, decay 0.99), LLM-only, LLM-A\* (original code)
* Prompts: Few-Shot (`standard`), Chain-of-Thought (`cot`), RePE (`repe`), unchanged from the original code
* LLM: `gpt-4o-mini-2024-07-18`, temperature 0, max. 1000 output tokens, no stop sequence, chat completions API
* Metrics: geometric mean of the per-sample ratios to A\* (operation, storage, path length) and valid path ratio, with 95 % confidence intervals

| Setting | Meaning |
|---|---|
| `QUERY_LLM = False` (default) | use the stored answers in `antworten_<prompt>.json`; reproduces our numbers exactly |
| `QUERY_LLM = True` | ask GPT-4o mini again (3100 requests). Answers that already exist in `antworten_<prompt>.json` are skipped, so move these files away for a complete new run. Numbers can differ slightly, because the API is not fully deterministic even at temperature 0. |

The notebook also contains the truncation experiment (answers cut after the first line as in the original API wrapper, Section 8) and an analysis of answers with and without waypoints (Section 9).

**Our results** (GPT-4o mini, in % of A\*):

| Method | Prompt | Operation | Storage | Path length | Valid paths |
|---|---|---|---|---|---|
| A\* | – | 100 | 100 | 100 | 100 |
| Dynamic WA\* | – | 60.90 | 78.52 | 100.24 | 100 |
| LLM-only | Few-Shot / CoT / RePE | – | – | 119.38 / 124.20 / 117.33 | 6.8 / 6.2 / 9.9 |
| LLM-A\* | Few-Shot | 46.09 | 65.40 | 102.74 | 100 |
| LLM-A\* | CoT | 47.61 | 66.24 | 102.61 | 100 |
| LLM-A\* | RePE | 50.13 | 68.31 | 102.30 | 100 |

**Additional analysis:** `table1_reproduction/WA_Variants.ipynb` compares weighted A\* variants (Pohl's dynamic weighting, static w = 2, Dynamic WA\* with and without re-scoring of the open list).

---

## Part 2: LLM-A*-WW

### Run LLM-A*-WW on a map

`LLMAStarWW` has the same input and output format as `LLMAStar` of the original code. It asks GPT-4o mini for waypoints (same prompts as LLM-A\*), so `OPENAI_API_KEY` must be set.

```python
import sys
sys.path.insert(0, "improving_llm_star/llm_astar_ww")   # folder that contains the llmastar package

from llmastar.pather import AStar, LLMAStarWW

query = {"start": [5, 5], "goal": [27, 15], "size": [51, 31],
         "horizontal_barriers": [[10, 0, 25], [15, 30, 50]],
         "vertical_barriers": [[25, 10, 22]],
         "range_x": [0, 51], "range_y": [0, 31]}

astar = AStar().searching(query=query, filepath="astar.png")
ww = LLMAStarWW(llm="gpt", prompt="standard").searching(query=query, filepath="llm_astar_ww.png")
print(ww)   # {"operation": ..., "storage": ..., "length": ..., "llm_output": [waypoints used]}
```

* `prompt`: `"standard"` (Few-Shot), `"cot"` or `"repe"`
* The model can be changed with the environment variable `LLM_ASTAR_MODEL` (default `gpt-4o-mini`).
* Optional arguments: `weighting="los"` (default), `"partial"` or `"none"`, and `switch_radius=3.0`; the other values are only used for the ablation.

### Reproduce our evaluation

**Notebook:** `improving_llm_star/LLM_AStar_WW.ipynb` (about 30 minutes locally with ablation; about 1 hour in Colab).
It runs A\*, Dynamic WA\*, static weighted A\* (w = 2), LLM-A\* and LLM-A\*-WW (and the ablation variants) on the same 1000 samples. LLM-A\* and LLM-A\*-WW use the same stored GPT-4o mini answers, so differences come from the search only.

| Setting | Meaning |
|---|---|
| `RUN_ABLATION` | also run the ablation variants (default `True`) |
| `LIMIT` | e.g. `50` for a quick test; `None` = all 1000 samples |
| `QUERY_LLM` | `True`: ask GPT-4o mini again (needs `OPENAI_API_KEY`) |

Results are written to `improving_llm_star/results/`, the report figures (example searches and failure cases) to `improving_llm_star/figures/`.

**Our results** (operation ratio in % of A\*, mean over 1000 samples):

| Prompt | LLM-A\* | LLM-A\*-WW |
|---|---|---|
| Few-Shot | 46.09 | 34.75 |
| CoT | 47.61 | 35.24 |
| RePE | 50.13 | 35.08 |

Static weighted A\* (w = 2) reaches 34.32. All methods find a valid path in 100 % of the samples. Full tables with confidence intervals: `improving_llm_star/results/ww_with_ci.csv`.

---

## Part 3: Experimental search improvements

The supplementary work is collected in [`further_improvements/`](further_improvements/README.md), corresponding to the further attempted optimizations in Section 6.3 and Appendix G of the [team report](Team22_Report.pdf). The separate research implementation investigates adaptive waypoint weighting, **LLM-A-VM\*** (verified macro-edges), and **LLM-RH\*** (bounded regional cost guidance). Original baselines remain available, and cached `gpt-4o-mini-2024-07-18` responses support offline comparisons.

The latest evaluation covers **100 tasks on 60 fresh map geometries**, with 209 passing tests and 4,217 independently checked configuration paths. The research improves search robustness and efficiency over the original implementation, but **does not establish a reliable additional LLM benefit over strong matched geometric controls**. These experiments use a different dataset from Parts 1 and 2.

- [Research overview and running instructions](further_improvements/README.md)
- [Research implementation](further_improvements/improving_llm_star/llmastar/research/)
- [Full research report (PDF)](further_improvements/improving_llm_star/experiments/results/research_session7/REPORT.pdf)
- [Methods and reproduction commands](further_improvements/improving_llm_star/experiments/research/session7/README.md)
