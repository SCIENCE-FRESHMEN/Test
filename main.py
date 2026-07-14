from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from arm_agent.pipeline import PaperToARMOrchestrator, to_yaml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NEURONCLAW A-track Paper-to-ARM orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Generate a full ARM package or blocked failure report.")
    run.add_argument("--input", nargs="+", required=True, help="One to five paper text files.")
    run.add_argument("--output-dir", default="outputs", help="Directory for exported ARM assets.")
    run.add_argument("--format", choices=["json", "yaml", "both"], default="both", help="Console output format.")

    demo = sub.add_parser("demo", help="Run the bundled success and failure cases.")
    demo.add_argument("--output-dir", default="outputs", help="Directory for exported demo assets.")
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        orchestrator = PaperToARMOrchestrator(output_dir=args.output_dir)
        result = orchestrator.run(args.input, export_yaml=args.format in {"yaml", "both"})
        payload = result.model_dump()
        if args.format == "yaml":
            print(to_yaml(payload))
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command == "demo":
        success_input = Path("brain_ECS_review.txt")
        failure_input = Path("fixtures/incomplete_paper.txt")
        orchestrator = PaperToARMOrchestrator(output_dir=args.output_dir)
        success = orchestrator.run([str(success_input)], export_yaml=True)
        failure = orchestrator.run([str(failure_input)], export_yaml=True)
        summary = {
            "deepseek_api_key_configured": bool(os.getenv("DEEPSEEK_API_KEY")),
            "success": {
                "status": success.full_arm.metadata.processing_status if hasattr(success.full_arm, "metadata") else "unknown",
                "arm_id": success.full_arm.metadata.arm_id if hasattr(success.full_arm, "metadata") else None,
                "claims": len(success.full_arm.claims) if hasattr(success.full_arm, "claims") else 0,
                "ecs_related": success.full_arm.metadata.ecs_related if hasattr(success.full_arm, "metadata") else None,
                "run_id": success.trace_record.run_id,
            },
            "failure": {
                "status": failure.full_arm["metadata"]["processing_status"],
                "blocked": failure.full_arm["failure_report"]["no_success_arm_generated"],
                "risks": failure.full_arm["failure_report"]["missing_or_risky_items"],
                "run_id": failure.trace_record.run_id,
            },
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
