"""Role tiers — the declared kind of work a model call performs.

This is a **label**, not a model selection. Nothing in this codebase reads a tier
to decide which model to run; `delegation.model` is still global, exactly as
CLAUDE.md:190 says. Wiring a tier to a model choice is STOP 6 in BUILD_LEDGER.md,
and it is deliberately blocked until the eval loop can show that tiering down did
not cost quality.

The label lands ahead of the wiring for one reason: a tier recorded in the run log
from the start means the baseline runs are already labelled when STOP 6 arrives.
A tier introduced at the same time as the model switch would have no labelled
history to compare against, which is the position STOP 6 exists to avoid.

  mechanical — grades or checks against a fixed reference. Exercises no judgement
               about what the work should have been. Verify-only manager verdicts
               and quality grading are the current members.
  judgment   — decides what the work should be, or weighs things that are not
               reducible to a checklist.

**The default is `judgment`, and that is the fail-closed direction.** For a
guardrail, "safe" usually means restrictive; here the risky move is running
important work on a cheap model, so an unclassified role defaults to the stronger
side. An unlabelled role must never drift down a tier because nobody got around
to classifying it.
"""

from __future__ import annotations

from enum import Enum


class RoleTier(str, Enum):
    MECHANICAL = "mechanical"
    JUDGMENT = "judgment"


# Manager-side call sites, which are not roster agents and so carry their tier
# here rather than in roster.py.
#
# Both are mechanical: each is handed a fixed reference — the brief's success
# criteria, or a role's rubric — and reports how the return measures against it.
# Neither decides what the work should have been.
VERDICT_TIER = RoleTier.MECHANICAL
GRADER_TIER = RoleTier.MECHANICAL
