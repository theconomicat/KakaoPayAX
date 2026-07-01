import json
from pathlib import Path
import unittest


class ManifestAndRulesTest(unittest.TestCase):
    def test_manifest_has_required_plugin_shape(self):
        manifest = json.loads(Path(".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "kps-analyst-workbench")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertIn("interface", manifest)
        self.assertIsInstance(manifest["interface"]["defaultPrompt"], list)

    def test_source_policy_defines_access_statuses(self):
        schema = json.loads(Path("rules/output_schema.json").read_text(encoding="utf-8"))
        for status in ["ok", "partial", "blocked", "auth_required", "not_found", "fixture"]:
            self.assertIn(status, schema["access_status_values"])


if __name__ == "__main__":
    unittest.main()
