"""Approval gates.

Two rules from CLAUDE.md, both enforced here:

  - The gate is checked *before* the work is briefed, not after it comes back.
  - Preparing a gated action is delegable. Executing one is not.

The orchestrator halts and returns to the operator. It does not proceed, queue,
or assume approval. There is deliberately no `approve()` function in this
module: approval arrives as a fresh operator request, not as a flag the run can
set on itself.

**Two enforcement points, and the rule that relates them.**

  1. Pre-flight, on the brief's *declaration* (`enforce`). Cheap: it halts before
     a delegation is sent, so a gated task costs nothing.
  2. Invocation boundary, on the *observed target* (`require_approval`). This is
     the backstop. It keys off a static map from target to class, in code, and
     never off a model's description of what it is doing — a guardrail that asks
     the actor whether it is about to do something risky is a guardrail the actor
     can talk its way past.

The declaration may only **add** halts, never remove them. A brief declaring
`none` cannot downgrade a classed target: `effective_class` unions the two and
the map always wins. If that were an override instead of a union, the whole
second enforcement point would be optional at the writer's discretion, which is
the bypass this design exists to close.

**Fail closed.** An unmapped target requires approval. There is no default-safe
branch and no "not in the map means fine" path — a target nobody has classified
is precisely the one nobody has thought about.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import ApprovalRequired, GateHit


class GateClass(str, Enum):
    """The five classes a gated target can fall into.

    One vocabulary, deliberately. These are the operator's class names, and the
    declaration strings in `GATES` below are aliased onto them rather than kept
    as a second set — two vocabularies for one concept is how a `production`
    declaration ends up not matching a `prod` class and silently clearing.
    """

    MONEY = "money"
    PROD = "prod"
    PERMISSIONS = "permissions"
    PUBLIC = "public"
    IRREVERSIBLE = "irreversible"


# The gate triggers from CLAUDE.md, in the order they are checked, each mapped
# onto the class it belongs to. The first element stays the declaration keyword
# so existing briefs and `check()` behaviour are unchanged.
GATES: tuple[tuple[str, str, GateClass], ...] = (
    ("money", "spend, billing, plan tier, new payment method", GateClass.MONEY),
    ("production", "deploys, track promotion, publishing, live config", GateClass.PROD),
    ("permissions", "new access, wider network exposure, loosened auth", GateClass.PERMISSIONS),
    ("public-output", "anything posted, listed, or shipped to users", GateClass.PUBLIC),
    ("destructive", "destructive or irreversible operations", GateClass.IRREVERSIBLE),
    # A metered API is spend, so it classes as money even though CLAUDE.md lists
    # it as its own trigger.
    ("paid-tool", "any use of a paid tool or metered API not already authorized", GateClass.MONEY),
)

GATE_NAMES = tuple(name for name, _, _ in GATES)

CLASS_FOR_DECLARATION: dict[str, GateClass] = {name: cls for name, _, cls in GATES}


# ---------------------------------------------------------------------------
# The static target -> class map. Code-owned policy, not inferred from anything.
#
# Keys are `module.callable`, the observed target. A target appears here because
# someone classified it deliberately; absence is not clearance, it is an unknown,
# and `classify` treats an unknown as requiring approval.
#
# `integrations/meta_client.py` writes are the first real entries. They were
# already unreachable via NotImplementedError, which is fail-closed by accident.
# Classifying them makes it fail-closed on purpose, and means the class is
# already correct on the day the method body is written.
# ---------------------------------------------------------------------------
TOOL_CLASS: dict[str, GateClass] = {
    # Publishing is public output — posted, listed, shipped to users.
    "meta_client.publish_ig_post": GateClass.PUBLIC,
    "meta_client.publish_page_post": GateClass.PUBLIC,
    # A comment reply is public speech under the account's name.
    "meta_client.reply_to_comment": GateClass.PUBLIC,
    # Deletion cannot be undone and destroys someone else's words. Not `public`:
    # the harm is the irreversibility, and classing it as publishing would let a
    # publishing approval cover a destructive act.
    "meta_client.delete_comment": GateClass.IRREVERSIBLE,
}


def classify(target: str) -> GateClass | None:
    """The class of an observed target, or None when it is unmapped.

    None means unknown, and unknown means approval is required — see
    `require_approval`. This function does not decide that; it only reports what
    the map says, so the fail-closed rule lives in exactly one place.
    """
    return TOOL_CLASS.get(target)


def effective_class(target: str, declared: str = "none") -> GateClass | None:
    """Union of the declaration and the map. The map always wins.

    Declared-safe cannot downgrade a classed target — that is the rule that
    makes the second enforcement point non-optional. The declaration can only
    contribute an *additional* class the map does not know about.
    """
    from_map = classify(target)
    if from_map is not None:
        return from_map
    check_result = check(declared)
    if not check_result.clear:
        return CLASS_FOR_DECLARATION.get(check_result.gate)
    return None


def require_approval(target: str, *, declared: str = "none") -> None:
    """Halt before executing a gated target. Called at the invocation boundary.

    Raises `ApprovalRequired` always — either with the target's class, or, when
    the target is unmapped, with the reason that an unclassified target is not a
    cleared one. `declared` is accepted so a caller can show what the brief said,
    but it can only add to the halt, never remove it.
    """
    gate_class = effective_class(target, declared)

    if gate_class is None:
        raise ApprovalRequired(
            target,
            "unclassified",
            f"{target} is not in the tool->class map. An unclassified target "
            f"requires approval: absence from the map is an unknown, not a "
            f"clearance. Classify it in gates.TOOL_CLASS before enabling it.",
        )

    raise ApprovalRequired(
        target,
        gate_class.value,
        f"{target} is classed '{gate_class.value}' and requires operator approval "
        f"before execution. Approval arrives as a fresh operator request; it is "
        f"not a flag this run can set on itself."
        + (
            ""
            if classify(target) is not None
            else f" (class contributed by the brief's declaration {declared!r})"
        ),
    )


@dataclass(frozen=True)
class GateCheck:
    """Result of checking a brief against the gate list."""

    gate: str | None
    detail: str

    @property
    def clear(self) -> bool:
        return self.gate is None


def check(gates_touched: str) -> GateCheck:
    """Check a brief's `Approval gates touched` field.

    The field is filled by the operator or the manager when the brief is
    written, per task_brief_template.md — the orchestrator reads a declaration,
    it does not infer intent from prose. `none` is the explicit word for a
    brief that touches no gate; anything else names a gate and halts.
    """
    declared = gates_touched.strip().lower()
    if not declared:
        raise GateHit(
            "unfilled",
            "brief did not declare `Approval gates touched`; write `none` if it touches none",
        )
    if declared == "none":
        return GateCheck(None, "")
    for name, description, _cls in GATES:
        if name in declared or description.split(",")[0] in declared:
            return GateCheck(name, gates_touched.strip())
    # Declared something that is not `none` and does not match a known gate.
    # Treat as gated: an unrecognized declaration is not a clearance.
    return GateCheck("unrecognized", gates_touched.strip())


def enforce(gates_touched: str) -> None:
    """Raise GateHit if the brief touches a gate. Called before delegating."""
    result = check(gates_touched)
    if not result.clear:
        raise GateHit(result.gate, result.detail)
