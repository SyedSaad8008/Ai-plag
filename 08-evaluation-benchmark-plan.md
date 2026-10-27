# Evaluation & Benchmark Plan (how you prove it works)

You can't benchmark against Turnitin directly — so benchmark against everything else, publicly and honestly. This document is also your best college-pitch asset: "here are our measured numbers and known limits" is exactly what the universities that disabled Turnitin's AI detector said was missing.

---

## Dataset 1 — AI-detection labeled set

| Class | Count | How to obtain |
|---|---|---|
| Human academic paragraphs | 150 | Faculty/student volunteers (anonymized, consented), English seminar reports, Shodhganga thesis excerpts |
| GPT/LLM-generated | 150 | ChatGPT/Claude/Gemini prompted to write the same topics |
| LLM + light human edit | 75 | Have volunteers edit 3 of the AI ones lightly (realistic student behavior) |
| LLM + heavy human edit | 75 | Volunteers rewrite half the sentences |
| ESL human writing | 50 | Consented Indian students writing in English — **the false-positive canary** |
| Adversarial "AI-detector-bypassed" | 50 | Free paraphrasers/“humanizers” run on AI text — know your enemy honestly |

Mix of STEM/humanities. Store in `evaluation/datasets/ai_labeled.jsonl` with fields `{id, label, text, source, length_words}`.

## Dataset 2 — Similarity labeled set

| Case | Count | How to obtain |
|---|---|---|
| Verbatim copies | 100 | Copy spans of exactly 8/12/20/50/100 words from OpenAlex/Shodhganga texts into fresh paragraphs |
| Light-edit copies | 50 | Same spans, synonym-swapped |
| Heavy paraphrase | 50 | Rewritten keeping meaning |
| Genuine original | 100 | Same human paragraphs as Dataset 1 |
| Cross-batch self-plagiarism | 30 | Real old theses vs new submissions (college archive) |

## Metrics & targets

**Similarity engine:**
- Recall vs copied-span length curve (this empirically validates the k+w−1 winnowing guarantee from doc 03). **Target: 100% recall at ≥12 words verbatim; ≥95% at 8–11 words.**
- Precision: false-match rate < 1% at default exclusions.
- Localization accuracy: reported span covers ≥90% of the true copied span (IoU).
- Speed: 8k-word doc vs 5M-doc index < 30 s (doc 02 target).

**AI indicator:**
- AUROC on Dataset 1 overall; **target ≥ 0.90 on clean English** (Binoculars with proper 7B models reports >90% detection at 0.01% FPR — your budget cascade should be compared against your own measured numbers, and reported with CIs).
- **ESL false-positive rate (the headline number): target ≤ 5%** on the ESL subset at the operating threshold. If you can't hit it, raise the threshold — a detector that's quiet-but-right beats loud-but-wrong for adoption.
- Accuracy drop on the edited classes (light edit / heavy edit) — report it, don't hide it.

## Baselines to compare against

- Free detectors: GPTZero (free tier), ZeroGPT, Copyleaks trial — run the same JSONL through each manually, record outputs. This is the "how do I stand vs the ₹150/report guys" answer with data.
- Your own engine ablations: stage 1 only / stage 1+2 / all stages — the table justifies the cascade design.
- Literature anchor: Binoculars (Hans et al., ICML 2024) published numbers, stated as literature, not your measurement.

## Protocol rules (what makes it credible)

1. **Frozen test set**: split 70/30 train(calibration)/test ONCE; never tune on test.
2. Report confusion matrix + AUROC + FPR-at-chosen-threshold + F1; bootstrap CIs (1000 resamples).
3. Every result reproducible from `evaluation/run_benchmarks.py` with a seed.
4. Publish the fail cases: 10 worst false positives and false negatives in the report appendix. Professors trust tools that show their failures.

## Deliverable: `evaluation/report_2026-XX.pdf`

One page of charts (recall-vs-length, ROC, ESL-FPR bar), one table vs baselines, limits section. This single PDF, attached to the college pitch (doc 09), does more for adoption than any feature.
