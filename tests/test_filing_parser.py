from pathlib import Path
import unittest

from tools.filing_parser import parse_filing_target, to_source


ROOT = Path(__file__).resolve().parents[1]


class FilingParserTests(unittest.TestCase):
    def test_extracts_financial_statement_rows_from_html_table(self):
        result = parse_filing_target(str(ROOT / "examples" / "sample_dart_filing.html"))
        self.assertEqual(result["access_status"], "ok")
        self.assertGreaterEqual(len(result["tables"]), 2)
        rows = result["financial_statement_rows"]
        self.assertTrue(any(row["line_item"] == "매출액" for row in rows))
        self.assertTrue(any(row["line_item"] == "영업이익" for row in rows))
        source = to_source(result, "financials")
        self.assertEqual(source["type"], "financials")
        self.assertTrue(source["numeric_facts"])


if __name__ == "__main__":
    unittest.main()
