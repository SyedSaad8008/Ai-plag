# Ai-plag

Complete Project Research Kit and Reference Implementation for an on-premises, privacy-preserving academic similarity and AI-writing detection platform.

---

## Overview

This repository contains the complete research, technical blueprints, prompt library, compliance documentation, and reference code for building a self-hosted academic integrity tool.

See [00-README-START-HERE.md](00-README-START-HERE.md) for the complete table of contents and reading guide.

### Key Contents
- **`00-README-START-HERE.md`**: Guide to all files and key architecture decisions
- **`01-hardware-and-storage-proposal.md`**: Infrastructure sizing, pricing, and storage strategy
- **`02-architecture-blueprint.md`**: Complete system architecture, database schema, and API specs
- **`03-similarity-engine-guide.md`**: Winnowing fingerprints, MinHash/LSH, embedding index
- **`04-ai-detection-guide.md`**: 3-stage cascade detection architecture (perplexity, judge, Binoculars)
- **`05-prompt-library.md`**: Prompts for Qwen models (coach mode, citation assistant, judge)
- **`06-docx-pptx-pipeline.md`**: Non-destructive run-level XML modification for DOCX & PPTX
- **`07-data-sources-playbook.md`**: OpenAlex, PMC, arXiv, and Shodhganga ingest workflows
- **`08-evaluation-benchmark-plan.md`**: Benchmarking datasets, evaluation metrics, and baselines
- **`09-college-pitch-pack.md`**: College presentation pitch, cost breakdown, UGC compliance
- **`10-roadmap-and-build-order.md`**: 6-phase development roadmap with acceptance criteria
- **`11-ethics-and-product-positioning.md`**: Product positioning and ethical guardrails
- **`code/`**: Working reference implementations (fingerprinting, MinHash, embeddings, in-place document editing, etc.)
