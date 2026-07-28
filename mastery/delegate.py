"""The one place that talks to the Claude Agent SDK.

Everything else in this package is plain Python, so the guardrails can be
tested without a model, a network, or a credential. Swap `Runner` for a fake
and the whole orchestrator runs offline — see tests/test_orchestrator.py.

Delegation is a flat `query()` per task, not the SDK's own subagent mechanism.
That is deliberate:

  - Routing is code's job. Handing the SDK a roster and letting the model pick
    would move routing into a model, which CLAUDE.md forbids.
  - Context is opt-in. A `query()` gets exactly the brief's context payload and
    nothing else; `setting_sources=[]` stops the SDK auto-loading CLAUDE.md,
    project settings, or user settings into a delegation.
  - Spawn depth is 1. The `Agent` tool is denied, so a sub-agent cannot
    delegate — enforced by the permission layer, not by asking it not to.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Protocol

from .brief import TaskBrief
from .config import Config
from .errors import DelegationFailed, TaskTimeout

SYSTEM_PROMPT = """You are a sub-agent in a code-owned multi-agent system, running one \
scoped task. Your role definition is the agent doc in your context payload — read \
it and stay inside it.

Rules that are enforced, not suggested:

- Your context payload is everything you get. It is listed in the brief under \
"Context provided". Do not assume access to files, history, or systems outside it.
- Do not do work the brief puts out of scope, even if you can see it needs doing. \
Another agent owns it.
- Do not delegate. You have no Agent tool.
- If required context is missing and guessing it would change the outcome, do not \
guess. Return status "blocked" and name what is missing in next_step.
- If you hit an approval gate — money, production, permissions, public output, \
anything destructive or irreversible — stop and return status "blocked". Do not \
prepare-then-execute.
- Prefer honest failure over fabricated success. A task you could not finish is \
"failed" or "partial", never "complete".

Your entire reply must be one JSON object matching this schema, and nothing else \
— no preamble, no explanation around it, no markdown outside the object:

{
  "task_id": "<echo the brief's task_id verbatim>",
  "status": "complete" | "partial" | "failed" | "blocked",
  "summary": "<prose for a human: what you did, or why you could not>",
  "deliverables": ["<label>", ...],
  "risks": ["<risk or named gap>", ...],
  "next_step": "<prose for a human; when blocked, name the gate or missing input>"
}

status is the only field the orchestrator acts on, so it must be accurate:

- complete — every success criterion in the brief is met, in full.
- partial  — some criteria met; name every gap in risks.
- failed   — could not complete; the reason goes in summary.
- blocked  — you hit an approval gate, a missing prerequisite, or (if you are a \
review gate) you are returning closed. Name the trigger in next_step.
"""


@dataclass(frozen=True)
class RunnerResult:
    """What a runner observed. Telemetry travels with the text.

    `permission_denials` is the guardrail's own audit trail: every tool call the
    permission layer refused. An empty list on a normal run is the expected
    state; entries mean a sub-agent reached for something outside its allowlist,
    which is worth seeing in the run log rather than only in a probe.
    """

    text: str
    num_turns: int = 0
    cost_usd: float | None = None
    permission_denials: tuple = ()


@dataclass(frozen=True)
class Invocation:
    """One model call's raw outcome. Parsing and validation happen upstream."""

    raw: str
    duration_s: float
    num_turns: int = 0
    cost_usd: float | None = None
    permission_denials: tuple = ()


class Runner(Protocol):
    """The seam between the orchestrator and the SDK."""

    async def run(
        self,
        *,
        system_prompt: str,
        prompt: str,
        max_turns: int,
        tools: tuple[str, ...] = (),
    ) -> RunnerResult: ...


class SdkRunner:
    """Runs a delegation through claude-agent-sdk."""

    def __init__(self, config: Config):
        self.config = config

    async def run(
        self,
        *,
        system_prompt: str,
        prompt: str,
        max_turns: int,
        tools: tuple[str, ...] = (),
    ) -> RunnerResult:
        # Imported here so the rest of the package works without the SDK
        # installed — tests, schema validation, and brief assembly do not need it.
        from claude_agent_sdk import (  # noqa: PLC0415
            ClaudeAgentOptions,
            ResultMessage,
            query,
        )

        d = self.config.delegation
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            model=d.model,
            max_turns=max_turns,
            # Pre-approved only, and per agent — a researcher needs the web, a
            # content agent must not have it. What blocks everything else is
            # permission_mode; see the note on that field in config.py.
            allowed_tools=list(tools or d.allowed_tools),
            disallowed_tools=list(d.denied_tools),
            permission_mode=d.permission_mode,
            # Empty: no CLAUDE.md, no project settings, no user settings.
            setting_sources=list(d.setting_sources),
            cwd=str(self.config.cwd),
            env=self.config.auth.env(),
        )

        result = RunnerResult(text="")
        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, ResultMessage):
                    result = RunnerResult(
                        text=message.result or "",
                        num_turns=message.num_turns or 0,
                        cost_usd=message.total_cost_usd,
                        permission_denials=tuple(message.permission_denials or ()),
                    )
        except Exception as exc:
            # The SDK raises instead of yielding a ResultMessage when a
            # delegation ends without one — turn exhaustion is the common case,
            # and it is an ordinary outcome, not a crash. Convert it into a task
            # failure so the orchestrator can retry or report it.
            raise DelegationFailed(f"delegation ended without a result: {exc}") from exc

        return result


async def run_task(brief: TaskBrief, runner: Runner, config: Config) -> Invocation:
    """Send one brief and return the raw text of its final message.

    The brief has already been validated and gate-checked by the orchestrator;
    this function does not re-decide whether the task should run.
    """
    agent = brief.agent_def()
    # Both budgets are agent-shaped. A research pass needs many turns and real
    # wall-clock; a content agent writing two hooks needs neither. Getting these
    # wrong does not degrade gracefully — the delegation ends with no result.
    timeout = agent.timeout_seconds or config.caps.task_timeout_seconds
    prompt = f"{brief.render()}\n\n{brief.render_context()}"
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(
            runner.run(
                system_prompt=SYSTEM_PROMPT,
                prompt=prompt,
                max_turns=agent.max_turns or config.caps.max_subagent_turns,
                tools=agent.tools,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError as exc:
        raise TaskTimeout(f"{brief.task_id} ({brief.agent}) exceeded {timeout}s") from exc
    return Invocation(
        raw=result.text,
        duration_s=time.monotonic() - started,
        num_turns=result.num_turns,
        cost_usd=result.cost_usd,
        permission_denials=result.permission_denials,
    )


async def run_manager(
    prompt: str,
    runner: Runner,
    config: Config,
    *,
    system_prompt: str,
    max_turns: int = 1,
) -> Invocation:
    """A manager-side model call: no tools, and it produces text, not actions.

    Both current uses — verifying a return, and drafting a plan — are judgement
    on material already in the prompt. Neither looks anything up, so neither
    gets tools, and one turn is enough.
    """
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(
            runner.run(
                system_prompt=system_prompt,
                prompt=prompt,
                max_turns=max_turns,
                tools=(),
            ),
            timeout=config.caps.task_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise TaskTimeout("manager invocation timed out") from exc
    return Invocation(
        raw=result.text,
        duration_s=time.monotonic() - started,
        num_turns=result.num_turns,
        cost_usd=result.cost_usd,
        permission_denials=result.permission_denials,
    )


DRAFT_SYSTEM_PROMPT = (
    "You are the manager, translating an operator's raw request into scoped task "
    "briefs for a human to review. You are drafting a proposal, not running "
    "anything.\n\n"
    "You have no tools. Any file the operator mentions is a name you refer to in "
    "context_needed, not something you can open — do not attempt to read it. "
    "Work only from the text in this prompt.\n\n"
    "Reply with one JSON object and nothing else."
)


async def run_draft(prompt: str, runner: Runner, config: Config) -> Invocation:
    # More than one turn: the plan is a large structured object, and a denied
    # tool attempt costs a turn. One turn is enough for a verdict, not for this.
    return await run_manager(
        prompt, runner, config, system_prompt=DRAFT_SYSTEM_PROMPT, max_turns=8
    )


async def run_verdict(prompt: str, runner: Runner, config: Config) -> Invocation:
    """The manager's verify-only invocation.

    One turn, no tools. The manager is checking a return against the brief's
    criteria — it has nothing to look up.
    """
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(
            runner.run(
                system_prompt=(
                    "You verify one completed task against its brief. "
                    "Reply with one JSON object and nothing else."
                ),
                prompt=prompt,
                max_turns=1,
            ),
            timeout=config.caps.task_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise TaskTimeout("manager verification timed out") from exc
    return Invocation(
        raw=result.text,
        duration_s=time.monotonic() - started,
        num_turns=result.num_turns,
        cost_usd=result.cost_usd,
        permission_denials=result.permission_denials,
    )
