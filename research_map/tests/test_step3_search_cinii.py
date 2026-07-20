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


if __name__ == "__main__":
    unittest.main()
