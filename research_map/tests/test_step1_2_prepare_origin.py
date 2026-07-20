import json
import tempfile
import unittest
from pathlib import Path

from research_map.step1_2_prepare_origin import build_search_query, main


class TestBuildSearchQuery(unittest.TestCase):
    def test_uses_top_keywords_without_title(self):
        query = build_search_query(["CNN", "画像分類", "深層学習", "転移学習"], max_keywords=3)
        self.assertEqual(query, "CNN 画像分類 深層学習")

    def test_deduplicates_keywords(self):
        query = build_search_query(["CNN", "CNN", "画像分類"])
        self.assertEqual(query.split().count("CNN"), 1)


class TestMainEndToEnd(unittest.TestCase):
    def test_main_writes_origin_json_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            text_path = Path(tmp) / "paper.txt"
            text_path.write_text(
                "転移学習を用いた画像分類の研究。畳み込みニューラルネットワークを用いる。",
                encoding="utf-8",
            )
            out_path = Path(tmp) / "origin.json"

            import sys

            argv = sys.argv
            sys.argv = [
                "step1_2_prepare_origin.py",
                "--file", str(text_path),
                "--title", "テストタイトル",
                "--authors", "著者A,著者B",
                "--pub-date", "2020-01-01",
                "--out", str(out_path),
            ]
            try:
                main()
            finally:
                sys.argv = argv

            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["title"], "テストタイトル")
            self.assertEqual(data["authors"], ["著者A", "著者B"])
            self.assertEqual(data["year"], 2020)
            self.assertIn("転移学習", data["keywords"])
            self.assertIn("転移学習", data["search_query"])
            self.assertNotIn("テストタイトル", data["search_query"])


if __name__ == "__main__":
    unittest.main()
