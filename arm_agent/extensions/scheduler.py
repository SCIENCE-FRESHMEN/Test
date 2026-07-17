from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Priority = Literal["light", "heavy", "online"]


@dataclass(frozen=True)
class ScheduledTask:
    name: str
    priority: Priority
    sequence: int
    rationale: str


def schedule_tasks(task_names: list[str]) -> list[dict]:
    order = {"light": 0, "heavy": 1, "online": 2}
    tasks = []
    for index, name in enumerate(task_names):
        priority: Priority = "light"
        if "figure" in name or "conflict" in name:
            priority = "heavy"
        if "search" in name or "online" in name:
            priority = "online"
        tasks.append(ScheduledTask(name=name, priority=priority, sequence=index, rationale=f"{priority}_task_runtime_order"))
    return [task.__dict__ for task in sorted(tasks, key=lambda task: (order[task.priority], task.sequence))]
