# Architecture Blueprint

Target: single-college deployment, fully local, pilot on one laptop, later one server.

---

## System overview

```
┌─────────────────────────────── Your existing UI (liquid glass) ───────────────────────────────┐
│   Upload DOCX/PPTX/PDF  →  live progress  →  report view  →  coach/cite actions  →  export    │
└──────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                               │ HTTP (FastAPI, localhost / LAN)
┌──────────────────────────────────────────────▼────────────────────────────────────────────────┐
│ BACKEND (FastAPI + background queue)                                                          │
│                                                                                               │
│  1. INGEST      extract text + structure (python-docx / python-pptx / PyMuPDF for PDF input)  │
│  2. SEGMENT     split into sentences / paragraphs; strip references + quoted blocks           │
│  3. ENGINE A    similarity (no LLM):                                                          │
│                    a) winnowing fingerprints  →  MinHash-LSH candidate sources                 │
│                    b) exact fingerprint verification → matched spans with positions            │
│                    c) embedding search (bge-m3) for paraphrase-level similarity                 │
│                    d) optional external check (OpenAlex fingerprints; full text fetched        │
│                       only for suspected matches)                                              │
│  4. ENGINE B    AI-indicator cascade:                                                         │
│                    stage 1: perplexity + burstiness (0.6B model, cheap, every segment)         │
│                    stage 2: Qwen 3 8B judge — only on suspicious segments (JSON verdict)       │
│                    stage 3 (optional): Binoculars-style whole-document score                   │
│  5. REPORT      merge → per-segment highlights, matched sources, %, UGC level, exclusions     │
│  6. ACTIONS     Coach mode / Cite-assist (prompts doc 05) → human edits, or in-place rewrite   │
│                 of flagged text in DOCX/PPTX preserving ALL formatting (doc 06)                │
│  7. ARCHIVE     store submission fingerprint + text + embeddings → the college moat           │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Repo layout (create this and give it to Antigravity)

```
bi-plagiarism/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, endpoints below
│   │   ├── queue.py             # simple job queue (RQ+Redis later; asyncio queue for pilot)
│   │   └── settings.py          # paths, thresholds, model names — ALL knobs in one file
│   ├── ingest/
│   │   ├── docx_reader.py       # paragraphs, tables, headers/footers → segments w/ locations
│   │   ├── pptx_reader.py       # slides, shapes, tables, notes → segments w/ locations
│   │   ├── pdf_reader.py        # PyMuPDF text extraction; flag "no text layer → needs OCR"
│   │   └── segmenter.py         # sentence/paragraph splitting; reference & quote stripping
│   ├── engines/
│   │   ├── fingerprint.py       # ← adapt from code/fingerprint.py
│   │   ├── minhash_index.py     # ← adapt from code/minhash_index.py
│   │   ├── embedding_index.py   # ← adapt from code/embedding_index.py
│   │   ├── perplexity.py        # ← adapt from code/perplexity_burstiness.py
│   │   ├── llm_judge.py         # Ollama client + prompts from doc 05
│   │   └── cascade.py           # orchestrates stage1 → stage2 → (optional) stage3
│   ├── rewrite/
│   │   ├── docx_editor.py       # ← adapt from code/docx_inplace.py
│   │   ├── pptx_editor.py       # ← adapt from code/pptx_inplace.py
│   │   └── edit_log.py          # every change recorded → AI-use disclosure log (doc 11)
│   ├── report/
│   │   ├── build_report.py      # JSON report model below
│   │   └── ugc_levels.py        # similarity % → UGC 2018 level 0–3 + suggested action
│   └── archive/
│       └── store.py             # add submission to local corpus
├── indexes/                     # faiss.index, lsh.pkl, catalog.db (SQLite), NOT in git
├── data/raw/  data/cache/       # originals; cached external full text
├── evaluation/                  # doc 08: datasets, scripts, results
├── docs/                        # this folder
└── code/                        # reference implementations
```

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/check` | Upload file → job id. Params: `exclude_quotes`, `exclude_references`, `min_match_words` (default 8), `web_check` (default false) |
| GET | `/api/check/{job_id}` | Progress (ingest 10% → engine A 40% → engine B 70% → report 100%) |
| GET | `/api/report/{job_id}` | Full JSON report |
| POST | `/api/coach/{job_id}` | Coach-mode guidance for one flagged segment (doc 05 prompt) |
| POST | `/api/cite/{job_id}` | Cite-assist for one flagged segment + matched source |
| POST | `/api/rewrite` | Apply replacements in place (DOCX/PPTX), returns edited file + edit log |
| GET | `/api/archive/stats` | Corpus size, growth chart data (for the college dashboard) |

## Report JSON model (what the UI consumes)

```json
{
  "document": {"name": "thesis.docx", "words": 8420, "format": "docx"},
  "similarity": {
    "percent": 17.4,
    "percent_after_exclusions": 12.1,
    "ugc_level": 1,
    "ugc_note": "10–40%: revise and resubmit (UGC 2018, Level 1)",
    "sources": [
      {"source_id": "oa:W276…", "title": "…", "url": "https://doi.org/…",
       "matched_words": 214, "spans": [{"start": 1120, "end": 1334, "excerpt": "…", "source_excerpt": "…"}]}
    ],
    "exclusions_applied": {"quotes": 41, "references": 18, "small_matches_lt_8_words": 9}
  },
  "ai_indicator": {
    "document_band": "unclear",
    "note": "Indicator only — for human review, not a verdict.",
    "segments": [
      {"span": [500, 980], "perplexity": 3.1, "burstiness": 0.18,
       "judge_verdict": {"ai_likelihood": 0.83, "signals": ["uniform sentence length", "generic hedging"], "confidence": "medium"},
       "excerpt": "…"}
    ]
  },
  "edit_log_ref": "editlog_2026-10-26_001.json"
}
```

## Database schema (SQLite `catalog.db`)

```sql
CREATE TABLE documents(          -- everything ever checked or ingested
  id INTEGER PRIMARY KEY, kind TEXT CHECK(kind IN ('submission','source')),
  title TEXT, authors TEXT, year INTEGER, url TEXT, doi TEXT,
  file_path TEXT, word_count INTEGER, added_at TEXT);
CREATE TABLE segments(
  id INTEGER PRIMARY KEY, document_id INTEGER REFERENCES documents(id),
  seq INTEGER, text TEXT, word_count INTEGER, is_reference INTEGER DEFAULT 0, is_quote INTEGER DEFAULT 0);
CREATE TABLE fingerprints(       -- winnowing fingerprints (hash, position) per document
  document_id INTEGER, hash INTEGER, pos INTEGER);           -- ~1 row per ~60–100 words
CREATE TABLE minhash(            -- 128 uint32 signatures per document (25 KB/paper)
  document_id INTEGER, perm INTEGER, value INTEGER);
CREATE TABLE embeddings_meta(    -- vector rows live in faiss.index; this maps row → segment
  rowid INTEGER PRIMARY KEY, segment_id INTEGER);
CREATE TABLE checks(
  id INTEGER PRIMARY KEY, document_id INTEGER, checked_at TEXT,
  similarity_percent REAL, ai_band TEXT, report_path TEXT);
```

## Model roster (Ollama names)

| Role | Model | Size | When |
|---|---|---|---|
| Embeddings | `bge-m3` | ~1.2 GB | every segment, all the time |
| Stat detector | Qwen3-0.6B via transformers (needs logprobs — Ollama doesn't expose them) | ~1.5 GB | stage 1 |
| Judge | `qwen3:8b` Q4_K_M | ~5.5 GB | stage 2, suspicious segments only |
| Deep judge (batch/overnight) | your 30B-A3B GGUF | ~10.7 GB | optional quality pass |
| Judge on strong server | `qwen3:14b` | ~9 GB | when 16 GB VRAM available |

## Non-functional requirements

- **Privacy:** no document text leaves the machine. External check sends short query snippets only; `web_check=false` = fully offline.
- **Speed targets (pilot laptop):** DOCX ≤ 8,000 words: ingest < 5 s; similarity vs 5M-doc index < 30 s; stage 1 < 30 s; stage 2 only on flagged ~10% of segments ≈ 1–2 min.
- **Determinism:** all thresholds in `settings.py`; same file + same thresholds = same report.
- **Auditability:** every report reproducible; every rewrite logged (doc 11 edit log).
