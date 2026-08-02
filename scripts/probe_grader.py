"""Calibration probe for the quality grader — run it against every rubric.

`quality.py` scores an output against its role's rubric. Nothing in that path
establishes that the rubric *discriminates*, and a grader that returns 3 whatever
it is shown produces a clean, plausible, entirely uninformative trend. The trend
cannot detect it: a rubber-stamp grader and an excellent agent draw the same flat
line.

The obvious remedy — run harder cases until a low score appears — is circular.
Under the rubber-stamp hypothesis those runs also come back 3.0 and read as
corroboration, so the investigation grows more confident as it grows more wrong.
**Sampling cannot audit the instrument doing the sampling.** The question is
answered with known inputs, not more unknown ones.

So this feeds the real grader a *ladder*: one fixed brief, one return per rubric
level, each written against that rubric's own anchor text, so its correct score is
known before the grader sees it. If the reported scores track the intended ones,
the rubric has markings.

**This is a per-rubric obligation, not a one-time gate.** A pass for one role says
nothing about the other sixteen — different dimensions, different anchors,
different failure modes — and it is void the moment that rubric's version changes.
Until a rubric has a passing ladder on record, `mastery eval --set-baseline`
refuses to record a baseline from its scores. See `mastery/calibration.py` for why
that is the enforcement point and not the delegation path.

Ladders are data, in `docs/agents/calibration_ladders.md`. Adding a role is
writing one, not editing this file.

**Nothing here is written to the run log.** These returns are synthetic and their
scores would be indistinguishable from real ones in the very trend the probe
exists to audit, so it drives the runner directly and never touches `Orchestrator`
or `runlog`. The calibration result goes to `evals/calibration.json` instead,
under `--record`.

Costs one grader call per rung. Needs a credential.

    python scripts/probe_grader.py --agent fact-checker
    python scripts/probe_grader.py --agent fact-checker --record
    python scripts/probe_grader.py --status
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

# Runnable as `python scripts/probe_grader.py` from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mastery import calibration, quality, roster
from mastery.cli import _force_utf8_stdio
from mastery.brief import ContextItem, build
from mastery.config import Config
from mastery.delegate import SdkRunner, run_grader
from mastery.errors import OrchestratorError
from mastery.schema import Status, TaskResult

# Task ids have to satisfy `brief.build`, so rungs carry real-shaped ids in a
# reserved 9xx block. Nothing here is logged, but a synthetic id that could
# collide with a real task would be a trap for whoever greps the logs later.
PROBE_DATE = "20260801"


@dataclass(frozen=True)
class Observation:
    intended: int
    label: str
    why: str
    score: quality.QualityScore | None
    model: str = ""
    cost_usd: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


def _brief(ladder: dict, rung: dict, agent: str):
    """The ladder's one brief. Identical for every rung, by construction.

    Holding it constant is what makes the rungs comparable: any difference in
    score has to come from the output, because nothing else changed.
    """
    b = ladder["brief"]
    brief = build(
        task_id=f"{PROBE_DATE}-{rung['label']}",
        agent=agent,
        urgency="normal",
        objective=b["objective"],
        success_criteria=list(b["success_criteria"]),
        context=[ContextItem(c["label"], c["body"]) for c in b["context"]],
        constraints=b["constraints"],
        out_of_scope=b["out_of_scope"],
        approval_gates_touched="none",
        expected_deliverables=list(b["expected_deliverables"]),
    )
    # Held to the same contract as a real brief, and for a reason that already
    # cost something: these were assembled by `build`, which checks only the task
    # id, and the ladders carried `constraints` as a *list* where `TaskBrief`
    # declares a string. Invisible while the grader was never shown the field.
    # The moment it is, every ladder renders a Python list repr that no real run
    # produces, and calibrates against a prompt nobody will ever see in
    # production. `validate` catches it here, before any call is paid for.
    brief.validate(Config.load().caps.max_context_bytes)
    return brief


def _result(rung: dict) -> TaskResult:
    return TaskResult(
        task_id=f"{PROBE_DATE}-{rung['label']}",
        status=Status(rung["status"]),
        summary=rung["summary"],
        deliverables=tuple(rung["deliverables"]),
        risks=tuple(rung["risks"]),
        next_step=rung["next_step"],
    )


async def _grade(ladder: dict, rung: dict, agent: str, config: Config) -> Observation:
    brief = _brief(ladder, rung, agent)
    common = dict(intended=rung["intended"], label=rung["label"], why=rung["why"])
    try:
        invocation = await run_grader(quality.build_prompt(brief, _result(rung)), SdkRunner(config), config)
        score = quality.parse(
            invocation.raw, expected_task_id=brief.task_id, expected_agent=agent
        )
    except OrchestratorError as exc:
        return Observation(**common, score=None, error=f"{type(exc).__name__}: {exc}")
    usage = getattr(invocation, "usage", None)
    return Observation(
        **common,
        score=score,
        model=_model_of(invocation),
        cost_usd=invocation.cost_usd,
        input_tokens=getattr(usage, "input_tokens", 0),
        output_tokens=getattr(usage, "output_tokens", 0),
    )


def _model_of(invocation) -> str:
    """The model that actually graded — `Usage.model`, already joined by
    `delegate.usage_from` when a call spans more than one.

    Recorded on the calibration so a later reader can tell whether the ladder was
    run on the same model as the scores it is being used to license. A ladder
    passed on a strong model does not license a cheap model's numbers.
    """
    usage = getattr(invocation, "usage", None)
    return getattr(usage, "model", "") or ""


def _report(observations: list[Observation], agent: str, rubric_version: str) -> calibration.CalibrationResult | None:
    """Print the ladder. Returns the result, or None if it could not be assessed."""
    print(f"\n{'=' * 78}")
    print(
        f"GRADER CALIBRATION — agent {agent}, rubric v{rubric_version}, "
        f"prompt {quality.prompt_fingerprint()}"
    )
    print(f"{'=' * 78}")

    for obs in observations:
        print(f"\n{obs.label}  intended {obs.intended}/3")
        print(f"  built to be: {obs.why}")
        if obs.error:
            print(f"  GRADER FAILED: {obs.error}")
            continue
        for d in obs.score.dimensions:
            delta = d.score - obs.intended
            flag = "  " if delta == 0 else f" {delta:+d}"
            print(f"    {d.dimension:34} {d.score}/3{flag}  {d.justification}")
        print(f"    {'OVERALL':34} {obs.score.overall}/3")

    graded = [o for o in observations if o.score is not None]
    if len(graded) < len(observations):
        print(
            f"\nINCONCLUSIVE — {len(observations) - len(graded)} of {len(observations)} "
            f"rungs did not return a score. A partial ladder cannot assess the "
            f"instrument, and is not recorded either way; fix the failures and re-run."
        )
        return None

    ordered = sorted(graded, key=lambda o: o.intended)
    result = calibration.CalibrationResult(
        agent=agent,
        rubric_version=rubric_version,
        # What the grader was shown, hashed. A ladder proves a rubric readable
        # through one particular prompt and says nothing about any other, so the
        # result records which one it ran through rather than leaving a reader to
        # assume it was whatever the prompt happens to be when they look.
        prompt_fingerprint=quality.prompt_fingerprint(),
        model="+".join(sorted({o.model for o in ordered if o.model})),
        ts=calibration.now_ts(),
        intended=tuple(o.intended for o in ordered),
        observed=tuple(o.score.overall for o in ordered),
        per_rung=tuple(
            {
                "label": o.label,
                "intended": o.intended,
                "observed": o.score.overall,
                "dimensions": {d.dimension: d.score for d in o.score.dimensions},
                "cost_usd": o.cost_usd,
                "input_tokens": o.input_tokens,
                "output_tokens": o.output_tokens,
            }
            for o in ordered
        ),
    )

    # A dimension that never moves is dead weight in the aggregate: it adds a
    # constant to every score and dilutes the dimensions that do discriminate.
    flat = [
        name
        for name in (d.dimension for d in ordered[0].score.dimensions)
        if len({dict((x.dimension, x.score) for x in o.score.dimensions)[name] for o in ordered}) == 1
    ]

    print(f"\n{'-' * 78}")
    print("  intended   " + "  ".join(f"{i}.0" for i in result.intended))
    print("  observed   " + "  ".join(f"{o:.1f}" for o in result.observed))
    print(f"  spread     {result.spread:.2f}  (needs >= {calibration.MIN_SPREAD} on a 3-point scale)")
    print(f"  monotonic  {result.monotonic}")
    if result.cost_usd is not None:
        per = [r["cost_usd"] for r in result.per_rung if r.get("cost_usd") is not None]
        print(f"  cost       ${result.cost_usd} for {len(per)} calls "
              f"(per-call ${min(per)} - ${max(per)})")
    if flat:
        print(f"  flat dims  {', '.join(flat)}  (same score on every rung)")
    print(f"{'-' * 78}")

    if result.spread < calibration.MIN_SPREAD:
        print(
            f"\nRUBBER STAMP — a deliberately {result.intended[0]}-level output and a "
            f"deliberately {result.intended[-1]}-level output scored within "
            f"{result.spread:.2f} of each other.\nThis rubric is not reading its own "
            f"anchors, and any score it has produced is uninformative. No baseline can\n"
            f"be recorded from it until the rubric or the ladder is fixed."
        )
    elif not result.monotonic:
        print(
            "\nNOT MONOTONIC — the grader separates outputs but does not order them the way\n"
            "the anchors do. It is responding to something, though not reliably to quality.\n"
            "Treat the trend as noisy rather than wrong; no baseline until it orders."
        )
    else:
        print(
            f"\nDISCRIMINATES — ordered, spread {result.spread:.2f} on a 3-point scale.\n"
            f"This rubric's scores can carry a baseline, for rubric v{rubric_version}\n"
            f"read through grading prompt {quality.prompt_fingerprint()}, and nothing else:\n"
            f"editing either the rubric or the prompt voids this and the ladder is re-run."
        )
    return result


def _print_status() -> int:
    """Where every rubric stands. No model calls."""
    rows = []
    for agent in sorted(a.name for a in roster.DELEGATABLE):
        if not quality.has_rubric(agent):
            rows.append((agent, "-", "NO RUBRIC", "cannot be delegated at all"))
            continue
        version = quality.rubric_version(agent)
        verdict, why = calibration.status(agent, version)
        rows.append((agent, f"v{version}", verdict.value.upper(), why))

    width = max(len(r[0]) for r in rows)
    state_width = max(len(r[2]) for r in rows)
    trusted = sum(1 for r in rows if r[2] == "CALIBRATED")
    print(
        f"calibration status — {trusted} of {len(rows)} rubrics calibrated, "
        f"grading prompt {quality.prompt_fingerprint()}\n"
    )
    for agent, version, state, why in rows:
        print(f"  {agent:{width}}  {version:4} {state:{state_width}} {why}")
    print(
        f"\nAn uncalibrated rubric still runs and still scores. What it cannot do is\n"
        f"have a baseline recorded from those scores — see mastery/calibration.py."
    )
    return 0 if trusted == len(rows) else 1


async def main() -> int:
    # Borrowed from cli.main rather than reimplemented. Without it this script
    # dies in print() on any justification containing an arrow or a dash -- after
    # every grader call has been paid for. That is the exact failure cli.py's
    # docstring describes, and it recurred here because the probe is a second
    # entry point that never went through cli.main. Two ladders were lost to it.
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", default=None, help="which rubric to calibrate")
    parser.add_argument(
        "--record",
        action="store_true",
        help=f"write the result to {calibration.RESULTS_PATH.name}, pass or fail",
    )
    parser.add_argument(
        "--status", action="store_true", help="show every rubric's state; no model calls"
    )
    args = parser.parse_args()

    if args.status:
        return _print_status()
    if not args.agent:
        print("--agent is required (or --status). Ladders are per rubric.", file=sys.stderr)
        return 2

    config = Config.load()
    quality.require_rubric(args.agent)
    version = quality.rubric_version(args.agent)

    try:
        ladder = calibration.ladder_for(args.agent, rubric_version=version)
    except calibration.LadderMissing as exc:
        print(f"{exc}", file=sys.stderr)
        return 2

    rungs = sorted(ladder["rungs"], key=lambda r: r["intended"])
    print(
        f"grading {len(rungs)} synthetic returns for {args.agent} "
        f"(rubric v{version}) — {len(rungs)} model calls, no run log written"
    )

    observations = [await _grade(ladder, rung, args.agent, config) for rung in rungs]
    result = _report(observations, args.agent, version)

    if result is None:
        return 1
    if args.record:
        calibration.record(result)
        print(f"\nrecorded -> {calibration.RESULTS_PATH}")
    elif result.discriminates:
        print("\nNOT recorded. Re-run with --record to license baselines for this rubric.")

    return 0 if result.discriminates else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
