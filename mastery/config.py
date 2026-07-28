"""Orchestrator limits, as code.

These are the values from the "Orchestrator requirements" table in CLAUDE.md.
That table calls its numbers a starting proposal; the values here are the
actual enforced ones. Change them here, not in prose.

Nothing in this module asks a model to respect a limit. Each value is read by
the code path that enforces it, named in the comment beside it.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path

# Repo root, so agent docs and templates resolve regardless of cwd.
REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Caps:
    """Hard limits on a single operator request."""

    # orchestrator.run(): stop and report once this many delegations have gone out.
    max_delegations_per_request: int = 5

    # Reserved for a future conversational manager loop. The manager is currently
    # code, not a model; the only model calls made on its behalf are the two
    # below — verifying a return, and drafting a plan.
    max_manager_turns: int = 12

    # delegate.run_verdict(): the verify-only invocation.
    #
    # This is a budget, not a guardrail. What makes the call safe is that it is
    # handed no tools at all (`tools=()`) and cannot go looking for anything;
    # the turn count only decides whether it gets to finish.
    #
    # It was 1, on the reasoning that checking a return against criteria is a
    # single judgement. Measured, that is wrong twice over: a budget of 1 never
    # returns a result, and turn usage is not deterministic — the same prompt
    # failed at 3 and succeeded at 3 on consecutive runs. A verdict that dies
    # here destroys a completed delegation, so the budget is set well clear of
    # the observed range rather than trimmed to it.
    verdict_turns: int = 6

    # delegate.run_draft(): proposing a plan. Larger because the output is a
    # whole structured plan, not one verdict.
    draft_turns: int = 8

    # delegate.run_task(): passed to ClaudeAgentOptions.max_turns.
    max_subagent_turns: int = 6

    # delegate.run_task(): briefs over this are rejected, never truncated.
    # CLAUDE.md leaves this as "set explicitly"; 60 KB fits an agent doc plus a
    # few file excerpts without approaching the context window. Revisit once
    # real briefs exist — see the note in README.
    max_context_bytes: int = 60_000

    # orchestrator.run(): one retry with a corrected brief, then fail honestly.
    retries_per_failed_task: int = 1

    # delegate.run_task(): flat. Sub-agents cannot delegate, enforced by
    # denying the Agent tool, not by asking them not to.
    spawn_depth: int = 1

    # delegate.run_task(): asyncio timeout around the whole delegation.
    task_timeout_seconds: int = 300


@dataclass(frozen=True)
class Delegation:
    """How sub-agent invocations are configured.

    CLAUDE.md: no per-role model routing; `delegation.model` is global.
    """

    model: str = "sonnet"

    # Pre-approved: these run without prompting. This is an ALLOW list, not a
    # restriction — see permission_mode below for what actually blocks things.
    allowed_tools: tuple[str, ...] = ("Read", "Glob", "Grep")

    # Hard-denied regardless of permission_mode. `Agent` is the one that
    # enforces spawn_depth=1: a sub-agent with no Agent tool cannot delegate.
    # Verified absent from the advertised tool set by scripts/probe.py.
    denied_tools: tuple[str, ...] = ("Agent", "Bash", "Write", "Edit", "NotebookEdit")

    # Not loaded from `.claude/` or `~/.claude/`. An empty list means the SDK
    # does not auto-load CLAUDE.md, project settings, or user settings into a
    # delegation — context is opt-in and assembled by hand. Verified by
    # scripts/probe.py against a control run.
    permission_mode: str = "dontAsk"
    """Load-bearing. This is what makes a delegation read-only.

    The SDK advertises its full tool set (~26 tools) to every delegation
    regardless of `allowed_tools` — that field only pre-approves. Anything not
    pre-approved is refused at call time *by this mode*, which is what keeps
    WebSearch, WebFetch, SendMessage, and the scheduling tools out of reach.

    Changing this to `acceptEdits` or `bypassPermissions` silently removes that
    protection while `allowed_tools` still looks correct. scripts/probe.py
    asserts a non-allowlisted tool is actually denied; run it after any change
    here.
    """

    setting_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class Auth:
    """Which credential the SDK uses. Asserted, never inherited.

    An earlier version of this had an `inherit` mode that passed no auth env
    and let the bundled binary resolve whatever the shell happened to have.
    That is the wrong shape for this system: a set `ANTHROPIC_API_KEY` silently
    shadows the Claude Code OAuth credential, so the same config would bill the
    API account on one machine and the subscription on another, with no error
    and no log line. That is the "silent billable fallback" CLAUDE.md forbids.

    Both modes below therefore assert the environment matches the declared
    intent, and fail loudly when it does not.

      subscription — the Claude Code OAuth credential in ~/.claude/. Draws down
                     the same budget as interactive Claude Code usage.
      api_key      — metered API billing. Crosses the money gate; choose it
                     deliberately, not by leaving a variable exported.
    """

    mode: str = "subscription"  # "subscription" | "api_key"
    api_key_env: str = "ANTHROPIC_API_KEY"

    def env(self) -> dict[str, str]:
        """Auth env for the delegation subprocess, after checking intent.

        The SDK's `env` is additive over the inherited environment, so an
        exported key cannot be unset from here — it can only be detected and
        refused.
        """
        if self.mode == "api_key":
            key = os.environ.get(self.api_key_env)
            if not key:
                raise RuntimeError(
                    f"auth.mode is 'api_key' but {self.api_key_env} is unset"
                )
            return {"ANTHROPIC_API_KEY": key}

        if self.mode == "subscription":
            if os.environ.get(self.api_key_env):
                raise RuntimeError(
                    f"auth.mode is 'subscription' but {self.api_key_env} is set in the "
                    f"environment. It would shadow the OAuth credential and bill the API "
                    f"account instead. Unset it, or set auth.mode='api_key' on purpose."
                )
            return {}

        raise RuntimeError(
            f"unknown auth.mode {self.mode!r}; want 'subscription' or 'api_key'"
        )


@dataclass(frozen=True)
class Config:
    caps: Caps = field(default_factory=Caps)
    delegation: Delegation = field(default_factory=Delegation)
    auth: Auth = field(default_factory=Auth)

    # Where run logs land. One JSONL file per operator request.
    log_dir: Path = REPO_ROOT / ".runs"

    # Working directory handed to a delegation.
    cwd: Path = REPO_ROOT

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Read overrides from JSON, falling back to the defaults above.

        Only keys present in the file are overridden, so a partial config is a
        patch rather than a replacement.
        """
        cfg = cls()
        if path is None or not path.exists():
            return cfg
        raw = json.loads(path.read_text(encoding="utf-8"))
        if "caps" in raw:
            cfg = replace(cfg, caps=replace(cfg.caps, **raw["caps"]))
        if "delegation" in raw:
            d = dict(raw["delegation"])
            for key in ("denied_tools", "setting_sources"):
                if key in d:
                    d[key] = tuple(d[key])
            cfg = replace(cfg, delegation=replace(cfg.delegation, **d))
        if "auth" in raw:
            cfg = replace(cfg, auth=replace(cfg.auth, **raw["auth"]))
        if "log_dir" in raw:
            cfg = replace(cfg, log_dir=Path(raw["log_dir"]))
        if "cwd" in raw:
            cfg = replace(cfg, cwd=Path(raw["cwd"]))
        return cfg
