# DOCX / PPTX Pipeline (edit in place, destroy nothing)

The reason your PPT output "feels worst" is almost certainly that the deck gets rebuilt. Don't rebuild — **edit the original file in place**. Both `python-docx` and `python-pptx` let you change text inside existing runs while every bit of formatting (theme, fonts, colors, images, animations, layouts) stays untouched. Reference code: `code/docx_inplace.py`, `code/pptx_inplace.py`.

---

## The one concept that explains everything: runs

Word and PowerPoint do NOT store a paragraph as one string. They store **runs** — arbitrary fragments of text each carrying its own formatting. `"The model achieved 94% accuracy"` may be stored as 4 runs because Word split it at a spell-check boundary or a formatting change.

Consequences:
- `paragraph.text` (concatenation) is what you match against.
- A replacement may span several runs → you must redistribute text across them (that's what `replace_in_paragraph()` in the reference code does: first affected run gets prefix+new+suffix, covered runs get emptied, the last keeps its tail).
- If a paragraph's formatting is uniform, a safe shortcut exists: put the whole new sentence in the first run and empty the rest. Use the general routine anyway — it's written once.

## DOCX flow (`code/docx_inplace.py`)

```
open .docx (zip) → walk all Paragraph objects:
    body paragraphs, table cells (doc.tables → rows → cells → paragraphs),
    headers/footers (section.header/footer), textboxes are NOT exposed by python-docx
    → flag them as "manual review" (count them; they're rare in academic docs)
for each replacement (old_text → new_text) from the report:
    find owning paragraph via concatenated text → replace_in_paragraph()
save as thesis_checked.docx (never overwrite the upload)
```

- Keep a byte offset / paragraph index map from the ingest step so report spans locate instantly.
- Quotes & references: mark segments before checking so the editor skips them.
- Optional advanced: real tracked changes require inserting raw `w:ins`/`w:del` XML around runs — doable but leave it for a later phase; until then the **edit log** (doc 11) is your change record.

## PPTX flow (`code/pptx_inplace.py`)

```
Presentation(path) → for each slide:
    shape.has_text_frame  → walk paragraphs → runs → replace_in_paragraph()
    shape.has_table       → cells → same
    shape.has_chart       → SKIP + flag "chart text needs manual edit"
    SmartArt (graphicFrame with a:graphicData/@uri containing 'diagram')
                          → SKIP + flag "SmartArt needs manual edit"
    pictures of text (rasterized AI-exported slides)
                          → no text found → flag "uneditable text image"
    slide.notes_slide     → editable like any text frame
save copy → report the flagged shapes back into the report JSON
```

Why skip charts/SmartArt: chart labels live in the chart part (often backed by an embedded XLSX), SmartArt lives in separate diagram XML parts — neither is exposed cleanly by python-pptx, and a bad edit corrupts the file. Flagging them honestly beats corrupting them. (Aggressive option for later: edit the underlying `ppt/charts/chartN.xml` and `ppt/diagrams/data*.xml` directly via lxml — Phase 6+.)

## PDF: input-only, permanently

- Reading: PyMuPDF (`fitz`) — `page.get_text("blocks")`. If `len(text) < 50` chars/page → scanned → flag "needs OCR" (`pytesseract` + `pdf2image`, or Ollama vision model as an OCR assist — a nice Phase 5 experiment).
- The official PDF flow: **PDF in → auto-convert to DOCX (`docx` via `pdf2docx` library or Word COM automation on Windows for best fidelity) → report + edits happen in DOCX.** PDFs are never edited, never emitted. Say this on the UI as a feature: "PDF is checked read-only; edits happen in the generated DOCX."

## Rewrite semantics (what the product does)

For every flagged span, the UI offers three actions — and the file is only touched when the user acts:

1. **Student rewrites (coach)** → user pastes their new sentence → in-place replace → re-run engine check on that segment only → score updates.
2. **Cite-assist** → inserts the citation placeholder at the right position → in-place replace (tiny, safe edit).
3. **Direct replacement** (own words already prepared) → in-place replace.

Every action appends to `edit_log` (doc 11) — which is what makes the whole workflow academically presentable.

## Testing checklist (run before trusting any release)

- [ ] Round-trip: open → save with zero replacements → file opens in Word/PowerPoint with zero visual diffs.
- [ ] Replace a span crossing bold/italic boundaries → formatting outside the span intact.
- [ ] Replace in table cell, header, footer, speaker notes.
- [ ] Deck with SmartArt + charts → files flagged, file still opens cleanly.
- [ ] 200-slide stress deck → runtime < 30 s.
- [ ] Non-ASCII (Devanagari, Tamil) text replacements → correct on save.
