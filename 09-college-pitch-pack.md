# College Pitch Pack

---

## The one-page pitch (read this aloud in the meeting)

> **Problem.** UGC's 2018 regulations require every institution to check similarity in theses and papers. The tool colleges use — Turnitin — costs about ₹5,00,000 per year. We cannot afford it, so our research output goes unchecked, our journals desk-reject us for similarity, and students pay ₹100–150 per check to unregulated online tools that upload our intellectual property to unknown servers.
>
> **Proposal.** A college-owned plagiarism and AI-writing screening system, built in-house, running on college hardware, free forever. It uses the same published fingerprinting methods the commercial systems use (winnowing, Stanford SIGMOD 2003), a local reference index of millions of open papers (OpenAlex, Shodhganga), and — uniquely — our own growing archive of every submission ever checked here.
>
> **Privacy.** No document ever leaves college computers. Unlike Turnitin, which adds submissions to its global corpus, our students' work stays ours.
>
> **Cost.** Stage 1: ~₹10,000 (drives) to pilot on existing hardware. Stage 2: ~₹1.1 lakh one-time for a server. Compare ₹5,00,000 *every year*.
>
> **Ask.** Approve a 2-month pilot with 2 departments. We return with measured numbers (doc 08) before any larger commitment.

## Cost table (put on the slide)

| | Turnitin | This system |
|---|---|---|
| Year 1 | ₹5,00,000 | ₹10,000 (pilot) → ₹1,10,000 (server) |
| Year 2 | ₹5,00,000 | ~₹6,000 electricity |
| Year 5 total | ₹25,00,000 | ~₹1,30,000 |
| Data ownership | Submissions enter vendor's global corpus | 100% college-owned |
| AI-writing check | Extra module, disabled by 50+ universities over false positives | Indicator + human-review design, documented limits |
| Per-check fees to students | ₹0 (college pays) | ₹0 — permanently |

## UGC 2018 compliance mapping (the slide that convinces the principal)

| UGC level | Similarity | Regulation's consequence | What our tool does |
|---|---|---|---|
| Level 0 | ≤ 10% | No penalty | Green report, auto-note "compliant" |
| Level 1 | 10–40% | Revise & resubmit | Report + coach mode + cite-assist to fix it |
| Level 2 | 40–60% | Debarment from submitting for a year etc. | Red report + faculty explainer (prompt P6) |
| Level 3 | > 60% | Registration cancellation etc. | Red report + evidence pack (all spans, sources) |

The tool implements exactly the regulation's bands, with quotes/references excluded as the regulation allows — that mapping is what the IQAC/Research Cell needs to see.

## 5-minute demo script (memorize the order)

1. **Upload a real thesis chapter** (DOCX) → report renders: similarity %, UGC level, matched spans side-by-side with sources. (60 s)
2. **Show the archive counter** — "every submission makes this stronger; in 3 years no online tool can offer this for our college." (30 s)
3. **Toggle web_check off** — "fully offline mode; nothing ever leaves campus." (30 s)
4. **AI-indicator section**: flagged paragraph + the *signals* bullets + the disclaimer line. "Indicator for human review — the same reason 50 universities rejected Turnitin's AI score." (60 s)
5. **Coach mode**: flagged sentence → questions for the student → student rewrite → re-check → score drops. "We fix writing, not scores." (60 s)
6. **Cost slide** → ask for the pilot. (60 s)

## Faculty FAQ (prepare these answers verbatim)

- **"Is this legal?"** Yes — it uses open datasets (CC0/OpenAlex), published algorithms, and local processing; it implements UGC 2018 bands. No student data leaves campus.
- **"Will it replace faculty judgment?"** No — reports are screening + evidence; decisions stay with the guide/HOD (same as Turnitin's intended use).
- **"What if it falsely accuses a student?"** AI section is an indicator, never a verdict, with published FPR including on ESL writers (doc 08 measures ours). Similarity matches are shown as evidence, not conclusions.
- **"Who maintains it when the students graduate?"** Stage-2 handover: docs 02+10 are written for a new maintainer; the Research Cell owns it; student team trains successors annually.
- **"Why not the free online checkers?"** They upload student work to foreign servers, have no archive, no UGC mapping, no citation support — and the ₹100-150 per-report ones are unregulated.
- **"Can we see it fail?"** Yes — doc 08's report includes worst false positives. Trust requires showing failure modes up front.

## Extra leverage

- **Journal pre-screening**: faculty submit to journals that run iThenticate; a pre-check prevents desk rejections (mention the college's recent rejections if any).
- **Research Cell reporting**: monthly similarity statistics across departments → accreditation (NAAC/NIRF) paperwork comes pre-generated.
- **SIH angle**: this is itself a Smart India Hackathon-grade problem statement ("affordable academic integrity infrastructure for Indian HEIs").
