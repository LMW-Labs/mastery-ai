"""Per-rubric calibration of the quality grader. The instrument that audits the instrument.

`quality.py` scores an output against its role's rubric. Nothing in that path
establishes that the rubric *discriminates* — a grader that returns 3 whatever it
is shown produces a clean, plausible, entirely uninformative trend, and the trend
cannot detect it, because a broken instrument and an excellent agent generate the
same flat line.

This was not hypothetical. `fact-checker` sat at 3.0/3 across 15 anchors for days.
The tempting remedy — run harder cases until a non-3 appears — is circular: under
the rubber-stamp hypothesis those runs *also* return 3.0 and read as confirmation,
so the investigation grows more confident as it grows more wrong. **Sampling
cannot audit the instrument doing the sampling.** The question is answered with
known inputs, not more unknown ones.

So each rubric gets a *ladder*: a set of returns for one fixed brief, each written
against a named row of that rubric's own anchor text, whose correct score is
therefore known before the grader sees it. Run the real grader over the ladder and
compare. If the reported scores track the intended ones, the rubric has markings.

**This is a per-rubric obligation, not a one-time gate.** Calibrating one rubric
says nothing about the other sixteen — they are different dimensions, different
anchors, and different failure modes. And it is bound to `rubric_version`: editing
a rubric invalidates its calibration, because the anchors the ladder was written
against no longer exist. A calibration that silently carried across a version bump
would be worse than none, since it would attest to markings nobody had checked.

**What a missing calibration blocks, and what it does not.** It does not block
delegations, and it does not block scoring. Scores stay write-only and
observational — halting real work over an unwritten ladder would make an
uncalibrated rubric worse than no rubric at all, and `status` remains the only
thing the orchestrator branches on.

It blocks **baselines**. A baseline is the artifact that gets trusted: it is what
STOP 6's tiering comparison is measured against, and a baseline drawn through an
unverified instrument is a number that looks like evidence without being any. So
`evals.set_baseline` refuses unless a passing calibration exists for that exact
`(agent, rubric_version)`. Same principle as `IncomparableScores` — refuse rather
than emit a figure whose meaning is undetermined.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from pathlib import Path

from .config import REPO_ROOT
from .errors import OrchestratorError

LADDERS_PATH = REPO_ROOT / "docs" / "agents" / "calibration_ladders.md"
RESULTS_PATH = REPO_ROOT / "evals" / "calibration.json"

# Minimum separation, on the 0-3 scale, between the rung built to be worst and
# the rung built to be best. Below this the rubric is not resolving the range its
# own anchors describe. Deliberately loose: this is a smoke test for "does the
# dial move", not a precision requirement. A grader that scores the 0-rung at 0.2
# and the 3-rung at 3.0 has proven the point; one that scores them 2.8 and 3.0
# has not, whatever else it got right.
MIN_SPREAD = 1.0


class LadderMissing(OrchestratorError):
    """No calibration ladder is written for this agent."""


class Uncalibrated(OrchestratorError):
    """This rubric's discriminating power has not been established."""


class Verdict(str, Enum):
    CALIBRATED = "calibrated"
    MISSING = "missing"
    STALE = "stale"
    FAILED = "failed"

    @property
    def trusted(self) -> bool:
        return self is Verdict.CALIBRATED


@lru_cache(maxsize=1)
def _ladders() -> dict:
    raw = json.loads(LADDERS_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def has_ladder(agent: str) -> bool:
    return agent in _ladders()


def ladder_for(agent: str, *, rubric_version: str | None = None) -> dict:
    """The agent's ladder, or fail loudly.

    When `rubric_version` is given, the ladder must declare that same version.
    A ladder is written against specific anchor text; once the rubric moves, the
    rungs no longer correspond to the levels they claim, and running them would
    produce a number that looks like a calibration and is not one.
    """
    try:
        ladder = _ladders()[agent]
    except KeyError:
        raise LadderMissing(
            f"no calibration ladder for {agent!r} in {LADDERS_PATH.name}. Its rubric's "
            f"discriminating power is unestablished, so its scores cannot be trusted "
            f"and no baseline can be recorded from them. Write a ladder: one brief, "
            f"one return per level, each built against that rubric's own anchors."
        ) from None

    if rubric_version is not None and ladder["rubric_version"] != rubric_version:
        raise LadderMissing(
            f"{agent}'s ladder was written against rubric v{ladder['rubric_version']} "
            f"but the rubric is now v{rubric_version}. The rungs were built from anchor "
            f"text that has since changed, so running them would calibrate nothing. "
            f"Rewrite the ladder against the current anchors."
        )
    return ladder


@dataclass(frozen=True)
class CalibrationResult:
    """One ladder run. Immutable evidence, appended, never edited in place."""

    agent: str
    rubric_version: str
    model: str
    ts: str
    intended: tuple[int, ...]
    observed: tuple[float, ...]
    per_rung: tuple[dict, ...] = field(default_factory=tuple)

    @property
    def spread(self) -> float:
        return round(max(self.observed) - min(self.observed), 3)

    @property
    def monotonic(self) -> bool:
        """Non-decreasing as intended level rises.

        Ties are allowed. A grader that scores two adjacent rungs the same has
        coarse resolution, which is a limitation; one that scores them in the
        wrong order is responding to something other than the anchors, which is
        a fault.
        """
        pairs = sorted(zip(self.intended, self.observed))
        return all(a <= b for (_, a), (_, b) in zip(pairs, pairs[1:]))

    @property
    def discriminates(self) -> bool:
        return self.spread >= MIN_SPREAD and self.monotonic

    def as_dict(self) -> dict:
        return {
            "agent": self.agent,
            "rubric_version": self.rubric_version,
            "model": self.model,
            "ts": self.ts,
            "intended": list(self.intended),
            "observed": list(self.observed),
            "spread": self.spread,
            "monotonic": self.monotonic,
            "discriminates": self.discriminates,
            "min_spread_required": MIN_SPREAD,
            "per_rung": list(self.per_rung),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CalibrationResult":
        return cls(
            agent=d["agent"],
            rubric_version=d["rubric_version"],
            model=d.get("model", ""),
            ts=d.get("ts", ""),
            intended=tuple(d["intended"]),
            observed=tuple(d["observed"]),
            per_rung=tuple(d.get("per_rung", ())),
        )


def now_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_results(path: Path = RESULTS_PATH) -> dict:
    if not path.exists():
        return {
            "_note": "written by `python scripts/probe_grader.py --record`. "
            "Keyed agent|rubric_version. A rubric with no passing entry here cannot "
            "have a baseline recorded from its scores — see mastery/calibration.py.",
            "calibrations": {},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def result_key(agent: str, rubric_version: str) -> str:
    return f"{agent}|{rubric_version}"


def record(result: CalibrationResult, *, path: Path = RESULTS_PATH) -> dict:
    """Store a ladder run, passing or failing.

    A failed calibration is recorded, not discarded. It is the evidence that this
    rubric's numbers should not be trusted yet, and deleting it would leave the
    rubric merely *unmeasured* rather than *known bad* — a strictly worse state to
    hand the next person, who would have no way to tell the two apart.
    """
    data = load_results(path)
    data.setdefault("calibrations", {})
    data["calibrations"][result_key(result.agent, result.rubric_version)] = result.as_dict()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data["calibrations"][result_key(result.agent, result.rubric_version)]


def status(
    agent: str, rubric_version: str, *, path: Path = RESULTS_PATH
) -> tuple[Verdict, str]:
    """Trust state for one rubric version, and a sentence saying why."""
    data = load_results(path).get("calibrations", {})

    entry = data.get(result_key(agent, rubric_version))
    if entry is not None:
        if entry.get("discriminates"):
            return (
                Verdict.CALIBRATED,
                f"ladder run {entry.get('ts', '?')}: intended "
                f"{entry['intended']} -> observed {entry['observed']}, "
                f"spread {entry.get('spread')}",
            )
        return (
            Verdict.FAILED,
            f"ladder run {entry.get('ts', '?')} did not discriminate: observed "
            f"{entry['observed']}, spread {entry.get('spread')} "
            f"(needs >= {entry.get('min_spread_required', MIN_SPREAD)}), "
            f"monotonic={entry.get('monotonic')}",
        )

    others = sorted(
        v for k, v in ((k, k.split("|", 1)) for k in data) if v[0] == agent
    )
    if others:
        versions = ", ".join(f"v{v[1]}" for v in others)
        return (
            Verdict.STALE,
            f"calibrated at {versions}, but the rubric is now v{rubric_version}. "
            f"The anchors the ladder was written against have changed.",
        )

    return (
        Verdict.MISSING,
        f"no ladder has ever been run for {agent}. Its rubric may or may not "
        f"discriminate; nothing on record says which.",
    )


def require_calibrated(
    agent: str, rubric_version: str, *, path: Path = RESULTS_PATH
) -> None:
    """Refuse to treat this rubric's scores as evidence until it is calibrated.

    Called by `evals.set_baseline`. Not called by the orchestrator: an
    uncalibrated rubric still runs, still scores, and still logs. What it cannot
    do is have those scores promoted into a baseline that later decisions rest on.
    """
    verdict, why = status(agent, rubric_version, path=path)
    if verdict.trusted:
        return
    raise Uncalibrated(
        f"{agent} rubric v{rubric_version} is {verdict.value}: {why}\n"
        f"A baseline is the number STOP 6's tiering is measured against, and one "
        f"drawn through an unverified instrument is not evidence. Run:\n"
        f"    python scripts/probe_grader.py --agent {agent} --record"
    )
