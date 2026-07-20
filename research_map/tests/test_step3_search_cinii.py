import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from research_map import cinii_client, step3_search_cinii

FIXTURE = Path(__file__).parent.parent / "fixtures" / "cinii_response_sample.json"


class TestStep3EndToEnd(unittest.TestCase):
    def test_main_writes_csv_excluding_origin_paper(self):
        fixture_data = json.loads(FIXTURE.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as tmp:
            origin_path = Path(tmp) / "origin_paper.json"
            origin_path.write_text(
                json.dumps({
                    "title": "「権記」所載の一条院出離歌について",
                    "keywords": ["権記", "一条", "皇后", "定子"],
                    "search_query": "権記 一条 皇后",
                }, ensure_ascii=False),
                encoding="utf-8",
            )
            out_path = Path(tmp) / "related_papers.csv"

            argv = sys.argv
            sys.argv = [
                "step3_search_cinii.py",
                "--origin", str(origin_path),
                "--out", str(out_path),
                "--max-results", "3",
                "--min-results", "1",
            ]
            try:
                with mock.patch.object(cinii_client, "_fetch_json", return_value=fixture_data), \
                     mock.patch("time.sleep", return_value=None):
                    step3_search_cinii.main()
            finally:
                sys.argv = argv

            self.assertTrue(out_path.exists())
            with out_path.open(encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))

            # フィクスチャ3件のうち起点論文と同名の1件は除外され、2件になるはず
            self.assertEqual(len(rows), 2)
            titles = [r["title"] for r in rows]
            self.assertNotIn("「権記」所載の一条院出離歌について", titles)
            self.assertIn("深層学習を用いたクラウド型画像分類システムの開発", titles)

            row = next(r for r in rows if "クラウド型" in r["title"])
            self.assertIn("深層学習", row["subject_keywords"])
            self.assertIn(";", row["subject_keywords"])  # 複数キーワードがセミコロン区切り


class TestBuildQueryCandidates(unittest.TestCase):
    def test_candidates_go_from_specific_to_broad(self):
        candidates = step3_search_cinii.build_query_candidates(["権記", "一条", "皇后", "定子"])
        self.assertEqual(
            candidates,
            ["権記 一条 皇后 定子", "権記 一条 皇后", "権記 一条", "権記"],
        )

    def test_fewer_keywords_than_max_tier(self):
        candidates = step3_search_cinii.build_query_candidates(["権記", "一条"])
        self.assertEqual(candidates, ["権記 一条", "権記"])

    def test_empty_keywords_returns_no_candidates(self):
        self.assertEqual(step3_search_cinii.build_query_candidates([]), [])


class TestSearchWithFallback(unittest.TestCase):
    def test_broadens_query_when_too_few_results(self):
        """narrow(4語)クエリはヒットが少なく、より広いクエリで補完される想定を再現する。"""
        narrow_result = [{"title": "起点論文自身", "authors": [], "subject_keywords": [], "ndl_links": []}]
        broad_result = narrow_result + [
            {"title": f"関連論文{i}", "authors": [], "subject_keywords": [], "ndl_links": []}
            for i in range(5)
        ]

        def fake_search_articles(query, max_results, **kwargs):
            # 語数が多い（具体的な）クエリほど結果が少ない、という実際に観測した挙動を再現
            return narrow_result if query.count(" ") >= 2 else broad_result

        with mock.patch.object(cinii_client, "search_articles", side_effect=fake_search_articles):
            records, summary = step3_search_cinii.search_with_fallback(
                ["権記", "一条", "皇后", "定子"], max_results=10, min_results=3
            )

        titles = [r["title"] for r in records]
        self.assertIn("関連論文0", titles)
        self.assertIn("=>", summary)

    def test_no_keywords_returns_empty(self):
        records, summary = step3_search_cinii.search_with_fallback([], max_results=10)
        self.assertEqual(records, [])


if __name__ == "__main__":
    unittest.main()
