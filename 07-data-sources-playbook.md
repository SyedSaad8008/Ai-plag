# Data Sources Playbook (free, legal, and how exactly to get them)

All sources below are free and legal. Rule of thumb: **abstracts + fingerprints at scale (cheap), full text on demand (cached).** Ingest reference: `code/openalex_ingest.py`.

---

## 1. OpenAlex — your primary index (250M+ works, CC0, no API key)

- What: metadata + abstracts (as inverted indexes) for essentially all indexed research; CC0 license; free API with a polite-pool (add `mailto=` to requests); full data snapshot on AWS S3 (`s3://openalex`, anonymous access) if you ever want bulk.
- College strategy: pull **your disciplines only**, 2010→present. A department's relevant slice is typically 0.5–5M works.
- Example pull (works about education, filtered, cursor-paginated):
  ```
  https://api.openalex.org/works?filter=from_publication_date:2010-01-01,primary_topic.field.id:fields/17&per-page=200&cursor=*&mailto=you@college.ac.in
  ```
  (fields/17 = Computer Science; swap the field id per department. Store: `id, title, doi, publication_year, abstract_inverted_index, open_access.oa_url, primary_location.source.display_name`.)
- Reconstruct abstracts from the inverted index (code in `code/openalex_ingest.py::abstract_from_inverted`).
- Rate limits: ~10 req/s polite pool. 5M abstracts ≈ 25k requests ≈ ~1.5–3 h, one time. Fingerprint + MinHash each as they arrive (adds ~1 ms each).
- Also: OpenAlex now offers a fulltext product (~65M OA PDFs with license info) — ignore for now; fetch-on-demand covers you.

## 2. Shodhganga — the Indian-theses goldmine (600,000+ theses, free)

- What: UGC's national e-theses repository (INFLIBNET) — **600k+ full-text Indian PhD theses, ~12,000 added per year**. This is the single most relevant plagiarism source for an Indian college: retired theses from your own field, and often from nearby universities.
- Access: no bulk API — browse by university/department and download per thesis (PDF). Strategy: pick your department + 10 related universities, fetch the last 10 years selectively (a few hundred GB if unchecked — cap at abstracts + first chapters, or extract text and store only that).
- Extract with PyMuPDF → segment → fingerprint + MinHash → archive index. Originals optional (store text, save disk).

## 3. PubMed Central Open Access — free bulk full text

- What: millions of full-text biomedical articles, XML, bulk FTP — the only truly *bulk full-text* source on this list.
- Where: `https://www.ncbi.nlm.nih.gov/pmc/tools/openftlist/` → `oa_bulk` folders (oa_comm = commercial-use OK). ~30–50 GB compressed.
- Use if your college has life-sciences departments; otherwise skip (biomed abstracts are already in OpenAlex).

## 4. S2ORC (Semantic Scholar) — 8.1M parsed full texts

- What: structured full text (sections, citations) for ~8.1M open-access papers + metadata for 100M+. Free after a one-page license agreement (research use).
- Where: `github.com/allenai/s2orc` → license form → download (hosted in chunks on HuggingFace).
- Use when: you want full-text fingerprints of a broad slice without per-paper fetching. Start with `metadata` + full text of your discipline's slice only.

## 5. arXiv — CS/engineering/physics

- API: `http://export.arxiv.org/api/query?search_query=cat:cs.CL&max_results=200` (Atom XML, includes abstracts; polite rate 1 req/3 s).
- Bulk: Kaggle arXiv dataset (~2M papers metadata+abstracts) or the official S3 requester-pays bucket.
- Perfect for engineering colleges; abstracts are fingerprint-friendly.

## 6. CORE / Unpaywall / DOAJ — the fetch-on-demand layer

- **Unpaywall** (`api.unpaywall.org/v2/DOI?email=…`): given a DOI, returns the legal free-PDF URL. This is your fetch-on-demand resolver for matched sources.
- **CORE** (`core.ac.uk`, free API key): 200M+ OA works aggregator, full-text search — fallback when OpenAlex lacks an OA link.
- **DOAJ**: directory of OA journals — useful for checking whether a suspect journal itself is indexed (predatory-venue hint in reports is a bonus feature nobody expects).

## 7. The college's own archive (priority zero)

Past question papers, lab manuals, project reports, previous theses, faculty publications (faculty CVs are the fastest source). This costs nothing, is legally yours, and is the corpus that actually catches your students' real self-plagiarism. Digitize the paper era with a scanner + OCR if budget allows (comes under the ₹10k ask: many colleges have a scanner already).

---

## Storage plan for all of the above (fits the 1 TB ask)

| Source | What you store | Size |
|---|---|---|
| OpenAlex discipline slice (5M) | metadata + abstract + MinHash + abstract embedding (int8) | ~35–50 GB |
| Shodhganga (selective, 2–5k theses) | extracted text + fingerprints (+ PDFs optional) | 5–50 GB |
| PMC OA (optional) | XML full text + fingerprints | 40–80 GB |
| S2ORC slice (optional) | full text JSONL slice + fingerprints | 50–200 GB |
| College archive (10 yrs) | files + text + fingerprints + embeddings | 20–30 GB |
| Cached fetched full texts, logs, indexes | grows slowly | <50 GB |
| **Total** | | **~150–450 GB** — comfortable on 1 TB |

## Privacy rules (write these into the college proposal)

1. Student submissions NEVER leave the machine. Ever. (This is a selling point over ₹100-150/report online tools AND over Turnitin, which retains submissions in its global corpus.)
2. External checking sends only short text snippets (candidate n-grams) or DOIs/titles to OpenAlex/Unpaywall/Crossref — never the document, never embeddings of student text.
3. `web_check=false` mode = fully air-gapped operation for sensitive theses.
4. Publicize rule 1 in the UI ("Your document never leaves this computer") — it will win over faculty instantly.

## Ingest order (what to build first)

1. College archive (free, immediate, highest real-world hit rate)
2. OpenAlex discipline slice (one overnight script)
3. Shodhganga department slice (script + patience)
4. arXiv (if engineering)
5. S2ORC/PMC (only when the server exists)
