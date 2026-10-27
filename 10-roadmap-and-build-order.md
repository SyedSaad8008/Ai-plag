# Roadmap & Build Order (give this to Antigravity phase by phase)

Each phase has acceptance criteria — do not start the next phase until they pass. Estimated with an agentic IDE, part-time: Phase 1 ≈ 1 week, Phase 2 ≈ 1 week, Phase 3 ≈ 1–2 weeks, Phase 4 ≈ 1–2 weeks, Phase 5 ≈ 1 week, Phase 6 ≈ ongoing.

---

## Phase 0 — Setup (day 1)
- Repo per doc 02; Python 3.11/3.12 venv; `requirements.txt` from `code/`.
- Ollama installed; `ollama pull bge-m3 qwen3:8b`.
- Antigravity prompt: *"Read docs/02-architecture-blueprint.md and docs/03-similarity-engine-guide.md. Scaffold the repo layout exactly as specified."*

## Phase 1 — Engine A MVP (similarity, local only)
- `fingerprint.py` + `minhash_index.py` adapted into `engines/`; ingest DOCX only; SQLite catalog; report JSON; simple report page in existing UI.
- **Accept:** (a) a doc with a copied 20-word span is caught with correct span positions; (b) 8-word span caught (k=5,w=4); (c) 7-word span NOT reported by default; (d) 8k-word doc checks in < 30 s against a 10k-doc test corpus; (e) round-trip file untouched (doc 06 checklist item 1).
- Antigravity prompt: *"Implement Phase 1 per docs/10-roadmap-and-build-order.md using code/fingerprint.py and code/minhash_index.py as reference. Acceptance criteria must pass — write a pytest for each."*

## Phase 2 — External index (OpenAlex) + college archive
- `openalex_ingest.py` adapted; overnight pull of your discipline's slice; Unpaywall fetch-on-demand with caching; archive every checked submission.
- **Accept:** (a) 1M-abstract index built overnight on the laptop; (b) a paragraph copied from an indexed paper is matched to the right source with DOI link; (c) `web_check=false` produces identical local-only results; (d) archive stats endpoint returns counts.

## Phase 3 — Engine B cascade
- Stage 1 (`perplexity_burstiness.py`), stage 2 (P1 judge via `llm_judge.py`), calibration script (doc 08), report bands.
- **Accept:** (a) AUROC ≥ 0.85 on a first 100-paragraph labeled set; (b) judge returns valid JSON ≥ 98% of calls (retry logic otherwise); (c) full 8k-word doc processed < 5 min on the 8 GB laptop; (d) every flagged segment shows human-readable signals.

## Phase 4 — PPTX + rewrite actions + edit log
- `pptx_editor.py`, `docx_editor.py` wired to UI actions (coach paste, cite-insert, direct replace); edit-log JSON per document (doc 11).
- **Accept:** full doc 06 testing checklist green; a 40-slide deck with charts/SmartArt passes with honest flags; rewrite preserves all formatting (diff screenshots).

## Phase 5 — Evaluation + pilot
- Doc 08 harness run; produce `evaluation/report_*.pdf`; run the 2-department pilot (2 faculty, ~50 documents); collect feedback; calibrate thresholds on real data.
- **Accept:** benchmark PDF exists with CIs; pilot satisfaction ≥ 4/5 from faculty; zero corrupted output files across pilot.

## Phase 6 — Stage-2 server + college-wide rollout
- Build server per doc 01; nightly batch ingestion (S2ORC/PMC slices if relevant); faculty dashboard (archive growth, per-department stats); maintainer handover doc written by the team; SIH submission.
- **Accept:** 200 documents processed overnight unattended; handover doc executed by a non-author junior successfully.

## Risk register (top 5)

| Risk | Mitigation |
|---|---|
| Python/lib version churn (3.14 wheels) | Pin venv to 3.11/3.12; lock `requirements.txt` |
| LLM judge inconsistency | JSON forcing + retry + "unsure" default (doc 05) |
| False accusation incident | Indicator-not-verdict design (doc 04) + ESL FPR target + faculty explainer P6 |
| College says no to Stage 2 | Pilot data (doc 08 report) + cost table (doc 09) — evidence beats requests |
| Corpus bloat on laptop | Abstracts+fingerprint-only strategy (docs 01, 07); full text cached on demand |
