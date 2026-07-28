"""Run-loop tests against a scripted fake runner.

No SDK, no network, no credential — the point is that every guardrail is
enforced by this package's own code, so it can be proven without a model.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from mastery import pipelines
from mastery.brief import ContextItem, build
from mastery.config import Caps, Config
from mastery.errors import CapExceeded
from mastery.orchestrator import Orchestrator, Outcome, summarize


def result_json(task_id="20260727-ff-014", status="complete", **overrides) -> str:
    payload = {
        "task_id": task_id,
        "status": status,
        "summary": "Did the thing.",
        "deliverables": ["FeedViewModel.kt"],
        "risks": [],
        "next_step": "Hand to qa.",
    }
    payload.update(overrides)
    return json.dumps(payload)


def verdict_json(task_id="20260727-ff-014", verdict="accept", **overrides) -> str:
    payload = {"task_id": task_id, "verdict": verdict, "reason": "Criteria met."}
    payload.update(overrides)
    return json.dumps(payload)


class ScriptedRunner:
    """Returns queued replies in order and records every prompt it was sent."""

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.prompts: list[str] = []
        self.system_prompts: list[str] = []
        self.max_turns: list[int] = []

    async def run(self, *, system_prompt: str, prompt: str, max_turns: int) -> str:
        self.prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        self.max_turns.append(max_turns)
        if not self.replies:
            raise AssertionError("runner called more times than the test scripted")
        return self.replies.pop(0)


def a_brief(**overrides):
    kwargs = dict(
        task_id="20260727-ff-014",
        agent="mobile-dev",
        urgency="none",
        objective="Fix the crash on pull-to-refresh when the feed is empty.",
        success_criteria=["Does not crash on empty-feed refresh."],
        context=[ContextItem("FeedViewModel.kt", "class FeedViewModel { }")],
        constraints="Touch FeedViewModel.kt only.",
        out_of_scope="Do not test or sign off — qa owns that.",
        approval_gates_touched="none",
        expected_deliverables=["FeedViewModel.kt"],
    )
    kwargs.update(overrides)
    return build(**kwargs)


class OrchestratorTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.config = Config(log_dir=Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def orch(self, replies: list[str]) -> tuple[Orchestrator, ScriptedRunner]:
        runner = ScriptedRunner(replies)
        return Orchestrator(self.config, runner, run_id="test"), runner


class TestHappyPath(OrchestratorTestCase):
    async def test_complete_still_goes_through_manager_verification(self):
        """A `complete` status is a claim, not a clearance."""
        orch, runner = self.orch([result_json(), verdict_json()])
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.ACCEPTED)
        self.assertIsNotNone(outcome.manager_verdict)
        # two calls: the delegation, then the verify-only invocation
        self.assertEqual(len(runner.prompts), 2)
        self.assertEqual(runner.max_turns, [self.config.caps.max_subagent_turns, 1])

    async def test_delegation_prompt_carries_only_the_context_payload(self):
        orch, runner = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief())
        prompt = runner.prompts[0]

        self.assertIn("docs/agents/mobile-dev.md", prompt)
        self.assertIn("FeedViewModel.kt", prompt)
        # The project doc is never passed to a sub-agent.
        self.assertNotIn("Personal agent operating system for Austin", prompt)

    async def test_verification_prompt_excludes_the_context_payload(self):
        """The manager checks a contract; it does not re-do the task."""
        orch, runner = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief())
        verify_prompt = runner.prompts[1]

        self.assertIn("Does not crash on empty-feed refresh.", verify_prompt)
        self.assertNotIn("class FeedViewModel", verify_prompt)

    async def test_run_log_records_the_delegation(self):
        orch, _ = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief())
        events = {e["event"] for e in orch.log.read()}

        self.assertIn("delegation_start", events)
        self.assertIn("delegation_end", events)
        self.assertIn("verdict", events)
        start = next(e for e in orch.log.read() if e["event"] == "delegation_start")
        self.assertEqual(start["agent"], "mobile-dev")
        self.assertGreater(start["context_bytes"], 0)


class TestHalting(OrchestratorTestCase):
    async def test_gate_halts_before_any_delegation(self):
        orch, runner = self.orch([])  # runner must never be called
        outcome = await orch.execute(
            a_brief(approval_gates_touched="production: promote to the internal track")
        )

        self.assertIs(outcome.outcome, Outcome.HALTED)
        self.assertIn("production", outcome.detail)
        self.assertEqual(runner.prompts, [], "gated brief must not be sent")

    async def test_blocked_return_halts_with_no_retry(self):
        orch, runner = self.orch(
            [result_json(status="blocked", next_step="risk-review hold: policy risk")]
        )
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.HALTED)
        self.assertEqual(outcome.attempts, 1)
        self.assertEqual(len(runner.prompts), 1, "blocked must not be retried")

    async def test_qa_no_go_halts_the_release_pipeline(self):
        orch, _ = self.orch(
            [
                result_json(task_id="20260727-ff-020"),
                verdict_json(task_id="20260727-ff-020"),
                result_json(
                    task_id="20260727-ff-021",
                    status="blocked",
                    next_step="qa no-go: empty state still crashes on rotate",
                ),
            ]
        )

        def make_brief(stage, completed):
            seq = {"mobile-dev": "020", "qa": "021"}[stage]
            return a_brief(task_id=f"20260727-ff-{seq}", agent=stage)

        outcome = await orch.run_pipeline(pipelines.Trigger.RELEASE, make_brief)

        self.assertIs(outcome.outcome, Outcome.HALTED)
        self.assertIn("no-go", outcome.detail)
        self.assertEqual(len(outcome.completed_stages), 2)


class TestFailureHandling(OrchestratorTestCase):
    async def test_failed_retries_once_then_reports(self):
        orch, runner = self.orch(
            [result_json(status="failed"), result_json(status="failed")]
        )
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.FAILED)
        self.assertEqual(outcome.attempts, 2)
        self.assertEqual(len(runner.prompts), 2, "two attempts, then report")

    async def test_retry_brief_carries_the_correction(self):
        orch, runner = self.orch(
            [
                result_json(status="failed", summary="Could not reproduce."),
                result_json(),
                verdict_json(),
            ]
        )
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.ACCEPTED)
        self.assertIn("Could not reproduce.", runner.prompts[1])
        self.assertNotIn("Could not reproduce.", runner.prompts[0])

    async def test_schema_violation_is_a_task_failure_not_a_repair(self):
        orch, runner = self.orch(["I fixed it, looks good!", "still just prose"])
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.FAILED)
        self.assertEqual(len(runner.prompts), 2)
        failures = [e for e in orch.log.read() if e["event"] == "failure"]
        self.assertEqual(len(failures), 2)
        self.assertEqual(failures[0]["kind"], "SchemaViolation")

    async def test_schema_violation_retry_tells_the_agent_what_was_wrong(self):
        orch, runner = self.orch(["I fixed it, looks good!", result_json(), verdict_json()])
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.ACCEPTED)
        self.assertIn("no JSON object found", runner.prompts[1])

    async def test_manager_revise_triggers_a_retry(self):
        orch, runner = self.orch(
            [
                result_json(),
                verdict_json(verdict="revise", revision_note="Manual test steps missing."),
                result_json(),
                verdict_json(),
            ]
        )
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.ACCEPTED)
        self.assertEqual(outcome.attempts, 2)
        self.assertIn("Manual test steps missing.", runner.prompts[2])

    async def test_manager_reject_does_not_retry(self):
        orch, runner = self.orch(
            [result_json(), verdict_json(verdict="reject", reason="Wrong file changed.")]
        )
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.FAILED)
        self.assertEqual(outcome.attempts, 1)
        self.assertEqual(len(runner.prompts), 2)

    async def test_status_never_inferred_from_prose(self):
        """Prose saying 'blocked' with status complete is still complete."""
        orch, _ = self.orch(
            [
                result_json(summary="I am blocked and could not do this."),
                verdict_json(verdict="reject", reason="Summary contradicts status."),
            ]
        )
        outcome = await orch.execute(a_brief())
        # It reached the verdict step, which only happens for complete/partial.
        self.assertIsNotNone(outcome.manager_verdict)


class TestCaps(OrchestratorTestCase):
    async def test_delegation_cap_stops_the_run(self):
        self.config = replace(
            self.config, caps=Caps(max_delegations_per_request=1, retries_per_failed_task=5)
        )
        orch, _ = self.orch([result_json(status="failed"), result_json(status="failed")])

        with self.assertRaises(CapExceeded):
            await orch.execute(a_brief())

    async def test_subagent_turn_cap_is_passed_through(self):
        self.config = replace(self.config, caps=Caps(max_subagent_turns=3))
        orch, runner = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        self.assertEqual(runner.max_turns[0], 3)


class TestSummary(OrchestratorTestCase):
    async def test_halt_summary_names_the_next_step_as_the_operator(self):
        orch, _ = self.orch([])
        outcome = await orch.execute(a_brief(approval_gates_touched="money: new plan tier"))
        text = summarize(outcome)

        self.assertIn("halted", text)
        self.assertIn("money", text)
        self.assertIn("Next step: yours", text)

    async def test_pipeline_summary_lists_stages(self):
        orch, _ = self.orch(
            [
                result_json(task_id="20260727-ff-020"),
                verdict_json(task_id="20260727-ff-020"),
                result_json(task_id="20260727-ff-021"),
                verdict_json(task_id="20260727-ff-021"),
            ]
        )

        def make_brief(stage, completed):
            seq = {"mobile-dev": "020", "qa": "021"}[stage]
            return a_brief(task_id=f"20260727-ff-{seq}", agent=stage)

        outcome = await orch.run_pipeline(pipelines.Trigger.RELEASE, make_brief)
        text = summarize(outcome)

        self.assertIs(outcome.outcome, Outcome.NEEDS_APPROVAL)
        self.assertIn("mobile-dev", text)
        self.assertIn("qa", text)
        self.assertIn("Nothing has been published or promoted.", text)


if __name__ == "__main__":
    unittest.main()
