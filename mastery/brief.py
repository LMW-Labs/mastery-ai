"""The delegation contract, manager -> sub-agent.

Implements docs/agents/task_brief_template.md. Every section is filled before
the brief is sent; a section that genuinely does not apply carries the explicit
word `none`, not an empty string. An unfilled brief is not sent — it raises
BriefIncomplete, which the orchestrator surfaces as an escalation rather than
filling the gap with a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ids
from .errors import BriefIncomplete, ContextTooLarge
from .roster import Agent, get as get_agent

# Sections that must carry text. `urgency` and `approval_gates_touched` accept
# the literal `none`; blank is still a failure.
_REQUIRED_TEXT = ("objective", "constraints", "out_of_scope", "urgency", "approval_gates_touched")
_REQUIRED_LISTS = ("success_criteria", "expected_deliverables")


@dataclass(frozen=True)
class ContextItem:
    """One item in the context payload.

    `label` is what the brief lists under `Context provided`; `body` is the
    actual text handed to the agent. Naming each item is the point — the
    template requires context be "named, not gestured at".
    """

    label: str
    body: str

    def size(self) -> int:
        return len(self.body.encode("utf-8"))


@dataclass(frozen=True)
class TaskBrief:
    task_id: str
    agent: str
    vertical: str
    urgency: str
    objective: str
    success_criteria: tuple[str, ...]
    context: tuple[ContextItem, ...]
    constraints: str
    out_of_scope: str
    approval_gates_touched: str
    expected_deliverables: tuple[str, ...]

    # Set when this brief is the corrected retry of a failed task.
    retry_of: str | None = field(default=None, compare=False)

    def agent_def(self) -> Agent:
        return get_agent(self.agent)

    # -- validation ---------------------------------------------------------

    def validate(self, max_context_bytes: int) -> None:
        """Reject an unfilled or over-limit brief. Called before every send."""
        if not ids.is_valid(self.task_id):
            raise BriefIncomplete(
                f"task_id {self.task_id!r} is not YYYYMMDD-<ff|rd|ops>-NNN"
            )

        agent = self.agent_def()  # raises RoutingError if unknown
        if agent.name == "manager":
            raise BriefIncomplete(
                "the manager is the orchestrator, not a delegation target"
            )

        for name in _REQUIRED_TEXT:
            value = getattr(self, name)
            if not value or not value.strip() or value.strip().upper() == "TBD":
                raise BriefIncomplete(
                    f"section {name!r} is blank or TBD; "
                    f"write `none` if it does not apply, or escalate for the missing input"
                )

        for name in _REQUIRED_LISTS:
            value = getattr(self, name)
            if not value or not all(item.strip() for item in value):
                raise BriefIncomplete(f"section {name!r} is empty or has a blank entry")

        if not self.context:
            raise BriefIncomplete(
                "context payload is empty; the agent's own doc must at minimum be passed "
                "(agent docs are not auto-loaded for delegated sub-agents)"
            )

        labels = [item.label for item in self.context]
        expected_doc = f"docs/agents/{agent.name}.md"
        if expected_doc not in labels:
            raise BriefIncomplete(
                f"context payload does not include {expected_doc}; "
                f"without it the agent has no role definition"
            )

        size = self.context_bytes()
        if size > max_context_bytes:
            raise ContextTooLarge(
                f"context payload is {size} bytes, over the {max_context_bytes} limit; "
                f"narrow the brief rather than truncating the payload"
            )

    def context_bytes(self) -> int:
        return sum(item.size() for item in self.context)

    # -- rendering ----------------------------------------------------------

    def render(self) -> str:
        """The brief as markdown, matching task_brief_template.md."""
        criteria = "\n".join(f"- {c}" for c in self.success_criteria)
        provided = "\n".join(f"- {item.label}" for item in self.context)
        deliverables = "\n".join(f"- {d}" for d in self.expected_deliverables)
        return f"""# Task Brief

**task_id:** {self.task_id}
**agent:** {self.agent}
**vertical:** {self.vertical}
**urgency:** {self.urgency}

## Objective
{self.objective}

## Success criteria
{criteria}

## Context provided
{provided}

## Constraints
{self.constraints}

## Out of scope
{self.out_of_scope}

## Approval gates touched
{self.approval_gates_touched}

## Expected deliverables
{deliverables}
"""

    def render_context(self) -> str:
        """The context payload itself, labelled item by item.

        Nothing outside this list reaches the agent. There is no path in this
        codebase that appends CLAUDE.md, chat history, or unrelated docs.
        """
        blocks = []
        for item in self.context:
            blocks.append(f"<context label=\"{item.label}\">\n{item.body}\n</context>")
        return "\n\n".join(blocks)


def build(
    *,
    task_id: str,
    agent: str,
    urgency: str,
    objective: str,
    success_criteria: list[str],
    context: list[ContextItem],
    constraints: str,
    out_of_scope: str,
    approval_gates_touched: str,
    expected_deliverables: list[str],
    retry_of: str | None = None,
) -> TaskBrief:
    """Assemble a brief, prepending the agent's own doc to the context payload.

    The doc is prepended here rather than left to the caller because forgetting
    it is the single most likely delegation bug: the agent runs with no role
    definition and the failure looks like a bad model rather than a bad brief.
    """
    if not ids.is_valid(task_id):
        # Caught here rather than in validate() so a malformed ID fails at the
        # point it was written, not after the brief is otherwise assembled.
        raise BriefIncomplete(
            f"task_id {task_id!r} is not YYYYMMDD-<ff|rd|ops>-NNN"
        )

    agent_def = get_agent(agent)
    doc_label = f"docs/agents/{agent_def.name}.md"
    items = list(context)
    if not any(item.label == doc_label for item in items):
        items.insert(0, ContextItem(doc_label, agent_def.doc()))

    return TaskBrief(
        task_id=task_id,
        agent=agent,
        vertical=ids.vertical_name(task_id),
        urgency=urgency,
        objective=objective,
        success_criteria=tuple(success_criteria),
        context=tuple(items),
        constraints=constraints,
        out_of_scope=out_of_scope,
        approval_gates_touched=approval_gates_touched,
        expected_deliverables=tuple(expected_deliverables),
        retry_of=retry_of,
    )
