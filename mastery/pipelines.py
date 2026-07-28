"""Mandatory pipelines.

CLAUDE.md: "These sequences are enforced in orchestrator code. The manager
cannot skip a stage." So a pipeline here is an ordered list the orchestrator
walks one stage at a time. There is no API for jumping to a stage — `advance()`
only ever returns the next one, and a closed gate ends the walk.

Stages after `OPERATOR_APPROVAL` are never reached by the orchestrator: the run
halts there and returns to the operator. They are listed so the pipeline
definition matches the doc, and so the operator-facing summary can name what is
waiting on them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .schema import Status, TaskResult

OPERATOR_APPROVAL = "<operator approval>"


class Trigger(str, Enum):
    PUBLIC_OUTPUT = "public-output"
    RELEASE = "release"


@dataclass(frozen=True)
class Pipeline:
    trigger: Trigger
    stages: tuple[str, ...]
    # Agents whose `blocked` return halts the whole pipeline, with the verdict
    # each one is returning when it does.
    halting_gates: dict[str, str]

    def first(self) -> str:
        return self.stages[0]

    def advance(self, current: str) -> str | None:
        """The stage after `current`, or None if the pipeline is done.

        Raises ValueError if `current` is not in this pipeline — a stage the
        pipeline does not contain cannot be a position in it.
        """
        try:
            index = self.stages.index(current)
        except ValueError:
            raise ValueError(
                f"{current!r} is not a stage of the {self.trigger.value} pipeline"
            ) from None
        if index + 1 >= len(self.stages):
            return None
        return self.stages[index + 1]

    def halts_on(self, agent: str) -> str | None:
        """The closed-gate verdict this agent returns, if it is a halting gate."""
        return self.halting_gates.get(agent)


PUBLIC_OUTPUT = Pipeline(
    trigger=Trigger.PUBLIC_OUTPUT,
    stages=("content", "fact-checker", "risk-review", OPERATOR_APPROVAL, "publish"),
    halting_gates={
        "fact-checker": "not publishable",
        "risk-review": "hold",
        "legal-review": "counsel required",
    },
)

RELEASE = Pipeline(
    trigger=Trigger.RELEASE,
    stages=("mobile-dev", "qa", OPERATOR_APPROVAL, "promote to track"),
    halting_gates={"qa": "no-go"},
)

ALL: dict[Trigger, Pipeline] = {
    Trigger.PUBLIC_OUTPUT: PUBLIC_OUTPUT,
    Trigger.RELEASE: RELEASE,
}


def for_agent(agent: str) -> Pipeline | None:
    """The pipeline an agent belongs to, if any.

    Used to catch a delegation that starts mid-pipeline: briefing `risk-review`
    directly skips `content` and `fact-checker`, which the orchestrator refuses.
    """
    for pipeline in ALL.values():
        if agent in pipeline.stages:
            return pipeline
    return None


def needs_legal_review(result: TaskResult, *, names_real_party: bool) -> bool:
    """Whether legal-review is inserted before operator approval.

    Two triggers from CLAUDE.md: either reviewer escalates, or a real party is
    named. Escalation is read from `status`, never from the prose in `summary`
    — a reviewer that escalates returns `blocked`, per the escalation rule.
    `names_real_party` is an operator-declared fact about the draft, not
    something inferred from the text.
    """
    return names_real_party or result.status is Status.BLOCKED
