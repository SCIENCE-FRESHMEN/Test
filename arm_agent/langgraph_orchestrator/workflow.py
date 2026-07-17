from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from arm_agent.pipeline import PaperToARMOrchestrator

from .checkpoint import JsonCheckpointStore
from .state import GraphRunState, HumanReviewRequest, PaperTaskState


class LangGraphEnhancedOrchestrator:
    """Optional checkpointed orchestrator.

    It does not replace the existing PaperToARMOrchestrator. When LangGraph is
    unavailable, this class still provides the same checkpoint/retry/review
    semantics through a deterministic fallback loop.
    """

    def __init__(self, output_dir: str = "outputs/langgraph_runs", checkpoint_dir: str = "outputs/langgraph_checkpoints") -> None:
        self.output_dir = output_dir
        self.store = JsonCheckpointStore(checkpoint_dir)

    def start(self, paper_files: list[str], run_id: str | None = None) -> dict[str, Any]:
        state = GraphRunState(run_id=run_id or f"lg-{uuid4().hex[:12]}", paper_tasks=[PaperTaskState(source_file=item) for item in paper_files])
        self.store.save(state)
        return self.resume(state.run_id)

    def resume(self, run_id: str) -> dict[str, Any]:
        state = self.store.load(run_id)
        if state is None:
            raise FileNotFoundError(f"No checkpoint found for run_id={run_id}")
        while state.cursor < len(state.paper_tasks):
            task = state.paper_tasks[state.cursor]
            if task.status == "completed":
                state.cursor += 1
                continue
            self._run_single_task(state, task)
            self.store.save(state)
            state.cursor += 1
        state.completed = True
        self.store.save(state)
        return {"status": "completed", "run_id": state.run_id, "state": state.model_dump()}

    def approve(self, run_id: str, review_id: str, decision: str = "approved", supplement: dict[str, Any] | None = None) -> dict[str, Any]:
        state = self.store.load(run_id)
        if state is None:
            raise FileNotFoundError(f"No checkpoint found for run_id={run_id}")
        for review in state.review_requests:
            if review.review_id == review_id:
                review.status = decision  # type: ignore[assignment]
                if supplement:
                    review.payload["supplement"] = supplement
        self.store.save(state)
        return {"status": "review_updated", "run_id": run_id, "review_id": review_id, "decision": decision}

    def _run_single_task(self, state: GraphRunState, task: PaperTaskState) -> None:
        task.status = "running"
        task.attempts += 1
        task.trace.append({"stage": "task_started", "attempt": task.attempts})
        try:
            if not Path(task.source_file).exists():
                raise FileNotFoundError(task.source_file)
            result = PaperToARMOrchestrator(output_dir=self.output_dir).run([task.source_file], export_yaml=False)
            payload = result.model_dump()
            task.result = payload
            metadata = payload["full_arm"].get("metadata", {}) if isinstance(payload["full_arm"], dict) else {}
            if metadata.get("processing_status") == "failed":
                task.status = "isolated"
                task.failure_report = payload["full_arm"].get("failure_report")
                state.review_requests.append(HumanReviewRequest(review_id=f"review-{len(state.review_requests)+1:03d}", reason="tool_failure", payload={"source_file": task.source_file}))
            else:
                task.status = "completed"
            task.trace.append({"stage": "task_finished", "status": task.status})
        except Exception as exc:  # noqa: BLE001 - isolated failure report for batch tolerance.
            task.status = "failed" if task.attempts >= 2 else "isolated"
            task.failure_report = {"status": "blocked", "reason": type(exc).__name__, "message": str(exc), "source_file": task.source_file}
            task.trace.append({"stage": "task_failed", "error": str(exc)})
            state.review_requests.append(HumanReviewRequest(review_id=f"review-{len(state.review_requests)+1:03d}", reason="tool_failure", payload=task.failure_report))
