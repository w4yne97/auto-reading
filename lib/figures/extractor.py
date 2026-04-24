"""PDF figure extraction: embedded images + page-render fallback."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FigureCandidate:
    id: str
    file_name: str
    page: int
    bbox: tuple[float, float, float, float] | None
    kind: Literal["embedded", "page-render"]
    width: int
    height: int
    nearest_caption: str | None


def extract_candidates(
    pdf_path: Path,
    output_dir: Path,
    *,
    min_side_px: int = 100,
) -> list[FigureCandidate]:
    """Extract figure candidates from pdf_path into output_dir.

    Clears output_dir if it exists, then writes one PNG per candidate plus
    a candidates.json manifest. Returns the list ordered by (page asc, xref asc).
    """
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    doc = fitz.open(pdf_path)
    try:
        candidates = _extract_embedded(doc, output_dir, min_side_px)
    finally:
        doc.close()

    manifest_path = output_dir / "candidates.json"
    manifest_path.write_text(
        json.dumps(
            {
                "total": len(candidates),
                "candidates": [_candidate_to_dict(c) for c in candidates],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    logger.info("Wrote %d candidates to %s", len(candidates), output_dir)
    return candidates


def _candidate_to_dict(c: FigureCandidate) -> dict:
    """Serialize FigureCandidate to dict, using 'file' as the key for file_name."""
    d = asdict(c)
    d["file"] = d.pop("file_name")
    return d


def _extract_embedded(
    doc: fitz.Document, output_dir: Path, min_side_px: int
) -> list[FigureCandidate]:
    out: list[FigureCandidate] = []
    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_num = page_idx + 1
        # (xref, smask, width, height, bpc, colorspace, alt, name, filter, referencer)
        images = page.get_images(full=True)
        for idx, img in enumerate(sorted(images, key=lambda r: r[0]), start=1):
            xref = img[0]
            width, height = img[2], img[3]
            if width < min_side_px or height < min_side_px:
                continue

            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha > 3:  # CMYK → convert to RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)

            file_name = f"img_p{page_num:02d}_{idx:02d}.png"
            pix.save(output_dir / file_name)
            pix = None  # release

            bbox = _find_image_bbox(page, xref)
            out.append(
                FigureCandidate(
                    id=f"img_p{page_num:02d}_{idx:02d}",
                    file_name=file_name,
                    page=page_num,
                    bbox=bbox,
                    kind="embedded",
                    width=width,
                    height=height,
                    nearest_caption=None,
                )
            )
    return out


def _find_image_bbox(
    page: fitz.Page, xref: int
) -> tuple[float, float, float, float] | None:
    """Return the first bbox for the given image xref on the page."""
    for item in page.get_image_info(xrefs=True):
        if item.get("xref") == xref:
            bbox = item.get("bbox")
            if bbox:
                return tuple(bbox)
    return None
