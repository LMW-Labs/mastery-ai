"""STOP 7 pins.

Four properties, each one a way the eval loop could be quietly defeated:

  1. an accepted output goes unscored, and nothing says so
  2. a score is laundered back into the graded agent's own input
  3. an agent self-reports its own score
  4. incomparable scores get averaged into one meaningless trend

Every test here fails if the corresponding guard is removed.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mastery import calibration, evals, quality
from mastery.config import Config
from mastery.errors import RubricMissing, SchemaViolation
from mastery.evals import IncomparableScores, ScoreKey, ScoreRecord
from mastery.orchestrator import Orchestrator, Outcome
from mastery.quality import QualityScore
from tests.test_orchestrator import (
    OrchestratorTestCase,
    ScriptedRunner,
    a_brief,
    result_json,
    score_json,
    verdict_json,
)


# --------------------------------------------------------------------------
# PIN 1 — an ACCEPTED outcome is never silently unscored
# --------------------------------------------------------------------------


class TestPin1AcceptedImpliesScored(OrchestratorTestCase):
    async def test_accepted_outcome_carries_a_score(self):
        """The bypass pin. Remove the `_score` call in `execute` and this fails."""
        orch, _ = self.orch([result_json(), verdict_json()])
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.ACCEPTED)
        self.assertIsNotNone(
            outcome.quality, "an accepted output was taken as final unmeasured"
        )
        self.assertIsInstance(outcome.quality, QualityScore)

    async def test_accepted_outcome_emits_a_quality_score_event(self):
        orch, _ = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        events = [e for e in orch.log.read() if e["event"] == "quality_score"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["task_id"], "20260727-ff-014")

    async def test_accepted_is_never_both_unscored_and_unexplained(self):
        """The actual invariant: measured, or explicitly recorded as unmeasured
        with a reason. Never neither — silence is the failure mode."""
        orch, _ = self.orch([result_json(), verdict_json()])
        outcome = await orch.execute(a_brief())

        scored = [e for e in orch.log.read() if e["event"] == "quality_score"]
        skipped = [e for e in orch.log.read() if e["event"] == "quality_skipped"]
        self.assertTrue(
            (outcome.quality is not None and scored) or skipped,
            "accepted output is neither scored nor recorded as skipped",
        )

    async def test_a_grading_failure_is_logged_not_swallowed(self):
        """A grading fault must not destroy accepted work, but the hole in the
        trend has to be visible."""
        runner = ScriptedRunner(
            [result_json(), verdict_json(), "this is not json"], auto_score=False
        )
        orch = Orchestrator(self.config, runner, run_id="test")
        outcome = await orch.execute(a_brief())

        # The work survived.
        self.assertIs(outcome.outcome, Outcome.ACCEPTED)
        self.assertIsNotNone(outcome.result)
        # And the missing score is named, not silent.
        self.assertIsNone(outcome.quality)
        skipped = [e for e in orch.log.read() if e["event"] == "quality_skipped"]
        self.assertEqual(len(skipped), 1)
        self.assertIn("grading failed", skipped[0]["reason"])

    async def test_failed_outcome_is_not_scored_but_says_so_by_absence(self):
        """Only accepted work is graded — scoring discarded attempts would bias
        the trend with outputs nobody kept."""
        orch, _ = self.orch([result_json(status="failed"), result_json(status="failed")])
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.FAILED)
        self.assertIsNone(outcome.quality)
        self.assertEqual([e for e in orch.log.read() if e["event"] == "quality_score"], [])


class TestPin1FailClosedOnMissingRubric(OrchestratorTestCase):
    async def test_unrubriced_agent_halts_before_any_spend(self):
        """Fail closed, and do it for free.

        This asserts the *behaviour*, with the rubric table patched to be empty,
        rather than reaching for whichever roster agent happens to lack a rubric
        today. It used to name `strategy` — and on 2026-07-31, when the last
        nine rubrics were written, `strategy` acquired one and this test silently
        stopped testing anything. It failed loudly only because the scripted
        runner refused the call it should never have received.

        That is the sharp edge of completing the rubric set: the guard's own
        test lost its subject. A pin that depends on some other part of the
        system staying incomplete is not a pin.
        """
        from unittest.mock import patch

        runner = ScriptedRunner([])  # must never be called
        orch = Orchestrator(self.config, runner, run_id="test")

        with patch.object(quality, "_rubrics", return_value={}):
            with self.assertRaises(RubricMissing):
                await orch.execute(a_brief(agent="strategy"))

        self.assertEqual(
            runner.prompts, [], "paid for a delegation it could never have scored"
        )

class TestGateClosuresAreScored(OrchestratorTestCase):
    """A gate's `blocked` is its deliverable, and it gets measured.

    Added 2026-07-31 after a harder fact-checker baseline set produced three runs
    and zero scores. Scoring only accepted outcomes made the four gates
    measurable solely on inputs they did not need to stop — every discriminating
    case was censored out of the sample by construction, so the resulting
    baseline sat at 3.0/3 with zero variance and could not have detected a
    regression it was built to detect.
    """

    async def test_a_gate_closure_is_scored(self):
        runner = ScriptedRunner([result_json(task_id="20260731-rd-001", status="blocked")])
        orch = Orchestrator(self.config, runner, run_id="test")

        outcome = await orch.execute(
            a_brief(task_id="20260731-rd-001", agent="fact-checker")
        )

        self.assertIs(outcome.outcome, Outcome.HALTED)
        self.assertIsNotNone(outcome.quality, "a gate closed and nobody measured it")
        scored = [e for e in orch.log.read() if e["event"] == "quality_score"]
        self.assertEqual(len(scored), 1)

    async def test_fired_gate_has_no_return_path_to_control_flow(self):
        """No verdict on a closure, and this is deliberate.

        The verdict returns accept/revise/reject. A `revise` on a closure would be
        a model with the power to send a gate back for another attempt — an
        attempt that could come back with a different status. That is a reopening
        path, and CLAUDE.md forbids it: a `hold` or a `no-go` halts the pipeline.
        Nothing goes back through.
        """
        runner = ScriptedRunner([result_json(task_id="20260731-rd-001", status="blocked")])
        orch = Orchestrator(self.config, runner, run_id="test")

        await orch.execute(a_brief(task_id="20260731-rd-001", agent="fact-checker"))

        self.assertEqual(
            [e for e in orch.log.read() if e["event"] == "verdict"],
            [],
            "a gate closure was verified, which creates a path to reopen it",
        )

    async def test_a_gate_closure_is_never_retried(self):
        """One delegation. A closure is final regardless of what it scores."""
        runner = ScriptedRunner([result_json(task_id="20260731-rd-001", status="blocked")])
        orch = Orchestrator(self.config, runner, run_id="test")

        outcome = await orch.execute(
            a_brief(task_id="20260731-rd-001", agent="fact-checker")
        )

        self.assertEqual(outcome.attempts, 1)
        starts = [e for e in orch.log.read() if e["event"] == "delegation_start"]
        self.assertEqual(len(starts), 1, "a gate was sent back through")

    async def test_an_ordinary_agent_blocked_is_not_scored(self):
        """`blocked` from a non-gate means it hit a gate or lacked a prerequisite.
        That is work not being used, and scoring it would bias the trend with
        attempts nobody kept — the original rule, still right for this case."""
        runner = ScriptedRunner([result_json(status="blocked")])
        orch = Orchestrator(self.config, runner, run_id="test")

        outcome = await orch.execute(a_brief(agent="mobile-dev"))

        self.assertIs(outcome.outcome, Outcome.HALTED)
        self.assertIsNone(outcome.quality)
        self.assertEqual([e for e in orch.log.read() if e["event"] == "quality_score"], [])


class TestRubricCoverage(OrchestratorTestCase):
    def test_every_delegatable_agent_is_rubriced(self):
        """As of 2026-07-31, every delegatable agent has a rubric, so none is
        blocked from running by `RubricMissing`.

        Deliberately asserted rather than left implicit. This test previously
        hardcoded the *unrubriced* set, so that adding a rubric had to break it —
        adding one is a decision about what "good" means for a role and should
        not slip in as a side effect. Now that the set is complete, the same
        intent is served by the inverse: **removing** a rubric, or adding a new
        delegatable agent without one, breaks this.

        A new agent failing here is not a reason to weaken the assertion. It
        means that agent cannot run yet, which is the fail-closed behaviour Pin 1
        exists to enforce.

        Review status is tracked in BUILD_LEDGER, not here: `fact-checker`,
        `risk-review`, and `legal-review` are operator-reviewed. The remaining
        nine were derived from each agent's own "Rules and guardrails" and are
        not yet reviewed — they will produce scores regardless, which is exactly
        why the distinction is recorded.
        """
        from mastery.roster import DELEGATABLE

        unrubriced = sorted(a.name for a in DELEGATABLE if not quality.has_rubric(a.name))
        self.assertEqual(unrubriced, [], f"agents that cannot run for want of a rubric: {unrubriced}")
        self.assertEqual(len(DELEGATABLE), 17)


# --------------------------------------------------------------------------
# PIN 2 — no grade laundering
# --------------------------------------------------------------------------


class TestPin2NoLaundering(OrchestratorTestCase):
    def test_corrected_does_not_accept_a_score(self):
        """`_corrected` builds the retry brief. If a score could reach it, the
        agent would be optimising against the grader."""
        import inspect

        from mastery.orchestrator import _corrected

        params = set(inspect.signature(_corrected).parameters)
        self.assertEqual(params, {"brief", "note"})

    async def test_a_score_never_reaches_a_retry_brief(self):
        """Revise, then accept. The second delegation prompt must carry the
        verdict's revision note and nothing from any grader."""
        orch, runner = self.orch(
            [
                result_json(),
                verdict_json(verdict="revise", revision_note="name the crash path"),
                result_json(),
                verdict_json(),
            ]
        )
        outcome = await orch.execute(a_brief())
        self.assertIs(outcome.outcome, Outcome.ACCEPTED)

        retry_prompt = runner.prompts[2]
        self.assertIn("name the crash path", retry_prompt)
        for leak in ("dimension", "rubric", "overall", "justification", "score"):
            self.assertNotIn(
                leak, retry_prompt.lower(), f"grade material {leak!r} leaked into a retry"
            )

    async def test_the_graded_agent_never_sees_its_grade(self):
        """No delegation prompt in a run contains grading material."""
        orch, runner = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        delegation_prompts = [
            p for p in runner.prompts if not ScriptedRunner._is_grading(p)
        ]
        for p in delegation_prompts:
            self.assertNotIn("rubric", p.lower())

    async def test_grading_happens_after_the_verdict_not_before(self):
        """Ordering matters: a grade produced before acceptance could influence
        it. The verdict must already be in before the grader runs."""
        orch, runner = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        kinds = [
            "grading" if ScriptedRunner._is_grading(p) else "other"
            for p in runner.prompts
        ]
        self.assertEqual(kinds, ["other", "other", "grading"])

    async def test_score_does_not_change_the_outcome(self):
        """Observational only. A floor score and a ceiling score both accept."""
        for score in (0, 3):
            runner = ScriptedRunner(
                [
                    result_json(),
                    verdict_json(),
                    score_json(agent="mobile-dev", score=score),
                ],
                auto_score=False,
            )
            orch = Orchestrator(self.config, runner, run_id="test")
            outcome = await orch.execute(a_brief())
            self.assertIs(
                outcome.outcome,
                Outcome.ACCEPTED,
                f"score {score} changed control flow; only `status` may",
            )
            self.assertEqual(outcome.quality.overall, float(score))


# --------------------------------------------------------------------------
# PIN 3 — no self-report
# --------------------------------------------------------------------------


class TestPin3NoSelfReport(unittest.TestCase):
    def test_no_quality_field_in_the_task_output_schema(self):
        """Same shape as the STOP 1 telemetry pin. An agent cannot grade itself
        because the contract has no field for it, and additionalProperties:false
        rejects any it invents."""
        from mastery.schema import schema

        props = set(schema()["properties"])
        forbidden = {
            "quality",
            "score",
            "overall",
            "rubric_version",
            "dimension_scores",
            "normalised",
        }
        self.assertEqual(props & forbidden, set())
        self.assertFalse(schema()["additionalProperties"])

    def test_the_score_schema_is_closed_and_has_no_overall(self):
        """Code computes the aggregate. A model-supplied total could disagree
        with its own parts and nothing would catch it."""
        s = quality.score_schema()
        self.assertFalse(s["additionalProperties"])
        self.assertNotIn("overall", s["properties"])
        self.assertNotIn("normalised", s["properties"])

    def test_grader_gets_no_tools(self):
        """It grades what is in the prompt. It looks nothing up."""
        import inspect

        from mastery import delegate

        src = inspect.getsource(delegate.run_grader)
        self.assertIn("run_manager", src)
        self.assertIn("tools=()", inspect.getsource(delegate.run_manager))

    def test_grader_prompt_excludes_the_context_payload(self):
        """Judging output against a fixed reference, not re-doing the task."""
        brief = a_brief()
        from mastery.schema import Status, TaskResult

        result = TaskResult(
            task_id=brief.task_id,
            status=Status.COMPLETE,
            summary="did it",
            deliverables=("FeedViewModel.kt",),
            risks=(),
            next_step="hand to qa",
        )
        prompt = quality.build_prompt(brief, result)
        self.assertNotIn("class FeedViewModel { }", prompt)
        self.assertIn("scope_discipline", prompt)

    def test_dimension_mismatch_is_a_schema_violation(self):
        """A grader that invents or drops a dimension has not produced a
        comparable number."""
        bad = json.dumps(
            {
                "task_id": "20260727-ff-014",
                "agent": "mobile-dev",
                "rubric_version": "1",
                "dimension_scores": [
                    {"dimension": "made_up", "score": 3, "justification": "x"}
                ],
            }
        )
        with self.assertRaises(SchemaViolation):
            quality.parse(bad, expected_task_id="20260727-ff-014", expected_agent="mobile-dev")

    def test_wrong_rubric_version_is_a_schema_violation(self):
        bad = json.dumps(
            {
                "task_id": "20260727-ff-014",
                "agent": "mobile-dev",
                "rubric_version": "99",
                "dimension_scores": [
                    {"dimension": d["dimension"], "score": 2, "justification": "x"}
                    for d in quality.rubric_for("mobile-dev")["dimensions"]
                ],
            }
        )
        with self.assertRaises(SchemaViolation):
            quality.parse(bad, expected_task_id="20260727-ff-014", expected_agent="mobile-dev")

    def test_out_of_range_score_is_rejected(self):
        bad = json.dumps(
            {
                "task_id": "20260727-ff-014",
                "agent": "mobile-dev",
                "rubric_version": "1",
                "dimension_scores": [
                    {"dimension": d["dimension"], "score": 7, "justification": "x"}
                    for d in quality.rubric_for("mobile-dev")["dimensions"]
                ],
            }
        )
        with self.assertRaises(SchemaViolation):
            quality.parse(bad, expected_task_id="20260727-ff-014", expected_agent="mobile-dev")

    def test_aggregate_is_computed_from_the_parts(self):
        raw = score_json(agent="qa", score=2)
        s = quality.parse(raw, expected_task_id="20260727-ff-014", expected_agent="qa")
        self.assertEqual(s.overall, 2.0)
        self.assertAlmostEqual(s.normalised, 2 / 3, places=3)


# --------------------------------------------------------------------------
# PIN 4 — incomparable scores are refused, never averaged
# --------------------------------------------------------------------------


def _rec(agent="researcher", version="1", model="claude-sonnet-4-5", overall=2.0, tid="20260729-rd-001"):
    return ScoreRecord(
        key=ScoreKey(agent=agent, rubric_version=version, model=model),
        task_id=tid,
        run_id="r",
        ts="2026-07-29T00:00:00",
        overall=overall,
        normalised=round(overall / 3, 4),
        dimensions={"source_primacy": int(overall)},
        cost_usd=0.01,
    )


def _calibrated(
    tmp: str,
    agent="researcher",
    version="1",
    observed=(0.2, 1.0, 2.0, 3.0),
    fingerprint=None,
) -> Path:
    """A calibration file saying this rubric's ladder passed.

    Baselines now require one. Tests that are about *comparability* still need to
    reach the code past that check, so they supply a fixture rather than pointing
    at the repo's real `evals/calibration.json` — a unit test that depended on
    which rubrics happen to be calibrated today would break whenever one was
    added, and would silently stop testing anything if the real file were deleted.
    """
    path = Path(tmp) / "calibration.json"
    calibration.record(
        calibration.CalibrationResult(
            agent=agent,
            rubric_version=version,
            model="claude-sonnet-4-5",
            ts="2026-08-01T00:00:00+00:00",
            intended=(0, 1, 2, 3),
            observed=tuple(observed),
            prompt_fingerprint=fingerprint or quality.prompt_fingerprint(),
        ),
        path=path,
    )
    return path


class TestPin4NoIncomparableAveraging(unittest.TestCase):
    def test_mixed_rubric_versions_are_refused(self):
        with self.assertRaises(IncomparableScores) as ctx:
            evals.check_comparable([_rec(version="1"), _rec(version="2")])
        self.assertIn("rubric version", str(ctx.exception))

    def test_mixed_models_are_refused(self):
        """The STOP 6 guard: a cheap run compared against a cheap baseline shows
        no regression no matter how much quality was lost."""
        with self.assertRaises(IncomparableScores) as ctx:
            evals.check_comparable(
                [_rec(model="claude-sonnet-4-5"), _rec(model="claude-haiku-4-5")]
            )
        self.assertIn("models", str(ctx.exception))

    def test_comparable_scores_pass(self):
        evals.check_comparable([_rec(overall=2.0), _rec(overall=3.0)])

    def test_grouping_keys_on_the_full_triple(self):
        groups = evals.group(
            [
                _rec(model="claude-sonnet-4-5"),
                _rec(model="claude-haiku-4-5"),
                _rec(agent="content"),
            ]
        )
        self.assertEqual(len(groups), 3)

    def test_set_baseline_refuses_incomparable_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baselines.json"
            with self.assertRaises(IncomparableScores):
                evals.set_baseline(
                    [_rec(model="a"), _rec(model="b")], label="x", path=path
                )
            self.assertFalse(path.exists())

    def test_labels_are_stored_separately_not_averaged(self):
        """A fresh baseline and a retroactive sanity check must not merge. If they
        diverge, that divergence is the finding."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baselines.json"
            cal = _calibrated(tmp)
            evals.set_baseline(
                [_rec(overall=3.0)], label="fresh-strong-model", path=path, calibration_path=cal
            )
            evals.set_baseline(
                [_rec(overall=1.0)], label="retro-sanity-check", path=path, calibration_path=cal
            )

            data = json.loads(path.read_text(encoding="utf-8"))
            key = "researcher|1|claude-sonnet-4-5"
            self.assertEqual(data["baselines"][key]["fresh-strong-model"]["overall_mean"], 3.0)
            self.assertEqual(data["baselines"][key]["retro-sanity-check"]["overall_mean"], 1.0)

    def test_an_uncalibrated_rubric_cannot_carry_a_baseline(self):
        """The obligation, in one test.

        Scores exist, they are perfectly comparable, and the baseline is still
        refused — because nothing on record says this rubric's grader can tell a
        good output from a bad one. A number promoted past that question looks
        like evidence and is not.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baselines.json"
            empty = Path(tmp) / "calibration.json"
            with self.assertRaises(calibration.Uncalibrated) as ctx:
                evals.set_baseline(
                    [_rec(overall=3.0)], label="x", path=path, calibration_path=empty
                )
            self.assertIn("probe_grader.py", str(ctx.exception))
            self.assertFalse(path.exists(), "a refused baseline still wrote a file")

    def test_calibration_does_not_carry_across_a_rubric_edit(self):
        """Version-bound, and this is the trap the whole thing turns on.

        A ladder is written against specific anchor text. Edit the rubric and
        those rungs claim levels that no longer exist, so the old pass attests to
        markings nobody has checked — worse than no calibration, because it reads
        as one.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cal = _calibrated(tmp, version="1")
            verdict, why = calibration.status("researcher", "2", path=cal)
            self.assertIs(verdict, calibration.Verdict.STALE)
            self.assertIn("v1", why)

            with self.assertRaises(calibration.Uncalibrated):
                evals.set_baseline(
                    [_rec(version="2")],
                    label="x",
                    path=Path(tmp) / "b.json",
                    calibration_path=cal,
                )

    def test_a_failed_calibration_is_recorded_and_still_refuses(self):
        """A rubber-stamp result is evidence, and it is kept.

        Discarding it would leave the rubric merely *unmeasured* rather than
        *known bad*, and the next person would have no way to tell those apart.
        Keeping it must not be mistaken for licensing it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cal = _calibrated(tmp, observed=(2.9, 3.0, 3.0, 3.0))  # spread 0.1
            verdict, why = calibration.status("researcher", "1", path=cal)
            self.assertIs(verdict, calibration.Verdict.FAILED)
            self.assertIn("did not discriminate", why)

            key = calibration.result_key("researcher", "1", quality.prompt_fingerprint())
            self.assertIn(key, calibration.load_results(cal)["calibrations"])
            with self.assertRaises(calibration.Uncalibrated):
                evals.set_baseline(
                    [_rec()], label="x", path=Path(tmp) / "b.json", calibration_path=cal
                )

    def test_calibration_does_not_carry_across_a_grader_prompt_change(self):
        """The second axis, and the one that was missing.

        A ladder proves a rubric readable *through a particular prompt*. Change
        what `quality._render` puts in front of the grader and the rubric is
        untouched while the instrument is not — so every calibration on file
        would go on reporting `calibrated` about a grader that no longer exists.
        Version-binding's own trap, through the door version-binding leaves open.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cal = _calibrated(tmp, fingerprint="0ldpr0mpt00")
            verdict, why = calibration.status("researcher", "1", path=cal)
            self.assertIs(verdict, calibration.Verdict.PROMPT_CHANGED)

            with self.assertRaises(calibration.Uncalibrated):
                evals.set_baseline(
                    [_rec()], label="x", path=Path(tmp) / "b.json", calibration_path=cal
                )

    def test_a_changed_prompt_is_not_reported_as_a_changed_rubric(self):
        """Two causes, two repairs. `STALE` means rewrite the ladder against new
        anchors; `PROMPT_CHANGED` means the ladder is still correct and only needs
        re-running. Collapsing them would send the reader to rewrite rungs that
        were never wrong."""
        with tempfile.TemporaryDirectory() as tmp:
            cal = _calibrated(tmp, fingerprint="0ldpr0mpt00")
            _, prompt_why = calibration.status("researcher", "1", path=cal)
            _, rubric_why = calibration.status("researcher", "2", path=cal)

            self.assertIn("the rubric is fine", prompt_why)
            self.assertIn("anchors", rubric_why)
            self.assertNotIn("anchors", prompt_why)

    def test_a_result_that_cannot_name_its_prompt_is_not_recorded(self):
        """Refused at the write, not tolerated and filtered at the read.

        An entry with no fingerprint is not evidence about any prompt. Storing it
        would create a row that has to be special-cased forever by everything that
        reads the file, and special cases are where a default of 'assume current'
        eventually gets written.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.json"
            with self.assertRaises(calibration.Uncalibrated):
                calibration.record(
                    calibration.CalibrationResult(
                        agent="researcher", rubric_version="1", model="m", ts="t",
                        intended=(0, 1, 2, 3), observed=(0.0, 1.0, 2.0, 3.0),
                    ),
                    path=path,
                )
            self.assertFalse(path.exists())

    def test_the_fingerprint_moves_when_the_grader_is_shown_a_new_field(self):
        """The fingerprint has to detect the exact change that is coming next.

        `content`'s ladder fails because two of its dimensions ask whether the
        output honoured instructions the grader is never shown. The fix is to show
        it the brief's constraints — and that fix must invalidate all seventeen
        calibrations rather than pass unnoticed. This is that, in advance.
        """
        before = quality.prompt_fingerprint()
        original = quality._render

        def _render_with_constraints(brief, result, rubric):
            return original(brief, result, rubric) + f"\nconstraints: {brief.constraints}\n"

        try:
            quality._render = _render_with_constraints
            quality.prompt_fingerprint.cache_clear()
            self.assertNotEqual(before, quality.prompt_fingerprint())
        finally:
            quality._render = original
            quality.prompt_fingerprint.cache_clear()

        self.assertEqual(before, quality.prompt_fingerprint())

    def test_the_fingerprint_does_not_move_when_a_rubric_moves(self):
        """The two axes stay separate.

        A fingerprint that shifted whenever any rubric was edited would mark all
        seventeen calibrations dead over a one-word change to one of them, and the
        obvious way to stop the noise would be to stop believing the fingerprint.
        Hence the canonical rubric fixture: the hash answers 'what does the grader
        see', and `rubric_version` answers 'measured against what'.
        """
        before = quality.prompt_fingerprint()
        original = quality._rubrics
        edited = {
            "researcher": {
                "rubric_version": "99",
                "dimensions": [
                    {"dimension": "d", "asks": "different", "anchors": {"0": "x", "3": "y"}}
                ],
            }
        }
        try:
            quality._rubrics = lambda: edited
            quality.prompt_fingerprint.cache_clear()
            self.assertEqual(before, quality.prompt_fingerprint())
        finally:
            quality._rubrics = original
            quality.prompt_fingerprint.cache_clear()

        self.assertEqual(before, quality.prompt_fingerprint())

    def test_every_recorded_calibration_names_the_prompt_it_ran_through(self):
        """The repo's own file, not a fixture.

        The seventeen entries predate the fingerprint and were rekeyed rather than
        re-run — defensible only because `quality.py` provably did not change
        between the runs and the rekey. This pin makes any later entry that lacks
        a fingerprint, or whose key disagrees with its body, a test failure rather
        than a silent claim about a prompt nobody identified.
        """
        for key, entry in calibration.load_results()["calibrations"].items():
            with self.subTest(key=key):
                agent, version, fingerprint = calibration._parts(key)
                self.assertTrue(fingerprint, "recorded calibration names no prompt")
                self.assertEqual(entry.get("prompt_fingerprint"), fingerprint)
                self.assertEqual(entry["agent"], agent)
                self.assertEqual(entry["rubric_version"], version)

    def test_a_non_monotonic_ladder_is_not_a_pass(self):
        """Spread alone is not discrimination. A grader that separates outputs but
        orders them wrongly is responding to something other than the anchors."""
        result = calibration.CalibrationResult(
            agent="researcher", rubric_version="1", model="m", ts="t",
            intended=(0, 1, 2, 3), observed=(3.0, 1.0, 2.0, 0.5),
        )
        self.assertGreaterEqual(result.spread, calibration.MIN_SPREAD)
        self.assertFalse(result.monotonic)
        self.assertFalse(result.discriminates)

    def test_every_ladder_matches_its_rubric_version(self):
        """A ladder in the repo that has drifted off its rubric is caught here,
        not by a probe run that would report a meaningless number."""
        for agent, ladder in calibration._ladders().items():
            with self.subTest(agent=agent):
                self.assertTrue(quality.has_rubric(agent), f"ladder for unrubriced {agent}")
                self.assertEqual(
                    ladder["rubric_version"],
                    quality.rubric_version(agent),
                    f"{agent}'s ladder was written against a rubric version that has "
                    f"since changed; rewrite it against the current anchors",
                )

    def test_every_ladder_covers_every_rubric_level(self):
        """A ladder missing its 0 rung cannot demonstrate spread, and one missing
        its 3 rung cannot show the top of the scale is reachable."""
        for agent, ladder in calibration._ladders().items():
            with self.subTest(agent=agent):
                levels = sorted(r["intended"] for r in ladder["rungs"])
                self.assertEqual(
                    levels,
                    list(range(quality.MAX_DIMENSION_SCORE + 1)),
                    f"{agent}'s ladder does not cover every level once",
                )
                for rung in ladder["rungs"]:
                    self.assertTrue(
                        rung["why"].strip(),
                        f"{agent} rung {rung['label']} does not say which anchors it "
                        f"was built to satisfy, so its intended level is unarguable",
                    )

    def test_coverage_is_counted_by_agent_name_not_agent_object(self):
        """`roster.DELEGATABLE` holds `Agent` objects; the rubric and calibration
        tables are keyed by name. Passing the objects straight through returns
        False for every lookup and reports a confident, wrong 0/17 — a counter
        that fails the same way the grader it counts was suspected of failing.
        """
        from mastery import roster

        names = [a.name for a in roster.DELEGATABLE]
        self.assertTrue(all(isinstance(n, str) for n in names))
        self.assertTrue(
            any(quality.has_rubric(n) for n in names),
            "no delegatable agent resolved to a rubric — coverage counting is broken",
        )
        self.assertFalse(
            any(quality.has_rubric(a) for a in roster.DELEGATABLE),  # type: ignore[arg-type]
            "an Agent object resolved to a rubric; this test no longer guards anything",
        )

    def test_trend_is_ordered_and_comparable(self):
        t = evals.trend([_rec(overall=1.0), _rec(overall=2.0), _rec(overall=3.0)])
        self.assertEqual([v for _, v in t], [1.0, 2.0, 3.0])


class TestEvalRendering(OrchestratorTestCase):
    async def test_scores_are_queryable_from_the_log_dir(self):
        """Trendable means readable back out of the run logs, not just written."""
        orch, _ = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        records = evals.load_scores(self.config.log_dir)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].key.agent, "mobile-dev")
        self.assertEqual(records[0].task_id, "20260727-ff-014")

        out = evals.render(self.config.log_dir)
        self.assertIn("mobile-dev", out)
        self.assertIn("overall=", out)

    def test_render_is_honest_when_there_is_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("no quality scores", evals.render(Path(tmp)))

    async def test_skips_are_surfaced_in_the_render(self):
        runner = ScriptedRunner(
            [result_json(), verdict_json(), "not json"], auto_score=False
        )
        orch = Orchestrator(self.config, runner, run_id="test")
        await orch.execute(a_brief())

        out = evals.render(self.config.log_dir)
        self.assertIn("unscored", out)
        self.assertIn("holes in the trend", out)


class TestGraderTelemetry(OrchestratorTestCase):
    async def test_the_grader_call_is_telemetered_with_its_tier(self):
        """The grader is a model call; its cost must be visible, and its declared
        tier recorded so STOP 6 has labelled history."""
        from dataclasses import replace as dc_replace

        from mastery.delegate import usage_from
        from tests.test_orchestrator import SDK_USAGE

        class TelemetryRunner(ScriptedRunner):
            async def run(self, **kwargs):
                base = await super().run(**kwargs)
                return dc_replace(base, cost_usd=0.004, usage=usage_from(SDK_USAGE))

        runner = TelemetryRunner([result_json(), verdict_json()])
        orch = Orchestrator(self.config, runner, run_id="test")
        await orch.execute(a_brief())

        ev = next(e for e in orch.log.read() if e["event"] == "quality_score")
        self.assertEqual(ev["role_tier"], "mechanical")
        self.assertEqual(ev["model"], "claude-sonnet-4-5")
        self.assertEqual(ev["cost_usd"], 0.004)
        self.assertEqual(ev["input_tokens"], 1204)

    async def test_a_stage_full_cost_joins_on_task_id(self):
        """delegation_end + verdict + quality_score, one id, three calls."""
        orch, _ = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        rows = [
            e
            for e in orch.log.read()
            if e.get("task_id") == "20260727-ff-014"
            and e["event"] in ("delegation_end", "verdict", "quality_score")
        ]
        self.assertEqual(
            sorted(e["event"] for e in rows),
            ["delegation_end", "quality_score", "verdict"],
        )


if __name__ == "__main__":
    unittest.main()
