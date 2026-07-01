import unittest

from tools.source_deep_probe import (
    candidate_priority,
    is_followable_candidate,
    public_browser_probe_view,
)


class SourceDeepProbeTests(unittest.TestCase):
    def test_followable_public_json_candidate(self):
        self.assertTrue(
            is_followable_candidate(
                {
                    "url": "https://www.tipranks.com/calendars/earnings/payload.json",
                    "status_code": 200,
                    "method": "GET",
                    "content_type": "application/json; charset=utf-8",
                }
            )
        )

    def test_skips_static_assets_and_blocked_candidates(self):
        self.assertFalse(
            is_followable_candidate(
                {
                    "url": "https://tr-cdn.tipranks.com/static/v2/static/logos/FDS.svg",
                    "status_code": 200,
                    "method": "GET",
                    "content_type": "image/svg+xml",
                }
            )
        )
        self.assertFalse(
            is_followable_candidate(
                {
                    "url": "https://www.tipranks.com/api/users/followingStocks",
                    "status_code": 200,
                    "method": "GET",
                    "content_type": "application/json",
                }
            )
        )
        self.assertFalse(
            is_followable_candidate(
                {
                    "url": "https://tr-cdn.tipranks.com/config/prod/popups/payload.json",
                    "status_code": 200,
                    "method": "GET",
                    "content_type": "application/json",
                }
            )
        )

    def test_payload_json_is_prioritized(self):
        payload = {
            "url": "https://www.tipranks.com/calendars/earnings/payload.json",
            "status_code": 200,
            "method": "GET",
            "content_type": "application/json; charset=utf-8",
        }
        generic_api = {
            "url": "https://example.com/api/public-data",
            "status_code": 200,
            "method": "GET",
            "content_type": "application/json",
        }
        self.assertLess(candidate_priority(payload), candidate_priority(generic_api))

    def test_public_browser_probe_view_hides_private_candidates(self):
        probe = {
            "network_candidates": [
                {
                    "url": "https://www.tipranks.com/calendars/earnings/payload.json",
                    "status_code": 200,
                    "method": "GET",
                    "content_type": "application/json",
                },
                {
                    "url": "https://www.tipranks.com/api/users/getUserSettings2",
                    "status_code": 200,
                    "method": "GET",
                    "content_type": "application/json",
                },
            ]
        }

        visible = public_browser_probe_view(probe)

        self.assertEqual(len(visible["network_candidates"]), 1)
        self.assertIn("/payload.json", visible["network_candidates"][0]["url"])


if __name__ == "__main__":
    unittest.main()
