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
from dataclasses import dataclass, field
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
class Usage:
    """Token accounting for one model call, as the SDK reported it.

    Every field here comes from `ResultMessage.model_usage`, which the CLI fills
    in from the API's own response. Nothing in this dataclass is ever asked of a
    model: a sub-agent cannot observe its own token count or know which model
    served it, so a self-reported number would be a guess wearing the costume of
    telemetry. That is the fabrication CLAUDE.md forbids, and it is why these
    live here and not in structured_output_schema.md.

    The cache split is two fields rather than one total because that is the only
    way to tell a cached static prefix from a re-billed one: `cache_read` high
    with `cache_creation` near zero means the prefix was served from cache. A
    single `tokens` sum, or a dollar figure, cannot distinguish those.

    `model` is the resolved model that actually served the call, not the alias
    that was requested — `config.delegation.model` is "sonnet", which is not
    what gets billed or what a tiering decision needs to be checked against.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    model: str = ""

    @property
    def total_tokens(self) -> int:
        """Fresh input plus output. Cache reads are counted separately, because
        folding them in here would hide the thing the split exists to show."""
        return self.input_tokens + self.output_tokens

    def as_log_fields(self) -> dict:
        """Log fields for this call's accounting.

        `model` is the resolved model id. It was called `model_tier` for two
        commits, which was a bad name twice over: it held a model, not a tier,
        and it collided with the real tier label (`tiers.RoleTier`) that the eval
        loop needs. Renamed while no real run log carried it.
        """
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "model": self.model,
        }


def usage_from(model_usage: dict | None) -> Usage:
    """Fold `ResultMessage.model_usage` into one Usage.

    The SDK keys usage by model string and hands the value through verbatim from
    the CLI, so the keys are camelCase and every field is optional in practice.
    A call normally involves one model; when it involves more, the counts sum and
    the model names join, because the alternative — picking one and dropping the
    rest — would under-report real spend.

    An absent or empty `model_usage` yields a zeroed Usage rather than raising.
    Missing telemetry must not be able to fail a delegation that succeeded.
    """
    if not model_usage:
        return Usage()

    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}
    names: list[str] = []
    for key, entry in model_usage.items():
        entry = entry or {}
        totals["input"] += entry.get("inputTokens", 0) or 0
        totals["output"] += entry.get("outputTokens", 0) or 0
        totals["cache_read"] += entry.get("cacheReadInputTokens", 0) or 0
        totals["cache_creation"] += entry.get("cacheCreationInputTokens", 0) or 0
        names.append(entry.get("canonicalModel") or key)

    return Usage(
        input_tokens=totals["input"],
        output_tokens=totals["output"],
        cache_read_tokens=totals["cache_read"],
        cache_creation_tokens=totals["cache_creation"],
        model="+".join(sorted(set(names))),
    )


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
    usage: Usage = field(default_factory=Usage)


@dataclass(frozen=True)
class Invocation:
    """One model call's raw outcome. Parsing and validation happen upstream."""

    raw: str
    duration_s: float
    num_turns: int = 0
    cost_usd: float | None = None
    permission_denials: tuple = ()
    usage: Usage = field(default_factory=Usage)


class Runner(Protocol):
    """The seam between the orchestrator and the SDK."""

    async def run(
        self,
        *,
        system_prompt: str,
        prompt: str,
        max_turns: int,
        tools: tuple[str, ...] | None = None,
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
        tools: tuple[str, ...] | None = None,
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
            #
            # `None` means "unspecified, use the default"; `()` means "none, on
            # purpose". These are not the same, and conflating them was a real
            # bug: `tools or d.allowed_tools` treated the empty tuple as falsy,
            # so every manager and verdict call — documented here and in
            # CLAUDE.md as no-tools — was handed the full default allowlist.
            # A verdict call then spent its single turn reaching for a tool and
            # died with "Reached maximum number of turns (1)", destroying the
            # completed delegation it was supposed to be verifying.
            allowed_tools=list(d.allowed_tools if tools is None else tools),
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
                        # Token counts and the resolved model, straight off the
                        # SDK's own accounting. Read here because this is the one
                        # place that sees a ResultMessage.
                        usage=usage_from(message.model_usage),
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
        usage=result.usage,
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
    gets tools. Callers pass `tools=()` explicitly: `None` means "use the
    default allowlist", which is not what a manager call wants.
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
        usage=result.usage,
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
    # The plan is a large structured object and needs room. Low budgets are not
    # a guardrail here — `tools=()` is — and a budget of 1 does not return a
    # result at all; see the note in run_verdict.
    return await run_manager(
        prompt, runner, config, system_prompt=DRAFT_SYSTEM_PROMPT,
        max_turns=config.caps.draft_turns,
    )


async def run_verdict(prompt: str, runner: Runner, config: Config) -> Invocation:
    """The manager's verify-only invocation.

    No tools — that is the guardrail, and it is now enforced directly by passing
    `tools=()` rather than inferred from a turn budget.

    The budget is 3, not 1. "One turn" was a proxy for "it has nothing to look
    up", and it was a bad one: `max_turns=1` never returns a result at all. The
    CLI's own accounting makes a budget of 1 unreachable — the same call that
    fails at 1 succeeds at 3 and then reports having used one turn. Measured,
    not reasoned about, after a one-turn verdict call destroyed a completed
    30-turn research delegation.

    Turn count is a budget, not a guardrail. The property that matters is that
    the manager cannot go looking for anything, and `tools=()` says so.
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
                max_turns=config.caps.verdict_turns,
                tools=(),
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
        usage=result.usage,
    )
