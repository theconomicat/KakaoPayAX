from pathlib import Path
import tempfile
import unittest

from tools.public_page_reader import _public_url_variants, read_public_page


class PublicPageReaderTest(unittest.TestCase):
    def test_local_html_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "sample.html"
            page.write_text(
                "<html><head><title>Sample Source</title></head>"
                "<body><article>" + ("public source text " * 30) + "</article></body></html>",
                encoding="utf-8",
            )
            result = read_public_page(str(page))
        self.assertEqual(result["access_status"], "ok")
        self.assertEqual(result["title"], "Sample Source")
        self.assertGreater(result["text_length"], 200)
        self.assertEqual(result["retrieval_method"], "local_file")
        self.assertTrue(result["trace"])

    def test_public_url_variants_include_no_key_public_routes(self):
        variants = dict(_public_url_variants("https://www.example.com/articles/item"))
        self.assertEqual(variants["original"], "https://www.example.com/articles/item")
        self.assertEqual(variants["mobile_subdomain"], "https://m.example.com/articles/item")
        self.assertEqual(variants["rss"], "https://www.example.com/articles/item/rss")
        self.assertEqual(variants["feed"], "https://www.example.com/articles/item/feed")
        self.assertEqual(variants["json_suffix"], "https://www.example.com/articles/item.json")
        self.assertEqual(variants["jina_reader"], "https://r.jina.ai/https://www.example.com/articles/item")


if __name__ == "__main__":
    unittest.main()
