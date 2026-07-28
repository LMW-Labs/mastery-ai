"""Command line entry point.

Deliberately thin, and usable from a VPS or a mobile shell — no TUI, no
interactive prompts, output is plain text.

    mastery check                 validate config, roster, and schemas
    mastery run <brief.json>      run one delegation from a brief file
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from . import roster, schema, verdict
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mastery")
    parser.add_argument("--config", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="validate config, roster, and schemas")
    run_cmd = sub.add_parser("run", help="run one delegation from a brief file")
    run_cmd.add_argument("brief", type=Path)

    draft_cmd = sub.add_parser(
        "draft", help="turn a raw request into reviewable briefs (does not run them)"
    )
    draft_cmd.add_argument("request", nargs="?", help="the request, in your own words")
    draft_cmd.add_argument("--file", type=Path, help="read the request from a file instead")
    draft_cmd.add_argument(
        "--attach", action="append", default=[], help="a file the request refers to"
    )
    draft_cmd.add_argument("--out", type=Path, default=Path("briefs"))

    args = parser.parse_args(argv)
    config = Config.load(args.config)

    try:
        if args.command == "check":
            return _check(config)
        if args.command == "run":
            return asyncio.run(_run(config, args.brief))
        if args.command == "draft":
            text = args.file.read_text(encoding="utf-8") if args.file else args.request
            if not text or not text.strip():
                print("nothing to draft from", file=sys.stderr)
                return 2
            return asyncio.run(_draft(config, text, args.attach, args.out))
    except OrchestratorError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
