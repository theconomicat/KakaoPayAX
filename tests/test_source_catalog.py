import unittest

from tools.market_data_reader import _list_get
from tools.source_catalog import SourceCatalogParser, search_catalog


CATALOG_HTML = """
<h2>재무제표</h2>
<a href="https://finance.yahoo.com/">Yahoo Finance 재무제표 종합 데이터</a>
<a href="https://stockanalysis.com/">Stock Analysis 재무제표 시각화 및 분석</a>
<h2>옵션 플로우</h2>
<a href="https://unusualwhales.com/live-options-flow">Unusual Whales 옵션 플로우</a>
<h3>트위터</h3>
<a href="https://x.com/unusual_whales">@unusual_whales</a>
"""


class SourceCatalogTests(unittest.TestCase):
    def test_parses_categorized_source_links(self):
        parser = SourceCatalogParser("https://www.theconomicat.com/")
        parser.feed(CATALOG_HTML)
        self.assertEqual(len(parser.items), 4)
        self.assertEqual(parser.items[0].category, "재무제표")
        self.assertIn("Yahoo Finance", parser.items[0].name)

    def test_search_filters_category_and_social_links(self):
        parser = SourceCatalogParser("https://www.theconomicat.com/")
        parser.feed(CATALOG_HTML)
        selected = search_catalog(parser.items, query="unusual", category="옵션", include_social=False, limit=10)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].url, "https://unusualwhales.com/live-options-flow")

    def test_list_get_handles_missing_market_data_cells(self):
        self.assertEqual(_list_get([1, 2.5], 1), 2.5)
        self.assertIsNone(_list_get([1], 3))
        self.assertIsNone(_list_get(None, 0))


if __name__ == "__main__":
    unittest.main()
