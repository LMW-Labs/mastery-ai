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
    # code, not a model, so it takes no turns — see verdict.py for the one
    # model call made on the manager's behalf (verify-only, single turn).
    max_manager_turns: int = 12

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

    # Refused for every delegation. `Agent` enforces spawn_depth=1: a sub-agent
    # that cannot call Agent cannot delegate. The rest keep a scoped task from
    # reaching the network or the shell unless the brief asked for it.
    denied_tools: tuple[str, ...] = ("Agent", "Task", "Bash", "Write", "Edit")

    # Not loaded from `.claude/` or `~/.claude/`. An empty list means the SDK
    # does not auto-load CLAUDE.md, project settings, or user settings into a
    # delegation — context is opt-in and assembled by hand.
    setting_sources: tuple[str, ...] = ()

    # No interactive prompts in a delegated run; unapproved calls are denied
    # rather than blocking on a human who is not watching.
    permission_mode: str = "dontAsk"


@dataclass(frozen=True)
class Auth:
    """Which credential the SDK uses.

    The Agent SDK documents `ANTHROPIC_API_KEY` (and the cloud-provider env
    vars). It does not document running on a Claude subscription credential,
    and Anthropic's terms restrict offering claude.ai login to third parties.
    `mode="inherit"` passes no auth env explicitly and lets the bundled binary
    resolve whatever credential the invoking user already has — fine for a
    single-operator system on Austin's own machine, not something to ship to
    other people. `mode="api_key"` is the documented path.
    """

    mode: str = "inherit"  # "inherit" | "api_key"
    api_key_env: str = "ANTHROPIC_API_KEY"

    def env(self) -> dict[str, str]:
        if self.mode == "api_key":
            key = os.environ.get(self.api_key_env)
            if not key:
                raise RuntimeError(
                    f"auth.mode is 'api_key' but {self.api_key_env} is unset"
                )
            return {"ANTHROPIC_API_KEY": key}
        return {}


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
