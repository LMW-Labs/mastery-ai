"""STOP 2: gating at the invocation boundary.

The property under test is not "gated things are gated" — it is that the gate
cannot be talked past. Three ways it could be, each pinned here:

  - by declaring the task safe (declaration must only ADD halts)
  - by invoking something nobody classified (unknown must fail closed)
  - by asking the actor about its own intent (there is no such input; every
    assertion below reaches the gate through the observed target alone)
"""

from __future__ import annotations

import unittest

from mastery import gates
from mastery.errors import ApprovalRequired, GateHit
from mastery.gates import GateClass


class TestClassMap(unittest.TestCase):
    def test_the_four_meta_writes_are_classified(self):
        """The first real targets, and the classes the operator assigned."""
        self.assertEqual(
            gates.classify("meta_client.publish_ig_post"), GateClass.PUBLIC
        )
        self.assertEqual(
            gates.classify("meta_client.publish_page_post"), GateClass.PUBLIC
        )
        self.assertEqual(
            gates.classify("meta_client.reply_to_comment"), GateClass.PUBLIC
        )
        self.assertEqual(
            gates.classify("meta_client.delete_comment"), GateClass.IRREVERSIBLE
        )

    def test_delete_is_irreversible_not_public(self):
        """Classing deletion as publishing would let a publishing approval cover
        a destructive act. The harm is the irreversibility."""
        self.assertNotEqual(
            gates.classify("meta_client.delete_comment"),
            gates.classify("meta_client.publish_ig_post"),
        )

    def test_unmapped_target_has_no_class(self):
        self.assertIsNone(gates.classify("meta_client.get_ig_account"))
        self.assertIsNone(gates.classify("something.nobody.wrote"))

    def test_declaration_vocabulary_maps_onto_the_five_classes(self):
        """One vocabulary. A `production` declaration must reach the `prod`
        class, or a declaration could name a gate that no class matches."""
        for name in gates.GATE_NAMES:
            self.assertIn(
                gates.CLASS_FOR_DECLARATION[name],
                set(GateClass),
                f"declaration {name!r} maps to no class",
            )


class TestFailClosed(unittest.TestCase):
    def test_unknown_target_requires_approval(self):
        """Absence from the map is an unknown, not a clearance."""
        with self.assertRaises(ApprovalRequired) as ctx:
            gates.require_approval("integrations.something_new.publish")
        self.assertEqual(ctx.exception.gate_class, "unclassified")
        self.assertIn("not a", str(ctx.exception))

    def test_there_is_no_input_that_permits_execution(self):
        """`require_approval` always raises. No argument clears it, because
        approval arrives as a fresh operator request, not as a flag."""
        for declared in ("none", "", "money", "already approved", "public-output"):
            with self.assertRaises(ApprovalRequired):
                gates.require_approval("meta_client.publish_ig_post", declared=declared)

    def test_approval_required_is_a_gate_hit(self):
        """Every existing `except GateHit` path must already halt on this.
        Widening a guardrail must not require callers to opt in."""
        self.assertTrue(issubclass(ApprovalRequired, GateHit))
        with self.assertRaises(GateHit):
            gates.require_approval("meta_client.delete_comment")


class TestDeclarationIsAddOnly(unittest.TestCase):
    """The rule that makes the second enforcement point non-optional."""

    def test_declared_safe_cannot_downgrade_a_classed_target(self):
        cls = gates.effective_class("meta_client.publish_ig_post", declared="none")
        self.assertEqual(cls, GateClass.PUBLIC)

    def test_declared_safe_still_halts_on_a_classed_target(self):
        """DONE-WHEN clause: a declared-safe task invoking a classed tool halts."""
        with self.assertRaises(ApprovalRequired) as ctx:
            gates.require_approval("meta_client.reply_to_comment", declared="none")
        self.assertEqual(ctx.exception.gate_class, "public")

    def test_the_map_wins_over_a_conflicting_declaration(self):
        """A declaration naming a *different, lesser* gate cannot reclass the
        target. The map is the authority on what a target is."""
        cls = gates.effective_class("meta_client.delete_comment", declared="money")
        self.assertEqual(cls, GateClass.IRREVERSIBLE)

    def test_declaration_can_add_a_class_the_map_lacks(self):
        """Add-only cuts both ways: an unmapped target that the brief declares
        gated is gated on the declaration's class."""
        cls = gates.effective_class("meta_client.get_ig_account", declared="money")
        self.assertEqual(cls, GateClass.MONEY)

    def test_unmapped_and_undeclared_is_still_not_cleared(self):
        """`effective_class` reports None, and `require_approval` halts anyway —
        the fail-closed decision lives in one place, not in every caller."""
        self.assertIsNone(
            gates.effective_class("meta_client.get_ig_account", declared="none")
        )
        with self.assertRaises(ApprovalRequired):
            gates.require_approval("meta_client.get_ig_account", declared="none")


class TestMetaClientWritesHalt(unittest.TestCase):
    """DONE-WHEN clause: the four meta_client writes halt-for-approval by class.

    Constructed without touching the network or the environment — the gate must
    fire before any request is built, so it must also fire before a token is
    needed.
    """

    def client(self):
        from integrations.meta_client import MetaClient

        c = MetaClient.__new__(MetaClient)  # no __init__: no env, no token
        return c

    def test_publish_ig_post_halts_public(self):
        with self.assertRaises(ApprovalRequired) as ctx:
            self.client().publish_ig_post(caption="hello")
        self.assertEqual(ctx.exception.gate_class, "public")
        self.assertEqual(ctx.exception.target, "meta_client.publish_ig_post")

    def test_publish_page_post_halts_public(self):
        with self.assertRaises(ApprovalRequired) as ctx:
            self.client().publish_page_post(message="hello")
        self.assertEqual(ctx.exception.gate_class, "public")

    def test_reply_to_comment_halts_public(self):
        with self.assertRaises(ApprovalRequired) as ctx:
            self.client().reply_to_comment("123", "hi")
        self.assertEqual(ctx.exception.gate_class, "public")

    def test_delete_comment_halts_irreversible(self):
        with self.assertRaises(ApprovalRequired) as ctx:
            self.client().delete_comment("123")
        self.assertEqual(ctx.exception.gate_class, "irreversible")

    def test_no_write_raises_notimplementederror_any_more(self):
        """The old halt was NotImplementedError — fail-closed by accident, and it
        would vanish the day someone wrote a body. The halt must be about what
        the method *is*, not about whether it was finished."""
        c = self.client()
        for call in (
            lambda: c.publish_ig_post(),
            lambda: c.publish_page_post(),
            lambda: c.reply_to_comment(),
            lambda: c.delete_comment(),
        ):
            with self.assertRaises(ApprovalRequired):
                call()

    def test_read_methods_are_not_gated_at_the_boundary(self):
        """Reads must not route through require_approval, or the client becomes
        unusable. Verified structurally: no read method names a gated target."""
        for name in (
            "get_ig_account",
            "get_ig_media",
            "get_media_insights",
            "get_page_insights",
        ):
            self.assertIsNone(gates.classify(f"meta_client.{name}"))


class TestPreFlightStillWorks(unittest.TestCase):
    """Two enforcement points, not one replacing the other. The pre-flight halts
    before spend; removing it would trade a cheap halt for an expensive one."""

    def test_declared_gate_still_halts_pre_flight(self):
        with self.assertRaises(GateHit):
            gates.enforce("production")

    def test_declared_none_still_clears_pre_flight(self):
        gates.enforce("none")  # must not raise

    def test_unfilled_declaration_still_halts(self):
        with self.assertRaises(GateHit):
            gates.enforce("")

    def test_unrecognized_declaration_is_not_a_clearance(self):
        self.assertFalse(gates.check("something vague").clear)


if __name__ == "__main__":
    unittest.main()
