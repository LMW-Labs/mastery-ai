"""The CLI has to be able to print what the agents actually produce.

Regression test for a run that succeeded, cost real quota, was written to the
run log — and then died in `print(summarize(...))` because the Windows console
codepage could not encode an arrow. Nothing about the delegation was wrong; the
report was lost on the way to the terminal.
"""

from __future__ import annotations

import io
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
