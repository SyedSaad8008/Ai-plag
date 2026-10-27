"""
DOCX in-place editing without destroying formatting — reference implementation.

Key idea: Word stores paragraphs as RUNS (formatting fragments). We match on the
concatenated paragraph text and redistribute the replacement across runs, so
every run's formatting survives. See docs/06-docx-pptx-pipeline.md.

Requires: pip install python-docx
Run `python docx_inplace.py` for the self-test (builds a temp docx).
Adapt into bi-plagiarism/backend/rewrite/docx_editor.py.
"""
from __future__ import annotations

import tempfile

from docx import Document  # type: ignore
from docx.document import Document as _Doc  # type: ignore
from docx.table import Table  # type: ignore
from docx.text.paragraph import Paragraph  # type: ignore


def iter_paragraphs(parent):
    """Every paragraph: body, table cells, headers, footers.
    (Textboxes are NOT exposed by python-docx — flag them for manual review.)"""
    if isinstance(parent, _Doc):
        for p in parent.paragraphs:
            yield p
        for t in parent.tables:
            yield from iter_paragraphs(t)
        for s in parent.sections:
            for hf in (s.header, s.footer):
                for p in hf.paragraphs:
                    yield p
    elif isinstance(parent, Table):
        for row in parent.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    yield p
                for t in cell.tables:
                    yield from iter_paragraphs(t)


def replace_in_paragraph(par: Paragraph, old: str, new: str) -> bool:
    """Replace `old` with `new` inside one paragraph, preserving run formatting.

    Handles matches that span multiple runs (Word splits text arbitrarily).
    The first affected run keeps its prefix and receives the new text; covered
    runs are emptied; the last keeps its suffix.
    """
    runs = par.runs
    texts = [r.text for r in runs]
    full = "".join(texts)
    start = full.find(old)
    if start < 0:
        return False
    end = start + len(old)
    pos, replaced = 0, False
    for r in runs:
        rs, re_ = pos, pos + len(r.text)
        pos = re_
        if re_ <= start or rs >= end:
            continue
        prefix = r.text[: max(0, start - rs)]
        suffix = r.text[max(0, end - rs) :]  # "" if match extends past this run
        if not replaced:
            r.text = prefix + new + suffix
            replaced = True
        else:
            r.text = prefix + suffix
    return replaced


def apply_replacements(path: str, replacements: dict[str, str], out_path: str | None = None) -> dict:
    """Apply {old: new} across a whole document. Never overwrites the original
    unless out_path is None (still returns stats; caller owns file safety)."""
    doc = Document(path)
    done, missed = {}, []
    remaining = dict(replacements)
    for par in iter_paragraphs(doc):
        if not remaining:
            break
        full = par.text
        for old in list(remaining):
            if old and old in full:
                if replace_in_paragraph(par, old, remaining[old]):
                    done[old] = remaining.pop(old)
                else:  # pragma: no cover
                    missed.append(old)
    for old in remaining:
        missed.append(old)
    if out_path:
        doc.save(out_path)
    return {"replaced": done, "missed": missed}


def find_paragraphs_matching(path: str, needle: str) -> list[str]:
    doc = Document(path)
    return [p.text for p in iter_paragraphs(doc) if needle in p.text]


# ---------------------------------------------------------------------------
# Self-test: `python docx_inplace.py`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    doc = Document()
    # one paragraph whose text Word will likely split across runs
    p = doc.add_paragraph()
    r1 = p.add_run("The proposed ")
    r1.bold = True
    r2 = p.add_run("adaptive droop controller achieved 34 percent lower voltage deviation")
    r3 = p.add_run(" during the village field trials.")
    t = doc.add_table(rows=1, cols=1)
    t.rows[0].cells[0].paragraphs[0].add_run("Photovoltaic microgrids suffer from morning load spikes in rural India.")

    with tempfile.TemporaryDirectory() as td:
        src = f"{td}/in.docx"
        out = f"{td}/out.docx"
        doc.save(src)
        reps = {
            "adaptive droop controller achieved 34 percent lower voltage deviation": "self-tuning droop mechanism cut voltage deviation by roughly one third",
            "Photovoltaic microgrids suffer from morning load spikes in rural India.": "Morning demand surges destabilize village solar microgrids across India.",
        }
        res = apply_replacements(src, reps, out)
        assert len(res["replaced"]) == 2, res
        chk = Document(out)
        paras = [p.text for p in iter_paragraphs(chk)]
        assert any("self-tuning droop mechanism" in t for t in paras), paras
        assert any("Morning demand surges" in t for t in paras), paras
        # formatting survives: first run of the edited paragraph is still bold
        for p2 in chk.paragraphs:
            if "self-tuning" in p2.text:
                assert p2.runs[0].bold, "bold formatting lost"
                break
        print("docx_inplace.py self-test passed (multi-run replace + table cell + bold preserved)")
