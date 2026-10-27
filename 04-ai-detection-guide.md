# Engine B — AI-Writing Indicator (cascade design)

Goal: an honest, evidence-backed *indicator* of AI-generated text — never a verdict. This design exists because even Turnitin's AI detector was disabled by 50+ universities (Vanderbilt, MIT, Yale, Georgetown, UCLA, Michigan State...) over false positives — Turnitin claimed ~1% FPR, and at Vanderbilt's scale that meant ~750 falsely accused students per year, with documented bias against non-native English speakers. Your tool being *more honest than Turnitin here* is a selling point, not a weakness.

---

## Why a cascade

Running Qwen over every paragraph is slow and dilutes its accuracy. Instead: cheap statistical screening for everything, expensive judgment only where it matters. On the 8 GB laptop the stages also share VRAM by running **one after another** instead of together.

```
every segment → STAGE 1: perplexity + burstiness (Qwen3-0.6B, transformers, ~1.5 GB)
                     │  keep segments above threshold (typically 10–20% of segments)
                     ▼
               STAGE 2: Qwen 3 8B judge (Ollama) → JSON verdict + visible signals
                     │
                     ▼
               STAGE 3 (optional, whole-doc): Binoculars-style score (two small models)
```

## Stage 1 — Perplexity + burstiness (`code/perplexity_burstiness.py`)

LLM text is *predictable* text: high per-token probability, uniformly smooth across sentences. Humans are spiky.

- Run a small causal LM (Qwen3-0.6B or GPT-2-large) over each segment with teacher forcing; collect token log-probs.
- **Perplexity** = exp(−mean log-prob). Low → suspicious.
- **Burstiness** = std/mean of *sentence-level* mean log-probs. Low variance → suspicious.
- Score: combine both (start with a 2D threshold box, calibrate into logistic regression on your labeled set — doc 08).
- **Requires logprobs → use `transformers` directly, not Ollama** (Ollama does not expose token logprobs). 0.6B fp16 fits in ~1.5 GB; batch segments for speed.

Known failure modes (document them): factual/technical writing (equations, lists, abstracts) looks "predictable" regardless of author; short segments (<40 words) are noisy — set a minimum length.

## Stage 2 — Qwen as judge (`05-prompt-library.md`, prompt `P1`)

For each flagged segment, Qwen 3 8B returns strict JSON:

```json
{"ai_likelihood": 0.0–1.0, "confidence": "low|medium|high",
 "signals": ["uniform sentence rhythm", "generic hedging", "no first-person specificity"],
 "note": "one human-readable sentence"}
```

Design rules for 8B-class judges: one paragraph per call, temperature 0.2, JSON schema written into the prompt, 1–2 few-shot examples, explicit "if unsure say unsure". Ask for **signals a human can verify** — the UI shows them as bullet points under each highlight; that's what makes the report defensible in front of a professor.

## Stage 3 — Binoculars-style whole-document score (optional but impressive)

Binoculars (Hans et al., ICML 2024) is zero-shot, training-free, and detects >90% of ChatGPT text at 0.01% FPR using two closely-related models:

```
score = perplexity(text under OBSERVER model) / perplexity(text under PERFORMER model)
```

with OBSERVER = base model, PERFORMER = its instruction-tuned twin. AI text scores low (it's easy for the instruct twin to predict); human text scores high. Original uses Falcon-7B pair (needs ~14 GB — server territory). **Budget variant for your 8 GB laptop:** Llama-3.2-1B + Llama-3.2-1B-Instruct (~2.5 GB total fp16). Weaker than the published pair but the same mechanism; measure your own AUROC in doc 08's harness and report it honestly. Scaffolding is in `code/perplexity_burstiness.py::binoculars_score`.

## Calibration & reporting bands

- Logistic regression: features = (perplexity, burstiness, judge_likelihood, binoculars) → probability. Fit on doc 08's labeled set. Re-fit per domain (essays vs lab reports differ).
- Report bands (never bare percentages to end users):
  - `very_unlikely` (<0.2), `unlikely`, `unclear`, `likely`, `very_likely` (>0.8)
- Always printed under the band: *"AI-writing indicator — evidence for human review. High scores are not proof; low scores are not clearance. ESL writers are disproportionately flagged by all such systems."*

## Known limits to state publicly (put in report footer + pitch)

1. All AI detectors — including Turnitin's — have meaningful false-positive rates; 50+ universities disabled theirs.
2. Light human editing of AI text reduces detection; that's true for every detector, which is why the *process* evidence (edit log, coach-mode history, viva) matters more than any score.
3. Scores are calibrated for English academic prose; Indic-language output is a separate calibration project.
4. The indicator's job: point humans to passages worth a conversation. The conversation, not the number, is the integrity mechanism.

## Hardware mapping (8 GB VRAM laptop)

| Pass | Model | VRAM | Runtime (8k-word doc) |
|---|---|---|---|
| Stage 1 | Qwen3-0.6B (transformers, fp16) | ~1.5 GB | ~20–40 s all segments |
| Stage 2 | qwen3:8b Q4 (Ollama) | ~5.5 GB | 1–2 min (only flagged segments) |
| Stage 3 | 2× 1B pair (transformers) | ~2.5 GB | ~10 s whole doc |

Run stages sequentially (pipeline), never concurrently, on the laptop. On the Stage-2 server (16 GB), Stage 1+3 resident together and 8B judge alongside is comfortable.
