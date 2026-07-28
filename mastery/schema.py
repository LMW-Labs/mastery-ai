"""Structured output: parse, validate, branch.

The schema itself lives in docs/agents/structured_output_schema.md and is
loaded from there — one definition, not a copy that drifts.

Two rules from CLAUDE.md are load-bearing here:

  - `status` is the only field the orchestrator branches on. It is never
    inferred from prose. `summary`, `risks`, and `next_step` are for humans and
    are never parsed for control flow.
  - Validation failure is a task failure, not something to patch. There is no
    repair path in this module.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema import ValidationError as _JsonSchemaError

from .config import REPO_ROOT
from .errors import SchemaViolation

SCHEMA_PATH = REPO_ROOT / "docs" / "agents" / "structured_output_schema.md"


class Status(str, Enum):
    """The four terminal states of a delegated task."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"


class Action(str, Enum):
    """What the orchestrator does with a return. Derived from `status` alone."""

    ACCEPT = "accept"  # complete: verify, then continue the pipeline
    REVIEW = "review"  # partial: back to the manager for accept-or-retry
    RETRY = "retry"  # failed: one retry with a corrected brief, then report
    HALT = "halt"  # blocked: return to operator, no retry


# The status table from CLAUDE.md, as a dispatch map rather than prose.
ACTION_FOR: dict[Status, Action] = {
    Status.COMPLETE: Action.ACCEPT,
    Status.PARTIAL: Action.REVIEW,
    Status.FAILED: Action.RETRY,
    Status.BLOCKED: Action.HALT,
}


@lru_cache(maxsize=1)
def schema() -> dict:
    """The output contract, read from its doc."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    return Draft202012Validator(schema())


@dataclass(frozen=True)
class TaskResult:
    """A validated sub-agent return."""

    task_id: str
    status: Status
    summary: str
    deliverables: tuple[str, ...]
    risks: tuple[str, ...]
    next_step: str

    @property
    def action(self) -> Action:
        return ACTION_FOR[self.status]

    @property
    def is_gate_closed(self) -> bool:
        """True when this is a gate returning closed.

        A risk-review `hold`, a fact-checker `not publishable`, a qa `no-go`, a
        legal-review `counsel-required` — all of these return `blocked`, so the
        orchestrator halts rather than treating a closed gate as a completed
        task that happens to say no in its prose.
        """
        return self.status is Status.BLOCKED


def extract_json(raw: str) -> str:
    """Pull the JSON object out of a model's final text.

    Accepts a bare object or one inside a ```json fence. Deliberately narrow:
    if the return is not recognisably a single JSON object, that is a schema
    violation, not something to salvage with a looser parse.
    """
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise SchemaViolation("no JSON object found in the return", raw=raw)
    return text[start : end + 1]


def parse(raw: str, *, expected_task_id: str | None = None) -> TaskResult:
    """Validate a raw return and build a TaskResult. Raises SchemaViolation."""
    payload_text = extract_json(raw)
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise SchemaViolation(f"return is not valid JSON: {exc}", raw=raw) from exc

    errors = sorted(_validator().iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(_describe(e) for e in errors)
        raise SchemaViolation(f"return failed schema validation: {detail}", raw=raw)

    if expected_task_id is not None and payload["task_id"] != expected_task_id:
        # The brief says the task_id is "echoed back verbatim". A mismatch means
        # the return belongs to a different task, so it cannot be accepted for
        # this one.
        raise SchemaViolation(
            f"task_id mismatch: brief was {expected_task_id!r}, "
            f"return echoed {payload['task_id']!r}",
            raw=raw,
        )

    return TaskResult(
        task_id=payload["task_id"],
        status=Status(payload["status"]),
        summary=payload["summary"],
        deliverables=tuple(payload["deliverables"]),
        risks=tuple(payload["risks"]),
        next_step=payload["next_step"],
    )


def _describe(error: _JsonSchemaError) -> str:
    where = ".".join(str(p) for p in error.path) or "<root>"
    return f"{where}: {error.message}"
