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
- The team report PDF is preserved unchanged. Primary WW implementation, notebook,
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
