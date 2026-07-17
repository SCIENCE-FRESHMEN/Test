from __future__ import annotations

import json
from pathlib import Path

from .state import GraphCheckpoint, GraphRunState


class JsonCheckpointStore:
    def __init__(self, root: str = "outputs/langgraph_checkpoints") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    def save(self, state: GraphRunState) -> GraphCheckpoint:
        path = self.path_for(state.run_id)
        checkpoint = GraphCheckpoint(checkpoint_id=state.run_id, state=state, storage_path=str(path))
        path.write_text(checkpoint.model_dump_json(indent=2), encoding="utf-8")
        return checkpoint

    def load(self, run_id: str) -> GraphRunState | None:
        path = self.path_for(run_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return GraphCheckpoint(**payload).state
