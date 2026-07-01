import json
from pathlib import Path
import unittest


class SkillsAndToolsInventoryTest(unittest.TestCase):
    def test_every_skill_has_required_frontmatter(self):
        for skill in Path("skills").glob("*/SKILL.md"):
            text = skill.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), skill)
            frontmatter = text.split("---", 2)[1]
            self.assertIn("name:", frontmatter, skill)
            self.assertIn("description:", frontmatter, skill)

    def test_expected_tools_exist(self):
        expected = [
            "byul_client.py",
            "build_source_packet.py",
            "dart_public_client.py",
            "filing_parser.py",
            "financial_snapshot.py",
            "kind_public_client.py",
            "market_data_reader.py",
            "playwright_probe.mjs",
            "public_page_reader.py",
            "research_workbench.py",
            "source_catalog.py",
            "source_fetcher.py",
            "technical_indicators.py",
        ]
        for tool in expected:
            self.assertTrue((Path("tools") / tool).exists(), tool)

    def test_live_public_sources_config_has_urls(self):
        config = json.loads(Path("examples/live_public_sources.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(config["urls"]), 3)
        self.assertTrue(config.get("byul"))
        self.assertTrue(config.get("filing_urls"))
        self.assertTrue(config.get("dart_public"))
        self.assertTrue(config.get("kind_public"))
        self.assertTrue((Path("tools") / "collectors" / "dart_public.py").exists())
        self.assertTrue((Path("tools") / "collectors" / "kind_public.py").exists())
        self.assertTrue((Path("tools") / "parsers" / "filing_tables.py").exists())


if __name__ == "__main__":
    unittest.main()
