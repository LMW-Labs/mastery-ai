"""Command line entry point.

Deliberately thin, and usable from a VPS or a mobile shell — no TUI, no
interactive prompts, output is plain text.

    mastery check                 validate config, roster, and schemas
    mastery draft <request>       propose briefs from a raw request; runs nothing
    mastery run <brief.json>      run one delegation from a brief file
    mastery verify <brief.json>   verify a delegation already in the run log
    mastery ingest                copy run logs into Postgres for querying
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from . import calibration, quality, roster, schema, verdict, warehouse
from .brief import ContextItem, build
from .config import Config
from .delegate import SdkRunner
from .errors import OrchestratorError
from .orchestrator import Orchestrator, summarize


def _check(config: Config) -> int:
    """Confirm the parts that must agree actually agree, before any model call."""
    problems: list[str] = []

    for agent in roster.all_agents():
        if not agent.doc_path.exists():
            problems.append(f"{agent.name}: no doc at {agent.doc_path}")

    try:
        schema.schema()
    except Exception as exc:
        problems.append(f"structured_output_schema.md: {exc}")

    try:
        verdict.verdict_schema()
    except Exception as exc:
        problems.append(f"manager_verdict_schema.md: {exc}")

    if problems:
        print("FAIL")
        for p in problems:
            print(f"  - {p}")
        return 1

    caps = config.caps
    print("OK")
    print(f"  agents            {len(roster.all_agents())} ({len(roster.DELEGATABLE)} delegatable)")
    print(f"  max delegations   {caps.max_delegations_per_request}")
    print(f"  max sub-agent turns {caps.max_subagent_turns}")
    print(f"  max context bytes {caps.max_context_bytes}")
    print(f"  retries           {caps.retries_per_failed_task}")
    print(f"  task timeout      {caps.task_timeout_seconds}s")
    print(f"  model             {config.delegation.model}")
    print(f"  denied tools      {', '.join(config.delegation.denied_tools)}")
    print(f"  auth mode         {config.auth.mode}")

    # Coverage, not a failure. An uncalibrated rubric still runs and still scores;
    # it just cannot carry a baseline. Reporting it here means the number is in
    # front of the operator before they go looking for a baseline that will be
    # refused, rather than after.
    calibrated = sum(
        1
        for a in (x.name for x in roster.DELEGATABLE)
        if quality.has_rubric(a)
        and calibration.status(a, quality.rubric_version(a))[0].trusted
    )
    print(f"  rubrics calibrated {calibrated}/{len(roster.DELEGATABLE)}  "
          f"(uncalibrated rubrics score but cannot carry a baseline)")
    return 0


def _load_brief(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    context = [
        ContextItem(item["label"], item["body"]) for item in raw.get("context", [])
    ]
    return build(
        task_id=raw["task_id"],
        agent=raw["agent"],
        urgency=raw["urgency"],
        objective=raw["objective"],
        success_criteria=raw["success_criteria"],
        context=context,
        constraints=raw["constraints"],
        out_of_scope=raw["out_of_scope"],
        approval_gates_touched=raw["approval_gates_touched"],
        expected_deliverables=raw["expected_deliverables"],
    )


async def _run(config: Config, brief_path: Path) -> int:
    brief = _load_brief(brief_path)
    orch = Orchestrator(config, SdkRunner(config))
    orch.log.run_start(f"cli run {brief_path.name}")
    outcome = await orch.execute(brief)
    print(summarize(outcome))
    print(f"\nrun log: {orch.log.path}")
    return 0 if outcome.accepted else 1


async def _verify(config: Config, brief_path: Path, run_id: str | None) -> int:
    """Verify a delegation that already ran, from the run log.

    The delegation is the expensive half. When a manager-side fault loses the
    verdict — a one-turn call that blew up, a crash after the return landed —
    the work is still on disk and re-running the task would pay for it twice.
    This runs the missing half only.

    It is not a way around verification: the same prompt, the same schema, the
    same three verdicts. The only thing it skips is repeating work already done.
    """
    from . import verdict as verdict_mod
    from .delegate import run_verdict
    from .runlog import recover_result

    brief = _load_brief(brief_path)
    found = recover_result(config.log_dir, brief.task_id, run_id=run_id)
    if found is None:
        where = f"run {run_id}" if run_id else str(config.log_dir)
        print(f"no completed delegation for {brief.task_id} in {where}", file=sys.stderr)
        return 2

    result, source_run = found
    print(f"verifying {brief.task_id} ({brief.agent}) from run {source_run}")
    print(f"  returned status: {result.status.value}, {len(result.deliverables)} deliverable(s)")

    invocation = await run_verdict(
        verdict_mod.build_prompt(brief, result), SdkRunner(config), config
    )
    mv = verdict_mod.parse(invocation.raw, expected_task_id=brief.task_id)

    print(f"\nverdict: {mv.verdict.value}")
    print(f"reason : {mv.reason}")
    if mv.revision_note:
        print(f"revise : {mv.revision_note}")
    return 0 if mv.accepted else 1


async def _draft(config: Config, request: str, attachments: list[str], out: Path) -> int:
    """Turn a raw operator request into reviewable briefs. Never executes."""
    from . import drafter
    from .delegate import Invocation, SdkRunner, run_draft

    runner = SdkRunner(config)
    prompt = drafter.build_prompt(request, attachments=attachments)
    invocation: Invocation = await run_draft(prompt, runner, config)
    plan = drafter.parse(invocation.raw)

    print(drafter.render(plan))

    if not plan.scoped:
        return 1

    if drafter.over_cap(plan, config):
        print(
            f"\nNOTE: {len(plan.stages)} stages against a cap of "
            f"{config.caps.max_delegations_per_request} delegations per operator request, "
            f"and a retry costs a delegation too. Run these as separate requests, one "
            f"`mastery run` per brief, rather than as a single pipeline."
        )

    from datetime import date

    written = drafter.write_briefs(plan, out, stamp=date.today().strftime("%Y%m%d"))
    print("\nbriefs written (context payloads are placeholders — fill them):")
    for path in written:
        print(f"  {path}")
    print("\nNothing has run. Edit a brief, then: mastery run <brief>")
    return 0


def _force_utf8_stdio() -> None:
    """Make stdout survive the output it is asked to print.

    Windows consoles default to a legacy codepage (cp1252 here), and agent
    output is full of arrows, dashes, and section signs. Without this, a run
    that fully succeeded dies in `print(summarize(...))` with UnicodeEncodeError
    — the work is done, logged, and then thrown away at the last step. That is
    the worst possible failure: expensive, silent about its real cause, and
    indistinguishable at the shell from the task itself failing.

    `errors="replace"` rather than "strict": a terminal that genuinely cannot
    render a glyph should show a placeholder, not lose the whole report. The
    run log is UTF-8 regardless and stays the faithful copy.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _eval(config: Config, set_baseline: str | None, agent: str | None) -> int:
    """Trend scores, or record a baseline from them."""
    from . import evals

    if set_baseline is None:
        print(evals.render(config.log_dir))
        return 0

    if not agent:
        print("--set-baseline requires --agent", file=sys.stderr)
        return 2

    records = [r for r in evals.load_scores(config.log_dir) if r.key.agent == agent]
    if not records:
        print(f"no quality scores recorded for agent {agent!r}", file=sys.stderr)
        return 2

    try:
        entry = evals.set_baseline(records, label=set_baseline)
    except evals.IncomparableScores as exc:
        # Refused rather than averaged. An average across incomparable runs looks
        # like a number, which is worse than having none.
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    except calibration.Uncalibrated as exc:
        # Same refusal, one step earlier: these scores may be perfectly comparable
        # with each other and still come from an instrument nobody has checked.
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    print(f"baseline '{set_baseline}' recorded for {agent}")
    print(f"  rubric_version   {entry['rubric_version']}")
    print(f"  model            {entry['model']}")
    print(f"  n                {entry['n']}")
    print(f"  overall mean     {entry['overall_mean']}/3 ({entry['normalised_mean']:.1%})")
    for dim, mean in entry["per_dimension_mean"].items():
        print(f"    {dim:36} {mean}")
    print(f"  -> {evals.BASELINES_PATH}")
    return 0


def _ingest(config: Config, url: str | None, run_id: str | None) -> int:
    """Copy run logs into Postgres. Never called during a run — see warehouse.py."""
    from . import warehouse

    try:
        report = warehouse.ingest(config.log_dir, url=url, run_id=run_id)
    except warehouse.WarehouseUnavailable as exc:
        print(f"ingest unavailable: {exc}", file=sys.stderr)
        return 2

    print(f"ingested from {config.log_dir}: {report}")
    for complaint in report.malformed:
        # Named, not swallowed. A line that would not parse is a real defect in
        # the log and the operator is the only one who can decide it is benign.
        print(f"  malformed: {complaint}", file=sys.stderr)
    return 1 if report.malformed else 0


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(prog="mastery")
    parser.add_argument("--config", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="validate config, roster, and schemas")
    run_cmd = sub.add_parser("run", help="run one delegation from a brief file")
    run_cmd.add_argument("brief", type=Path)

    verify_cmd = sub.add_parser(
        "verify", help="run the manager verdict against a delegation already in the run log"
    )
    verify_cmd.add_argument("brief", type=Path)
    verify_cmd.add_argument("--run", default=None, help="run id; defaults to the most recent")

    draft_cmd = sub.add_parser(
        "draft", help="turn a raw request into reviewable briefs (does not run them)"
    )
    draft_cmd.add_argument("request", nargs="?", help="the request, in your own words")
    draft_cmd.add_argument("--file", type=Path, help="read the request from a file instead")
    draft_cmd.add_argument(
        "--attach", action="append", default=[], help="a file the request refers to"
    )
    draft_cmd.add_argument("--out", type=Path, default=Path("briefs"))

    eval_cmd = sub.add_parser(
        "eval", help="trend recorded quality scores, or record a baseline"
    )
    eval_cmd.add_argument(
        "--set-baseline",
        metavar="LABEL",
        default=None,
        help="record the scores for --agent as a baseline under this label "
        "(e.g. fresh-strong-model, retro-sanity-check)",
    )
    eval_cmd.add_argument(
        "--agent", default=None, help="required with --set-baseline: which agent"
    )

    ingest_cmd = sub.add_parser(
        "ingest", help="copy run logs into Postgres for querying (does not run anything)"
    )
    ingest_cmd.add_argument(
        "--dsn", default=None, help=f"connection string; defaults to ${warehouse.DSN_ENV}"
    )
    ingest_cmd.add_argument(
        "--run", default=None, help="ingest only this run id; defaults to all logs"
    )

    args = parser.parse_args(argv)

    try:
        # Inside the handler: Config.load enforces the guardrail floor, so a
        # config that tries to widen permission_mode or empty denied_tools
        # raises here. That is an expected refusal with an actionable message,
        # not a crash, and it should read like one.
        config = Config.load(args.config)

        if args.command == "check":
            return _check(config)
        if args.command == "run":
            return asyncio.run(_run(config, args.brief))
        if args.command == "verify":
            return asyncio.run(_verify(config, args.brief, args.run))
        if args.command == "draft":
            text = args.file.read_text(encoding="utf-8") if args.file else args.request
            if not text or not text.strip():
                print("nothing to draft from", file=sys.stderr)
                return 2
            return asyncio.run(_draft(config, text, args.attach, args.out))
        if args.command == "eval":
            return _eval(config, args.set_baseline, args.agent)
        if args.command == "ingest":
            return _ingest(config, args.dsn, args.run)
    except OrchestratorError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
