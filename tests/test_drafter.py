"""Drafter tests. No SDK, no network — `parse` and `write_briefs` are plain code.

The drafter is the one component that turns model prose into something the
orchestrator will later act on, so the tests here are mostly about what it
refuses to pass through: an invented agent, a plan that does not match the
schema, a stage count the cap cannot fund.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mastery import drafter
from mastery.config import Caps, Config
from mastery.errors import RoutingError, SchemaViolation


def stage(agent="researcher", **overrides) -> dict:
    payload = {
        "agent": agent,
        "objective": "Answer the five research questions.",
        "success_criteria": ["Every claim carries a source URL and a date."],
        "context_needed": ["docs/agents/researcher.md"],
        "constraints": "Five searches per question.",
        "out_of_scope": "Drafting any public copy.",
        "approval_gates_touched": "none",
        "expected_deliverables": ["Fact pack"],
    }
    payload.update(overrides)
    return payload


def plan_json(**overrides) -> str:
    payload = {
        "vertical": "rd",
        "scoped": True,
        "pipeline": "public-output",
        "legal_review_required": False,
        "stages": [stage()],
        "open_questions": [],
    }
    payload.update(overrides)
    return json.dumps(payload)


class ParseTests(unittest.TestCase):
    def test_parses_a_well_formed_plan(self):
        plan = drafter.parse(plan_json())
        self.assertTrue(plan.scoped)
        self.assertEqual(plan.vertical, "rd")
        self.assertEqual(plan.stages[0].agent, "researcher")
        self.assertEqual(plan.stages[0].context_needed, ("docs/agents/researcher.md",))

    def test_tolerates_a_fenced_reply(self):
        plan = drafter.parse(f"```json\n{plan_json()}\n```")
        self.assertEqual(len(plan.stages), 1)

    def test_rejects_non_json(self):
        with self.assertRaises(SchemaViolation):
            drafter.parse("Here is my plan: first, research it.")

    def test_rejects_an_unknown_field(self):
        # additionalProperties: false — a plan carrying something the
        # orchestrator does not model is a contract failure, not a warning.
        with self.assertRaises(SchemaViolation):
            drafter.parse(plan_json(estimated_cost_usd=4.0))

    def test_rejects_a_stage_with_no_success_criteria(self):
        with self.assertRaises(SchemaViolation):
            drafter.parse(plan_json(stages=[stage(success_criteria=[])]))

    def test_rejects_an_invented_agent(self):
        # Routing is checked against the roster in code. A model naming an
        # agent that does not exist must not reach a brief file.
        with self.assertRaises(RoutingError):
            drafter.parse(plan_json(stages=[stage(agent="seo-agent")]))

    def test_refusal_is_a_first_class_outcome(self):
        raw = plan_json(
            scoped=False,
            stages=[],
            scope_problem="No deliverable named.",
            open_questions=["What should this produce?"],
        )
        plan = drafter.parse(raw)
        self.assertFalse(plan.scoped)
        self.assertEqual(plan.stages, ())
        self.assertIn("No deliverable named", drafter.render(plan))
        self.assertIn("NOT SCOPED", drafter.render(plan))


class WriteBriefTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_writes_one_brief_per_stage_with_sequential_ids(self):
        plan = drafter.parse(
            plan_json(stages=[stage(), stage(agent="content"), stage(agent="fact-checker")])
        )
        written = drafter.write_briefs(plan, self.dir, stamp="20260728")
        self.assertEqual(
            [p.name for p in written],
            ["20260728-rd-001.json", "20260728-rd-002.json", "20260728-rd-003.json"],
        )

    def test_sequence_skips_ids_already_on_disk(self):
        (self.dir / "20260728-rd-001.json").write_text("{}", encoding="utf-8")
        plan = drafter.parse(plan_json())
        written = drafter.write_briefs(plan, self.dir, stamp="20260728")
        self.assertEqual(written[0].name, "20260728-rd-002.json")

    def test_context_bodies_are_placeholders_not_content(self):
        # Context stays opt-in and hand-assembled: the drafter names what a
        # stage needs, the operator pastes it. A drafter that filled these in
        # would be assembling context on a model's say-so.
        plan = drafter.parse(plan_json())
        written = drafter.write_briefs(plan, self.dir, stamp="20260728")
        payload = json.loads(written[0].read_text(encoding="utf-8"))
        self.assertEqual(len(payload["context"]), 1)
        self.assertIn("FILL", payload["context"][0]["body"])
        self.assertEqual(payload["context"][0]["label"], "docs/agents/researcher.md")

    def test_written_brief_loads_through_the_normal_brief_builder(self):
        # The drafter's output is not a special case — it has to satisfy the
        # same validation as a hand-written brief.
        from mastery.cli import _load_brief

        plan = drafter.parse(plan_json())
        written = drafter.write_briefs(plan, self.dir, stamp="20260728")
        brief = _load_brief(written[0])
        self.assertEqual(brief.agent, "researcher")
        self.assertEqual(brief.task_id, "20260728-rd-001")


class CapTests(unittest.TestCase):
    def config(self, max_delegations: int) -> Config:
        base = Config.load(None)
        return Config(
            caps=Caps(
                max_delegations_per_request=max_delegations,
                max_subagent_turns=base.caps.max_subagent_turns,
                max_context_bytes=base.caps.max_context_bytes,
                retries_per_failed_task=base.caps.retries_per_failed_task,
                task_timeout_seconds=base.caps.task_timeout_seconds,
            ),
            delegation=base.delegation,
            auth=base.auth,
        )

    def test_a_plan_at_the_cap_is_flagged(self):
        # At the cap there is no retry headroom: the pipeline can only finish
        # if every stage succeeds first try. That is over the cap in practice.
        plan = drafter.parse(plan_json(stages=[stage() for _ in range(5)]))
        self.assertTrue(drafter.over_cap(plan, self.config(5)))

    def test_a_plan_below_the_cap_is_not_flagged(self):
        plan = drafter.parse(plan_json(stages=[stage() for _ in range(4)]))
        self.assertFalse(drafter.over_cap(plan, self.config(5)))


if __name__ == "__main__":
    unittest.main()
