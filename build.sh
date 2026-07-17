#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r requirements.txt
python scripts/full_score_demo.py
python -m pytest tests --basetemp=/tmp/pytest_tmp
mkdir -p outputs/package
python main.py demo --output-dir outputs/package
printf "Build complete. Web: uvicorn web_app:app --host 127.0.0.1 --port 8000\n"

