"""Task IDs: `YYYYMMDD-<vertical>-<nnn>`.

The same pattern is enforced here and in structured_output_schema.md, so a
sub-agent that echoes back a different ID fails validation rather than being
quietly accepted.
"""

from __future__ import annotations

import re
from datetime import date

VERTICALS = ("ff", "rd", "ops")

TASK_ID_RE = re.compile(r"^(?P<date>[0-9]{8})-(?P<vertical>ff|rd|ops)-(?P<seq>[0-9]{3})$")

VERTICAL_NAMES = {
    "ff": "FaithFeed",
    "rd": "Research and Debunk",
    "ops": "Operations and Sourcing",
}


def is_valid(task_id: str) -> bool:
    return TASK_ID_RE.match(task_id) is not None


def parse(task_id: str) -> tuple[str, str, int]:
    """Return (yyyymmdd, vertical, sequence). Raises ValueError if malformed."""
    m = TASK_ID_RE.match(task_id)
    if not m:
        raise ValueError(f"malformed task_id: {task_id!r} (want YYYYMMDD-<ff|rd|ops>-NNN)")
    return m["date"], m["vertical"], int(m["seq"])


def mint(vertical: str, sequence: int, on: date | None = None) -> str:
    """Build a task ID. `sequence` is the operator's counter for the day."""
    if vertical not in VERTICALS:
        raise ValueError(f"unknown vertical {vertical!r}; want one of {VERTICALS}")
    if not 0 <= sequence <= 999:
        raise ValueError(f"sequence {sequence} outside 000-999")
    stamp = (on or date.today()).strftime("%Y%m%d")
    return f"{stamp}-{vertical}-{sequence:03d}"


def vertical_name(task_id: str) -> str:
    """Human-readable vertical for a task ID, for the operator-facing summary."""
    return VERTICAL_NAMES[parse(task_id)[1]]
