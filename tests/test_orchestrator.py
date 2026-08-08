"""Run-loop tests against a scripted fake runner.

No SDK, no network, no credential — the point is that every guardrail is
enforced by this package's own code, so it can be proven without a model.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from mastery import pipelines
from mastery.brief import ContextItem, build
from mastery.config import Caps, Config
from mastery.delegate import RunnerResult, usage_from
from mastery.errors import CapExceeded, DelegationFailed
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


def score_json(task_id="20260727-ff-014", agent="researcher", score=2) -> str:
    """A schema-valid quality score for whichever rubric `agent` has."""
    from mastery.quality import rubric_for

    return json.dumps(
        {
            "task_id": task_id,
            "agent": agent,
            "rubric_version": rubric_for(agent)["rubric_version"],
            "dimension_scores": [
                {"dimension": d["dimension"], "score": score, "justification": "because."}
                for d in rubric_for(agent)["dimensions"]
            ],
        }
    )


class ScriptedRunner:
    """Returns queued replies in order and records every prompt it was sent.

    A queued item may be an Exception, which is raised instead of returned —
    that is how SDK-level failures (turn exhaustion) are simulated.

    Grading prompts are answered automatically when nothing is queued for them.
    Every accepted delegation now costs a third call, and threading a score reply
    through every halting, retry, and cap test would bury what those tests are
    actually about. Tests that care about the score queue one explicitly, or read
    `grading_prompts`.
    """

    def __init__(self, replies: list, *, auto_score: bool = True):
        self.replies = list(replies)
        self.prompts: list[str] = []
        self.system_prompts: list[str] = []
        self.max_turns: list[int] = []
        self.tools: list[tuple] = []
        self.grading_prompts: list[str] = []
        self.auto_score = auto_score

    @staticmethod
    def _is_grading(prompt: str) -> bool:
        return "grading the quality of one completed task's output" in prompt

    def _auto_score_for(self, prompt: str) -> str:
        """Build a valid score from the task_id and agent named in the prompt."""
        task_id = re.search(r'"task_id": "([^"]+)"', prompt).group(1)
        agent = re.search(r"agent `([^`]+)`", prompt).group(1)
        return score_json(task_id=task_id, agent=agent)

    async def run(
        self,
        *,
        system_prompt: str,
        prompt: str,
        max_turns: int,
        tools: tuple | None = None,
    ) -> RunnerResult:
        self.prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        self.max_turns.append(max_turns)
        self.tools.append(tools)

        if self._is_grading(prompt):
            self.grading_prompts.append(prompt)
            # Answered without consuming the queue. Consuming it would make a
            # grading call eat the *next stage's* scripted reply, which silently
            # shifts every reply in a multi-stage pipeline test by one.
            if self.auto_score:
                return RunnerResult(text=self._auto_score_for(prompt), num_turns=1)

        if not self.replies:
            raise AssertionError("runner called more times than the test scripted")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return RunnerResult(text=reply, num_turns=1)


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
        outcome = await orch.execute(a_brief(agent="content"))

        self.assertIs(outcome.outcome, Outcome.ACCEPTED)
        self.assertIsNotNone(outcome.manager_verdict)
        # three calls: the delegation, the verify-only invocation, then grading.
        # An accepted stage costs three model calls, and that is visible here on
        # purpose — the third one is not free.
        self.assertEqual(len(runner.prompts), 3)
        self.assertEqual(
            runner.max_turns,
            [
                self.config.caps.max_subagent_turns,
                self.config.caps.verdict_turns,
                self.config.caps.verdict_turns,
            ],
        )

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

    async def test_tools_are_granted_per_agent_not_globally(self):
        """A researcher needs the web; a content agent must not have it.

        permission_mode refuses anything not pre-approved, so a too-narrow
        allowlist silently disables an agent rather than erroring — the
        researcher simply cannot research.
        """
        orch, runner = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief(agent="researcher"))
        self.assertIn("WebSearch", runner.tools[0])

        orch2, runner2 = self.orch([result_json(), verdict_json()])
        await orch2.execute(a_brief(agent="content"))
        self.assertNotIn("WebSearch", runner2.tools[0])
        self.assertIn("Read", runner2.tools[0])

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

    async def test_turn_exhaustion_is_a_task_failure_not_a_crash(self):
        """The SDK raises instead of returning a result when turns run out.

        Observed against claude-agent-sdk 0.2.128: a sub-agent that burns its
        turn budget raises rather than yielding a ResultMessage. That is an
        ordinary outcome and must not take the run down.
        """
        orch, runner = self.orch(
            [
                DelegationFailed("delegation ended without a result: max turns (6)"),
                result_json(),
                verdict_json(),
            ]
        )
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.ACCEPTED)
        self.assertEqual(outcome.attempts, 2)
        failures = [e for e in orch.log.read() if e["event"] == "failure"]
        self.assertEqual(failures[0]["kind"], "DelegationFailed")

    async def test_turn_exhaustion_twice_reports_cleanly(self):
        orch, _ = self.orch(
            [DelegationFailed("max turns"), DelegationFailed("max turns")]
        )
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.FAILED)
        self.assertIn("max turns", outcome.detail)

    async def test_permission_denials_reach_the_run_log(self):
        """A sub-agent reaching outside its allowlist must be visible in prod."""

        class DenyingRunner(ScriptedRunner):
            async def run(self, **kw):
                base = await super().run(**kw)  # keeps the scripted reply order
                return RunnerResult(
                    text=base.text,
                    num_turns=2,
                    cost_usd=0.12,
                    permission_denials=({"tool_name": "WebSearch"},),
                )

        runner = DenyingRunner([result_json(), verdict_json()])
        orch = Orchestrator(self.config, runner, run_id="test")
        await orch.execute(a_brief())

        end = next(e for e in orch.log.read() if e["event"] == "delegation_end")
        self.assertEqual(end["permission_denials"], [{"tool_name": "WebSearch"}])
        self.assertEqual(end["cost_usd"], 0.12)

    async def test_the_verdict_call_is_given_no_tools(self):
        """"One turn, no tools" has to be true, not just documented.

        `()` and `None` are different requests: none-on-purpose versus
        unspecified. While the runner conflated them, every verdict call was
        handed the full default allowlist, and a one-turn call that reaches for
        a tool has no turn left to answer in.
        """
        orch, runner = self.orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        task_tools, verdict_tools, grader_tools = runner.tools
        self.assertEqual(verdict_tools, ())
        # The grader is a manager-side call too, and gets the same treatment: it
        # grades what is in its prompt and has nothing to look up.
        self.assertEqual(grader_tools, ())
        self.assertIsNotNone(task_tools)
        self.assertIn("Read", task_tools)

    async def test_a_failed_verdict_does_not_destroy_the_completed_work(self):
        """The delegation is already paid for. Losing it to a verdict fault is
        the most expensive way this can fail, and it happened for real."""
        orch, runner = self.orch(
            [result_json(), DelegationFailed("Reached maximum number of turns (1)")]
        )
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.FAILED)
        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.result.deliverables, ("FeedViewModel.kt",))
        self.assertIn("verdict could not be produced", outcome.detail)
        # Attributable: this was the manager's fault, not the sub-agent's.
        failure = next(e for e in orch.log.read() if e["event"] == "failure")
        self.assertTrue(failure["kind"].startswith("verification/"))
        # And it is not silently retried — that would pay twice for one result.
        self.assertEqual(outcome.attempts, 1)

    async def test_an_unverified_return_is_never_accepted(self):
        """Preserving the work must not become a back door to accepting it."""
        orch, _ = self.orch([result_json(status="complete"), DelegationFailed("boom")])
        outcome = await orch.execute(a_brief())

        self.assertIsNot(outcome.outcome, Outcome.ACCEPTED)
        self.assertFalse(outcome.accepted)
        self.assertIsNone(outcome.manager_verdict)

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
        await orch.execute(a_brief(agent="content"))

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


# Shaped exactly like the SDK's dict[str, ModelUsage]: keyed by model string,
# camelCase keys, passed through verbatim from the CLI.
SDK_USAGE = {
    "claude-sonnet-4-5-20250929": {
        "inputTokens": 1204,
        "outputTokens": 830,
        "cacheReadInputTokens": 18_400,
        "cacheCreationInputTokens": 0,
        "costUSD": 0.0912,
        "canonicalModel": "claude-sonnet-4-5",
    }
}


class TestUsageFold(unittest.TestCase):
    """`usage_from` is the only thing that reads the SDK's usage dict."""

    def test_folds_camelcase_sdk_shape(self):
        u = usage_from(SDK_USAGE)
        self.assertEqual(u.input_tokens, 1204)
        self.assertEqual(u.output_tokens, 830)
        self.assertEqual(u.cache_read_tokens, 18_400)
        self.assertEqual(u.cache_creation_tokens, 0)
        self.assertEqual(u.model, "claude-sonnet-4-5")
        self.assertEqual(u.total_tokens, 2034)

    def test_cache_read_is_not_folded_into_the_total(self):
        """The split is the whole point: a total that absorbs cache reads cannot
        show whether a static prefix is being re-billed."""
        u = usage_from(SDK_USAGE)
        self.assertNotIn(u.cache_read_tokens, (u.total_tokens,))
        self.assertEqual(u.total_tokens, u.input_tokens + u.output_tokens)

    def test_missing_usage_is_zeroed_not_fatal(self):
        """Absent telemetry must not fail a delegation that succeeded."""
        for absent in (None, {}):
            u = usage_from(absent)
            self.assertEqual(u.total_tokens, 0)
            self.assertEqual(u.model, "")

    def test_multiple_models_sum_and_join(self):
        """Dropping one model's usage would under-report real spend."""
        u = usage_from(
            {
                "model-a": {"inputTokens": 10, "outputTokens": 5, "canonicalModel": "a"},
                "model-b": {"inputTokens": 1, "outputTokens": 2, "canonicalModel": "b"},
            }
        )
        self.assertEqual(u.input_tokens, 11)
        self.assertEqual(u.output_tokens, 7)
        self.assertEqual(u.model, "a+b")

    def test_partial_entry_does_not_raise(self):
        """Every ModelUsage key is optional in practice."""
        u = usage_from({"m": {"inputTokens": 3}})
        self.assertEqual(u.input_tokens, 3)
        self.assertEqual(u.output_tokens, 0)
        self.assertEqual(u.model, "m")


class TelemetryRunner(ScriptedRunner):
    """A ScriptedRunner that also reports token usage, as the SDK does."""

    async def run(self, **kwargs) -> RunnerResult:
        base = await super().run(**kwargs)
        return replace(base, cost_usd=0.0912, usage=usage_from(SDK_USAGE))


class TestTelemetryIsLogged(OrchestratorTestCase):
    """STOP 1: cost and tier land in the run log, joined by task_id, and no
    telemetry field is ever model-produced."""

    def telemetry_orch(self, replies):
        runner = TelemetryRunner(replies)
        return Orchestrator(self.config, runner, run_id="test"), runner

    async def test_tool_tier_comes_from_the_roster_not_the_agent(self):
        orch, _ = self.telemetry_orch([result_json(), verdict_json()])
        await orch.execute(a_brief(agent="researcher"))

        start = next(e for e in orch.log.read() if e["event"] == "delegation_start")
        # researcher's allowlist in roster.py, recorded as dispatched.
        self.assertEqual(
            start["tool_tier"], ["Read", "Glob", "Grep", "WebSearch", "WebFetch"]
        )

    async def test_delegation_end_carries_tokens_and_model(self):
        orch, _ = self.telemetry_orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        end = next(e for e in orch.log.read() if e["event"] == "delegation_end")
        self.assertEqual(end["input_tokens"], 1204)
        self.assertEqual(end["output_tokens"], 830)
        self.assertEqual(end["cache_read_tokens"], 18_400)
        self.assertEqual(end["cache_creation_tokens"], 0)
        self.assertEqual(end["model"], "claude-sonnet-4-5")
        # cost_usd is kept, not replaced: the dollar figure is what was billed,
        # the tokens are why.
        self.assertEqual(end["cost_usd"], 0.0912)

    async def test_model_and_role_tier_are_different_fields(self):
        """`model` is the resolved model id the SDK reported; `role_tier` is the
        declared kind of work. Conflating them is why the old name was wrong."""
        orch, _ = self.telemetry_orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        end = next(e for e in orch.log.read() if e["event"] == "delegation_end")
        self.assertEqual(end["model"], "claude-sonnet-4-5")
        # No roster agent is mechanical yet — the default keeps an unclassified
        # role on the stronger side. See tiers.py.
        self.assertEqual(end["role_tier"], "judgment")
        self.assertNotIn("model_tier", end, "renamed; the old name must be gone")

    async def test_verdict_call_is_also_telemetered(self):
        """The verdict is a real model call. Leaving it untelemetered would
        under-report a run's cost by one call per stage."""
        orch, _ = self.telemetry_orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        v = next(e for e in orch.log.read() if e["event"] == "verdict")
        self.assertEqual(v["cost_usd"], 0.0912)
        self.assertEqual(v["input_tokens"], 1204)
        self.assertEqual(v["model"], "claude-sonnet-4-5")
        # The verify-only call grades a return against fixed criteria — mechanical.
        self.assertEqual(v["role_tier"], "mechanical")

    async def test_stage_cost_joins_on_task_id(self):
        """A stage's true cost is its delegation_end plus every verdict sharing
        its task_id — that join is the DONE-WHEN."""
        orch, _ = self.telemetry_orch([result_json(), verdict_json()])
        await orch.execute(a_brief())

        rows = [
            e
            for e in orch.log.read()
            if e["event"] in ("delegation_end", "verdict")
            and e["task_id"] == "20260727-ff-014"
        ]
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(sum(r["cost_usd"] for r in rows), 0.1824, places=4)

    async def test_a_failed_return_is_telemetered_too(self):
        """Cost is incurred whether or not the work succeeded, so a failure that
        logged no cost would make runs look cheaper than they were."""
        orch, _ = self.telemetry_orch(
            [result_json(status="failed"), result_json(status="failed")]
        )
        outcome = await orch.execute(a_brief())

        self.assertIs(outcome.outcome, Outcome.FAILED)
        ends = [e for e in orch.log.read() if e["event"] == "delegation_end"]
        self.assertEqual(len(ends), 2)  # first attempt plus the one retry
        for end in ends:
            self.assertEqual(end["status"], "failed")
            self.assertEqual(end["cost_usd"], 0.0912)
            self.assertEqual(end["model"], "claude-sonnet-4-5")

    def test_no_telemetry_field_exists_in_the_task_output_schema(self):
        """The no-fabrication guarantee, asserted rather than asserted-in-prose.

        A sub-agent cannot report a token count or a model tier because the
        contract has no field for one, and `additionalProperties: false` rejects
        any it invents. If someone later adds one, this fails.
        """
        from mastery.schema import schema

        props = set(schema()["properties"])
        telemetry = {
            "tokens",
            "input_tokens",
            "output_tokens",
            "cache_read_tokens",
            "cache_creation_tokens",
            "model_tier",
            "role_tier",
            "model",
            "tool_tier",
            "cost_usd",
            "num_turns",
        }
        self.assertEqual(props & telemetry, set())
        self.assertFalse(schema()["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
