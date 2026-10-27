"""
Engine B stage 1 — AI-text statistics: token perplexity + sentence burstiness,
plus an optional Binoculars-style score. Reference implementation.

Why transformers and not Ollama: this stage needs per-token log-probabilities,
which Ollama does not expose. A 0.6B model in fp16 needs ~1.5 GB VRAM.

Requires: pip install torch transformers accelerate   (Python 3.11/3.12 venv)
Models: "Qwen/Qwen3-0.6B" (recommended) or "gpt2-large" (smallest test).
Optional Binoculars pair: "Llama-3.2-1B" + "Llama-3.2-1B-Instruct"
(published Binoculars uses Falcon-7B pair: >90% detection at 0.01% FPR,
Hans et al., ICML 2024 — measure YOUR pair's AUROC per docs/08 before trusting it).
"""
from __future__ import annotations

import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
MIN_WORDS = 40  # below this, statistics are noise -> return None

_cache: dict[str, tuple] = {}


def _load(model_name: str):
    if model_name in _cache:
        return _cache[model_name]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(model_name)
    dtype = torch.float16 if dev == "cuda" else torch.float32
    mdl = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype).to(dev).eval()
    _cache[model_name] = (tok, mdl, dev)
    return _cache[model_name]


@torch.no_grad()
def _token_logprobs(text: str, model_name: str) -> torch.Tensor:
    tok, mdl, dev = _load(model_name)
    ids = tok(text, return_tensors="pt", truncation=True, max_length=2048).input_ids.to(dev)
    logits = mdl(ids).logits[:, :-1, :]
    targets = ids[:, 1:]
    lp = torch.log_softmax(logits.float(), dim=-1)
    return lp.gather(-1, targets.unsqueeze(-1)).squeeze(-1)[0].cpu()


def segment_score(text: str, model_name: str = "Qwen/Qwen3-0.6B") -> dict | None:
    """Perplexity (lower = more predictable = more AI-suspicious) and burstiness
    (std/mean of sentence-level mean log-prob; lower = suspiciously uniform)."""
    if len(text.split()) < MIN_WORDS:
        return None
    sents = [s for s in SENT_SPLIT.split(text) if s.strip()]
    if len(sents) < 2:
        return None
    tok, _, _ = _load(model_name)
    lp = _token_logprobs(text, model_name)
    # map sentence boundaries to token positions via offsets mapping
    enc = tok(text, return_offsets_mapping=True, truncation=True, max_length=2048)
    offsets = enc["offset_mapping"][1:]  # aligned with lp (skip first token)
    sent_lp, si = [], 0
    for s in sents:
        start = text.find(s)
        end = start + len(s)
        vals = [lp[i].item() for i, (a, b) in enumerate(offsets) if a >= start and b <= end]
        if vals:
            sent_lp.append(sum(vals) / len(vals))
    if len(sent_lp) < 2:
        return None
    import statistics

    mean_lp = sum(sent_lp) / len(sent_lp)
    burstiness = statistics.pstdev(sent_lp) / max(1e-6, abs(mean_lp))
    return {
        "perplexity": round(pow(2.718281828, -mean_lp), 3),
        "burstiness": round(burstiness, 4),
        "sentences": len(sent_lp),
    }


@torch.no_grad()
def binoculars_score(
    text: str,
    observer: str = "meta-llama/Llama-3.2-1B",
    performer: str = "meta-llama/Llama-3.2-1B-Instruct",
) -> float | None:
    """score = perplexity under OBSERVER / perplexity under PERFORMER.
    Low ratio => text is surprisingly easy for the instruct twin => AI-suspect.
    Budget pair above; published pair: Falcon-7B / Falcon-7B-Instruct."""
    try:
        lp_o = _token_logprobs(text, observer).mean().item()
        lp_p = _token_logprobs(text, performer).mean().item()
    except Exception:
        return None
    return round(pow(2.718281828, lp_p - lp_o), 4)  # ppl_obs / ppl_perf via log difference


# Calibration: fit logistic regression on docs/08's labeled set with features
# (perplexity, burstiness, judge_likelihood[, binoculars]) — never ship raw
# thresholds you haven't measured on your own data.


if __name__ == "__main__":
    human = (
        "Our third prototype failed on 14 March because laterite dust clogged the pump "
        "inlet; we cleared it with a syringe and lost two hours. The fourth run held 12.1 "
        "bar for ninety minutes before the gasket wept at the flange. Two lessons went into "
        "the final build: a wire-mesh prefilter, and torque checks every twenty minutes. "
        "I would not trust the vendor's duty-cycle curve again."
    )
    ai = (
        "The experimental results demonstrate significant improvements across multiple "
        "evaluation metrics. Furthermore, the proposed methodology exhibits considerable "
        "potential for various real-world applications. It is worth noting that additional "
        "research is necessary to fully explore the multifaceted implications of these "
        "findings. Overall, this study contributes meaningfully to the growing body of "
        "knowledge in this important and rapidly evolving field of inquiry."
    )
    hs = segment_score(human)
    as_ = segment_score(ai)
    print("human :", hs)
    print("ai    :", as_)
    if hs and as_:
        # AI text should be more predictable (lower perplexity) and more uniform
        # (lower burstiness). Direction check only — calibrate thresholds on the
        # labeled set before using any numbers.
        assert as_["burstiness"] < hs["burstiness"] or as_["perplexity"] <= hs["perplexity"], \
            "direction check failed — recalibrate model choice"
    print("direction check passed (calibrate on labeled data before production)")
