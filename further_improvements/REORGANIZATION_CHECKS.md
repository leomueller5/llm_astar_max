# Submission layout verification — 22 November 2026

This packaging change relocates supplementary research; it introduces no new
search mechanism, benchmark claims, or API requests.

- Offline suite: **209 passed** (23.00 s) after relocation.
- Frozen-source integrity: **54 production/dependency files verified**.
- **1,937 moved research files** checked byte-for-byte against the preceding
  commit; unchanged. The project findings document received a layout note and
  the integrity-audit wrapper dropped obsolete publication-branch assertions.
- Standalone adaptive-alpha comparison ran successfully on all six existing
  fixtures and four main variants; output was directed to `/tmp/`, leaving
  historical results unchanged.
- Newly written documentation links and shared-data links resolve.
- Staged research files scanned for credential patterns and the configured API
  key without printing or persisting the key; no findings. Local SQLite ledgers,
  private reports, and environment files remain excluded.
- At the initial layout checkpoint the team report PDF was preserved unchanged.
  A subsequent editorial correction removed only the duplicate bibliography from
  page 6; all other 9 pages have identical text and pixel renderings, and the
  report still has 10 pages with one complete bibliography.
  Primary WW implementation, notebook,
  result tables, figures, original implementation, and shared datasets are unchanged.

Reproduce the checks from the repository root:

```sh
source .venv/bin/activate
cd further_improvements
export PYTHONPATH="$PWD/improving_llm_star"
python -m pytest improving_llm_star/tests -q
python improving_llm_star/experiments/research/session7/integrity_audit.py --output /tmp/llm-astar-integrity.json
python improving_llm_star/experiments/compare_adaptive_alpha.py --output-dir /tmp/llm-astar-smoke --repeats 1 --warmups 0
```

Historical evidence stays in the original session reports. This document records
only validation of the repository reorganization.

## Report directory guide

A subsequent documentation addition inserts a short pointer in Appendix B and
adds Appendix I (Code and Artifact Locations). The report now has 11 pages. All
pre-existing text is preserved; the other nine original pages render identically.
All listed code, notebook, result, cache, and test paths were verified against the
repository, and the added page was visually reviewed. The AI Usage Statement and
experimental results are unchanged. One complete bibliography remains.

## Separate report submission

The final local team PDF includes the clickable project repository URL in Appendix B
(https://github.com/leomueller5/llm_astar_max). All other ten pages and the remainder
of Appendix B were verified unchanged. The PDF is now ignored and removed from
the current Git tree, while retained locally as `Team22_Report.pdf` for the ZIP
submission. Documentation no longer links to a report file absent from the repo.
