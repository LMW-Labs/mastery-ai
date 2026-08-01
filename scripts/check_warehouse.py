"""End-to-end check of the Postgres projection, against a real server.

tests/test_warehouse.py covers the half that needs no database: log -> rows.
This covers the half that cannot be faked -- that the rows actually insert,
that re-ingest is genuinely a no-op rather than merely intended to be, and that
every view in postgres_schema.sql returns what the SQL claims.

It writes to the database, so it uses its own run ids and deletes them at the
end. It is a check, not a test fixture: run it after provisioning, and after
any change to postgres_schema.sql or warehouse.py.

    set -a; . /root/.mastery/postgres.env; set +a
    python scripts/check_warehouse.py

Exit 0 if every assertion holds, 1 otherwise, with the failure named.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mastery import warehouse  # noqa: E402
from mastery.runlog import RunLog  # noqa: E402

RUN_ID = "wcheck01"
TASK_ID = "20260730-ops-900"

failures: list[str] = []


def check(label: str, got, want) -> None:
    if got == want:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label}: got {got!r}, want {want!r}")
        failures.append(label)


def build_log(directory: Path) -> RunLog:
    """A run log covering every event the views read."""
    log = RunLog.open(directory, RUN_ID)
    log.run_start("check_warehouse synthetic run")
    log.delegation_start(
        task_id=TASK_ID, agent="ops", context_bytes=4096, attempt=1,
        tools=["Read", "Glob", "Grep"],
    )
    log.delegation_end(
        task_id=TASK_ID, agent="ops", status="complete",
        duration_s=42.5, num_turns=4, cost_usd=0.25,
        permission_denials=["WebSearch"],
        summary="Provisioned Postgres.",
        deliverables=["postgres_schema.sql applied"],
        risks=["listen_addresses is localhost only"],
        next_step="Ingest run logs.",
        role_tier="mechanical",
    )
    log.verdict(
        task_id=TASK_ID, verdict="accept", reason="criteria met",
        duration_s=3.0, num_turns=2, cost_usd=0.05, role_tier="judgment",
    )
    log.gate_hit(gate="production", detail="synthetic", task_id=TASK_ID)
    log.failure(kind="synthetic", detail="not a real failure", task_id=TASK_ID)
    # A second delegation that starts and never ends -- the crash signal.
    log.delegation_start(task_id=TASK_ID + "-b", agent="qa", context_bytes=512, attempt=1)
    log.run_end(outcome="accepted", detail="check complete")
    return log


def main() -> int:
    url = warehouse.dsn()

    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp)
        log = build_log(log_dir)
        total = len(log.read())

        print(f"log: {total} records in {log.path.name}")

        print("\nfirst ingest")
        first = warehouse.ingest(log_dir, url=url)
        check("all records inserted", first.inserted, total)
        check("nothing skipped on a fresh run", first.skipped, 0)
        check("no malformed lines", first.malformed, [])

        print("\nsecond ingest (idempotency)")
        second = warehouse.ingest(log_dir, url=url)
        check("nothing inserted twice", second.inserted, 0)
        check("all records reported as present", second.skipped, total)

    import psycopg

    print("\nviews")
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        def one(sql: str, *params):
            cur.execute(sql, params)
            row = cur.fetchone()
            return row[0] if row else None

        check("events rows", one("SELECT count(*) FROM events WHERE run_id=%s", RUN_ID), total)
        check("v_runs sees the run", one("SELECT count(*) FROM v_runs WHERE run_id=%s", RUN_ID), 1)
        check("v_runs outcome",
              one("SELECT outcome FROM v_runs WHERE run_id=%s", RUN_ID), "accepted")
        check("v_runs request survived",
              one("SELECT request FROM v_runs WHERE run_id=%s", RUN_ID),
              "check_warehouse synthetic run")

        check("v_delegations sees one completed delegation",
              one("SELECT count(*) FROM v_delegations WHERE run_id=%s", RUN_ID), 1)
        check("delegation joined to its start for context_bytes",
              one("SELECT context_bytes FROM v_delegations WHERE run_id=%s", RUN_ID), 4096)
        check("granted tools recorded",
              one("SELECT tools_granted::text FROM v_delegations WHERE run_id=%s", RUN_ID),
              '["Read", "Glob", "Grep"]')
        check("denial surfaced",
              one("SELECT denial_count FROM v_delegations WHERE run_id=%s", RUN_ID), 1)
        check("cost cast out of jsonb",
              float(one("SELECT cost_usd FROM v_delegations WHERE run_id=%s", RUN_ID)), 0.25)

        check("v_open_delegations catches the delegation with no end",
              one("SELECT task_id FROM v_open_delegations WHERE run_id=%s", RUN_ID),
              TASK_ID + "-b")

        check("v_verdicts", one("SELECT verdict FROM v_verdicts WHERE run_id=%s", RUN_ID), "accept")
        check("v_gate_hits", one("SELECT gate FROM v_gate_hits WHERE run_id=%s", RUN_ID), "production")
        check("v_failures", one("SELECT kind FROM v_failures WHERE run_id=%s", RUN_ID), "synthetic")

        # The point of v_stage_cost: delegation 0.25 + verdict 0.05 = 0.30, not 0.25.
        check("v_stage_cost sums delegation and verdict",
              float(one("SELECT total_cost_usd FROM v_stage_cost WHERE run_id=%s", RUN_ID)), 0.30)
        check("v_stage_cost keeps the delegation figure separate",
              float(one("SELECT delegation_cost_usd FROM v_stage_cost WHERE run_id=%s", RUN_ID)),
              0.25)
        check("v_stage_cost last_verdict",
              one("SELECT last_verdict FROM v_stage_cost WHERE run_id=%s", RUN_ID), "accept")

        cur.execute("DELETE FROM events WHERE run_id=%s", (RUN_ID,))
        conn.commit()
        check("synthetic rows cleaned up",
              one("SELECT count(*) FROM events WHERE run_id=%s", RUN_ID), 0)

    if failures:
        print(f"\nFAILED: {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("\nOK — projection verified end to end against a live server")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
