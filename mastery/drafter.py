"""Operator intent -> proposed briefs. The manager's other half.

`manager.md` lists as the manager's first responsibility: "Translate operator
intent into a scoped task, or reject it as too vague." The orchestrator built
the verification half and left translation to the operator, which put the whole
burden of the brief contract — routing, checkable criteria, gate declaration —
on a human writing JSON by hand. That is the friction this closes.

Three properties are deliberate, and they are what keep this from quietly
undoing the guardrails it sits in front of:

  1. It proposes; it never runs. Routing and context selection are the two
     decisions CLAUDE.md keeps out of a model's hands. Drafting a brief for a
     human to approve preserves that; auto-executing would invert it.
  2. It names context, it does not assemble it. A stage says *what* it needs;
     the operator attaches the actual bytes. Context stays opt-in.
  3. It can refuse. The rubric's Step 0 says an unscoped request is not routed.
     A drafter that always emits a plan would paper over exactly the vagueness
     the rubric exists to catch, so `scoped: false` is a first-class outcome.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from . import ids
from .config import REPO_ROOT, Config
from .errors import SchemaViolation
from .roster import DELEGATABLE, get as get_agent
from .schema import extract_json

PLAN_SCHEMA_PATH = REPO_ROOT / "docs" / "agents" / "draft_plan_schema.md"
RUBRIC_PATH = REPO_ROOT / "docs" / "agents" / "manager_decision_rubric.md"
TEMPLATE_PATH = REPO_ROOT / "docs" / "agents" / "task_brief_template.md"


@lru_cache(maxsize=1)
def plan_schema() -> dict:
    return json.loads(PLAN_SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    return Draft202012Validator(plan_schema())


@dataclass(frozen=True)
class Stage:
    agent: str
    objective: str
    success_criteria: tuple[str, ...]
    context_needed: tuple[str, ...]
    constraints: str
    out_of_scope: str
    approval_gates_touched: str
    expected_deliverables: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    vertical: str
    scoped: bool
    pipeline: str
    legal_review_required: bool
    stages: tuple[Stage, ...]
    open_questions: tuple[str, ...]
    scope_problem: str = ""
    legal_review_reason: str = ""
    notes_for_operator: str = ""


def build_prompt(request: str, *, attachments: list[str]) -> str:
    """The drafting prompt.

    The manager is the one agent with broad context, so handing it the rubric
    and the brief template is correct here — unlike a delegation, where the
    payload is deliberately narrow.
    """
    roster = "\n".join(
        f"- {a.name} — owns: {a.owns}; does NOT own: {a.does_not_own}"
        for a in DELEGATABLE
    )
    files = "\n".join(f"- {a}" for a in attachments) or "- (none)"

    return f"""You are the manager of a code-owned multi-agent system. Translate the
operator's raw request below into a plan of scoped task briefs.

You are drafting a proposal for a human to review and edit. You are not running
anything, and nothing you write executes on its own.

## The operator's request, verbatim

{request}

## Files the operator referenced

{files}

## The roster you may route to

{roster}

## Routing rules

{RUBRIC_PATH.read_text(encoding="utf-8")}

## How a brief must be written

{TEMPLATE_PATH.read_text(encoding="utf-8")}

## Rules for this plan

- One agent per stage. A stage needing two agents is two stages.
- Order stages so each depends only on stages before it.
- If the request produces public-facing output, set pipeline to "public-output"
  and order the stages content -> fact-checker -> risk-review. If it is a
  release, use "release" and order mobile-dev -> qa. Otherwise "none".
- Set legal_review_required true when a real, identifiable party is named, or
  when a reviewer would plainly escalate, and say why. Add legal-review as a
  stage when you do.
- Success criteria must be checkable by someone who did not do the work.
  "Good copy" is not a criterion; "three variants, each under 280 characters,
  each with a distinct angle" is.
- context_needed lists what the stage must be *given* — named files, prior stage
  output, specific excerpts. Do not include the content itself; the operator
  attaches it. If something needed does not exist yet, say so in open_questions.
- approval_gates_touched is "none" or names the gate: money, production,
  permissions, public output, destructive. Publishing is a gate. Drafting
  something that will later be published is not.
- If the request is too vague to route, set scoped false, explain in
  scope_problem, and return an empty stages array. Do not invent a plan to
  avoid saying so.
- Put anything you had to assume, or that the operator must decide, in
  open_questions.

Reply with one JSON object matching this schema exactly, and nothing else:

{json.dumps(plan_schema(), indent=2)}
"""


def parse(raw: str) -> Plan:
    """Validate a drafted plan. Same strictness as any other contract."""
    try:
        payload = json.loads(extract_json(raw))
    except json.JSONDecodeError as exc:
        raise SchemaViolation(f"plan is not valid JSON: {exc}", raw=raw) from exc

    errors = sorted(_validator().iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(
            f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        )
        raise SchemaViolation(f"plan failed schema validation: {detail}", raw=raw)

    # Routing is checked against the roster in code, not trusted from the model.
    for stage in payload["stages"]:
        get_agent(stage["agent"])  # raises RoutingError on an invented agent

    return Plan(
        vertical=payload["vertical"],
        scoped=payload["scoped"],
        pipeline=payload["pipeline"],
        legal_review_required=payload["legal_review_required"],
        stages=tuple(
            Stage(
                agent=s["agent"],
                objective=s["objective"],
                success_criteria=tuple(s["success_criteria"]),
                context_needed=tuple(s["context_needed"]),
                constraints=s["constraints"],
                out_of_scope=s["out_of_scope"],
                approval_gates_touched=s["approval_gates_touched"],
                expected_deliverables=tuple(s["expected_deliverables"]),
            )
            for s in payload["stages"]
        ),
        open_questions=tuple(payload["open_questions"]),
        scope_problem=payload.get("scope_problem", ""),
        legal_review_reason=payload.get("legal_review_reason", ""),
        notes_for_operator=payload.get("notes_for_operator", ""),
    )


def next_sequence(brief_dir: Path, vertical: str, stamp: str) -> int:
    """Next unused sequence for a vertical on a given day."""
    used = set()
    for path in brief_dir.glob(f"{stamp}-{vertical}-*.json"):
        try:
            used.add(ids.parse(path.stem)[2])
        except ValueError:
            continue
    seq = 1
    while seq in used:
        seq += 1
    return seq


def write_briefs(plan: Plan, brief_dir: Path, *, stamp: str) -> list[Path]:
    """Write one reviewable brief file per stage.

    Context entries are written as empty-bodied placeholders. That is not an
    oversight — the operator fills them, which is what keeps context opt-in and
    hand-assembled. `mastery run` rejects a brief whose payload is still empty.
    """
    brief_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for stage in plan.stages:
        seq = next_sequence(brief_dir, plan.vertical, stamp)
        task_id = f"{stamp}-{plan.vertical}-{seq:03d}"
        payload = {
            "task_id": task_id,
            "agent": stage.agent,
            "urgency": "none",
            "objective": stage.objective,
            "success_criteria": list(stage.success_criteria),
            "context": [
                {"label": label, "body": "<<< FILL: paste or reference the content >>>"}
                for label in stage.context_needed
            ],
            "constraints": stage.constraints,
            "out_of_scope": stage.out_of_scope,
            "approval_gates_touched": stage.approval_gates_touched,
            "expected_deliverables": list(stage.expected_deliverables),
        }
        path = brief_dir / f"{task_id}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written.append(path)

    return written


def render(plan: Plan) -> str:
    """The plan as prose, for the operator to read before editing anything."""
    if not plan.scoped:
        return (
            f"NOT SCOPED — no briefs written.\n\n{plan.scope_problem}\n\n"
            + "\n".join(f"  - {q}" for q in plan.open_questions)
        )

    lines = [
        f"vertical      : {plan.vertical} ({ids.VERTICAL_NAMES[plan.vertical]})",
        f"pipeline      : {plan.pipeline}",
        f"legal-review  : {'required — ' + plan.legal_review_reason if plan.legal_review_required else 'not required'}",
        f"stages        : {len(plan.stages)}",
        "",
    ]
    for i, stage in enumerate(plan.stages, 1):
        lines.append(f"{i}. {stage.agent}")
        lines.append(f"   objective : {stage.objective}")
        for c in stage.success_criteria:
            lines.append(f"   criterion : {c}")
        for c in stage.context_needed:
            lines.append(f"   needs     : {c}")
        lines.append(f"   gates     : {stage.approval_gates_touched}")
        lines.append("")

    if plan.open_questions:
        lines.append("open questions for you:")
        lines.extend(f"  - {q}" for q in plan.open_questions)
        lines.append("")
    if plan.notes_for_operator:
        lines.append(plan.notes_for_operator)

    return "\n".join(lines)


def over_cap(plan: Plan, config: Config) -> bool:
    """Does this plan exceed the per-request delegation cap?

    Each stage costs at least one delegation, and a retry costs another, so a
    plan *at* the cap is already over it in practice: it can only complete if
    every stage succeeds first try. Flagging only `>` would let a five-stage
    plan under a five-delegation cap look runnable right up until the first
    retry raises CapExceeded mid-pipeline, with earlier stages already spent.
    """
    return len(plan.stages) >= config.caps.max_delegations_per_request
