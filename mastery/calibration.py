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
anchors, and different failure modes.

**It is bound to two things, because a calibration is a claim about two.** A
ladder run says "this rubric discriminates *when a grader is shown these facts
about the output*". Both halves can move:

- the **rubric** (`rubric_version`) — editing it invalidates the calibration,
  because the anchors the rungs were written against no longer exist;
- the **grading prompt** (`quality.prompt_fingerprint`) — changing what
  `quality._render` puts in front of the grader invalidates it just as
  completely, because the instrument answered a different question.

Only the first was bound at first, and the omission surfaced in the way these
things do: `content`'s ladder failed because two of its four dimensions ask
whether the output honoured instructions the grader is never shown — the angle
lives in the context payload, the word limit in `constraints`, and neither
reaches the prompt. The fix is to show the grader more. But under version-binding
alone that fix would have silently voided all seventeen calibrations while every
one of them went on reporting `calibrated` — version-binding's own trap, arriving
through the door version-binding does not cover. Hence the fingerprint, and hence
`PROMPT_CHANGED` as a verdict distinct from `STALE`: different cause, different
repair, and collapsing them would hide which of the two actually moved.

A calibration that silently carried across either bump would be worse than none,
since it would attest to markings nobody had checked.

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

from . import quality
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
    PROMPT_CHANGED = "prompt-changed"
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
    # The grading prompt this ladder was actually run through. No default: a
    # result that does not know which prompt produced it is not evidence about
    # any prompt, and defaulting it to "whatever is current" would manufacture
    # exactly the false attestation the fingerprint exists to prevent.
    prompt_fingerprint: str = ""

    @property
    def cost_usd(self) -> float | None:
        """What this ladder actually cost. None if no rung reported a figure.

        Recorded because the first two ladders did not record it, and their bill
        is therefore unrecoverable: the probe drives `run_grader` directly, so no
        `quality_score` event was ever written, and the `Invocation` carrying
        `cost_usd` was read for its model name and discarded. Eight real grader
        calls with no price on record.

        That is the same defect as the untelemetered verdict call — a call path
        that spends and does not account — reintroduced by a design note that
        said "nothing here is written to the run log". True and deliberate about
        *scores*, which would corrupt the trend. Never true about *cost*, which
        is a separate concern that had no reason to be suppressed.
        """
        figures = [r["cost_usd"] for r in self.per_rung if r.get("cost_usd") is not None]
        return round(sum(figures), 6) if figures else None

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
            "prompt_fingerprint": self.prompt_fingerprint,
            "model": self.model,
            "ts": self.ts,
            "intended": list(self.intended),
            "observed": list(self.observed),
            "spread": self.spread,
            "monotonic": self.monotonic,
            "discriminates": self.discriminates,
            "min_spread_required": MIN_SPREAD,
            "cost_usd": self.cost_usd,
            "per_rung": list(self.per_rung),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CalibrationResult":
        return cls(
            agent=d["agent"],
            rubric_version=d["rubric_version"],
            prompt_fingerprint=d.get("prompt_fingerprint", ""),
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


def result_key(agent: str, rubric_version: str, prompt_fingerprint: str) -> str:
    """Both axes in the key, so a mismatch on either one simply misses.

    Keyed rather than compared-after-lookup on purpose: a lookup that found the
    entry and then checked a field would leave a code path where the entry is in
    hand and the check could be forgotten. There is no such path if the key is
    wrong from the start.
    """
    return f"{agent}|{rubric_version}|{prompt_fingerprint}"


def _parts(key: str) -> tuple[str, str, str]:
    """Split a stored key, tolerating the two-field keys written before the
    fingerprint existed. Those are reported as unfingerprinted, never as a match."""
    bits = key.split("|")
    return (bits[0], bits[1] if len(bits) > 1 else "", bits[2] if len(bits) > 2 else "")


def record(result: CalibrationResult, *, path: Path = RESULTS_PATH) -> dict:
    """Store a ladder run, passing or failing.

    A failed calibration is recorded, not discarded. It is the evidence that this
    rubric's numbers should not be trusted yet, and deleting it would leave the
    rubric merely *unmeasured* rather than *known bad* — a strictly worse state to
    hand the next person, who would have no way to tell the two apart.
    """
    if not result.prompt_fingerprint:
        raise Uncalibrated(
            f"{result.agent}'s ladder result carries no prompt fingerprint, so there "
            f"is no record of which grading prompt produced it. Recording it would "
            f"put an unattributable number where an attestation belongs."
        )
    key = result_key(result.agent, result.rubric_version, result.prompt_fingerprint)
    data = load_results(path)
    data.setdefault("calibrations", {})
    data["calibrations"][key] = result.as_dict()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data["calibrations"][key]


def status(
    agent: str,
    rubric_version: str,
    *,
    prompt_fingerprint: str | None = None,
    path: Path = RESULTS_PATH,
) -> tuple[Verdict, str]:
    """Trust state for one (rubric version, grading prompt), and why.

    Order matters. An exact hit is decided on its own merits; after that the
    near-misses are reported most-specific first, so the message names the thing
    that actually moved rather than the first difference found.
    """
    fingerprint = prompt_fingerprint or quality.prompt_fingerprint()
    data = load_results(path).get("calibrations", {})

    entry = data.get(result_key(agent, rubric_version, fingerprint))
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

    mine = [_parts(k) for k in data if _parts(k)[0] == agent]

    same_rubric = sorted({p[2] or "(unfingerprinted)" for p in mine if p[1] == rubric_version})
    if same_rubric:
        return (
            Verdict.PROMPT_CHANGED,
            f"calibrated at rubric v{rubric_version} — which has not changed — but "
            f"through grading prompt {', '.join(same_rubric)}, and the prompt is now "
            f"{fingerprint}. The grader is being shown a different set of facts than "
            f"the ladder proved it could read. Re-run the ladder; the rubric is fine.",
        )

    versions = sorted({p[1] for p in mine})
    if versions:
        return (
            Verdict.STALE,
            f"calibrated at {', '.join(f'v{v}' for v in versions)}, but the rubric is "
            f"now v{rubric_version}. The anchors the ladder was written against have "
            f"changed.",
        )

    return (
        Verdict.MISSING,
        f"no ladder has ever been run for {agent}. Its rubric may or may not "
        f"discriminate; nothing on record says which.",
    )


def require_calibrated(
    agent: str,
    rubric_version: str,
    *,
    prompt_fingerprint: str | None = None,
    path: Path = RESULTS_PATH,
) -> None:
    """Refuse to treat this rubric's scores as evidence until it is calibrated.

    Called by `evals.set_baseline`. Not called by the orchestrator: an
    uncalibrated rubric still runs, still scores, and still logs. What it cannot
    do is have those scores promoted into a baseline that later decisions rest on.
    """
    verdict, why = status(
        agent, rubric_version, prompt_fingerprint=prompt_fingerprint, path=path
    )
    if verdict.trusted:
        return
    raise Uncalibrated(
        f"{agent} rubric v{rubric_version} is {verdict.value}: {why}\n"
        f"A baseline is the number STOP 6's tiering is measured against, and one "
        f"drawn through an unverified instrument is not evidence. Run:\n"
        f"    python scripts/probe_grader.py --agent {agent} --record"
    )
