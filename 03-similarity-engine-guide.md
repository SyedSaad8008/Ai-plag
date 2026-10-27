# Engine A — Similarity Detection (no LLM needed)

The single biggest upgrade to your current tool: plagiarism/similarity detection does NOT need an LLM. Fingerprints are instant, exact, and scale to millions of documents. Reference implementation: `code/fingerprint.py`, `code/minhash_index.py`, `code/embedding_index.py`.

---

## Why fingerprints and not your Qwen models

An LLM "checking against a database" is slow (seconds per comparison), misses exact matches (it paraphrases what it reads — terrible for this job), and can't prove where a match is. Fingerprint matching is O(1) per lookup, exact, and gives you span positions for the report. Turnitin-style systems are built on exactly this (winnowing — Schleimer, Wilkerson & Aiken, Stanford, SIGMOD 2003, cited 2,000+ times).

## The pipeline

```
text → tokenize → k-gram hashing → winnowing → document fingerprint (small!)
                                                     │
        ┌────────────────────────────────────────────┘
        ▼
   MinHash-LSH index (candidate sources, sublinear query)
        ▼
   exact verification: which k-gram hashes overlap, WHERE → matched spans
        ▼
   (parallel) embedding search for paraphrase-level similarity
        ▼
   exclusions (quotes / references / <8-word matches) → report
```

## Step 1 — Winnowing fingerprints (`code/fingerprint.py`)

1. Tokenize: lowercase, keep `[a-z0-9]+`. Chinese/Hindi/Indic text: use the same on whitespace-split tokens — parameters stay tunable.
2. Hash every **k-gram** (k consecutive words) to a 64-bit integer (BLAKE2b — cryptographic, no collisions in practice).
3. Slide a **window of w hashes**; keep the minimum hash per window (rightmost on ties). Those selected (position, hash) pairs are the document's fingerprint.

**The guarantee you can put in your report:** any passage of **≥ k + w − 1 words** shared between two documents is *guaranteed* to produce at least one shared fingerprint — it cannot be missed. Recommended settings:

| Mode | k | w | Guaranteed detection of | Fingerprint size |
|---|---|---|---|---|
| Sensitive (default) | 5 | 4 | ≥ 8 words | ~1 hash / 5 words → ~60–100 KB per 8k-word doc |
| Balanced | 7 | 4 | ≥ 10 words | ~40% smaller |
| Strict (fear of false positives) | 9 | 4 | ≥ 12 words | smallest |

Align the default with Turnitin's familiar "exclude matches < 8 words" convention: k=5, w=4.

## Step 2 — Candidate retrieval with MinHash-LSH (`code/minhash_index.py`)

Comparing one submission against 5M papers fingerprint-to-fingerprint is too much brute force. Use datasketch:

- **Chunk both sides** (~120-word windows, 90-word stride) and index *chunks*, not whole documents — otherwise a 150-word copy inside an 8,000-word thesis is diluted to invisibility by Jaccard math. This was found empirically during the reference implementation's self-test (`code/minhash_index.py`).
- Per chunk: 128 MinHash permutations over word-5-gram shingles → 512 B per chunk (~30–40 KB per 8k-word document; ~1 KB per abstract).
- `MinHashLSH(threshold=0.4, num_perm=128)` — deliberately LOW: LSH is only a candidate generator (recall-oriented); exact verification happens next. Never report LSH output directly.

## Step 3 — Exact verification + span localization

For each candidate source: intersect fingerprint hashes → aligned token positions (i in submission, j in source) → **chain** consecutive alignments (allow gaps ≤ 3k words) into spans → keep spans ≥ `min_match_words` (default 8). Output per span: submission excerpt, source excerpt, positions, word count. This is what makes your report feel Turnitin-grade: it *shows* the copied passage next to the source passage.

Similarity % = matched words (after exclusions) / total words. Also compute **containment** = matched / submission length (the right metric when a 300-word chunk is copied into a 8,000-word thesis — Jaccard would dilute it).

## Step 4 — Paraphrase-level (semantic) similarity with embeddings

Fingerprints catch verbatim and light-edit copying. For heavily paraphrased plagiarism:

- Chunk both submission and indexed sources into ~1–3 sentence windows (40–80 words, slight overlap).
- Embed with `bge-m3` via Ollama (1024-dim, multilingual, ~1.2 GB VRAM). Normalize vectors.
- Index in FAISS (`IndexFlatIP` pilot; `IndexIVF`/`IndexHNSW` past ~1M chunks; `IndexScalarQuantizer` int8 to cut memory 4×).
- Threshold: cosine ≥ 0.75 flags "possible paraphrase", ≥ 0.85 "strong". Calibrate on your labeled set (doc 08) — never hardcode a number you didn't measure.
- Report semantic matches in a separate section labeled "paraphrase-similarity (needs human review)" — different evidence standard than verbatim matches. This honest labeling is something even Turnitin users complain the original doesn't do well.

## Step 5 — Exclusions (report quality lives here)

Apply in order, and **report what was excluded** (Turnitin parity):

1. **References section**: detect headings ("References", "Bibliography", "bibliografie"...) plus IEEE/numbered-citation line patterns → mark segments `is_reference=1`.
2. **Quoted material**: text in quotation marks > 10 words, or block-indent style — mark `is_quote=1`. (Perfect quote detection is impossible; be transparent that it's heuristic.)
3. **Small matches**: drop spans < 8 words (default; UI-tunable).
4. **Recurring/pattern text**: institutional templates, running headers, assignment question text — maintain a small whitelist per department.

## Step 6 — The external corpus strategy ("big like Turnitin, tiny like your SSD")

Store for external papers: metadata + abstract + MinHash + (optionally) abstract embedding. Full text is **fetched on demand only for suspected matches** (OpenAlex gives the open-access URL; cache it in `data/cache/`). Two effects: your index covers millions of papers in ~40 GB, and the "suspicion → fetch → verify" loop is exactly how you keep precision high.

For abstract-level fingerprints: abstracts are short (~150–250 words), so k=5/w=4 fingerprints of an abstract are ~40 hashes — ideal for LSH. Verbatim copying of full text shows up as abstract-overlap often enough to catch the paper, then the fetch verifies the real extent.

## Self-plagiarism / cross-batch checking (the archive moat)

Every submission gets fingerprinted and indexed the moment it's checked. Next semester's submission is automatically compared against every past one. Within 2–3 years your college has something no free online tool offers: a private, growing, campus-owned corpus. Make `/api/archive/stats` a dashboard widget — it's your best demo moment.

## Performance notes

- Fingerprinting 8,000 words: < 1 s in pure Python (see `code/fingerprint.py` — no numpy needed).
- LSH query: milliseconds per candidate bucket; verify only candidates.
- Batch mode: fingerprint + MinHash ingestion is CPU-bound → run overnight for the college's back-catalog (a few ms per document × thousands = under an hour).
