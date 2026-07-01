import json
from pathlib import Path
import unittest

from tools.build_source_packet import GUARDRAIL_NOTICE, build_packet


class BuildSourcePacketTest(unittest.TestCase):
    def test_packet_contains_required_sections_and_guardrail(self):
        data = json.loads(Path("examples/sample_raw_sources.json").read_text(encoding="utf-8"))
        packet = build_packet(data)
        for section in [
            "Request Interpretation",
            "Source Map",
            "News and Market Narrative Sources",
            "Disclosure and Filing Sources",
            "Financial Snapshot",
            "Market and Technical Signals",
            "Investor Lens Notes",
            "Draft Analyst Memo",
            "Conflicts, Gaps, and Follow-up Questions",
            "Guardrail Notice",
        ]:
            self.assertIn(section, packet)
        self.assertIn(GUARDRAIL_NOTICE, packet)
        self.assertIn("fixture", packet)

    def test_packet_avoids_recommendation_language(self):
        data = json.loads(Path("examples/sample_raw_sources.json").read_text(encoding="utf-8"))
        packet = build_packet(data).lower()
        self.assertNotIn("target price", packet.replace("not investment advice, a recommendation, or a target price", ""))
        self.assertNotIn("buy recommendation", packet)
        self.assertNotIn("sell recommendation", packet)


if __name__ == "__main__":
    unittest.main()

