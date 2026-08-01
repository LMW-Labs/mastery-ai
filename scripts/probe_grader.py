"""Calibration probe for the quality grader. STOP 7's open question.

Every fact-checker score on record is a 3.0/3. Two explanations fit that, and
they have opposite consequences:

  A. **Sampling.** Only accepted outcomes were scored, so every run that had to
     stop something was censored out of the sample. Fixed 2026-07-31 — gate
     closures are scored now.
  B. **Instrument.** The grader returns 3 whatever it is shown, and the number
     has never measured anything.

A flat trend cannot distinguish them, and neither can more real runs: if (B)
holds, those runs also come back 3.0 and look like confirmation. The only way
to separate them is to stop sampling and start calibrating — feed the grader
outputs whose correct score is already known, and see what it says.

That is what this does. Four returns for the same task, each written against
one row of the fact-checker rubric's own anchor text: a 0, a 1, a 2, a 3. The
real grader, over the real `run_grader` path, no tools. If the reported scores
track the intended ones the instrument discriminates and (A) was the story. If
everything comes back 3, the baseline in `evals/baselines.json` is measuring
nothing and STOP 6 has no evidence under it.

The ladder is scored on the anchors, not on my opinion of the writing. Each
rung names the anchors it was built to satisfy, so a disagreement between
intent and result is arguable against a fixed reference rather than a matter
of taste.

**Nothing here is written to the run log.** These returns are synthetic and
their scores would corrupt the trend they exist to audit, so the probe drives
the runner directly and never touches `Orchestrator` or `runlog`.

Costs one grader call per rung. Needs a credential.

    python scripts/probe_grader.py
    python scripts/probe_grader.py --agent risk-review   # ladder is fact-checker only
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

# Runnable as `python scripts/probe_grader.py` from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mastery import quality
from mastery.brief import ContextItem, build
from mastery.config import Config
from mastery.delegate import SdkRunner, run_grader
from mastery.errors import OrchestratorError
from mastery.schema import Status, TaskResult

# The draft under review, and the one source supplied to check it against. Kept
# small on purpose: the grader is judging the fact-check, not the underlying
# question, and a long fixture would let a rung score well for being thorough
# about something the rubric never asked about.
DRAFT = """A 2024 Pew study found that 63% of US adults pray daily. That makes
America the most prayerful nation in the developed world, and as Dr. Ellen Marsh
put it, we are watching "a generational shift" in public faith."""

SOURCE = """Pew Research Center, "Religious Landscape Study" (2024), p. 12:
"45% of U.S. adults say they pray daily, down from 58% in 2007." The report
covers the United States only and makes no cross-national comparison. No
researcher named Ellen Marsh appears in the report or its acknowledgements."""

# Three checkable assertions live in DRAFT: the 63% figure (explicit, numeric,
# and false against the source), the "most prayerful in the developed world"
# superlative (implied, and uncheckable from the supplied source), and the
# Marsh quote (an attribution the source cannot confirm). A rung's level is
# mostly determined by how many of those three it touches and how honestly.


# Task ids have to satisfy `brief.build`, so the rungs get real-shaped ones in a
# reserved 9xx block. Nothing here is logged, but a synthetic id that could
# collide with a real task would be a trap for whoever greps the logs later.
PROBE_DATE = "20260801"


@dataclass(frozen=True)
class Rung:
    """One return, built to sit at a known level on every dimension."""

    intended: int
    label: str
    why: str
    summary: str
    deliverables: tuple[str, ...]
    risks: tuple[str, ...]
    next_step: str
    status: Status = Status.BLOCKED


LADDER: tuple[Rung, ...] = (
    Rung(
        intended=0,
        label="rd-900",
        why=(
            "Only the headline claim adjudicated; the false figure rated supported; "
            "no source referenced; the uncheckable claims silently passed; no corrections."
        ),
        status=Status.COMPLETE,
        summary="Checked the post. The prayer statistic is accurate and the piece is fine to run.",
        deliverables=(
            "Claim 'a 2024 Pew study found 63% of US adults pray daily' - SUPPORTED.",
            "Overall: publishable.",
        ),
        risks=("None identified.",),
        next_step="Send to risk-review.",
    ),
    Rung(
        intended=1,
        label="rd-901",
        why=(
            "Explicit numeric claim found, superlative and attribution missed; a softened "
            "version checked so the overstatement passed; source named in general only; "
            "unchecked claims passed without comment; correction no better sourced."
        ),
        status=Status.COMPLETE,
        summary=(
            "Verified the prayer figure against the Pew material. A majority-pray framing is "
            "broadly consistent with the research, so the claim stands with a small edit."
        ),
        deliverables=(
            "Claim: many US adults pray daily - SUPPORTED by the Pew study.",
            "Suggested wording: 'a large share of US adults pray daily'.",
        ),
        risks=("Figures in this area move between survey waves.",),
        next_step="Send to risk-review.",
    ),
    Rung(
        intended=2,
        label="rd-902",
        why=(
            "Explicit claim plus one implied one; the attribution left out entirely; ratings "
            "defensible but the superlative rated too generously; most ratings tied to a named "
            "source, one not; the unchecked claim noted with a vague reason; correction mostly "
            "supported but reaches slightly past the source."
        ),
        summary=(
            "Two of the post's assertions were checked against the supplied Pew report. The 63% "
            "figure is wrong and the international comparison is not something this source settles."
        ),
        deliverables=(
            "Claim '63% of US adults pray daily' - FALSE. Pew 2024 reports 45%.",
            "Claim 'most prayerful nation in the developed world' - PARTIALLY SUPPORTED; US "
            "religiosity does run high among wealthy democracies, though this report is US-only.",
            "Correction: 'a 2024 Pew study found 45% of US adults pray daily, down from 58% "
            "in 2007, the sharpest decline the series has recorded'.",
        ),
        risks=("One assertion in the draft could not be resolved from what was supplied.",),
        next_step="Return to content for correction, then re-check.",
    ),
    Rung(
        intended=3,
        label="rd-903",
        why=(
            "All three assertions adjudicated including the implied superlative and the "
            "attribution; each rating the one the source permits; every rating names the page "
            "and passage; both uncheckable claims listed with the reason; the correction is "
            "wording the source actually supports and invents no citation."
        ),
        summary=(
            "Three checkable assertions in the draft. One is false against the supplied source, "
            "two cannot be checked from it at all. Not publishable as written."
        ),
        deliverables=(
            "Claim '63% of US adults pray daily' - FALSE. Pew 2024 p.12 states '45% of U.S. "
            "adults say they pray daily, down from 58% in 2007'. The draft overstates by 18 points.",
            "Claim 'most prayerful nation in the developed world' - UNCHECKED. Pew 2024 p.12 "
            "covers the United States only and makes no cross-national comparison, so the "
            "supplied source cannot settle this claim either way. No other source was provided.",
            "Attribution 'Dr. Ellen Marsh: a generational shift' - UNCHECKED. No researcher of "
            "that name appears in the report or its acknowledgements. Absence from this source "
            "is not proof the quote is fabricated, but nothing supplied supports it.",
            "Correction, using only what the source states: 'a 2024 Pew study found 45% of US "
            "adults say they pray daily, down from 58% in 2007'. The superlative and the Marsh "
            "quote should be cut or independently sourced; no citation was invented to keep them.",
        ),
        risks=(
            "Two of three assertions rest on sources not supplied to this check; a verdict on "
            "them requires evidence this task did not have.",
            "The 18-point gap is large enough that the draft's argument may not survive correction.",
        ),
        next_step=(
            "Blocked: not publishable. Return to content with the correction, and source the "
            "superlative and the Marsh quote or drop them."
        ),
    ),
)


def _brief(rung: Rung, agent: str):
    """The same brief for every rung — only the return varies.

    Holding the brief fixed is what makes the rungs comparable: any difference
    in score has to come from the output, because nothing else changed.
    """
    return build(
        task_id=f"{PROBE_DATE}-{rung.label}",
        agent=agent,
        urgency="normal",
        objective=(
            "Adjudicate every checkable claim in the supplied draft against the supplied "
            "source, and state which claims cannot be checked from it."
        ),
        success_criteria=[
            "Every checkable assertion in the draft is adjudicated, including implied "
            "claims, superlatives, and attributions.",
            "Each rating names the specific source passage it was checked against.",
            "Claims that cannot be checked from the supplied source are listed as unchecked, "
            "with the reason, rather than passed.",
            "Any corrected wording is supported by the supplied source.",
        ],
        context=[
            ContextItem("draft under review", DRAFT),
            ContextItem("supplied source", SOURCE),
        ],
        constraints=[
            "Use only the supplied source. Do not look anything up.",
            "Return `blocked` if the draft is not publishable as written.",
        ],
        out_of_scope=["Rewriting the piece beyond the minimal correction."],
        approval_gates_touched="none",
        expected_deliverables=["A per-claim adjudication with sources.", "Corrected wording."],
    )


def _result(rung: Rung) -> TaskResult:
    return TaskResult(
        task_id=f"{PROBE_DATE}-{rung.label}",
        status=rung.status,
        summary=rung.summary,
        deliverables=rung.deliverables,
        risks=rung.risks,
        next_step=rung.next_step,
    )


@dataclass(frozen=True)
class Observation:
    rung: Rung
    score: quality.QualityScore | None
    error: str | None = None


async def _grade(rung: Rung, agent: str, config: Config) -> Observation:
    brief = _brief(rung, agent)
    prompt = quality.build_prompt(brief, _result(rung))
    try:
        invocation = await run_grader(prompt, SdkRunner(config), config)
        score = quality.parse(
            invocation.raw, expected_task_id=brief.task_id, expected_agent=agent
        )
    except OrchestratorError as exc:
        return Observation(rung, None, f"{type(exc).__name__}: {exc}")
    return Observation(rung, score)


def _report(observations: list[Observation], agent: str) -> bool:
    """Print the ladder and return True if the grader discriminated."""
    rubric = quality.rubric_for(agent)
    dims = [d["dimension"] for d in rubric["dimensions"]]

    print(f"\n{'=' * 78}\nGRADER CALIBRATION — agent {agent}, rubric v{rubric['rubric_version']}\n{'=' * 78}")

    for obs in observations:
        print(f"\n{obs.rung.label}  intended {obs.rung.intended}/3")
        print(f"  built to be: {obs.rung.why}")
        if obs.error:
            print(f"  GRADER FAILED: {obs.error}")
            continue
        for d in obs.score.dimensions:
            delta = d.score - obs.rung.intended
            flag = "  " if delta == 0 else f" {delta:+d}"
            print(f"    {d.dimension:34} {d.score}/3{flag}  {d.justification}")
        print(f"    {'OVERALL':34} {obs.score.overall}/3")

    graded = [o for o in observations if o.score is not None]
    if len(graded) < len(observations):
        print(f"\nINCONCLUSIVE — {len(observations) - len(graded)} of {len(observations)} "
              f"rungs did not return a score. The instrument cannot be assessed from a "
              f"partial ladder; fix the failures and re-run.")
        return False

    overalls = [o.score.overall for o in graded]
    intended = [o.rung.intended for o in graded]
    spread = max(overalls) - min(overalls)
    monotonic = all(a <= b for a, b in zip(overalls, overalls[1:]))

    print(f"\n{'-' * 78}")
    print("  intended   " + "  ".join(f"{i}.0" for i in intended))
    print("  observed   " + "  ".join(f"{o:.1f}" for o in overalls))
    print(f"  spread     {spread:.2f}  (0-rung to 3-rung, on a 3-point scale)")
    print(f"  monotonic  {monotonic}")

    # A dimension that never moves is dead weight in the aggregate: it adds a
    # constant to every score and dilutes the dimensions that do discriminate.
    flat = [
        name
        for i, name in enumerate(dims)
        if len({o.score.dimensions[i].score for o in graded}) == 1
    ]
    if flat:
        print(f"  flat dims  {', '.join(flat)}  (same score on all four rungs)")

    print(f"{'-' * 78}")

    if spread < 1.0:
        print(
            f"\nRUBBER STAMP — a deliberately 0-level output and a deliberately 3-level\n"
            f"output scored within {spread:.2f} of each other. The grader is not reading the\n"
            f"anchors, and every score in evals/baselines.json is uninformative. STOP 6\n"
            f"tiering has no evidence under it until this is fixed."
        )
        return False

    if not monotonic:
        print(
            "\nNOT MONOTONIC — the grader separates outputs but does not order them the way\n"
            "the anchors do. It is responding to something, though not reliably to quality.\n"
            "Treat the trend as noisy rather than wrong, and re-run before drawing on it."
        )
        return False

    print(
        f"\nDISCRIMINATES — the ladder came back ordered, spread {spread:.2f} on a 3-point\n"
        f"scale. The instrument reads the anchors, so the flat 3.0 baseline was a property\n"
        f"of the sample, not of the grader: only accepted outcomes were ever scored."
    )
    return True


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent",
        default="fact-checker",
        help="agent whose rubric to calibrate. The ladder is written against "
        "fact-checker's anchors; another agent grades the same text on the wrong "
        "rubric, which measures nothing.",
    )
    args = parser.parse_args()

    if args.agent != "fact-checker":
        print(
            f"NOTE: the ladder's four rungs are written against fact-checker's anchors. "
            f"Grading them on {args.agent}'s rubric compares outputs to criteria they were "
            f"never built for, and a poor result would say nothing about the grader.\n",
            file=sys.stderr,
        )

    config = Config.load()
    quality.require_rubric(args.agent)

    print(f"grading {len(LADDER)} synthetic returns — {len(LADDER)} model calls, no run log written")
    observations = [await _grade(rung, args.agent, config) for rung in LADDER]
    return 0 if _report(observations, args.agent) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
