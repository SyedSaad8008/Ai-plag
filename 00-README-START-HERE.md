# BI Plagiarism — Complete Project Research Kit

Built for: a free, private, college-owned alternative to Turnitin for your college.
Prepared: October 2026. Everything in this folder is research + specifications + reference code.

---

## What this kit contains

| File | What it is | Read when |
|---|---|---|
| `01-hardware-and-storage-proposal.md` | Exact RAM / VRAM / storage to ask the college for, with prices and a staged approval strategy | Before asking for permission |
| `02-architecture-blueprint.md` | Full system design: modules, data flow, database schema, API endpoints, repo layout | Before writing any code |
| `03-similarity-engine-guide.md` | Deep dive on plagiarism detection WITHOUT an LLM: winnowing fingerprints, MinHash/LSH, embeddings, match localization | Phase 1 |
| `04-ai-detection-guide.md` | The 3-stage AI-writing detection cascade (perplexity → LLM judge → Binoculars-style), thresholds, honest limits | Phase 3 |
| `05-prompt-library.md` | Ready-to-paste prompts for Qwen 3 8B/14B (judge, coach mode, cite-assist, disclosure log) | Phase 3–4 |
| `06-docx-pptx-pipeline.md` | How to edit DOCX/PPTX **in place without destroying formatting**, and why PDF becomes input-only | Phase 4 |
| `07-data-sources-playbook.md` | Every free legal source of research papers (OpenAlex, PMC, S2ORC, arXiv, Shodhganga, CORE) with exact access steps + storage budget | Phase 2 |
| `08-evaluation-benchmark-plan.md` | How to prove your tool works: labeled test sets, metrics, baselines, target numbers | Phase 5 (but design for it from day 1) |
| `09-college-pitch-pack.md` | One-page pitch, cost tables, UGC 2018 compliance mapping, faculty FAQ, 5-minute demo script | When you present |
| `10-roadmap-and-build-order.md` | 6 phases with acceptance criteria — what to build in what order | Now |
| `11-ethics-and-product-positioning.md` | Why "no humanizer" is the winning strategy, and the 3 features that replace it | Before pitching to anyone |
| `code/` | Working reference implementations of the hard parts (fingerprinting, MinHash index, run-level DOCX/PPTX editing, OpenAlex ingest, perplexity scoring) | Copy into your repo |

## How to use this with Antigravity

1. Create a repo `bi-plagiarism/` with the layout in `02-architecture-blueprint.md`.
2. Copy `docs/` (this folder) and `code/` into the repo so the agent can read them as context.
3. Work phase by phase using `10-roadmap-and-build-order.md`. For each phase, tell the agent:
   > "Read docs/02-architecture-blueprint.md, docs/03-similarity-engine-guide.md and code/fingerprint.py.
   > Implement Phase 1 per docs/10-roadmap-and-build-order.md. Acceptance criteria are listed there."
4. Reference code in `code/` is meant to be *studied and adapted*, not blindly shipped — test it on your own documents.

## The 7 key decisions (already made, with reasons)

1. **Two engines, separated.** Similarity = fingerprints + embeddings (no LLM, instant, exact). AI-indicator = a cheap statistical pass + Qwen as judge. Never mix them.
2. **Storage ask: 1 TB NVMe + 1–2 TB backup.** ~₹10,000 one-time. You store fingerprints and abstracts of millions of external papers, and full text only on demand (details in 01 and 07).
3. **Your college's own submission archive is the moat.** Every semester it grows; that's what Turnitin has that you can replicate campus-by-campus.
4. **PDF is input-only.** Read PDFs (easy), never edit them. Official flow: PDF → converted DOCX → report + edits in DOCX. Output formats: DOCX and PPTX only.
5. **AI score is an indicator with highlighted evidence, never a verdict.** 50+ universities (Vanderbilt, MIT, Yale...) disabled Turnitin's AI detector over false positives. "Human-review-first" is both safer and more defensible — it's a feature, not a compromise.
6. **No "humanizer" feature.** It would get the tool blocked from official adoption and it's the one part that creates the problem it claims to solve. Replacements: Coach mode, Cite-assist, AI-use disclosure log (see 11).
7. **Everything local by default.** Ollama + local embeddings (`bge-m3`) + SQLite + FAISS/LSH on disk. Nothing leaves campus. Optional "web check" sends only short query snippets, and can be switched off.

## One technical warning before you start

Your laptop runs Python 3.14 — some libraries (`faiss-cpu`, `transformers`) may not have wheels for it yet. Make your project virtual environment with **Python 3.11 or 3.12** (`py -3.12 -m venv .venv`) if an install fails. This is noted again in `code/requirements.txt`.
