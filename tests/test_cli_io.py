"""The CLI has to be able to print what the agents actually produce.

Regression test for a run that succeeded, cost real quota, was written to the
run log — and then died in `print(summarize(...))` because the Windows console
codepage could not encode an arrow. Nothing about the delegation was wrong; the
report was lost on the way to the terminal.
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path

from mastery.cli import _force_utf8_stdio
from mastery.orchestrator import DelegationOutcome, Outcome, summarize
from mastery.schema import Status, TaskResult

# The characters agent output actually contains: arrow, em-dash, section sign,
# middle dot, curly quotes.
AGENT_GLYPHS = "content → fact-checker — 26 U.S.C. § 6700 · “redemption”"


class LegacyCodepageStdout(io.TextIOWrapper):
    """Stands in for a cp1252 console: strict, and cannot encode the glyphs."""

    def __init__(self):
        super().__init__(io.BytesIO(), encoding="cp1252", errors="strict")


class ForceUtf8Tests(unittest.TestCase):
    def setUp(self):
        self._stdout, self._stderr = sys.stdout, sys.stderr
        self.addCleanup(self._restore)

    def _restore(self):
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def test_a_legacy_codepage_stdout_would_fail_without_the_fix(self):
        # Establishes that the test's premise is real, not hypothetical: this
        # is the exact exception the CLI died with.
        sys.stdout = LegacyCodepageStdout()
        with self.assertRaises(UnicodeEncodeError):
            print(AGENT_GLYPHS)
            sys.stdout.flush()

    def test_force_utf8_makes_agent_output_printable(self):
        sys.stdout = LegacyCodepageStdout()
        sys.stderr = LegacyCodepageStdout()
        _force_utf8_stdio()
        print(AGENT_GLYPHS)  # must not raise
        self.assertEqual(sys.stdout.encoding, "utf-8")
        self.assertEqual(sys.stdout.errors, "replace")

    def test_it_is_safe_on_a_stream_that_cannot_reconfigure(self):
        # StringIO has no reconfigure(); pytest and some CI shells substitute
        # streams like it. The CLI must not crash on startup because of that.
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        _force_utf8_stdio()  # must not raise
        print(AGENT_GLYPHS)


class SummarizeTests(unittest.TestCase):
    def test_a_failed_run_still_reports_its_deliverables(self):
        # The substance of a `revise`-exhausted run is not worthless. If
        # summarize dropped it, the only surviving copy would be the run log.
        result = TaskResult(
            task_id="20260728-rd-002",
            status=Status.COMPLETE,
            summary=f"Answered Q5. {AGENT_GLYPHS}",
            deliverables=("Addendum: promoter liability — § 6700, § 7408",),
            risks=("justice.gov returned HTTP 403; dates are search-identified.",),
            next_step="Route to legal-review.",
        )
        outcome = DelegationOutcome(
            Outcome.FAILED,
            "20260728-rd-002",
            "researcher",
            result=result,
            detail="still not accepted after 2 attempts: exceeded the word cap",
            attempts=2,
        )
        text = summarize(outcome)
        self.assertIn("6700", text)
        self.assertIn("403", text)
        self.assertIn("Failed after 2 attempt(s)", text)


class CheckCwdTests(unittest.TestCase):
    """`mastery check` has to catch a `cwd` that points nowhere.

    Regression guard for the failure this check exists to make impossible: a
    config naming a repo that is not on this machine passes every other check,
    and the delegation it authorises spends full price to report an empty repo.
    """

    def _check(self, cwd) -> tuple[int, str]:
        from dataclasses import replace

        from mastery.cli import _check
        from mastery.config import Config

        buffer = io.StringIO()
        stdout, sys.stdout = sys.stdout, buffer
        try:
            code = _check(replace(Config(), cwd=cwd))
        finally:
            sys.stdout = stdout
        return code, buffer.getvalue()

    def test_a_cwd_that_does_not_exist_fails_the_check(self):
        code, output = self._check(Path("/nonexistent/StudioProjects/faithfeed"))
        self.assertEqual(code, 1)
        self.assertIn("FAIL", output)
        self.assertIn("faithfeed", output)

    def test_a_cwd_that_is_a_file_fails_the_check(self):
        with tempfile.NamedTemporaryFile(suffix=".json") as handle:
            code, output = self._check(Path(handle.name))
        self.assertEqual(code, 1)
        self.assertIn("not a directory", output)

    def test_a_real_directory_passes_and_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output = self._check(Path(directory))
            self.assertEqual(code, 0)
            self.assertIn("OK", output)
            # Printed, not just accepted — the operator has to be able to see
            # which repo a run will read before paying for it.
            self.assertIn(directory, output)


if __name__ == "__main__":
    unittest.main()
