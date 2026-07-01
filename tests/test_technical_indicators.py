import unittest

from tools.technical_indicators import read_prices_csv, summarize_prices


class TechnicalIndicatorsTest(unittest.TestCase):
    def test_summary_has_core_indicators_without_recommendations(self):
        prices = read_prices_csv("examples/sample_prices.csv")
        summary = summarize_prices(prices)
        self.assertEqual(summary["observations"], 30)
        self.assertIsNotNone(summary["sma_5"])
        self.assertIsNotNone(summary["sma_20"])
        self.assertIsNotNone(summary["rsi_14"])
        combined = " ".join(summary["interpretation"]).lower()
        self.assertNotIn("buy", combined)
        self.assertNotIn("sell", combined)


if __name__ == "__main__":
    unittest.main()

