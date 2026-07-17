from pathlib import Path

from fastapi.testclient import TestClient

from tools.pdf_parser_tools.figure_images import extract_pdf_figure_images, match_images_to_captions
from web_app import app


def test_materials_tab_removed_from_home() -> None:
    client = TestClient(app)
    html = client.get("/").text
    assert 'data-tab="materials"' not in html
    assert 'data-tab="figures"' in html
    assert '证据汇总 Excel' in html


def test_figure_image_tool_handles_txt_fallback() -> None:
    result = extract_pdf_figure_images("brain_ECS_review.txt")
    assert result["status"] == "figure_image_not_pdf"
    assert result["risks"]


def test_match_images_to_captions_keeps_caption_without_image() -> None:
    captions = [{"figure_id": "Figure 1", "source_file": "paper.pdf", "caption": "caption"}]
    result = match_images_to_captions([], captions)
    assert result[0]["caption"] == "caption"
    assert result[0]["image_status"] == "image_not_matched"


def test_web_figure_images_endpoint_for_failure_job() -> None:
    client = TestClient(app)
    with Path("fixtures/incomplete_paper.txt").open("rb") as handle:
        response = client.post("/api/upload-run", files=[("files", ("incomplete_paper.txt", handle, "text/plain"))])
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    payload = client.get(f"/api/jobs/{job_id}/figure-images").json()
    assert "figures_with_images" in payload
    assert "risks" in payload
