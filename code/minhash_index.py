"""
MinHash-LSH corpus index with exact fingerprint verification — reference.

Design (see docs/03-similarity-engine-guide.md):
  * Documents AND queries are chunked (~120-word windows, 90-word stride) and
    MATCHED AT CHUNK LEVEL, so a short copied passage is not diluted by Jaccard
    over whole long documents.
  * The LSH threshold is deliberately LOW (0.4): MinHashLSH is only a
    CANDIDATE generator (recall-oriented). Exact verification + span
    localization comes from fingerprint.match_spans — LSH output is NEVER
    reported directly.

Requires: pip install datasketch
Run `python minhash_index.py` for the self-test (in-memory corpus).
Adapt into bi-plagiarism/backend/engines/minhash_index.py, persisting
signatures + chunk texts in SQLite (schema in docs/02-architecture-blueprint.md).
"""
from __future__ import annotations

import os
import tempfile

from datasketch import MinHash, MinHashLSH

from fingerprint import K, W, fingerprint, match_spans, tokenize

NUM_PERM = 128
CHUNK_WORDS = 120
CHUNK_STRIDE = 90
LSH_THRESHOLD = 0.4
MERGE_GAP = 10  # tokens between spans still considered one passage


def chunk_tokens(tokens: list[str], size: int = CHUNK_WORDS, stride: int = CHUNK_STRIDE):
    """Yield (start_offset, tokens_window). Short docs = one chunk."""
    if len(tokens) == 0:
        return
    if len(tokens) <= size:
        yield 0, tokens
        return
    for s in range(0, len(tokens) - size + 1, stride):
        yield s, tokens[s : s + size]
    if (len(tokens) - size) % stride != 0:
        yield len(tokens) - size, tokens[-size:]


def chunk_minhash(tokens: list[str], k: int = K, num_perm: int = NUM_PERM) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for i in range(len(tokens) - k + 1):
        m.update(" ".join(tokens[i : i + k]).encode("utf-8"))
    return m


class CorpusIndex:
    """In-memory reference implementation. Production: reload signatures from
    SQLite on boot; keep the same interface."""

    def __init__(self, threshold: float = LSH_THRESHOLD):
        self.lsh = MinHashLSH(threshold=threshold, num_perm=NUM_PERM)
        self.chunks: dict[str, list] = {}  # key -> (doc_id, start, tokens)
        self.doc_words: dict[str, int] = {}

    def add(self, doc_id: str, text: str) -> int:
        tokens = tokenize(text)
        self.doc_words[doc_id] = len(tokens)
        n = 0
        for ci, (start, ctoks) in enumerate(chunk_tokens(tokens)):
            key = f"{doc_id}:{ci}"
            m = chunk_minhash(ctoks)
            self.lsh.insert(key, m)
            self.chunks[key] = (doc_id, start, ctoks)
            n += 1
        return n

    def check(self, text: str, min_words: int = 8) -> dict:
        """Check one submission against the whole corpus.

        Returns per-source matched-word counts, containment %, and merged spans
        with positions relative to the SUBMISSION text.
        """
        toks = tokenize(text)
        total = max(1, len(toks))
        # candidate source chunks per submission chunk
        hits: dict[tuple, list] = {}
        for start, ctoks in chunk_tokens(toks):
            m = chunk_minhash(ctoks)
            for key in self.lsh.query(m):
                doc_id, src_start, src_toks = self.chunks[key]
                hits.setdefault(doc_id, []).append((start, ctoks, src_start, src_toks))

        results = {}
        for doc_id, pairs in hits.items():
            all_spans = []
            for start, ctoks, src_start, src_toks in pairs:
                _, fp_q = fingerprint(" ".join(ctoks), K, W)
                _, fp_s = fingerprint(" ".join(src_toks), K, W)
                for sp in match_spans(ctoks, fp_q, src_toks, fp_s, K, min_words):
                    all_spans.append(
                        {
                            "q_start": sp["a_start"] + start,  # global submission token idx
                            "q_end": sp["a_end"] + start,
                            "s_start": sp["b_start"] + src_start,
                            "s_end": sp["b_end"] + src_start,
                        }
                    )
            merged = _merge_spans(all_spans, MERGE_GAP)
            matched = sum(s["q_end"] - s["q_start"] for s in merged)
            results[doc_id] = {
                "matched_words": matched,
                "containment_percent": round(100.0 * matched / total, 2),
                "spans": merged,
            }
        results = {d: r for d, r in results.items() if r["matched_words"] > 0}
        overall = sum(r["matched_words"] for r in results.values())
        return {
            "total_words": total,
            "matched_words": overall,
            "similarity_percent": round(100.0 * overall / total, 2),
            "sources": results,
        }


def _merge_spans(spans: list[dict], gap: int) -> list[dict]:
    if not spans:
        return []
    spans = sorted(spans, key=lambda s: s["q_start"])
    out = [dict(spans[0])]
    for s in spans[1:]:
        last = out[-1]
        if s["q_start"] <= last["q_end"] + gap:
            last["q_end"] = max(last["q_end"], s["q_end"])
            last["s_start"] = min(last["s_start"], s["s_start"])
            last["s_end"] = max(last["s_end"], s["s_end"])
        else:
            out.append(dict(s))
    return out


# ---------------------------------------------------------------------------
# Self-test: `python minhash_index.py`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    src1 = " ".join(
        f"sentence number {i} about rural microgrid droop control stability analysis" for i in range(60)
    )
    copied = (
        "This chapter reviews enzyme kinetics under saline stress measured by "
        "spectrophotometry. " + src1[500:1400] + " Additional unrelated discussion follows here."
    )
    unrelated = " ".join(f"quantum dot synthesis yield temperature {i} nanometers" for i in range(80))

    idx = CorpusIndex()
    idx.add("source1", src1)
    idx.add("unrelated", unrelated)

    r = idx.check(copied)
    assert r["sources"].get("source1", {}).get("matched_words", 0) >= 8, r
    assert "unrelated" not in r["sources"], r

    print("minhash_index.py self-test passed")
    print(f"  similarity: {r['similarity_percent']}%  matched: {r['matched_words']}/{r['total_words']}")
    print(f"  top source: source1 ({r['sources']['source1']['matched_words']} words, "
          f"{len(r['sources']['source1']['spans'])} spans)")
