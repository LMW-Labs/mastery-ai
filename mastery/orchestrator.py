"""The run loop.

This is the manager: it routes, assembles context, enforces the gates and caps,
verifies returns, and reports. Every guardrail in CLAUDE.md that says "enforced
in orchestrator code" is enforced from here or from a module this one calls.

The shape of one delegation:

    validate brief -> check gates -> delegate -> validate return
                   -> branch on status -> manager verdict -> accept or retry

and the two things it will not do: proceed past a gate, or accept a return it
could not validate.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from . import delegate, gates, pipelines, verdict as verdict_mod
from .brief import TaskBrief
from .config import Config
from .errors import (
    CapExceeded,
    DelegationFailed,
    GateHit,
    OrchestratorError,
    SchemaViolation,
    TaskTimeout,
)
from .runlog import RunLog
from .schema import Action, Status, TaskResult, parse as parse_result
from .verdict import ManagerVerdict, Verdict


class Outcome(str, Enum):
    ACCEPTED = "accepted"  # criteria met and verified
    HALTED = "halted"  # gate hit or blocked return; operator owns the next move
    FAILED = "failed"  # could not complete after the allowed retry
    NEEDS_APPROVAL = "needs_approval"  # pipeline reached its operator-approval stage


@dataclass
class DelegationOutcome:
    """What one delegation produced, and what the operator should do next."""

    outcome: Outcome
    task_id: str
    agent: str
    result: TaskResult | None = None
    manager_verdict: ManagerVerdict | None = None
    detail: str = ""
    attempts: int = 1

    @property
    def accepted(self) -> bool:
        return self.outcome is Outcome.ACCEPTED


@dataclass
class PipelineOutcome:
    outcome: Outcome
    trigger: pipelines.Trigger
    completed_stages: list[DelegationOutcome] = field(default_factory=list)
    detail: str = ""

    @property
    def last(self) -> DelegationOutcome | None:
        return self.completed_stages[-1] if self.completed_stages else None


# Given the stage name and every accepted outcome so far, produce that stage's
# brief. This is where context is assembled by hand: the callback decides what
# prior output the next stage depends on, and nothing else is carried forward.
BriefFactory = Callable[[str, list[DelegationOutcome]], TaskBrief]


class Orchestrator:
    def __init__(
        self,
        config: Config,
        runner: delegate.Runner,
        *,
        run_id: str | None = None,
    ):
        self.config = config
        self.runner = runner
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.log = RunLog.open(config.log_dir, self.run_id)
        self._delegations = 0

    # -- one delegation -----------------------------------------------------

    async def execute(self, brief: TaskBrief) -> DelegationOutcome:
        """Run one brief to a verified outcome, with at most one retry."""
        attempt = 0
        current = brief

        while True:
            attempt += 1
            self._charge_delegation()

            current.validate(self.config.caps.max_context_bytes)

            # Before the work is briefed, not after it comes back.
            try:
                gates.enforce(current.approval_gates_touched)
            except GateHit as hit:
                self.log.gate_hit(gate=hit.gate, detail=hit.detail, task_id=current.task_id)
                return DelegationOutcome(
                    Outcome.HALTED,
                    current.task_id,
                    current.agent,
                    detail=f"approval gate '{hit.gate}': {hit.detail}",
                    attempts=attempt,
                )

            self.log.delegation_start(
                task_id=current.task_id,
                agent=current.agent,
                context_bytes=current.context_bytes(),
                attempt=attempt,
                # The allowlist this delegation is actually dispatched with,
                # read from the roster — not what the agent reports having.
                tools=list(current.agent_def().tools),
            )

            try:
                invocation = await delegate.run_task(current, self.runner, self.config)
                result = parse_result(invocation.raw, expected_task_id=current.task_id)
            except (SchemaViolation, TaskTimeout, DelegationFailed) as exc:
                # All three are task failures. A schema violation is not
                # repaired, a timeout is not silently extended, and a delegation
                # that ended without a result (turn exhaustion) is reported
                # rather than crashing the run.
                self.log.failure(
                    kind=type(exc).__name__, detail=str(exc), task_id=current.task_id
                )
                if attempt > self.config.caps.retries_per_failed_task:
                    return DelegationOutcome(
                        Outcome.FAILED,
                        current.task_id,
                        current.agent,
                        detail=str(exc),
                        attempts=attempt,
                    )
                # Corrected, not identical: tell the agent what was wrong with
                # the return, or it has no reason to produce a different one.
                current = _corrected(current, str(exc))
                continue

            self.log.delegation_end(
                task_id=current.task_id,
                agent=current.agent,
                status=result.status.value,
                duration_s=invocation.duration_s,
                num_turns=invocation.num_turns,
                cost_usd=invocation.cost_usd,
                permission_denials=list(invocation.permission_denials),
                # The work product itself. A `failed` run can still carry
                # usable output, and without this it survives only in
                # terminal scrollback.
                summary=result.summary,
                deliverables=list(result.deliverables),
                risks=list(result.risks),
                next_step=result.next_step,
                usage=invocation.usage,
            )

            action = result.action

            if action is Action.HALT:
                # Includes a review gate returning closed. No retry.
                self.log.gate_hit(
                    gate="blocked-return", detail=result.next_step, task_id=result.task_id
                )
                return DelegationOutcome(
                    Outcome.HALTED,
                    result.task_id,
                    current.agent,
                    result=result,
                    detail=result.next_step,
                    attempts=attempt,
                )

            if action is Action.RETRY:
                if attempt > self.config.caps.retries_per_failed_task:
                    return DelegationOutcome(
                        Outcome.FAILED,
                        result.task_id,
                        current.agent,
                        result=result,
                        detail=result.summary,
                        attempts=attempt,
                    )
                current = _corrected(current, result.summary)
                continue

            # complete or partial: the manager still verifies. A `complete`
            # status is a claim, not a clearance — see verdict.py.
            try:
                mv = await self._verify(current, result)
            except (SchemaViolation, TaskTimeout, DelegationFailed) as exc:
                # The verification failed, not the task. The delegation is
                # already done and paid for, so the work must survive — before
                # this was caught, a one-turn verdict call blowing up took a
                # 30-turn research run down with it and the only copy left was
                # the run log.
                #
                # It is still not an accept: an unverified return has not been
                # checked against its criteria, and this is the one place that
                # check happens. Report it as failed, attach the work, and name
                # verification as the cause so it is not mistaken for the
                # sub-agent's failure. No retry — re-running the delegation
                # would pay for the same work twice to fix a manager-side fault.
                self.log.failure(
                    kind=f"verification/{type(exc).__name__}",
                    detail=str(exc),
                    task_id=result.task_id,
                )
                return DelegationOutcome(
                    Outcome.FAILED,
                    result.task_id,
                    current.agent,
                    result=result,
                    detail=(
                        f"the task returned {result.status.value}, but the manager "
                        f"verdict could not be produced: {exc}. The work is attached "
                        f"and logged; it has not been verified against the brief."
                    ),
                    attempts=attempt,
                )

            if mv.verdict is Verdict.ACCEPT:
                return DelegationOutcome(
                    Outcome.ACCEPTED,
                    result.task_id,
                    current.agent,
                    result=result,
                    manager_verdict=mv,
                    attempts=attempt,
                )

            if mv.verdict is Verdict.REJECT:
                return DelegationOutcome(
                    Outcome.FAILED,
                    result.task_id,
                    current.agent,
                    result=result,
                    manager_verdict=mv,
                    detail=mv.reason,
                    attempts=attempt,
                )

            # revise
            if attempt > self.config.caps.retries_per_failed_task:
                return DelegationOutcome(
                    Outcome.FAILED,
                    result.task_id,
                    current.agent,
                    result=result,
                    manager_verdict=mv,
                    detail=f"still not accepted after {attempt} attempts: {mv.reason}",
                    attempts=attempt,
                )
            current = _corrected(current, mv.revision_note or mv.reason)

    async def _verify(self, brief: TaskBrief, result: TaskResult) -> ManagerVerdict:
        prompt = verdict_mod.build_prompt(brief, result)
        invocation = await delegate.run_verdict(prompt, self.runner, self.config)
        mv = verdict_mod.parse(invocation.raw, expected_task_id=brief.task_id)
        self.log.verdict(
            task_id=mv.task_id,
            verdict=mv.verdict.value,
            reason=mv.reason,
            duration_s=invocation.duration_s,
            num_turns=invocation.num_turns,
            cost_usd=invocation.cost_usd,
            usage=invocation.usage,
        )
        return mv

    def _charge_delegation(self) -> None:
        if self._delegations >= self.config.caps.max_delegations_per_request:
            raise CapExceeded(
                f"hit the cap of {self.config.caps.max_delegations_per_request} "
                f"delegations for one operator request; stopping and reporting"
            )
        self._delegations += 1

    # -- a pipeline ---------------------------------------------------------

    async def run_pipeline(
        self, trigger: pipelines.Trigger, make_brief: BriefFactory
    ) -> PipelineOutcome:
        """Walk a mandatory pipeline, one stage at a time.

        The sequence comes from pipelines.py; `make_brief` only fills in the
        brief for whichever stage the pipeline says is next. It cannot choose
        the stage, skip one, or reorder them.
        """
        pipeline = pipelines.ALL[trigger]
        completed: list[DelegationOutcome] = []
        stage: str | None = pipeline.first()

        self.log.write("pipeline_start", trigger=trigger.value, stages=list(pipeline.stages))

        while stage is not None:
            if stage == pipelines.OPERATOR_APPROVAL:
                self.log.run_end(
                    outcome="needs_approval", detail=f"{trigger.value} awaiting operator"
                )
                return PipelineOutcome(
                    Outcome.NEEDS_APPROVAL,
                    trigger,
                    completed,
                    detail="every stage before operator approval is accepted",
                )

            outcome = await self.execute(make_brief(stage, list(completed)))
            completed.append(outcome)

            if outcome.outcome is not Outcome.ACCEPTED:
                closed = pipeline.halts_on(stage)
                detail = outcome.detail
                if closed and outcome.outcome is Outcome.HALTED:
                    detail = f"{stage} returned {closed}: {outcome.detail}"
                self.log.run_end(outcome=outcome.outcome.value, detail=detail)
                return PipelineOutcome(outcome.outcome, trigger, completed, detail=detail)

            stage = pipeline.advance(stage)

        self.log.run_end(outcome="accepted", detail=f"{trigger.value} pipeline complete")
        return PipelineOutcome(Outcome.ACCEPTED, trigger, completed)


def _corrected(brief: TaskBrief, note: str) -> TaskBrief:
    """The retry brief: same task, with the reason the first attempt failed.

    The correction is appended to constraints rather than rewriting the
    objective — a retry is the same task done right, not a different task.
    """
    from dataclasses import replace

    return replace(
        brief,
        constraints=f"{brief.constraints}\n\nPrevious attempt was not accepted: {note}",
        retry_of=brief.task_id,
    )


def summarize(outcome: DelegationOutcome | PipelineOutcome) -> str:
    """Manager-to-operator prose. The strict schema does not apply here.

    Short answer, what failed, what needs approval, recommended next step.
    """
    if isinstance(outcome, PipelineOutcome):
        lines = [f"Pipeline: {outcome.trigger.value} — {outcome.outcome.value}"]
        for stage in outcome.completed_stages:
            mark = "ok" if stage.accepted else stage.outcome.value
            lines.append(f"  - {stage.agent} ({stage.task_id}): {mark}")
        if outcome.detail:
            lines.append(f"\n{outcome.detail}")
        if outcome.outcome is Outcome.NEEDS_APPROVAL:
            lines.append("\nNext step: your approval. Nothing has been published or promoted.")
        return "\n".join(lines)

    lines = [f"{outcome.agent} ({outcome.task_id}): {outcome.outcome.value}"]
    if outcome.result:
        lines.append(f"\n{outcome.result.summary}")
        if outcome.result.deliverables:
            lines.append("\nDelivered:")
            lines.extend(f"  - {d}" for d in outcome.result.deliverables)
        if outcome.result.risks:
            lines.append("\nRisks:")
            lines.extend(f"  - {r}" for r in outcome.result.risks)
    if outcome.outcome is Outcome.HALTED:
        lines.append(f"\nHalted: {outcome.detail}")
        lines.append("Next step: yours. The run did not proceed past this point.")
    elif outcome.outcome is Outcome.FAILED:
        lines.append(f"\nFailed after {outcome.attempts} attempt(s): {outcome.detail}")
    elif outcome.result:
        lines.append(f"\nNext step: {outcome.result.next_step}")
    return "\n".join(lines)
