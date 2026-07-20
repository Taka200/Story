import json
import unittest
from pathlib import Path
from unittest import mock

from research_map import cinii_client

FIXTURE = Path(__file__).parent.parent / "fixtures" / "cinii_response_sample.json"


class TestNormalizeRecord(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.items = self.data["items"]

    def test_normalize_basic_fields(self):
        rec = cinii_client.normalize_record(self.items[0])
        self.assertEqual(rec["title"], "「権記」所載の一条院出離歌について")
        self.assertEqual(rec["authors"], ["山本 淳子"])
        self.assertEqual(rec["year"], 2006)
        self.assertEqual(rec["journal"], "日本文学")
        self.assertEqual(rec["doi"], "10.20620/nihonbungaku.55.9_35")
        self.assertEqual(rec["abstract_license_flag"], "disallow")

    def test_normalize_extracts_subject_keywords(self):
        rec = cinii_client.normalize_record(self.items[1])
        self.assertIn("深層学習", rec["subject_keywords"])
        self.assertIn("convolutional neural network", rec["subject_keywords"])

    def test_normalize_year_from_month_precision_date(self):
        rec = cinii_client.normalize_record(self.items[1])
        self.assertEqual(rec["publication_date_raw"], "2024-12")
        self.assertEqual(rec["year"], 2024)

    def test_normalize_missing_title_returns_none(self):
        self.assertIsNone(cinii_client.normalize_record({"dc:creator": ["誰か"]}))

    def test_normalize_ndl_links_deduplicated(self):
        rec = cinii_client.normalize_record(self.items[2])
        self.assertIn("https://dl.ndl.go.jp/pid/11700556", rec["ndl_links"])
        self.assertEqual(len(rec["ndl_links"]), len(set(rec["ndl_links"])))

    def test_all_fixture_items_parse(self):
        records = [cinii_client.normalize_record(it) for it in self.items]
        self.assertTrue(all(r is not None for r in records))
        self.assertEqual(len(records), 3)


class TestSearchArticles(unittest.TestCase):
    def test_search_articles_paginates_and_normalizes(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))

        with mock.patch.object(cinii_client, "_fetch_json", return_value=data) as fetch_mock, \
             mock.patch("time.sleep", return_value=None):
            records = cinii_client.search_articles("画像分類", max_results=3, page_size=20)

        self.assertEqual(len(records), 3)
        fetch_mock.assert_called_once()

    def test_search_articles_stops_on_empty_response(self):
        with mock.patch.object(cinii_client, "_fetch_json", return_value=None):
            records = cinii_client.search_articles("何かのクエリ", max_results=5)
        self.assertEqual(records, [])


if __name__ == "__main__":
    unittest.main()
