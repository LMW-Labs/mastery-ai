"""Personal agent operating system. Guardrails live in code, not in prose.

Module map:

    config       limits, as enforced values
    ids          task IDs
    roster       the 18 agents, as routing data
    brief        the delegation contract, manager -> sub-agent
    gates        approval gates; halts before work is briefed
    schema       structured returns: parse, validate, branch on status
    verdict      manager verify-only invocation and its verdict contract
    pipelines    the two mandatory sequences
    delegate     the only module that imports claude-agent-sdk
    orchestrator the run loop
    runlog       one JSONL per operator request
"""

from .config import Config
from .errors import (
    BriefIncomplete,
    CapExceeded,
    ContextTooLarge,
    GateHit,
    OrchestratorError,
    RoutingError,
    SchemaViolation,
    TaskTimeout,
)
from .orchestrator import DelegationOutcome, Orchestrator, Outcome, PipelineOutcome, summarize
from .schema import Action, Status, TaskResult
from .verdict import ManagerVerdict, Verdict

__all__ = [
    "Config",
    "Orchestrator",
    "Outcome",
    "DelegationOutcome",
    "PipelineOutcome",
    "summarize",
    "Status",
    "Action",
    "TaskResult",
    "Verdict",
    "ManagerVerdict",
    "OrchestratorError",
    "BriefIncomplete",
    "ContextTooLarge",
    "SchemaViolation",
    "GateHit",
    "CapExceeded",
    "RoutingError",
    "TaskTimeout",
]
