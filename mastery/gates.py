"""Approval gates.

Two rules from CLAUDE.md, both enforced here:

  - The gate is checked *before* the work is briefed, not after it comes back.
  - Preparing a gated action is delegable. Executing one is not.

The orchestrator halts and returns to the operator. It does not proceed, queue,
or assume approval. There is deliberately no `approve()` function in this
module: approval arrives as a fresh operator request, not as a flag the run can
set on itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import GateHit

# The gate triggers from CLAUDE.md, in the order they are checked.
GATES: tuple[tuple[str, str], ...] = (
    ("money", "spend, billing, plan tier, new payment method"),
    ("production", "deploys, track promotion, publishing, live config"),
    ("permissions", "new access, wider network exposure, loosened auth"),
    ("public-output", "anything posted, listed, or shipped to users"),
    ("destructive", "destructive or irreversible operations"),
    ("paid-tool", "any use of a paid tool or metered API not already authorized"),
)

GATE_NAMES = tuple(name for name, _ in GATES)


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
    for name, description in GATES:
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
