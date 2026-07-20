"""Step3: CiNii Research検索と結果のCSV化。

Step1/2で作成した origin_paper.json の検索クエリを使ってCiNii Researchを
検索し、書誌情報・識別子（DOI/NAID）・抄録・キーワード・関連リンクを
CSVに保存する。本文（PDF）の取得はここでは行わない（Step4で扱う）。

使い方（リポジトリのルートで実行、-m 必須）:
    python -m research_map.step3_search_cinii
    python -m research_map.step3_search_cinii --max-results 20
    python -m research_map.step3_search_cinii --query "カスタムクエリ"
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path

from research_map import cinii_client

DEFAULT_ORIGIN = Path(__file__).parent / "origin_paper.json"
DEFAULT_OUT = Path(__file__).parent / "related_papers.csv"

CSV_FIELDS = [
    "title", "authors", "year", "publication_date_raw", "journal", "publisher",
    "volume", "number", "start_page", "end_page", "doi", "naid", "crid_url",
    "ndl_links", "subject_keywords", "abstract_license_flag", "abstract",
]


def write_csv(records: list[dict], out_path: Path) -> None:
    # Excel（Windows）で開いても文字化けしないよう utf-8-sig（BOM付き）で保存する。
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["authors"] = "; ".join(record.get("authors") or [])
            row["ndl_links"] = "; ".join(record.get("ndl_links") or [])
            row["subject_keywords"] = "; ".join(record.get("subject_keywords") or [])
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Step3: CiNii Research検索とCSV化")
    parser.add_argument("--origin", default=str(DEFAULT_ORIGIN), help="Step1/2で作成したorigin_paper.jsonのパス")
    parser.add_argument("--query", help="検索クエリを直接指定（未指定ならorigin_paper.jsonのsearch_queryを使用）")
    parser.add_argument("--max-results", type=int, default=30)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    origin_path = Path(args.origin)
    if not origin_path.exists():
        parser.error(f"{origin_path} が見つかりません。先にStep1/2（step1_2_prepare_origin.py）を実行してください。")
    origin = json.loads(origin_path.read_text(encoding="utf-8"))

    query = args.query or origin.get("search_query")
    if not query:
        parser.error("検索クエリが決定できませんでした。--query を指定してください。")

    print(f"検索クエリ: {query}")
    records = cinii_client.search_articles(query, max_results=args.max_results)
    print(f"取得件数（起点論文を除く前）: {len(records)}")

    origin_title = (origin.get("title") or "").strip().lower()
    records = [r for r in records if r["title"].strip().lower() != origin_title]
    print(f"起点論文と同名のものを除外後: {len(records)}件")

    out_path = Path(args.out)
    write_csv(records, out_path)
    print(f"=> {out_path} に保存しました。")

    doi_count = sum(1 for r in records if r.get("doi"))
    print(f"うちDOIが取得できたもの: {doi_count}件（Step4での本文所在調査に使えます）")


if __name__ == "__main__":
    main()
