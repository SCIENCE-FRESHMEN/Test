from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arm_agent.extensions.benchmark import run_quantitative_benchmark
from tools.literature_search_online import literature_search_online


def main() -> None:
    out = Path("outputs/full_score_demo")
    out.mkdir(parents=True, exist_ok=True)
    search = literature_search_online("brain extracellular space", 2020, 2026)
    benchmark = run_quantitative_benchmark("tests/report/quantitative_report.md")
    payload = {"search": search, "benchmark": benchmark, "demo_mode_url": "/static/demo_mode.html"}
    (out / "full_score_extension_demo.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "output": str(out / "full_score_extension_demo.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
