"""The guardrails are code, but their values come from a file.

`Config.load` applies a JSON patch over the defaults, which means the settings
that decide whether a delegation can act on the world were, until this floor
existed, editable to nothing by a three-line config file. Nothing in the runtime
would have complained: `mastery check` prints OK either way, and `allowed_tools`
still reads correctly while `permission_mode` quietly permits everything.

These tests exist because "guardrails are enforced in orchestrator code, not in
prose" is only true if the code refuses to be told otherwise.

A sub-agent cannot reach any of this — none has a write tool, so none can edit a
config file. This is a floor under operator and developer error.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mastery.config import Config, Delegation
from mastery.errors import GuardrailWeakened


class ConfigFloorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, payload: dict) -> Path:
        path = self.dir / "config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    # -- permission_mode -------------------------------------------------------

    def test_bypass_permissions_is_refused(self):
        """The one-line config that un-sandboxes every delegation."""
        path = self.write({"delegation": {"permission_mode": "bypassPermissions"}})

        with self.assertRaises(GuardrailWeakened) as ctx:
            Config.load(path)

        self.assertIn("permission_mode", str(ctx.exception))

    def test_accept_edits_is_refused(self):
        path = self.write({"delegation": {"permission_mode": "acceptEdits"}})
        with self.assertRaises(GuardrailWeakened):
            Config.load(path)

    def test_the_default_mode_stated_explicitly_is_accepted(self):
        """Restating the default is not a widening, and must not be an error."""
        path = self.write({"delegation": {"permission_mode": "dontAsk"}})
        self.assertEqual(Config.load(path).delegation.permission_mode, "dontAsk")

    # -- denied_tools ----------------------------------------------------------

    def test_removing_the_agent_tool_from_the_deny_list_is_refused(self):
        """Denying `Agent` is what makes spawn depth 1 real; restoring it is a
        structural change to the system, not a configuration preference."""
        remaining = [t for t in Delegation().denied_tools if t != "Agent"]
        path = self.write({"delegation": {"denied_tools": remaining}})

        with self.assertRaises(GuardrailWeakened) as ctx:
            Config.load(path)

        self.assertIn("Agent", str(ctx.exception))

    def test_removing_write_tools_is_refused(self):
        path = self.write({"delegation": {"denied_tools": ["Agent"]}})

        with self.assertRaises(GuardrailWeakened) as ctx:
            Config.load(path)

        message = str(ctx.exception)
        for tool in ("Bash", "Write", "Edit", "NotebookEdit"):
            self.assertIn(tool, message)

    def test_an_empty_deny_list_is_refused(self):
        path = self.write({"delegation": {"denied_tools": []}})
        with self.assertRaises(GuardrailWeakened):
            Config.load(path)

    def test_adding_to_the_deny_list_is_allowed(self):
        """The floor is a minimum, not a fixed set. Denying more is always fine."""
        path = self.write(
            {"delegation": {"denied_tools": [*Delegation().denied_tools, "WebFetch"]}}
        )

        cfg = Config.load(path)

        self.assertIn("WebFetch", cfg.delegation.denied_tools)
        self.assertIn("Agent", cfg.delegation.denied_tools)

    # -- setting_sources -------------------------------------------------------

    def test_loading_project_settings_is_refused(self):
        """A non-empty value auto-loads CLAUDE.md into sub-agents that are
        supposed to see only the brief the manager assembled for them."""
        path = self.write({"delegation": {"setting_sources": ["project"]}})

        with self.assertRaises(GuardrailWeakened) as ctx:
            Config.load(path)

        self.assertIn("setting_sources", str(ctx.exception))

    def test_explicitly_empty_setting_sources_is_accepted(self):
        path = self.write({"delegation": {"setting_sources": []}})
        self.assertEqual(Config.load(path).delegation.setting_sources, ())

    # -- what the floor deliberately does not cover -----------------------------

    def test_caps_may_still_be_changed_freely(self):
        """Caps are budgets, not guardrails. Raising one costs money; lowering
        one is a legitimate thing to want. Flooring them would be cargo cult."""
        path = self.write({"caps": {"max_delegations_per_request": 2}})

        cfg = Config.load(path)

        self.assertEqual(cfg.caps.max_delegations_per_request, 2)

    def test_model_may_still_be_changed(self):
        path = self.write({"delegation": {"model": "opus"}})
        self.assertEqual(Config.load(path).delegation.model, "opus")

    def test_defaults_load_clean_with_no_file(self):
        """The floor must not fire on the shipped configuration."""
        cfg = Config.load(None)
        self.assertEqual(cfg.delegation.permission_mode, "dontAsk")
        self.assertEqual(cfg.delegation.setting_sources, ())

    def test_a_config_that_widens_two_things_names_the_first_one_hit(self):
        """Whichever fires, it must halt rather than load a weakened config."""
        path = self.write(
            {"delegation": {"permission_mode": "bypassPermissions", "denied_tools": []}}
        )
        with self.assertRaises(GuardrailWeakened):
            Config.load(path)


if __name__ == "__main__":
    unittest.main()
