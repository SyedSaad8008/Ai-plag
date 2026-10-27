"""
Semantic (paraphrase-level) similarity via Ollama bge-m3 embeddings — reference.

Catches reworded plagiarism that exact fingerprints miss. Report its results in
a separate, clearly-labeled section: "paraphrase-similarity — needs human review".

Requires: Ollama running with `ollama pull bge-m3`  (1024-dim, multilingual).
numpy only by default; FAISS optional past ~1M chunks (see INDEX note at bottom).
Run `python embedding_index.py` for the self-test (requires Ollama + bge-m3).
"""
from __future__ import annotations

import re

import numpy as np
import requests

OLLAMA = "http://localhost:11434"
MODEL = "bge-m3"
DIMS = 1024
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# bge-m3 cosine bands (VERIFY on your own labeled set per docs/08 before shipping):
#   >= 0.85 strong paraphrase match, 0.75-0.85 possible, < 0.75 ignore.
STRONG = 0.85
POSSIBLE = 0.75


def chunk_sentences(text: str, max_words: int = 60, min_words: int = 12) -> list[str]:
    """Sliding window of 1-3 sentences, ~60 words, 1-sentence overlap."""
    sents = [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]
    chunks, cur, cur_w = [], [], 0
    for s in sents:
        w = len(s.split())
        if cur and cur_w + w > max_words:
            chunks.append(" ".join(cur))
            cur, cur_w = cur[-1:], 0  # 1-sentence overlap
        cur.append(s)
        cur_w += w
    if cur:
        last = " ".join(cur)
        if len(last.split()) >= min_words:
            chunks.append(last)
        elif chunks:
            chunks[-1] += " " + last
    return chunks


def embed(texts: list[str], base: str = OLLAMA, model: str = MODEL) -> np.ndarray:
    """L2-normalized embeddings, shape (len(texts), 1024). Batched HTTP call."""
    r = requests.post(f"{base}/api/embed", json={"model": model, "input": texts}, timeout=600)
    r.raise_for_status()
    embs = np.asarray(r.json()["embeddings"], dtype=np.float32)
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    return embs / np.maximum(norms, 1e-9)


class EmbeddingIndex:
    """Brute-force cosine over a numpy matrix. 1M chunks * 1024 dims * fp16
    = 2 GB — fine. For >2M, switch to faiss.IndexHNSWFlat + IndexScalarQuantizer
    int8 (same interface)."""

    def __init__(self):
        self.matrix = np.zeros((0, DIMS), dtype=np.float32)
        self.meta: list[dict] = []  # {"doc_id", "chunk_id", "start_char", "text"}

    def add_document(self, doc_id: str, text: str, batch: int = 32) -> int:
        chunks = chunk_sentences(text)
        added = 0
        for i in range(0, len(chunks), batch):
            part = chunks[i : i + batch]
            vecs = embed(part)
            self.matrix = np.vstack([self.matrix, vecs]) if len(self.matrix) else vecs
            for j, c in enumerate(part):
                self.meta.append(
                    {"doc_id": doc_id, "chunk_id": i + j, "start_char": text.find(c[:40]), "text": c}
                )
            added += len(part)
        return added

    def search(self, query_text: str, top_k: int = 5) -> list[dict]:
        if not len(self.meta):
            return []
        q = embed([query_text])[0]
        scores = self.matrix @ q  # cosine (all unit vectors)
        order = np.argsort(-scores)[:top_k]
        return [{**self.meta[i], "score": round(float(scores[i]), 4)} for i in order]

    def check_document(self, text: str, top_k: int = 3) -> list[dict]:
        """Per-chunk search; keep chunks above POSSIBLE. Human-review list."""
        out = []
        for c in chunk_sentences(text):
            for hit in self.search(c, top_k):
                if hit["score"] >= POSSIBLE:
                    out.append({"query_chunk": c, **hit})
        return sorted(out, key=lambda h: -h["score"])


# ---------------------------------------------------------------------------
# Self-test: `python embedding_index.py`  (needs Ollama + bge-m3 running)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    source = (
        "Photovoltaic microgrids in rural India experience severe morning load spikes. "
        "This work introduces an adaptive droop control law whose coefficients are tuned "
        "by an online estimator, cutting bus-voltage deviation by 34 percent in field trials. "
        "Compared with fixed droop, the adaptive law maintains frequency within 0.2 Hz under "
        "step load changes without communication between inverters."
    )
    paraphrased = (
        "Morning demand surges destabilize village solar microgrids across India. "
        "We propose a self-tuning droop mechanism that adjusts its gains in real time; "
        "voltage excursions fell by roughly one third during two village deployments, and "
        "frequency stayed inside a 0.2 Hz band even during load steps, with no inter-inverter "
        "signaling required."
    )
    unrelated = (
        "Enzyme activity was quantified spectrophotometrically at 540 nm following saline "
        "stress treatments, and germination data were arc-sine transformed before ANOVA."
    )

    idx = EmbeddingIndex()
    n = idx.add_document("source1", source)
    hits = idx.search(paraphrased, top_k=1)
    assert hits and hits[0]["score"] >= POSSIBLE, f"paraphrase missed: {hits}"
    miss = idx.search(unrelated, top_k=1)
    assert not miss or miss[0]["score"] < POSSIBLE, f"false paraphrase: {miss}"
    print("embedding_index.py self-test passed")
    print(f"  indexed {n} chunks; paraphrase score {hits[0]['score']} (>= {POSSIBLE}); "
          f"unrelated {miss[0]['score'] if miss else 'n/a'}")

# INDEX NOTE (production): pip install faiss-cpu  (Python 3.11/3.12 venv!)
#   import faiss
#   index = faiss.IndexHNSWFlat(DIMS, 32)   # then add(); search(q, k)
#   int8 storage: faiss.IndexScalarQuantizer(index, DIMS, faiss.QT_8, faiss.METRIC_INNER_PRODUCT)
