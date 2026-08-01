"""Load run logs into Postgres for querying.

The JSONL run logs stay the source of truth. This module copies them into a
database so they can be queried with SQL; it never writes to the database on
the hot path of a run, and nothing in the orchestrator imports it.

That split is deliberate, and it is the whole design:

  * `runlog.py` is a local file append with no network dependency. It is why a
    run that times out or crashes still leaves a record of how far it got. A
    socket in that path would add a failure mode where the run dies *and* the
    record is lost — the silence runlog.py exists to prevent.
  * The system "must stay usable from a VPS and a mobile shell" (CLAUDE.md). A
    hard database dependency would make every run fail when the DB is down or
    unreachable, for a benefit — queryability — that is not needed mid-run.

So ingest is a separate, explicit step. If it fails, nothing is lost: the logs
are still on disk and the next ingest picks up everything.

`psycopg` is imported lazily and is not in requirements.txt. `mastery check`,
`draft`, `run`, `verify`, and `eval` all work without it installed.

Connection string comes from the `MASTERY_DATABASE_URL` environment variable,
not from config.json, because it carries a password and config.json is a repo
file. On the provisioned host it is written to /root/.mastery/postgres.env at
mode 0600 — `set -a; . /root/.mastery/postgres.env; set +a` before running.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DSN_ENV = "MASTERY_DATABASE_URL"

# Lifted into their own columns for indexing; they stay in `payload` as well, so
# the row remains a faithful copy of the logged record.
_LIFTED = ("ts", "event", "task_id")


class WarehouseUnavailable(RuntimeError):
    """psycopg is not installed, or no DSN is configured.

    Raised rather than warned-and-skipped: an ingest that silently does nothing
    is indistinguishable from an ingest that found no new records, and the whole
    point of the log is that absence is never silent.
    """


@dataclass
class IngestReport:
    """What one ingest actually did.

    `skipped` counts records already present — the normal result of re-running
    over logs that were ingested before, and the reason this is safe on a cron.
    `malformed` counts lines that would not parse; they are reported by file and
    line rather than dropped quietly.
    """

    files: int = 0
    inserted: int = 0
    skipped: int = 0
    malformed: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        parts = [
            f"{self.files} file(s)",
            f"{self.inserted} inserted",
            f"{self.skipped} already present",
        ]
        if self.malformed:
            parts.append(f"{len(self.malformed)} malformed")
        return ", ".join(parts)


def dsn(explicit: str | None = None) -> str:
    value = explicit or os.environ.get(DSN_ENV, "")
    if not value:
        raise WarehouseUnavailable(
            f"no connection string: pass --dsn or set {DSN_ENV}. "
            f"On the provisioned host: set -a; . /root/.mastery/postgres.env; set +a"
        )
    return value


def _connect(url: str):
    try:
        import psycopg  # noqa: PLC0415 — optional dependency, imported on use
    except ImportError as exc:  # pragma: no cover — depends on the environment
        raise WarehouseUnavailable(
            "psycopg is not installed. `pip install 'psycopg[binary]'` on the host "
            "that runs ingest. It is intentionally not in requirements.txt: the "
            "orchestrator does not need a database to run."
        ) from exc
    return psycopg.connect(url)


def rows_from_log(path: Path) -> tuple[list[tuple], list[str]]:
    """Parse one JSONL run log into insertable rows.

    Returns the rows and a list of complaints about lines that would not parse.
    A malformed line is skipped and named — never guessed at, and never allowed
    to abort the rest of the file, because one bad line should not cost the
    other 200 records of a run that already happened.

    `seq` is the line number, and with `run_id` it is the primary key. That is
    what makes re-ingest a no-op rather than a duplicate.
    """
    rows: list[tuple] = []
    malformed: list[str] = []
    run_id = path.stem

    for seq, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            malformed.append(f"{path.name}:{seq + 1}: {exc.msg}")
            continue
        if not isinstance(record, dict) or "event" not in record:
            malformed.append(f"{path.name}:{seq + 1}: not an event record")
            continue

        rows.append(
            (
                run_id,
                seq,
                record.get("ts"),
                record["event"],
                record.get("task_id"),
                json.dumps(record, ensure_ascii=False, default=str),
            )
        )
    return rows, malformed


_INSERT = """
    INSERT INTO events (run_id, seq, ts, event, task_id, payload)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (run_id, seq) DO NOTHING
"""


def ingest(log_dir: Path, *, url: str | None = None, run_id: str | None = None) -> IngestReport:
    """Copy every run log in `log_dir` into the database.

    Idempotent. Runs already present are re-read and re-offered; the database
    rejects the duplicates on the primary key, so the second run of this over
    the same directory inserts nothing and reports it as `skipped`.

    One transaction per file, so a failure partway through a directory leaves
    whole runs committed rather than half a run.
    """
    connection_url = dsn(url)
    logs = sorted(log_dir.glob("*.jsonl"))
    if run_id is not None:
        logs = [p for p in logs if p.stem == run_id]

    report = IngestReport()
    if not logs:
        return report

    with _connect(connection_url) as conn:
        for path in logs:
            rows, malformed = rows_from_log(path)
            report.malformed.extend(malformed)
            report.files += 1
            if not rows:
                continue
            with conn.cursor() as cur:
                before = 0
                cur.execute(
                    "SELECT count(*) FROM events WHERE run_id = %s", (path.stem,)
                )
                fetched = cur.fetchone()
                before = fetched[0] if fetched else 0

                cur.executemany(_INSERT, rows)

                cur.execute(
                    "SELECT count(*) FROM events WHERE run_id = %s", (path.stem,)
                )
                fetched = cur.fetchone()
                after = fetched[0] if fetched else 0

            inserted = after - before
            report.inserted += inserted
            report.skipped += len(rows) - inserted
            conn.commit()

    return report
