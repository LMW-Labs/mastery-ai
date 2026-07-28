"""Failure modes the orchestrator distinguishes.

Every one of these is a stop, not a thing to paper over. Nothing here is
recovered from by guessing a value or retrying silently.
"""


class OrchestratorError(Exception):
    """Base for every orchestrator failure."""


class BriefIncomplete(OrchestratorError):
    """A brief was sent with a blank or missing section.

    Per task_brief_template.md an unfilled brief is not sent. If the operator
    did not supply a section, that is an escalation, not a gap to guess at.
    """


class ContextTooLarge(OrchestratorError):
    """A delegation's context payload exceeded max_context_bytes.

    Rejected rather than truncated — silently dropping context changes what the
    sub-agent sees without telling anyone.
    """


class SchemaViolation(OrchestratorError):
    """A sub-agent return failed validation against structured_output_schema.

    Validation failure is a task failure, not something to patch.
    """

    def __init__(self, message: str, raw: str | None = None):
        super().__init__(message)
        self.raw = raw


class GateHit(OrchestratorError):
    """An approval gate was reached. The run halts and returns to the operator."""

    def __init__(self, gate: str, detail: str):
        super().__init__(f"{gate}: {detail}")
        self.gate = gate
        self.detail = detail


class CapExceeded(OrchestratorError):
    """A configured cap (delegations, turns, spawn depth) was hit."""


class RoutingError(OrchestratorError):
    """No agent in the roster owns the task, or the chosen agent does not exist."""


class TaskTimeout(OrchestratorError):
    """A delegation exceeded task_timeout_seconds."""


class DelegationFailed(OrchestratorError):
    """The SDK ended a delegation without producing a result.

    Turn exhaustion is the common case: `query()` raises rather than yielding a
    ResultMessage when a sub-agent burns its turn budget. That is a normal
    outcome, not a crash, so it is converted here into a task failure the
    orchestrator can retry or report.
    """
