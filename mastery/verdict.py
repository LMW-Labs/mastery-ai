"""Manager verification of a returned task.

Resolves the open item in CLAUDE.md: manager accept/revise/reject verdicts are
control flow but were not schema-bound. They are now, via the narrower of the
two options CLAUDE.md left open — a **verify-only invocation** that returns a
**minimal verdict schema**. Both, because the invocation needs a return
contract and the contract needs something to produce it.

Why verify-only rather than a conversational manager: the manager's routing,
gating, and context assembly are already code (orchestrator.py, gates.py,
brief.py). The one judgement that genuinely needs a model is "does this return
actually meet the brief's success criteria" — so that is the only thing the
manager is invoked for, with no tools and a single turn.

The verdict is checked against the brief's success criteria only. It is not a
second opinion on the work's quality, and it cannot widen scope.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .brief import TaskBrief
from .config import REPO_ROOT
from .errors import SchemaViolation
from .schema import TaskResult, extract_json

VERDICT_SCHEMA_PATH = REPO_ROOT / "docs" / "agents" / "manager_verdict_schema.md"


class Verdict(str, Enum):
    ACCEPT = "accept"  # criteria met; continue the pipeline
    REVISE = "revise"  # gap is nameable and fixable; retry with a corrected brief
    REJECT = "reject"  # wrong work, or unfixable by retry; return to operator


@lru_cache(maxsize=1)
def verdict_schema() -> dict:
    return json.loads(VERDICT_SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    return Draft202012Validator(verdict_schema())


@dataclass(frozen=True)
class ManagerVerdict:
    task_id: str
    verdict: Verdict
    reason: str
    revision_note: str | None = None

    @property
    def accepted(self) -> bool:
        return self.verdict is Verdict.ACCEPT


def build_prompt(brief: TaskBrief, result: TaskResult) -> str:
    """The verify-only prompt.

    The manager sees the brief's criteria and the return — not the context
    payload, and not the conversation that produced it. It is checking a
    contract, not re-doing the task.
    """
    criteria = "\n".join(f"- {c}" for c in brief.success_criteria)
    expected = "\n".join(f"- {d}" for d in brief.expected_deliverables)
    delivered = "\n".join(f"- {d}" for d in result.deliverables) or "- (none)"
    risks = "\n".join(f"- {r}" for r in result.risks) or "- (none)"

    return f"""You are verifying one returned task against the brief that produced it.

Decide only whether the return meets the success criteria as written. Do not
re-do the work, do not judge quality beyond the criteria, and do not widen
scope. If a criterion cannot be checked from what was returned, it is not met.

## The brief

task_id: {brief.task_id}
agent: {brief.agent}
objective: {brief.objective}

Success criteria:
{criteria}

Expected deliverables:
{expected}

## The return

status: {result.status.value}
summary: {result.summary}

Deliverables:
{delivered}

Risks:
{risks}

next_step: {result.next_step}

## Your verdict

Reply with one JSON object and nothing else:

{{"task_id": "{brief.task_id}", "verdict": "accept" | "revise" | "reject", "reason": "<one or two sentences>", "revision_note": "<required only when verdict is revise: what the corrected brief must change>"}}

- accept  — every success criterion is met by what was returned.
- revise  — a specific, nameable gap that a corrected brief could close.
- reject  — the wrong work was done, or the gap cannot be closed by retrying.
"""


def parse(raw: str, *, expected_task_id: str) -> ManagerVerdict:
    """Validate a verdict return. Raises SchemaViolation, same as a task return."""
    try:
        payload = json.loads(extract_json(raw))
    except json.JSONDecodeError as exc:
        raise SchemaViolation(f"verdict is not valid JSON: {exc}", raw=raw) from exc

    errors = sorted(_validator().iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(
            f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        )
        raise SchemaViolation(f"verdict failed schema validation: {detail}", raw=raw)

    if payload["task_id"] != expected_task_id:
        raise SchemaViolation(
            f"verdict task_id mismatch: expected {expected_task_id!r}, "
            f"got {payload['task_id']!r}",
            raw=raw,
        )

    return ManagerVerdict(
        task_id=payload["task_id"],
        verdict=Verdict(payload["verdict"]),
        reason=payload["reason"],
        revision_note=payload.get("revision_note"),
    )
