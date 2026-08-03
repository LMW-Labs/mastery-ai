"""Contract tests: IDs, roster, briefs, gates, schemas, pipelines.

Everything here runs without the SDK, a network, or a credential.
"""

from __future__ import annotations

import json
import unittest

from mastery import ids, pipelines, roster, verdict
from mastery.brief import ContextItem, build
from mastery.errors import (
    BriefIncomplete,
    ContextTooLarge,
    GateHit,
    RoutingError,
    SchemaViolation,
)
from mastery.gates import check, enforce
from mastery.schema import Action, Status, parse


def a_result(**overrides) -> str:
    payload = {
        "task_id": "20260727-ff-014",
        "status": "complete",
        "summary": "Fixed the crash.",
        "deliverables": ["FeedViewModel.kt"],
        "risks": [],
        "next_step": "Hand to qa.",
    }
    payload.update(overrides)
    return json.dumps(payload)


class TestIds(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(ids.is_valid("20260727-ff-014"))
        self.assertTrue(ids.is_valid("20260727-rd-000"))
        self.assertTrue(ids.is_valid("20260727-ops-999"))

    def test_invalid(self):
        for bad in (
            "2026727-ff-014",  # short date
            "20260727-app-014",  # unknown vertical
            "20260727-ff-14",  # sequence not padded
            "20260727-ff-0140",  # sequence too long
            "20260727_ff_014",
            "",
        ):
            with self.subTest(bad=bad):
                self.assertFalse(ids.is_valid(bad))

    def test_mint_pads_sequence(self):
        from datetime import date

        self.assertEqual(ids.mint("ff", 7, on=date(2026, 7, 27)), "20260727-ff-007")

    def test_mint_rejects_unknown_vertical(self):
        with self.assertRaises(ValueError):
            ids.mint("app", 1)

    def test_vertical_name(self):
        self.assertEqual(ids.vertical_name("20260727-rd-001"), "Research and Debunk")


class TestRoster(unittest.TestCase):
    def test_every_agent_has_a_doc(self):
        """The roster and docs/agents/ must not drift."""
        missing = [a.name for a in roster.all_agents() if not a.doc_path.exists()]
        self.assertEqual(missing, [], f"agents with no doc: {missing}")

    def test_roster_matches_readme_count(self):
        self.assertEqual(len(roster.all_agents()), 19)

    def test_manager_is_not_delegatable(self):
        self.assertNotIn("manager", [a.name for a in roster.DELEGATABLE])

    def test_unknown_agent_raises(self):
        with self.assertRaises(RoutingError):
            roster.get("seo-agent")

    def test_gate_agents_flagged(self):
        gate_names = {a.name for a in roster.all_agents() if a.is_gate}
        self.assertEqual(gate_names, {"qa", "risk-review", "fact-checker", "legal-review"})


class TestGates(unittest.TestCase):
    def test_none_is_clear(self):
        self.assertTrue(check("none").clear)
        self.assertTrue(check("  None  ").clear)

    def test_named_gate_halts(self):
        for declared in ("money", "production", "permissions", "public output", "destructive"):
            with self.subTest(declared=declared):
                self.assertFalse(check(declared).clear)

    def test_blank_is_not_a_clearance(self):
        with self.assertRaises(GateHit):
            check("")

    def test_unrecognized_declaration_is_not_a_clearance(self):
        """Anything that is not the explicit word `none` gates."""
        result = check("probably fine?")
        self.assertFalse(result.clear)
        self.assertEqual(result.gate, "unrecognized")

    def test_enforce_raises_with_gate_name(self):
        with self.assertRaises(GateHit) as ctx:
            enforce("money: upgrading the Play Console plan tier")
        self.assertEqual(ctx.exception.gate, "money")


def a_brief(**overrides):
    kwargs = dict(
        task_id="20260727-ff-014",
        agent="mobile-dev",
        urgency="none",
        objective="Fix the crash on pull-to-refresh when the feed is empty.",
        success_criteria=["Cold start with no cache, pull to refresh, does not crash."],
        context=[ContextItem("FeedViewModel.kt", "class FeedViewModel { }")],
        constraints="Touch FeedViewModel.kt only.",
        out_of_scope="Do not test or sign off — qa owns that.",
        approval_gates_touched="none",
        expected_deliverables=["FeedViewModel.kt", "manual test steps"],
    )
    kwargs.update(overrides)
    return build(**kwargs)


class TestBrief(unittest.TestCase):
    def test_agent_doc_is_prepended_to_context(self):
        brief = a_brief()
        self.assertEqual(brief.context[0].label, "docs/agents/mobile-dev.md")

    def test_valid_brief_passes(self):
        a_brief().validate(max_context_bytes=1_000_000)

    def test_blank_section_rejected(self):
        with self.assertRaises(BriefIncomplete):
            a_brief(constraints="   ").validate(max_context_bytes=1_000_000)

    def test_tbd_rejected(self):
        with self.assertRaises(BriefIncomplete):
            a_brief(out_of_scope="TBD").validate(max_context_bytes=1_000_000)

    def test_empty_success_criteria_rejected(self):
        with self.assertRaises(BriefIncomplete):
            a_brief(success_criteria=[]).validate(max_context_bytes=1_000_000)

    def test_bad_task_id_rejected(self):
        with self.assertRaises(BriefIncomplete):
            a_brief(task_id="ff-014").validate(max_context_bytes=1_000_000)

    def test_manager_is_not_a_delegation_target(self):
        with self.assertRaises(BriefIncomplete):
            a_brief(agent="manager").validate(max_context_bytes=1_000_000)

    def test_oversized_context_rejected_not_truncated(self):
        brief = a_brief(context=[ContextItem("huge.txt", "x" * 5000)])
        with self.assertRaises(ContextTooLarge):
            brief.validate(max_context_bytes=1000)
        # and nothing was dropped
        self.assertGreater(brief.context_bytes(), 1000)

    def test_render_includes_every_section(self):
        rendered = a_brief().render()
        for heading in (
            "## Objective",
            "## Success criteria",
            "## Context provided",
            "## Constraints",
            "## Out of scope",
            "## Approval gates touched",
            "## Expected deliverables",
        ):
            self.assertIn(heading, rendered)

    def test_context_payload_carries_only_listed_items(self):
        brief = a_brief()
        payload = brief.render_context()
        self.assertIn("docs/agents/mobile-dev.md", payload)
        self.assertIn("FeedViewModel.kt", payload)
        # The project doc is never in a delegation payload.
        self.assertNotIn("Personal agent operating system for Austin", payload)


class TestOutputSchema(unittest.TestCase):
    def test_valid_return_parses(self):
        result = parse(a_result(), expected_task_id="20260727-ff-014")
        self.assertIs(result.status, Status.COMPLETE)
        self.assertIs(result.action, Action.ACCEPT)

    def test_status_drives_action(self):
        for status, action in (
            ("complete", Action.ACCEPT),
            ("partial", Action.REVIEW),
            ("failed", Action.RETRY),
            ("blocked", Action.HALT),
        ):
            with self.subTest(status=status):
                self.assertIs(parse(a_result(status=status)).action, action)

    def test_unknown_status_rejected(self):
        with self.assertRaises(SchemaViolation):
            parse(a_result(status="done"))

    def test_additional_properties_rejected(self):
        with self.assertRaises(SchemaViolation):
            parse(a_result(confidence=0.9))

    def test_missing_required_field_rejected(self):
        payload = json.loads(a_result())
        del payload["risks"]
        with self.assertRaises(SchemaViolation):
            parse(json.dumps(payload))

    def test_task_id_mismatch_rejected(self):
        with self.assertRaises(SchemaViolation):
            parse(a_result(), expected_task_id="20260727-ff-999")

    def test_fenced_json_accepted(self):
        raw = f"```json\n{a_result()}\n```"
        self.assertIs(parse(raw).status, Status.COMPLETE)

    def test_prose_only_return_rejected(self):
        with self.assertRaises(SchemaViolation):
            parse("I fixed the crash, it looks good now.")

    def test_malformed_json_rejected_not_repaired(self):
        with self.assertRaises(SchemaViolation):
            parse('{"task_id": "20260727-ff-014", "status": "complete",}')

    def test_blocked_is_flagged_as_gate_closed(self):
        result = parse(a_result(status="blocked", next_step="risk-review hold: policy"))
        self.assertTrue(result.is_gate_closed)


class TestVerdictSchema(unittest.TestCase):
    def _verdict(self, **overrides) -> str:
        payload = {
            "task_id": "20260727-ff-014",
            "verdict": "accept",
            "reason": "Both criteria met.",
        }
        payload.update(overrides)
        return json.dumps(payload)

    def test_accept_parses(self):
        mv = verdict.parse(self._verdict(), expected_task_id="20260727-ff-014")
        self.assertIs(mv.verdict, verdict.Verdict.ACCEPT)
        self.assertTrue(mv.accepted)

    def test_revise_requires_a_revision_note(self):
        with self.assertRaises(SchemaViolation):
            verdict.parse(
                self._verdict(verdict="revise"), expected_task_id="20260727-ff-014"
            )

    def test_revise_with_note_parses(self):
        mv = verdict.parse(
            self._verdict(verdict="revise", revision_note="Add the manual test steps."),
            expected_task_id="20260727-ff-014",
        )
        self.assertEqual(mv.revision_note, "Add the manual test steps.")

    def test_unknown_verdict_rejected(self):
        with self.assertRaises(SchemaViolation):
            verdict.parse(
                self._verdict(verdict="maybe"), expected_task_id="20260727-ff-014"
            )

    def test_empty_reason_rejected(self):
        with self.assertRaises(SchemaViolation):
            verdict.parse(self._verdict(reason=""), expected_task_id="20260727-ff-014")

    def test_task_id_mismatch_rejected(self):
        with self.assertRaises(SchemaViolation):
            verdict.parse(self._verdict(), expected_task_id="20260727-ff-001")


class TestPipelines(unittest.TestCase):
    def test_public_output_order(self):
        self.assertEqual(
            pipelines.PUBLIC_OUTPUT.stages[:3], ("content", "fact-checker", "risk-review")
        )

    def test_release_order(self):
        self.assertEqual(pipelines.RELEASE.stages[:2], ("mobile-dev", "qa"))

    def test_advance_is_the_only_way_forward(self):
        p = pipelines.PUBLIC_OUTPUT
        self.assertEqual(p.advance("content"), "fact-checker")
        self.assertEqual(p.advance("fact-checker"), "risk-review")
        self.assertEqual(p.advance("risk-review"), pipelines.OPERATOR_APPROVAL)

    def test_advance_rejects_a_foreign_stage(self):
        with self.assertRaises(ValueError):
            pipelines.PUBLIC_OUTPUT.advance("qa")

    def test_last_stage_returns_none(self):
        self.assertIsNone(pipelines.PUBLIC_OUTPUT.advance("publish"))

    def test_halting_gates(self):
        self.assertEqual(pipelines.RELEASE.halts_on("qa"), "no-go")
        self.assertEqual(pipelines.PUBLIC_OUTPUT.halts_on("risk-review"), "hold")
        self.assertIsNone(pipelines.PUBLIC_OUTPUT.halts_on("content"))

    def test_for_agent_finds_the_pipeline(self):
        self.assertIs(pipelines.for_agent("qa"), pipelines.RELEASE)
        self.assertIs(pipelines.for_agent("content"), pipelines.PUBLIC_OUTPUT)
        self.assertIsNone(pipelines.for_agent("strategy"))

    def test_legal_review_inserted_on_escalation_or_named_party(self):
        escalated = parse(a_result(status="blocked", next_step="escalating"))
        clean = parse(a_result())
        self.assertTrue(pipelines.needs_legal_review(escalated, names_real_party=False))
        self.assertTrue(pipelines.needs_legal_review(clean, names_real_party=True))
        self.assertFalse(pipelines.needs_legal_review(clean, names_real_party=False))


if __name__ == "__main__":
    unittest.main()
