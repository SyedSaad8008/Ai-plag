# Hardware & Storage Proposal (what to ask the college for)

Purpose: a ready-to-submit spec. Present Stage 1 first (cheap, fast yes), then Stage 2 after the pilot demo. Staged asks get approved far more often than one big ask.

---

## The one-line ask (Stage 1 — prove it on existing hardware)

> "One external SSD of 1 TB and one 2 TB backup drive — about ₹10,000 one-time — to run a free, private plagiarism-checking system for our college, replacing a ₹5,00,000/year subscription."

## Stage 2 ask (department/institute server) — after the pilot demo

A desktop that runs everything for the whole campus:

| Component | Spec | Approx. price (₹) |
|---|---|---|
| CPU | Ryzen 5 7600 or Intel i5-13400 | 15,000–18,000 |
| Motherboard | B650 / B760 | 12,000–15,000 |
| RAM | **32 GB DDR5-5600** (2×16) | 7,000–9,000 |
| GPU | **RTX 4060 Ti 16 GB** (ideal) or RTX 3060 12 GB (budget) | 48,000–55,000 / 28,000–32,000 |
| Storage | **1 TB NVMe Gen4 SSD** (system + indexes) | 5,500–7,000 |
| Backup | 2 TB HDD/SSD (submission archive backups) | 4,500–9,000 |
| PSU | 650 W 80+ Bronze | 4,500–6,000 |
| Case + cooler | — | 4,000–5,000 |
| **Total** | with RTX 4060 Ti 16 GB ≈ **₹1.0–1.2 lakh**; with RTX 3060 12 GB ≈ **₹80–95k** | |

Running cost: ~₹400–600/month electricity if on 8 h/day. Compare: Turnitin ₹5,00,000 **per year**.

## The exact RAM / VRAM / storage numbers (put these in the requisition)

| Resource | Minimum | Recommended | Why |
|---|---|---|---|
| Storage | 500 GB free | **1 TB NVMe + 2 TB backup** | 20–30 GB college archive, 30–50 GB external fingerprint index (5M abstracts, no full text), headroom for indexes/caches |
| RAM | 16 GB | **32 GB** | MinHash/LSH index for millions of papers (~2–4 GB resident), SQLite page cache, OS, Ollama model residency, overnight batch jobs |
| VRAM | 8 GB | **12–16 GB** | 8 GB = Qwen3 8B Q4 (~5.5 GB) + bge-m3 embeddings (~1.2 GB) run one-after-another; 16 GB = 14B at higher quant + everything resident simultaneously, whole-department batches in one night |
| Network | none required | LAN | Entirely local; internet only for optional external-corpus checks and updates |

## What runs where (VRAM budget, your existing machines)

**Pilot laptop (8 GB VRAM / 16 GB DDR5-5600):**
- bge-m3 embeddings: ~1.2 GB VRAM (or CPU-only, just slower)
- Qwen3 0.6B (perplexity stage): ~1.5 GB
- Qwen3 8B Q4_K_M (judge stage): ~5.5 GB
- These three do NOT fit in 8 GB at once — run them as a **pipeline, one stage at a time** (that's exactly what the cascade design in doc 04 does), or keep the 0.6B on CPU.
- Qwen3 14B / the 30B-A3B (10.7 GB GGUF): partial CPU offload. The 30B-A3B MoE stays usable because only ~3B parameters are active per token — good for overnight batch quality, not for interactive use.

**Stage-2 server (16 GB VRAM):** 14B Q5/Q6 fully resident + embeddings concurrently; a department's weekly submissions processed overnight unattended.

## Storage budget detail (justification if someone asks "why 1 TB?")

| Item | Count | Size each | Total |
|---|---|---|---|
| Student/faculty submissions (10 years) | 15,000 docs | 0.5–2 MB | 15–30 GB |
| Extracted plain text of all of the above | 15,000 | 40–80 KB | ~1 GB |
| Fingerprint + embedding index of the above | 15,000 | ~75–275 KB | 1–4 GB |
| External abstracts + fingerprints (OpenAlex subset) | 5,000,000 | ~7–10 KB | 35–50 GB |
| Cached full text of matched sources only | growing | ~1 MB | <10 GB |
| SQLite DBs, FAISS/LSH files, logs, backups staging | — | — | 50–100 GB |
| **Total working set** | | | **~120–200 GB** → 1 TB gives 5× headroom |

## Answers to predictable objections

- **"Why not just use free online tools?"** Student work would be uploaded to unknown foreign servers (privacy + data-theft risk); per-check charges of ₹100–150 are unregulated; no college-owned archive; no UGC-2018 level mapping. (Full FAQ in doc 09.)
- **"Why not just buy Turnitin?"** ₹5,00,000/year, forever. This system: ₹1.1 lakh once, owned by the college, archive grows in value every year. (Full cost table in doc 09.)
- **"Can a student project really do this?"** The similarity engine uses the same published algorithm family Turnitin-style systems use (winnowing fingerprinting, Stanford SIGMOD 2003 — cited 2,000+ times). The reference implementation is in `code/fingerprint.py`. Evaluation targets are in doc 08.
- **"Who maintains it?"** That's the point of Stage 2 — a college-owned machine the team administers; docs 02 + 10 make it handover-ready.
