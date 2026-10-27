"""
PPTX in-place editing without touching the design — reference implementation.

Rules (docs/06-docx-pptx-pipeline.md): edit runs inside existing text frames;
SKIP + flag charts, SmartArt and grouped/picture text honestly instead of
corrupting them. Never rebuild a deck.

Requires: pip install python-pptx
Run `python pptx_inplace.py` for the self-test (builds a temp deck).
Adapt into bi-plagiarism/backend/rewrite/pptx_editor.py.
"""
from __future__ import annotations

import tempfile

from pptx import Presentation  # type: ignore
from pptx.enum.shapes import MSO_SHAPE_TYPE  # type: ignore

SMARTART_URI_MARKER = "diagram"  # a:graphicData/@uri containing 'diagram' = SmartArt


def iter_shapes(shapes):
    """Recursive walk including groups."""
    for sh in shapes:
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from iter_shapes(sh.shapes)
        else:
            yield sh


def classify(shape) -> str:
    """What kind of text container is this?"""
    if getattr(shape, "has_chart", False) and shape.has_chart:
        return "chart"  # chart labels live in the chart part -> manual edit
    try:
        uris = shape._element.xpath(".//a:graphicData/@uri")
        if any(SMARTART_URI_MARKER in u for u in uris):
            return "smartart"  # separate diagram XML part -> manual edit
    except Exception:
        pass
    if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
        return "text"
    return "other"  # pictures, media, placeholders without text


def scan(prs) -> dict:
    """What is editable in this deck? Drives honest UI flags."""
    counts = {"text": 0, "chart": 0, "smartart": 0, "other": 0, "notes": 0}
    editable: list[dict] = []
    for si, slide in enumerate(prs.slides):
        for sh in iter_shapes(slide.shapes):
            kind = classify(sh)
            counts[kind] += 1
            if kind == "text":
                editable.append({"slide": si + 1, "shape_id": sh.shape_id,
                                 "preview": sh.text_frame.text[:80]})
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            counts["notes"] += 1
    return {"counts": counts, "editable_text_shapes": editable}


def replace_in_text_frame(tf, old: str, new: str) -> bool:
    """Same run-redistribution logic as the DOCX editor, per paragraph."""
    for par in tf.paragraphs:
        runs = par.runs
        full = "".join(r.text for r in runs)
        start = full.find(old)
        if start < 0:
            continue
        end = start + len(old)
        pos, replaced = 0, False
        for r in runs:
            rs, re_ = pos, pos + len(r.text)
            pos = re_
            if re_ <= start or rs >= end:
                continue
            prefix = r.text[: max(0, start - rs)]
            suffix = r.text[max(0, end - rs) :]
            if not replaced:
                r.text = prefix + new + suffix
                replaced = True
            else:
                r.text = prefix + suffix
        if replaced:
            return True
    return False


def apply_replacements(path: str, replacements: dict[str, str], out_path: str) -> dict:
    """Apply {old: new} across slides, tables and speaker notes. Layout, theme,
    images and animations are untouched because the file is edited in place."""
    prs = Presentation(path)
    done, remaining = {}, dict(replacements)
    flagged: list[str] = []

    def try_frame(tf) -> int:
        n = 0
        for old in list(remaining):
            if replace_in_text_frame(tf, old, remaining[old]):
                done[old] = remaining.pop(old)
                n += 1
        return n

    for si, slide in enumerate(prs.slides):
        for sh in iter_shapes(slide.shapes):
            kind = classify(sh)
            if kind == "text":
                try_frame(sh.text_frame)
            elif kind in ("chart", "smartart"):
                flagged.append(f"slide {si + 1}: {kind} needs manual edit")
            if getattr(sh, "has_table", False) and sh.has_table:
                for row in sh.table.rows:
                    for cell in row.cells:
                        try_frame(cell.text_frame)
        if slide.has_notes_slide:
            try_frame(slide.notes_slide.notes_text_frame)

    prs.save(out_path)
    return {"replaced": done, "missed": list(remaining), "flagged": flagged}


# ---------------------------------------------------------------------------
# Self-test: `python pptx_inplace.py`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    tf = slide.shapes.title.text_frame
    r1 = tf.paragraphs[0].add_run()
    r1.text = "Adaptive droop control for "
    r1.font.bold = True
    r2 = tf.paragraphs[0].add_run()
    r2.text = "rural photovoltaic microgrids"
    body = slide.placeholders[1].text_frame
    body.text = "Morning load spikes destabilize the bus voltage in village microgrids."
    slide.notes_slide.notes_text_frame.text = "Emphasize the 34 percent reduction here."

    with tempfile.TemporaryDirectory() as td:
        src, out = f"{td}/in.pptx", f"{td}/out.pptx"
        prs.save(src)
        info = scan(Presentation(src))
        assert info["counts"]["text"] >= 2, info
        res = apply_replacements(
            src,
            {"rural photovoltaic microgrids": "village-scale solar microgrids",
             "Morning load spikes destabilize the bus voltage in village microgrids.":
                 "Morning demand surges destabilize bus voltage across village microgrids."},
            out,
        )
        assert len(res["replaced"]) == 2, res
        chk = Presentation(out)
        texts = [sh.text_frame.text for s in chk.slides for sh in iter_shapes(s.shapes)
                 if getattr(sh, "has_text_frame", False) and sh.has_text_frame]
        joined = " | ".join(texts)
        assert "village-scale solar microgrids" in joined, joined
        assert "Morning demand surges" in joined, joined
        assert "Emphasize the 34 percent" in chk.slides[0].notes_slide.notes_text_frame.text
        print("pptx_inplace.py self-test passed (title + body + notes replaced, deck edited in place)")
