from __future__ import annotations

from typing import Any


def ocr_scanned_pdf_stub(source_file: str) -> dict[str, Any]:
    """OCR integration placeholder with explicit review boundary.

    The project does not claim full image OCR unless an OCR backend is installed.
    This wrapper returns a standardized review-required result for scanned PDFs.
    """
    return {
        "status": "ocr_review_required",
        "source_file": source_file,
        "text_blocks": [],
        "risks": [{"code": "ocr_backend_not_configured", "severity": "medium", "review_required": True}],
        "trace": [{"stage": "ocr_stub_called", "source_file": source_file}],
    }
