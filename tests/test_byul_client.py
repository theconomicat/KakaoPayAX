import unittest

from tools.byul_client import calendar_item_to_source, index_result_to_source, news_item_to_source


class ByulClientTests(unittest.TestCase):
    def test_news_item_to_source_preserves_importance_symbols_and_claims(self):
        source = news_item_to_source(
            {
                "title": "테슬라 실적 발표",
                "originalUrl": "https://example.com/news",
                "content": "테슬라가 분기 실적을 발표했다.",
                "importanceScore": 7,
                "symbols": ["TSLA"],
                "sentiment": "positive",
                "keyPoints": ["매출 증가"],
            },
            "https://api.byul.ai/api/v1/news",
        )
        self.assertEqual(source["type"], "news")
        self.assertEqual(source["retrieval_method"], "byul_api")
        self.assertIn("importanceScore=7", source["numeric_facts"])
        self.assertIn("symbols=TSLA", source["numeric_facts"])

    def test_calendar_and_index_sources_are_structured(self):
        calendar = calendar_item_to_source(
            {
                "event_name": "S&P 글로벌 제조업 PMI",
                "importance": "high",
                "actual": "55.1",
                "forecast": "54.8",
                "currency": "USD",
            },
            "https://api.byul.ai/api/v1/economic-calendar/today",
        )
        self.assertEqual(calendar["type"], "calendar")
        self.assertTrue(any("actual=55.1" in fact for fact in calendar["numeric_facts"]))

        index = index_result_to_source(
            "vix",
            {
                "url": "https://api.byul.ai/api/v1/vix",
                "access_status": "ok",
                "data": {"success": True, "data": {"quote": 16.4, "volatility_level": "Normal"}},
            },
        )
        self.assertEqual(index["type"], "market_index")
        self.assertIn("quote=16.4", index["numeric_facts"])


if __name__ == "__main__":
    unittest.main()
