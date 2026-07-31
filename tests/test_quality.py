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

from mastery import evals, quality
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
        """Fail closed, and do it for free. `strategy` has no rubric."""
        runner = ScriptedRunner([])  # must never be called
        orch = Orchestrator(self.config, runner, run_id="test")

        with self.assertRaises(RubricMissing):
            await orch.execute(a_brief(agent="strategy"))

        self.assertEqual(
            runner.prompts, [], "paid for a delegation it could never have scored"
        )

    def test_the_unrubriced_agents_are_genuinely_unrubriced(self):
        """Documents the operational cost of fail-closed, so it cannot be
        forgotten: these agents cannot run until they have a rubric.

        Deliberately hardcoded. Adding a rubric must break this test, because
        adding one is a decision about what "good" means for a role and should
        not slip in as a side effect of some other change.

        `fact-checker` was added 2026-07-31 to run the first live gate test.
        Until then it could not execute at all: `RubricMissing` halts before any
        spend, which is why the two pipeline-halting gates had never once run.
        `risk-review` is still unrubriced and still cannot run.
        """
        from mastery.roster import DELEGATABLE

        rubriced = {a.name for a in DELEGATABLE if quality.has_rubric(a.name)}
        self.assertEqual(
            rubriced,
            {"researcher", "content", "data-model-agent", "mobile-dev", "qa", "fact-checker"},
        )
        self.assertEqual(len(DELEGATABLE) - len(rubriced), 11)


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
            evals.set_baseline([_rec(overall=3.0)], label="fresh-strong-model", path=path)
            evals.set_baseline([_rec(overall=1.0)], label="retro-sanity-check", path=path)

            data = json.loads(path.read_text(encoding="utf-8"))
            key = "researcher|1|claude-sonnet-4-5"
            self.assertEqual(data["baselines"][key]["fresh-strong-model"]["overall_mean"], 3.0)
            self.assertEqual(data["baselines"][key]["retro-sanity-check"]["overall_mean"], 1.0)

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
