"""Run log.

manager.md: "Log every delegation: task ID, agent, context size, result status."
One JSONL file per operator request, appended as the run proceeds so a run that
dies mid-flight still leaves a record of how far it got.

The log records what happened, including failures. It is written before the
outcome is known (`delegation_start`) and again after (`delegation_end`), so a
timeout or a crash is visible as a start with no end rather than as silence.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RunLog:
    path: Path
    run_id: str

    @classmethod
    def open(cls, log_dir: Path, run_id: str) -> "RunLog":
        log_dir.mkdir(parents=True, exist_ok=True)
        return cls(path=log_dir / f"{run_id}.jsonl", run_id=run_id)

    def write(self, event: str, **fields: Any) -> None:
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "run_id": self.run_id,
            "event": event,
            **fields,
        }
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # -- the events the orchestrator emits ----------------------------------

    def run_start(self, request: str) -> None:
        self.write("run_start", request=request)

    def delegation_start(self, *, task_id: str, agent: str, context_bytes: int, attempt: int) -> None:
        self.write(
            "delegation_start",
            task_id=task_id,
            agent=agent,
            context_bytes=context_bytes,
            attempt=attempt,
        )

    def delegation_end(self, *, task_id: str, agent: str, status: str, duration_s: float) -> None:
        self.write(
            "delegation_end",
            task_id=task_id,
            agent=agent,
            status=status,
            duration_s=round(duration_s, 2),
        )

    def verdict(self, *, task_id: str, verdict: str, reason: str) -> None:
        self.write("verdict", task_id=task_id, verdict=verdict, reason=reason)

    def gate_hit(self, *, gate: str, detail: str, task_id: str | None = None) -> None:
        self.write("gate_hit", gate=gate, detail=detail, task_id=task_id)

    def failure(self, *, kind: str, detail: str, task_id: str | None = None) -> None:
        self.write("failure", kind=kind, detail=detail, task_id=task_id)

    def run_end(self, *, outcome: str, detail: str) -> None:
        self.write("run_end", outcome=outcome, detail=detail)

    def read(self) -> list[dict]:
        """Every record in this run, for tests and the operator summary."""
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
