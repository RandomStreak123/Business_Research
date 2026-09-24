"""
Shared to-do list + activity log for a single run.

Keeps the pipeline inspectable: every agent action, task state change,
and model fallback gets written here, and it's persisted to a per-run
log file in data/logs/.
"""

import json
import os
import uuid
from datetime import datetime, timezone

from config import LOGS_DIR


class TaskManager:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or uuid.uuid4().hex[:8]
        self.tasks: dict[str, dict] = {}
        self.activity_log: list[dict] = []
        self.log_path = os.path.join(LOGS_DIR, f"{self.run_id}.log.jsonl")

    # -- to-do list -----------------------------------------------------
    def add_task(self, task_id: str, description: str, owner: str) -> None:
        self.tasks[task_id] = {
            "description": description,
            "owner": owner,
            "status": "pending",
            "created_at": self._now(),
        }
        self.log("task_added", owner, f"{task_id}: {description}")

    def start_task(self, task_id: str) -> None:
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "in_progress"
            self.log("task_started", self.tasks[task_id]["owner"], task_id)

    def complete_task(self, task_id: str, result_summary: str = "") -> None:
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "done"
            self.tasks[task_id]["result_summary"] = result_summary
            self.log("task_completed", self.tasks[task_id]["owner"], task_id)

    def fail_task(self, task_id: str, reason: str = "") -> None:
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["failure_reason"] = reason
            self.log("task_failed", self.tasks[task_id]["owner"], f"{task_id}: {reason}")

    def pending_tasks(self) -> list[dict]:
        return [
            {"id": tid, **t}
            for tid, t in self.tasks.items()
            if t["status"] in ("pending", "in_progress")
        ]

    def summary(self) -> str:
        lines = []
        for tid, t in self.tasks.items():
            lines.append(f"[{t['status'].upper():>11}] {tid} ({t['owner']}): {t['description']}")
        return "\n".join(lines)

    # -- activity log -----------------------------------------------------
    def log(self, event: str, agent: str, detail: str) -> None:
        entry = {
            "ts": self._now(),
            "run_id": self.run_id,
            "event": event,
            "agent": agent,
            "detail": detail,
        }
        self.activity_log.append(entry)
        self._persist(entry)
        print(f"[{entry['ts']}] ({agent}) {event}: {detail}")

    def _persist(self, entry: dict) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
