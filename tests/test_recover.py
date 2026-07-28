"""Recovering a completed delegation from the run log.

The delegation is the expensive half. When a manager-side fault loses the
verdict — a one-turn call that blew up, a crash after the return landed — the
work is already on disk, and re-running the task pays twice for one result.
These tests pin what may be recovered, and what must not be invented.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mastery.runlog import RunLog, recover_result
from mastery.schema import Status


def log_a_delegation(log: RunLog, *, task_id: str, status: str = "complete", **overrides):
    fields = dict(
        task_id=task_id,
        agent="researcher",
        status=status,
        duration_s=359.0,
        num_turns=30,
        cost_usd=1.43,
        summary="Closed Q5 — promoter liability.",
        deliverables=["Addendum: 26 U.S.C. § 6700 and § 7402"],
        risks=["justice.gov returns HTTP 403; dates are search-identified."],
        next_step="Route to legal-review.",
    )
    fields.update(overrides)
    log.delegation_end(**fields)


class RecoverTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_recovers_a_completed_delegation(self):
        log = RunLog.open(self.dir, "aaaa1111")
        log.run_start("cli run 20260728-rd-002.json")
        log_a_delegation(log, task_id="20260728-rd-002")

        result, run_id = recover_result(self.dir, "20260728-rd-002")
        self.assertEqual(run_id, "aaaa1111")
        self.assertIs(result.status, Status.COMPLETE)
        self.assertEqual(result.task_id, "20260728-rd-002")
        self.assertIn("6700", result.deliverables[0])
        self.assertIn("403", result.risks[0])

    def test_returns_none_when_the_delegation_never_completed(self):
        # A run that died mid-delegation has nothing to recover. Synthesizing a
        # result here would be the fabricated success the project forbids.
        log = RunLog.open(self.dir, "bbbb2222")
        log.run_start("cli run 20260728-rd-002.json")
        log.delegation_start(
            task_id="20260728-rd-002", agent="researcher", context_bytes=12361, attempt=1
        )
        log.failure(kind="TaskTimeout", detail="exceeded 900s", task_id="20260728-rd-002")

        self.assertIsNone(recover_result(self.dir, "20260728-rd-002"))

    def test_returns_none_for_an_unknown_task(self):
        log = RunLog.open(self.dir, "cccc3333")
        log_a_delegation(log, task_id="20260728-rd-002")
        self.assertIsNone(recover_result(self.dir, "20260728-ff-001"))

    def test_takes_the_last_attempt_not_the_first(self):
        # A retried task has two delegation_end records. The verdict belongs to
        # the attempt that actually stands.
        log = RunLog.open(self.dir, "dddd4444")
        log_a_delegation(log, task_id="20260728-rd-002", summary="first attempt")
        log_a_delegation(log, task_id="20260728-rd-002", summary="second attempt")

        result, _ = recover_result(self.dir, "20260728-rd-002")
        self.assertEqual(result.summary, "second attempt")

    def test_searches_newest_run_first_across_runs(self):
        import os
        import time

        old = RunLog.open(self.dir, "old00000")
        log_a_delegation(old, task_id="20260728-rd-002", summary="older run")
        # mtime resolution is coarse enough to need an explicit ordering.
        os.utime(old.path, (time.time() - 60, time.time() - 60))

        new = RunLog.open(self.dir, "new00000")
        log_a_delegation(new, task_id="20260728-rd-002", summary="newer run")

        result, run_id = recover_result(self.dir, "20260728-rd-002")
        self.assertEqual(run_id, "new00000")
        self.assertEqual(result.summary, "newer run")

    def test_run_id_pins_a_specific_run(self):
        import os
        import time

        old = RunLog.open(self.dir, "old00000")
        log_a_delegation(old, task_id="20260728-rd-002", summary="older run")
        os.utime(old.path, (time.time() - 60, time.time() - 60))

        new = RunLog.open(self.dir, "new00000")
        log_a_delegation(new, task_id="20260728-rd-002", summary="newer run")

        result, run_id = recover_result(self.dir, "20260728-rd-002", run_id="old00000")
        self.assertEqual(run_id, "old00000")
        self.assertEqual(result.summary, "older run")

    def test_a_blocked_return_is_recovered_as_blocked(self):
        # Recovery must not launder a status. A gate that returned closed is
        # still closed when it is verified later.
        log = RunLog.open(self.dir, "eeee5555")
        log_a_delegation(log, task_id="20260728-rd-006", status="blocked")

        result, _ = recover_result(self.dir, "20260728-rd-006")
        self.assertIs(result.status, Status.BLOCKED)


if __name__ == "__main__":
    unittest.main()
