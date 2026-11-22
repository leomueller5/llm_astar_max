# Further improvements: supplementary LLM-A* research

This folder contains Leonard Mueller's AI-assisted exploratory research beyond
the team's Table 1 reproduction and **LLM-A*-WW** implementation. The primary
submission is [Team22_Report.pdf](../Team22_Report.pdf); Section 6.3 and Appendix G
discuss the adaptive-alpha and hybrid-search attempts collected here. Later
experiments are supplementary and are not additional results of the WW notebook.

## What is included

- [Initial algorithm analysis (PDF)](LLM_AStar_Algorithm_Improvement_Analysis.pdf).

- [Project findings, in German](PROJEKT_ERKENNTNISSE.md): hypotheses, implementation
  details, limitations, and results from the research sessions.
- [Adaptive alpha](improving_llm_star/experiments/ADAPTIVE_ALPHA.md) and
  [search corrections](improving_llm_star/experiments/SEARCH_CORRECTIONS.md).
- [Research overview](improving_llm_star/experiments/research/README.md), including
  certificate-first and witness-first search, followed by the session directories.
- [Session 6: verified macro-edges](improving_llm_star/experiments/research/session6/README.md),
  [report PDF](improving_llm_star/experiments/results/research_session6/SESSION6_REPORT_FINAL.pdf).
- [Session 7: spatial heuristics](improving_llm_star/experiments/research/session7/README.md),
  [report PDF](improving_llm_star/experiments/results/research_session7/REPORT.pdf),
  [team brief](improving_llm_star/experiments/results/research_session7/TEAM_BRIEF.md).
- Research implementations, offline tests, cached model outputs, frozen manifests,
  historical source snapshots, and reproducible benchmark results.

The strongest methods improve upon the original implementation, but comparisons
with matched classical controls **do not establish a reliable additional benefit
from genuine LLM guidance**. Synthetic and oracle experiments are labelled as such.
Datasets and measurement protocols differ between sessions and the primary WW
evaluation; their numbers must not be combined into one benchmark.

## Run the research independently

From the repository root, create or activate a Python environment, then install
the research dependencies. The team's root requirements remain sufficient for the
primary notebooks; research dependencies include additional testing/model tools.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r further_improvements/improving_llm_star/requirements-dev.txt
cd further_improvements
export PYTHONPATH="$PWD/improving_llm_star${PYTHONPATH:+:$PYTHONPATH}"
python -m pytest improving_llm_star/tests -q
```

**Run historical commands from this directory**, not the repository root. The
internal `improving_llm_star/...` paths remain unchanged. If an older command uses
`.venv/bin/python`, use `python` from the activated repository environment instead.
All replay and correctness commands use cached responses; no API key or new paid
request is needed. Do not run collection scripts merely to replay results.

For example, check the frozen Session 7 sources without modifying result files:

```sh
python -c 'import json,sys; sys.path.insert(0,"improving_llm_star/experiments/research/session7"); from native_benchmark import verify_sources; verify_sources(json.load(open("improving_llm_star/experiments/results/research_session7/frozen_manifest.json"))); print("Frozen sources verified")'
python improving_llm_star/experiments/research/session7/native_benchmark.py --help
```

The session READMEs provide full replay commands. Write any reruns to **new output
directories** to preserve the committed historical observations.

## Layout and preservation

The research workspace retains its original internal layout so stored relative
paths, source hashes, and historical commands remain meaningful. Relative symbolic
links `llm-astar/` and `table1_reproduction/` refer to the unchanged shared original
code and cached team responses in the repository root. The research package's
`dataset/` and `docs/` links similarly refer to shared upstream assets. These links
are intentional; preserve them when cloning or copying the repository.

Research algorithm files and historical results were moved without changing their
contents. The current integrity-audit wrapper allows execution after integration
into `main`; its original pre-publication branch/main assertions remain available
in Git history. Frozen algorithm-source checks still apply.

Individual coursework/contribution reports stay in the ignored root
`personal_reports/` directory and are not part of this public team material.

## Editorial notes for the team report

The uploaded PDF is preserved unchanged. Before final submission, consider:

1. The AI Usage Statement already discloses assistance in shortening the report.
   It currently names Claude only. Sections 6.3 and Appendix G also include
   experiments developed with **OpenAI Codex** assistance; include that tool and
   distinguish coding/analysis assistance from the GPT-4o mini model evaluated.
2. The bibliography appears twice, before and after the AI Usage Statement.

These are editorial observations, not changes to the team's experimental claims.
