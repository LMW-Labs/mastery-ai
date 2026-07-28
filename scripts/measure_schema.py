"""Measure how reliably real sub-agents return schema-valid JSON.

`retries_per_failed_task` is 1, which is only defensible if malformed returns
are rare. Nothing had ever tested that — every schema test to date ran against
returns this repo wrote itself.

This runs real briefs through the real delegation path (`delegate.run_task` +
`SdkRunner`), so it measures what actually ships: full agent doc in context,
shipped system prompt, shipped tool and permission config.

What counts as a PASS is schema validity, not task success. A `blocked` or
`failed` return that validates is a pass — the contract held. Only malformed
JSON, missing or extra fields, a bad enum, or a mismatched task_id is a failure.

    python scripts/measure_schema.py [samples]

Costs real quota: roughly $0.15 notional per sample.
"""

from __future__ import annotations

import asyncio
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mastery import delegate, ids
from mastery.brief import ContextItem, build
from mastery.config import Config
from mastery.errors import DelegationFailed, SchemaViolation, TaskTimeout
from mastery.schema import parse as parse_result

CONFIG = Config()

# Read-only tasks across agents with differently sized docs, so the measurement
# is not a single prompt shape repeated. Each is genuinely answerable with the
# Read/Glob/Grep allowlist, or answerable from reasoning alone.
CASES: list[tuple[str, str, list[str]]] = [
    (
        "strategy",
        "Recommend whether to build iOS support for FaithFeed next quarter or "
        "keep iterating on Android, and say why in one paragraph.",
        ["A recommendation naming one option", "A stated tradeoff"],
    ),
    (
        "content",
        "Write two one-sentence hooks for a post about a Bible-reading streak feature.",
        ["Exactly two hooks", "Each under 120 characters"],
    ),
    (
        "data-model-agent",
        "Review docs/agents/structured_output_schema.md and name one field whose "
        "constraints are weaker than they should be.",
        ["One named field", "A stated reason"],
    ),
    (
        "ui-ux",
        "Describe the empty state for a feed with no posts yet, in three bullets.",
        ["Three bullets", "No implementation detail"],
    ),
    (
        "metrics-agent",
        "Define one KPI for a reading-streak feature and state exactly how it is computed.",
        ["One KPI named", "A computation stated"],
    ),
]


@dataclass
class Sample:
    agent: str
    ok: bool
    status: str = ""
    failure_kind: str = ""
    detail: str = ""
    raw_head: str = ""


async def one(case_index: int, sequence: int, runner) -> Sample:
    agent, objective, criteria = CASES[case_index % len(CASES)]
    task_id = ids.mint("ops", sequence)

    brief = build(
        task_id=task_id,
        agent=agent,
        urgency="none",
        objective=objective,
        success_criteria=criteria,
        context=[ContextItem("note", "This is a measurement run; keep the work small.")],
        constraints="Keep it brief. Do not modify any file.",
        out_of_scope="Do not do work another agent owns.",
        approval_gates_touched="none",
        expected_deliverables=["the requested output"],
    )

    try:
        invocation = await delegate.run_task(brief, runner, CONFIG)
    except (DelegationFailed, TaskTimeout) as exc:
        # Not a schema failure — the delegation never produced a return to judge.
        return Sample(agent, False, failure_kind=type(exc).__name__, detail=str(exc)[:120])

    try:
        result = parse_result(invocation.raw, expected_task_id=task_id)
    except SchemaViolation as exc:
        return Sample(
            agent,
            False,
            failure_kind="SchemaViolation",
            detail=str(exc)[:160],
            raw_head=(invocation.raw or "")[:160],
        )

    return Sample(agent, True, status=result.status.value)


async def main() -> int:
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    runner = delegate.SdkRunner(CONFIG)

    print(f"measuring schema compliance over {total} real delegations")
    print(f"model={CONFIG.delegation.model}  auth={CONFIG.auth.mode}\n")

    semaphore = asyncio.Semaphore(3)  # modest concurrency; this is shared quota

    async def guarded(i: int) -> Sample:
        async with semaphore:
            sample = await one(i, i + 1, runner)
            mark = "ok" if sample.ok else "FAIL"
            extra = sample.status if sample.ok else sample.failure_kind
            print(f"  {i + 1:>3}/{total}  {sample.agent:<20} {mark:<5} {extra}")
            return sample

    samples = await asyncio.gather(*(guarded(i) for i in range(total)))

    passed = sum(1 for s in samples if s.ok)
    failed = total - passed
    rate = passed / total

    print(f"\nschema-valid: {passed}/{total}  ({rate:.0%})")
    print("statuses:", dict(Counter(s.status for s in samples if s.ok)))

    if failed:
        print("\nfailures:")
        for s in samples:
            if not s.ok:
                print(f"  [{s.agent}] {s.failure_kind}: {s.detail}")
                if s.raw_head:
                    print(f"      raw: {s.raw_head!r}")

    # A retry budget of 1 fails only when two consecutive returns are malformed.
    # With no observed failures, the rule of three puts the 95% upper bound on
    # the per-call failure rate at about 3/n — so quote the bound, not a claim
    # that the rate is zero.
    if failed == 0:
        bound = 3 / total
        print(
            f"\n0 failures in {total}. 95% upper bound on the per-call failure "
            f"rate is ~{bound:.0%} (rule of three)."
        )
        print(
            f"A retry budget of 1 exhausts only on two consecutive failures: "
            f"at that bound, ~{bound * bound:.1%} of tasks. Budget is defensible."
        )
    else:
        p = failed / total
        print(
            f"\nobserved per-call failure rate {p:.0%}; two consecutive ~{p * p:.1%}. "
            f"If that is above your tolerance, raise retries or tighten the prompt."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
