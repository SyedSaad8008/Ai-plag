"""
Winnowing document fingerprinting — reference implementation.

Algorithm: Schleimer, Wilkerson & Aiken, "Winnowing: Local Algorithms for
Document Fingerprinting" (SIGMOD 2003). This is the algorithm family used by
Turnitin-style systems.

Guarantee: any passage of >= k + w - 1 words shared by two documents is
guaranteed to produce at least one shared fingerprint (cannot be missed).

Pure standard library. Run `python fingerprint.py` for the self-test.
Adapt into bi-plagiarism/backend/engines/fingerprint.py.
"""
from __future__ import annotations

import re
from collections import defaultdict
from hashlib import blake2b

TOKEN_RE = re.compile(r"[a-z0-9]+")

# Defaults aligned with Turnitin's familiar "exclude matches < 8 words":
# k=5, w=4 -> guaranteed detection of every match of >= 8 words.
K = 5
W = 4


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens. Numbers kept (important for academic text)."""
    return TOKEN_RE.findall(text.lower())


def token_offsets(text: str) -> list[tuple[int, int]]:
    """Char spans of each token, for highlighting in the UI."""
    return [m.span() for m in TOKEN_RE.finditer(text)]


def kgram_hashes(tokens: list[str], k: int = K) -> list[int]:
    """64-bit hash of every k-gram (BLAKE2b: no collisions in practice)."""
    out: list[int] = []
    for i in range(len(tokens) - k + 1):
        gram = " ".join(tokens[i : i + k]).encode("utf-8")
        out.append(int.from_bytes(blake2b(gram, digest_size=8).digest(), "big"))
    return out


def winnow(hashes: list[int], w: int = W) -> list[tuple[int, int]]:
    """Select fingerprints: min hash per window of w, rightmost on ties.

    Returns [(token_index, hash), ...]. At least one fingerprint comes from
    every window, which yields the k+w-1 guarantee.
    """
    n = len(hashes)
    if n == 0:
        return []
    if n < w:
        i = min(range(n), key=lambda j: hashes[j])
        return [(i, hashes[i])]
    fps: list[tuple[int, int]] = []
    prev = -1
    for s in range(n - w + 1):
        window = hashes[s : s + w]
        best = min(range(w), key=lambda j: (window[j], -j))
        idx = s + best
        if idx != prev:
            fps.append((idx, hashes[idx]))
            prev = idx
    return fps


def fingerprint(text: str, k: int = K, w: int = W):
    tokens = tokenize(text)
    return tokens, winnow(kgram_hashes(tokens, k), w)


def _chains(aligns: list[tuple[int, int]], max_gap: int) -> list[list[tuple[int, int]]]:
    """Chain aligned positions (i in A, j in B) into monotone runs.

    For each alignment, extend the compatible chain whose end is closest in j
    (handles the same passage appearing multiple times in B). Reference-grade
    greedy; a production build can swap in DP chaining.
    """
    aligns.sort()
    chains: list[list[tuple[int, int]]] = []
    for a in aligns:
        best = None
        for c in chains:
            li, lj = c[-1]
            if a[0] > li and a[1] > lj and (a[0] - li) <= max_gap and (a[1] - lj) <= max_gap:
                if best is None or c[-1][1] > best[-1][1]:
                    best = c
        if best is not None:
            best.append(a)
        else:
            chains.append([a])
    return chains


def match_spans(
    tokens_a: list[str],
    fps_a: list[tuple[int, int]],
    tokens_b: list[str],
    fps_b: list[tuple[int, int]],
    k: int = K,
    min_words: int = 8,
    max_gap: int = 15,
) -> list[dict]:
    """Find copied spans of A inside B (or vice versa; symmetric inputs).

    Returns [{"a_start","a_end","b_start","b_end","words"}] as token index
    ranges (end exclusive).
    """
    by_hash_a: dict[int, list[int]] = defaultdict(list)
    for i, h in fps_a:
        by_hash_a[h].append(i)

    aligns = [(i, j) for j, h in fps_b for i in by_hash_a.get(h, ())]
    spans = []
    for chain in _chains(aligns, max_gap):
        a0, b0 = chain[0]
        a1, b1 = chain[-1]
        words = a1 - a0 + k  # a full k-gram spans k tokens
        if words >= min_words:
            spans.append(
                {"a_start": a0, "a_end": a0 + words, "b_start": b0, "b_end": b0 + words, "words": words}
            )
    return spans


def _merge(spans: list[dict], gap: int = 10) -> list[dict]:
    """Merge overlapping/nearby spans so one copied passage = one report row."""
    if not spans:
        return []
    spans = sorted(spans, key=lambda s: s["a_start"])
    out = [dict(spans[0])]
    for s in spans[1:]:
        last = out[-1]
        if s["a_start"] <= last["a_end"] + gap:
            last["a_end"] = max(last["a_end"], s["a_end"])
            last["b_end"] = max(last["b_end"], s["b_end"])
            last["words"] = last["a_end"] - last["a_start"]
        else:
            out.append(dict(s))
    return out


def compare(text_a: str, text_b: str, k: int = K, w: int = W, min_words: int = 8) -> dict:
    """Compare two texts. Similarity is measured on A (containment-style):
    what fraction of A's words sit inside a span matched in B."""
    toks_a, fps_a = fingerprint(text_a, k, w)
    toks_b, fps_b = fingerprint(text_b, k, w)
    spans = _merge(match_spans(toks_a, fps_a, toks_b, fps_b, k, min_words))
    matched = sum(s["words"] for s in spans)
    return {
        "similarity_percent": round(100.0 * matched / max(1, len(toks_a)), 2),
        "matched_words": matched,
        "total_words": len(toks_a),
        "spans": spans,
    }


# ---------------------------------------------------------------------------
# Self-test: `python fingerprint.py`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    base = (
        "Microgrid controllers coordinate distributed energy resources to maintain "
        "stable frequency and voltage under varying load conditions. In rural India, "
        "photovoltaic microgrids suffer from morning load spikes that destabilize "
        "the bus voltage. This work proposes an adaptive droop controller that "
        "adjusts its coefficients using a lightweight online estimator, reducing "
        "voltage deviation by 34 percent during field trials across two villages."
    )
    long_copy = (
        "The present chapter reviews power electronic interfaces for rural electrification. "
        "Photovoltaic microgrids suffer from morning load spikes that destabilize "
        "the bus voltage. This work proposes an adaptive droop controller that "
        "adjusts its coefficients using a lightweight online estimator, reducing "
        "voltage deviation by 34 percent during field trials. " * 3
    )
    short_copy = base.replace("stable frequency and voltage", "stable voltage and frequency")
    unrelated = (
        "Enzyme kinetics under saline stress were measured using spectrophotometry at "
        "540 nanometers. Germination percentages were arc-sine transformed before "
        "analysis of variance and Tukey post hoc comparisons at five percent significance."
    )

    r = compare(base, long_copy)
    assert r["matched_words"] >= 30, f"long copy missed: {r}"
    r8 = compare(base, short_copy)
    assert r8["matched_words"] >= 8, f"8-word guarantee failed: {r8}"
    r0 = compare(base, unrelated)
    assert r0["matched_words"] == 0, f"false positive: {r0}"

    # Span positions must point at the right words in A.
    toks = tokenize(base)
    first = compare(base, long_copy)["spans"][0]
    excerpt = " ".join(toks[first["a_start"] : first["a_end"]])
    assert "droop" in excerpt or "microgrids" in excerpt, excerpt

    print("fingerprint.py self-test passed")
    print(f"  36-word copy:   {r['matched_words']} words matched, spans={len(r['spans'])}")
    print(f"  near-copy:      {r8['matched_words']} words matched (>= 8 guarantee)")
    print(f"  unrelated text: {r0['matched_words']} words matched (expect 0)")
