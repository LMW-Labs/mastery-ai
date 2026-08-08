"""The agent roster, as data.

Mirrors docs/agents/README.md. The doc is what a human reads; this is what the
orchestrator routes on. tests/test_roster.py asserts every entry here has a
matching doc file, so the two cannot drift silently.

An agent's doc is passed in the delegation's context payload — agent docs are
not auto-loaded for delegated sub-agents (setting_sources is empty), so
omitting it would leave the agent with no role definition.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import REPO_ROOT
from .errors import RoutingError
from .tiers import RoleTier

AGENT_DOC_DIR = REPO_ROOT / "docs" / "agents"


# Read-only default. Anything beyond this is granted per agent, below.
READ_ONLY: tuple[str, ...] = ("Read", "Glob", "Grep")


@dataclass(frozen=True)
class Agent:
    name: str
    tier: int
    owns: str
    does_not_own: str
    # Gate agents return `blocked` when they return closed, rather than
    # reporting a successful task that happens to say "no". See schema.py.
    is_gate: bool = False
    # Pre-approved tools for this agent. Global read-only is the floor; network
    # access is granted only where the role genuinely requires it, because
    # `permission_mode` refuses everything not listed here. A researcher with no
    # WebSearch cannot research, and a content agent with WebSearch could go
    # sourcing claims that fact-checker is supposed to adjudicate.
    tools: tuple[str, ...] = READ_ONLY
    # Turn budget for this agent, falling back to caps.max_subagent_turns.
    # Work shape differs enormously: a research pass spends a turn per search
    # and per fetch, while a content agent writing two hooks needs almost
    # none. A budget that is too low does not degrade — the SDK ends the
    # delegation with no result at all.
    max_turns: int | None = None
    # Wall-clock budget, falling back to caps.task_timeout_seconds. A web
    # research pass is slow; 300s cut one off mid-flight and, worse, spent the
    # retry that the actual quality gap then needed.
    timeout_seconds: int | None = None
    # Declared kind of work. A label only — nothing reads it to pick a model, and
    # `delegation.model` remains global. See tiers.py.
    #
    # Every roster agent defaults to `judgment` and none is marked mechanical
    # yet, deliberately. STOP 6 reserves the tiering decision to the operator,
    # and the one candidate its wording names — "fact-check retrieval" — is only
    # half of what `fact-checker` does; the adjudication half is judgement. So no
    # agent is classified here until that call is made, and the default keeps an
    # unclassified role on the stronger side in the meantime.
    role_tier: RoleTier = RoleTier.JUDGMENT

    @property
    def doc_path(self) -> Path:
        return AGENT_DOC_DIR / f"{self.name}.md"

    def doc(self) -> str:
        """The agent's own doc, for the context payload."""
        if not self.doc_path.exists():
            raise RoutingError(f"{self.name} has no doc at {self.doc_path}")
        return self.doc_path.read_text(encoding="utf-8")


_AGENTS: tuple[Agent, ...] = (
    # Tier 1 — always available
    Agent("manager", 1, "Routing, context delegation, verification, approvals", "Execution work"),
    Agent(
        "mobile-dev",
        1,
        "App code, builds, release prep",
        "Design decisions, QA sign-off",
        # Budgets, same reasoning as visual-design below. This role returns whole
        # file contents in its deliverables — it has no write tool, so a theme
        # rebuild is ~1,000 lines emitted as text, on top of the Reads that spend
        # a turn each. The 6-turn / 300s default is sized for a one-file bug fix;
        # 20260803-ff-002 produced a smaller payload at 20 turns and still ran
        # ~500s. Raised so a legitimate task is not failed by the clock. These are
        # budgets, not guardrails — the guardrails are the tool list and
        # permission_mode, which are untouched.
        max_turns=20,
        timeout_seconds=600,
    ),
    Agent(
        "researcher",
        1,
        "External evidence discovery",
        "Verifying finished drafts",
        tools=READ_ONLY + ("WebSearch", "WebFetch"),
        max_turns=30,
        timeout_seconds=900,
    ),
    Agent("qa", 1, "Regression, edge cases, release readiness", "Fixing what it finds", is_gate=True),
    Agent("marketing", 1, "Campaign decisions, publishing workflow", "Producing its own metrics"),
    Agent("risk-review", 1, "Platform, policy, reputational, safety risk", "Legal opinions", is_gate=True),
    Agent("strategy", 1, "Prioritization, tradeoffs, sequencing", "Execution"),
    Agent("ops", 1, "VPS, automation, portability, steady state", "Live incidents"),
    # Tier 2 — on demand
    Agent("ui-ux", 2, "Flows, screens, component specs", "Code, release scope"),
    Agent(
        "visual-design",
        2,
        "Visual system: colour, type, elevation, motion",
        "Flows, screen structure, code",
        # Budgets, for the reason in the field comments above. This role reads a
        # theme file and the call sites that bypass it, and each Read/Glob spends
        # a turn — the 6-turn default is a survey of two files. Sized against
        # fact-checker, which does comparable reading.
        max_turns=20,
        timeout_seconds=600,
    ),
    Agent("content", 2, "Copy, hooks, CTAs, scripts", "Choosing the angle, verifying claims"),
    Agent(
        "fact-checker",
        2,
        "Verification pass on drafted output",
        "New evidence discovery",
        is_gate=True,
        # WebFetch to check a cited source; no WebSearch, because open-ended
        # discovery is the researcher's job, not a verification pass.
        tools=READ_ONLY + ("WebFetch",),
        max_turns=20,
        timeout_seconds=600,
    ),
    Agent("legal-review", 2, "Legal exposure, counsel escalation", "Platform policy, publication clearance", is_gate=True),
    Agent("metrics-agent", 2, "KPI definition, measurement, trend detection", "Recommending decisions"),
    Agent("incident-response-agent", 2, "Triage, RCA, rollback, postmortem", "Steady-state ops"),
    Agent("prompt-engineer-agent", 2, "Agent docs, routing rules, delegation quality", "Application code"),
    Agent("data-model-agent", 2, "Schemas, output contracts, migrations", "Writing or running migrations"),
    # Tier 3 — periodic
    Agent("user-research-agent", 3, "First-party user signal synthesis", "Roadmap decisions, competitor data"),
    Agent("competitor-intelligence-agent", 3, "Named competitors, market moves", "Setting positioning"),
)

BY_NAME: dict[str, Agent] = {a.name: a for a in _AGENTS}

# Agents the orchestrator may delegate to. The manager is the orchestrator
# itself and is never a delegation target.
DELEGATABLE = tuple(a for a in _AGENTS if a.name != "manager")


def get(name: str) -> Agent:
    """Look up an agent, or fail loudly.

    Per manager_decision_rubric.md Step 5: do not route to the closest
    available agent when none fits. A miss here is returned to the operator.
    """
    try:
        return BY_NAME[name]
    except KeyError:
        raise RoutingError(
            f"no agent named {name!r} in the roster; "
            f"the task needs an owner that does not exist"
        ) from None


def all_agents() -> tuple[Agent, ...]:
    return _AGENTS
