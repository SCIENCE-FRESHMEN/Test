from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_model: str
    max_batch_size: int
    max_claims_per_paper: int
    min_success_claims: int
    output_dir: Path
    enable_caption_ocr: bool
    dry_run_timeout_seconds: int
    max_upload_mb: int
    api_request_interval_seconds: float
    api_max_concurrency: int
    api_retry_attempts: int
    api_retry_backoff_seconds: float
    api_timeout_seconds: int


def get_settings() -> Settings:
    return Settings(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY") or None,
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        max_batch_size=int(os.getenv("ARM_MAX_BATCH_SIZE", "5")),
        max_claims_per_paper=int(os.getenv("ARM_MAX_CLAIMS_PER_PAPER", "12")),
        min_success_claims=int(os.getenv("ARM_MIN_SUCCESS_CLAIMS", "5")),
        output_dir=Path(os.getenv("ARM_OUTPUT_DIR", "outputs")),
        enable_caption_ocr=os.getenv("ARM_ENABLE_CAPTION_OCR", "false").lower() == "true",
        dry_run_timeout_seconds=int(os.getenv("ARM_DRY_RUN_TIMEOUT_SECONDS", "30")),
        max_upload_mb=int(os.getenv("ARM_MAX_UPLOAD_MB", "80")),
        api_request_interval_seconds=float(os.getenv("ARM_API_REQUEST_INTERVAL_SECONDS", "1.2")),
        api_max_concurrency=int(os.getenv("ARM_API_MAX_CONCURRENCY", "1")),
        api_retry_attempts=int(os.getenv("ARM_API_RETRY_ATTEMPTS", "3")),
        api_retry_backoff_seconds=float(os.getenv("ARM_API_RETRY_BACKOFF_SECONDS", "2.0")),
        api_timeout_seconds=int(os.getenv("ARM_API_TIMEOUT_SECONDS", "60")),
    )
