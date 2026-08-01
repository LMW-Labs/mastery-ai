"""Parsing run logs into database rows.

The database half of ingest is exercised against a real Postgres in
scripts/check_warehouse.py, which needs a server. These tests cover the half
that must be right regardless of whether a server exists: that a log becomes
the rows it should, that a bad line is named rather than swallowed, and that
the key which makes re-ingest a no-op is actually stable.

Nothing here imports psycopg. That is itself part of the contract — the
orchestrator runs without a database, so its test suite must too.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mastery import warehouse
from mastery.runlog import RunLog


class RowsFromLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_every_record_becomes_one_row(self):
        log = RunLog.open(self.dir, "run0001")
        log.run_start("cli run 20260730-ops-001.json")
        log.delegation_start(task_id="20260730-ops-001", agent="ops", context_bytes=2048, attempt=1)
        log.delegation_end(
            task_id="20260730-ops-001",
            agent="ops",
            status="complete",
            duration_s=12.5,
            summary="Postgres provisioned.",
        )
        log.run_end(outcome="accepted", detail="done")

        rows, malformed = warehouse.rows_from_log(log.path)

        self.assertEqual(malformed, [])
        self.assertEqual(len(rows), 4)
        self.assertEqual([r[3] for r in rows], [
            "run_start", "delegation_start", "delegation_end", "run_end",
        ])

    def test_run_id_comes_from_the_filename_and_seq_is_the_line_number(self):
        """(run_id, seq) is the primary key that makes re-ingest a no-op."""
        log = RunLog.open(self.dir, "abc123")
        log.run_start("x")
        log.run_end(outcome="accepted", detail="")

        rows, _ = warehouse.rows_from_log(log.path)

        self.assertEqual([(r[0], r[1]) for r in rows], [("abc123", 0), ("abc123", 1)])

    def test_key_is_stable_across_repeated_parses(self):
        """Re-parsing the same file must yield identical keys, or ON CONFLICT
        would not suppress the duplicate and every ingest would grow the table."""
        log = RunLog.open(self.dir, "stable")
        for i in range(5):
            log.gate_hit(gate="money", detail=f"hit {i}")

        first, _ = warehouse.rows_from_log(log.path)
        second, _ = warehouse.rows_from_log(log.path)

        self.assertEqual([(r[0], r[1]) for r in first], [(r[0], r[1]) for r in second])

    def test_task_id_is_lifted_but_also_kept_in_the_payload(self):
        """The lifted column is for indexing; the payload stays a faithful copy."""
        log = RunLog.open(self.dir, "run0002")
        log.delegation_end(
            task_id="20260730-ff-014", agent="qa", status="failed", duration_s=1.0
        )

        (rows, _) = warehouse.rows_from_log(log.path)
        (row,) = rows

        self.assertEqual(row[4], "20260730-ff-014")
        self.assertEqual(json.loads(row[5])["task_id"], "20260730-ff-014")

    def test_run_level_events_have_no_task_id(self):
        log = RunLog.open(self.dir, "run0003")
        log.run_start("a request")

        (rows, _) = warehouse.rows_from_log(log.path)
        (row,) = rows

        self.assertIsNone(row[4])

    def test_payload_preserves_telemetry_the_views_read(self):
        """v_delegations casts these out of jsonb; if they are dropped here the
        cost columns silently become NULL rather than failing."""
        log = RunLog.open(self.dir, "run0004")
        log.delegation_end(
            task_id="20260730-rd-002",
            agent="researcher",
            status="complete",
            duration_s=359.0,
            num_turns=30,
            cost_usd=1.43,
            permission_denials=["WebSearch"],
            role_tier="judgment",
        )

        (rows, _) = warehouse.rows_from_log(log.path)
        (row,) = rows
        payload = json.loads(row[5])

        self.assertEqual(payload["cost_usd"], 1.43)
        self.assertEqual(payload["num_turns"], 30)
        self.assertEqual(payload["role_tier"], "judgment")
        self.assertEqual(payload["permission_denials"], ["WebSearch"])

    def test_a_malformed_line_is_named_and_the_rest_survive(self):
        """One truncated line — a run killed mid-write — must not cost the
        other records of a run that already happened."""
        path = self.dir / "torn.jsonl"
        path.write_text(
            '{"event": "run_start", "request": "a"}\n'
            '{"event": "delegation_start", "task_i\n'
            '{"event": "run_end", "outcome": "accepted"}\n',
            encoding="utf-8",
        )

        rows, malformed = warehouse.rows_from_log(path)

        self.assertEqual(len(rows), 2)
        self.assertEqual([r[3] for r in rows], ["run_start", "run_end"])
        self.assertEqual(len(malformed), 1)
        self.assertIn("torn.jsonl:2", malformed[0])

    def test_valid_json_that_is_not_an_event_is_rejected(self):
        path = self.dir / "odd.jsonl"
        path.write_text('{"event": "run_start"}\n[1, 2, 3]\n{"no": "event key"}\n', encoding="utf-8")

        rows, malformed = warehouse.rows_from_log(path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(len(malformed), 2)

    def test_blank_lines_are_skipped_without_complaint(self):
        path = self.dir / "spaced.jsonl"
        path.write_text('{"event": "run_start"}\n\n\n{"event": "run_end"}\n', encoding="utf-8")

        rows, malformed = warehouse.rows_from_log(path)

        self.assertEqual(len(rows), 2)
        self.assertEqual(malformed, [])

    def test_seq_still_counts_skipped_lines(self):
        """seq is the line number, not the row index. If blanks shifted it, a
        log edited between ingests would re-insert every record after the edit."""
        path = self.dir / "gap.jsonl"
        path.write_text('{"event": "run_start"}\n\n{"event": "run_end"}\n', encoding="utf-8")

        rows, _ = warehouse.rows_from_log(path)

        self.assertEqual([r[1] for r in rows], [0, 2])


class DsnTests(unittest.TestCase):
    def test_explicit_dsn_wins(self):
        self.assertEqual(warehouse.dsn("postgresql://x/y"), "postgresql://x/y")

    def test_missing_dsn_raises_rather_than_returning_empty(self):
        """A silent no-op ingest is indistinguishable from an ingest that found
        nothing new, which is exactly the ambiguity this project forbids."""
        import os

        saved = os.environ.pop(warehouse.DSN_ENV, None)
        self.addCleanup(lambda: os.environ.__setitem__(warehouse.DSN_ENV, saved) if saved else None)

        with self.assertRaises(warehouse.WarehouseUnavailable):
            warehouse.dsn()

    def test_env_var_is_used_when_no_explicit_dsn(self):
        import os

        saved = os.environ.get(warehouse.DSN_ENV)
        os.environ[warehouse.DSN_ENV] = "postgresql://from-env/db"
        self.addCleanup(
            lambda: os.environ.__setitem__(warehouse.DSN_ENV, saved)
            if saved is not None
            else os.environ.pop(warehouse.DSN_ENV, None)
        )

        self.assertEqual(warehouse.dsn(), "postgresql://from-env/db")


class IngestReportTests(unittest.TestCase):
    def test_report_reads_cleanly_with_nothing_to_do(self):
        self.assertEqual(str(warehouse.IngestReport()), "0 file(s), 0 inserted, 0 already present")

    def test_malformed_count_is_surfaced_not_hidden(self):
        report = warehouse.IngestReport(files=1, inserted=3, skipped=0, malformed=["a.jsonl:2: x"])
        self.assertIn("1 malformed", str(report))

    def test_ingest_of_an_empty_dir_needs_no_database(self):
        """No logs means no connection attempt — so a cron on a box with the DB
        down does not fail spuriously when there was nothing to send anyway."""
        with tempfile.TemporaryDirectory() as tmp:
            report = warehouse.ingest(Path(tmp), url="postgresql://unreachable:1/nope")
            self.assertEqual(report.files, 0)
            self.assertEqual(report.inserted, 0)


if __name__ == "__main__":
    unittest.main()
