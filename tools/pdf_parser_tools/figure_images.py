from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class FigureImage(BaseModel):
    figure_id: str
    source_file: str
    page: int | None = None
    image_index: int
    data_url: str | None = None
    width: int | None = None
    height: int | None = None
    bbox: list[float] | None = None
    extraction_method: str = "page_region_render"
    status: str = "image_extracted"
    message: str | None = None


class FigureImageResult(BaseModel):
    status: str
    source_file: str
    images: list[FigureImage] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)


def extract_pdf_figure_images(source_file: str, captions: list[dict[str, Any]] | None = None, max_images: int = 40) -> dict[str, Any]:
    """Render PDF page regions for figure evidence preview.

    This is a display helper only. It does not change ARM claims/evidence and it
    does not interpret plotted values or microscopy pixels. The extractor is
    caption-driven: for each caption with a page/bbox, it renders the region above
    the caption instead of enumerating embedded PDF images, which avoids logos and
    publisher UI assets such as "Check for updates".
    """
    path = Path(source_file)
    trace = [{"stage": "figure_image_extract_start", "source_file": str(path)}]
    risks: list[dict[str, Any]] = []
    images: list[FigureImage] = []
    if path.suffix.lower() != ".pdf":
        return FigureImageResult(
            status="figure_image_not_pdf",
            source_file=str(path),
            risks=[{"code": "not_pdf", "message": "Figure image extraction is available for PDF files only.", "review_required": False}],
            trace=trace,
        ).model_dump()
    try:
        import fitz  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return FigureImageResult(
            status="figure_image_backend_missing",
            source_file=str(path),
            risks=[{"code": "pymupdf_missing", "message": str(exc), "review_required": False}],
            trace=trace + [{"stage": "pymupdf_missing"}],
        ).model_dump()
    try:
        doc = fitz.open(str(path))
        source_captions = [caption for caption in captions or [] if _same_source(caption.get("source_file"), path)]
        seq = 0
        for caption in source_captions:
            if seq >= max_images:
                break
            rendered = _render_caption_region(doc, caption)
            if not rendered:
                continue
            seq += 1
            images.append(
                FigureImage(
                    figure_id=str(caption.get("figure_id") or f"Figure image {seq}"),
                    source_file=str(path),
                    page=rendered["page"],
                    image_index=seq,
                    data_url=rendered["data_url"],
                    width=rendered["width"],
                    height=rendered["height"],
                    bbox=rendered["bbox"],
                    extraction_method=rendered["method"],
                )
            )
        doc.close()
        if not images:
            risks.append({"code": "no_caption_region_images", "message": "No figure regions could be rendered from caption locations; captions are still available.", "review_required": False})
        trace.append({"stage": "figure_image_extract_completed", "image_count": len(images)})
        return FigureImageResult(status="figure_image_success" if images else "figure_image_empty", source_file=str(path), images=images, risks=risks, trace=trace).model_dump()
    except Exception as exc:  # noqa: BLE001
        risks.append({"code": "figure_image_extract_failed", "message": str(exc), "review_required": False})
        trace.append({"stage": "figure_image_extract_failed", "error": str(exc)})
        return FigureImageResult(status="figure_image_failed", source_file=str(path), images=images, risks=risks, trace=trace).model_dump()


def match_images_to_captions(images: list[dict[str, Any]], captions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched = []
    for idx, caption in enumerate(captions):
        source = str(caption.get("source_file") or "")
        source_images = [image for image in images if str(image.get("source_file")) == source]
        image = next((item for item in source_images if _figure_key(item.get("figure_id")) == _figure_key(caption.get("figure_id"))), None)
        if image is None:
            image = source_images[idx] if idx < len(source_images) else None
        row = dict(caption)
        row["image"] = image
        row["image_status"] = image.get("status") if image else "image_not_matched"
        matched.append(row)
    return matched


def _render_caption_region(doc: Any, caption: dict[str, Any]) -> dict[str, Any] | None:
    import fitz  # type: ignore

    try:
        page_number = int(caption.get("page") or 0)
    except (TypeError, ValueError):
        page_number = 0
    if page_number < 1 or page_number > len(doc):
        return None
    page = doc[page_number - 1]
    page_rect = page.rect
    bbox = caption.get("bbox") or []
    if len(bbox) == 4:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        top_margin = 22
        min_height = 130
        clip = page_rect & fitz.Rect(
            max(0, x0 - 18),
            max(0, y0 - 360),
            min(float(page_rect.width), x1 + 18),
            max(0, y0 - top_margin),
        )
        if clip.height < min_height:
            clip = page_rect & fitz.Rect(
                0,
                max(0, y0 - 430),
                float(page_rect.width),
                max(0, y0 - top_margin),
            )
        method = "caption_above_region"
    else:
        clip = page_rect & fitz.Rect(
            0,
            float(page_rect.height) * 0.08,
            float(page_rect.width),
            float(page_rect.height) * 0.72,
        )
        method = "page_region_fallback"
    if clip.is_empty or clip.width < 80 or clip.height < 80:
        return None
    pix = page.get_pixmap(matrix=_zoom_matrix(), clip=clip, alpha=False)
    data = pix.tobytes("png")
    if _looks_blank_png(data):
        return None
    return {
        "page": page_number,
        "data_url": "data:image/png;base64," + base64.b64encode(data).decode("ascii"),
        "width": pix.width,
        "height": pix.height,
        "bbox": [float(clip.x0), float(clip.y0), float(clip.x1), float(clip.y1)],
        "method": method,
    }


def _zoom_matrix() -> Any:
    import fitz  # type: ignore

    return fitz.Matrix(1.6, 1.6)


def _looks_blank_png(data: bytes) -> bool:
    try:
        from PIL import Image, ImageStat  # type: ignore
    except Exception:
        return False
    try:
        image = Image.open(io.BytesIO(data)).convert("L").resize((32, 32))
        stat = ImageStat.Stat(image)
        return bool(stat.extrema and stat.extrema[0][1] - stat.extrema[0][0] < 8)
    except Exception:
        return False


def _same_source(source: Any, path: Path) -> bool:
    source_text = str(source or "")
    return source_text == str(path) or Path(source_text).name == path.name


def _figure_key(value: Any) -> str:
    return re.sub(r"\W+", "", str(value or "").lower())
