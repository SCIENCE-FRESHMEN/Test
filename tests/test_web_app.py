from pathlib import Path

from fastapi.testclient import TestClient

from web_app import app


def test_web_home_and_materials() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "data-example" not in response.text
    assert "图表证据" in response.text
    materials = client.get("/api/project-materials").json()["materials"]
    assert len(materials) >= 10
    assert any(item["name"] == "提交检查清单" for item in materials)
    assert any(item["name"] == "七日开发日志" for item in materials)


def test_web_upload_failure_returns_review_gate() -> None:
    client = TestClient(app)
    with Path("fixtures/incomplete_paper.txt").open("rb") as handle:
        response = client.post(
            "/api/upload-run",
            files=[("files", ("incomplete_paper.txt", handle, "text/plain"))],
        )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "completed"
    assert job["summary"]["processing_status"] == "failed"
    assert job["summary"]["review_gate"]["failure_blocking"] is True


def test_web_p0_panels_endpoint() -> None:
    client = TestClient(app)
    with Path("fixtures/incomplete_paper.txt").open("rb") as handle:
        response = client.post(
            "/api/upload-run",
            files=[("files", ("incomplete_paper.txt", handle, "text/plain"))],
        )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    panel = client.get(f"/api/jobs/{job_id}/p0-panels").json()
    assert "figure_evidence" in panel
    assert "dry_run" in panel
