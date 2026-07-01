import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_logs import inspect_logs
from tools.fred_public_client import parse_fred_csv
from tools.kps_mcp_server import handle_request
from tools.openbb_public_sources import search_providers
from tools.sec_edgar_client import find_company, normalize_cik, summarize_companyfacts


class PublicProviderExpansionTests(unittest.TestCase):
    def test_fred_csv_parser_extracts_latest_value(self):
        payload = "observation_date,DGS10\n2026-06-30,4.24\n2026-07-01,4.28\n"

        parsed = parse_fred_csv(payload, "DGS10")

        self.assertEqual(parsed["latest"]["date"], "2026-07-01")
        self.assertEqual(parsed["latest"]["value"], 4.28)

    def test_sec_lookup_and_companyfacts_summarizer(self):
        tickers = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        matches = find_company(tickers, "aapl")
        self.assertEqual(matches[0]["cik"], "0000320193")
        self.assertEqual(normalize_cik(320193), "0000320193")

        facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "label": "Revenues",
                        "description": "Sales revenue.",
                        "units": {
                            "USD": [
                                {"fy": 2025, "fp": "FY", "form": "10-K", "filed": "2025-10-31", "end": "2025-09-27", "val": 391035000000}
                            ]
                        },
                    }
                }
            }
        }

        summary = summarize_companyfacts(facts)

        self.assertEqual(summary[0]["fact"], "Revenues")
        self.assertEqual(summary[0]["latest"][0]["val"], 391035000000)

    def test_openbb_inspired_catalog_has_no_key_sources(self):
        providers = search_providers("SEC FRED")
        names = {provider["name"] for provider in providers}
        self.assertIn("SEC EDGAR companyfacts", names)
        self.assertIn("FRED graph CSV", names)

    def test_mcp_lists_public_finance_tools(self):
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertIn("openbb_public_sources", names)
        self.assertIn("fred_series", names)
        self.assertIn("sec_companyfacts", names)

    def test_log_inspector_validates_jsonl_without_editing(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs = Path(tmp) / "logs" / "codex"
            logs.mkdir(parents=True)
            path = logs / "session.jsonl"
            path.write_text(
                json.dumps({"type": "session_meta"}) + "\n" + json.dumps({"type": "event_msg"}) + "\n",
                encoding="utf-8",
            )

            summary = inspect_logs(Path(tmp) / "logs")

            self.assertEqual(summary["status"], "ok")
            self.assertEqual(summary["jsonl_count"], 1)
            self.assertEqual(summary["jsonl"][0]["bad_lines"], [])


if __name__ == "__main__":
    unittest.main()
