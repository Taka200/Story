"""Step3: CiNii Research検索と結果のCSV化。

Step1/2で作成した origin_paper.json のキーワードを使ってCiNii Researchを
検索し、書誌情報・識別子（DOI/NAID）・抄録・キーワード・関連リンクを
CSVに保存する。本文（PDF）の取得はここでは行わない（Step4で扱う）。

CiNii ResearchのOpenSearchはスペース区切りの語をAND検索するため、
キーワードを詰め込みすぎると条件が厳しくなり、起点論文自身しか
ヒットしなくなることがある（実際に確認済み）。そのため、まずキーワード
上位3件で検索し、結果が少なければ自動的にキーワード数を減らして
再検索・結果をマージする。

使い方（リポジトリのルートで実行、-m 必須）:
    python -m research_map.step3_search_cinii
    python -m research_map.step3_search_cinii --max-results 20
    python -m research_map.step3_search_cinii --query "カスタムクエリ"  # 自動フォールバックなし
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
DEFAULT_MIN_RESULTS = 5

CSV_FIELDS = [
    "title", "authors", "year", "publication_date_raw", "journal", "publisher",
    "volume", "number", "start_page", "end_page", "doi", "naid", "crid_url",
    "ndl_links", "subject_keywords", "abstract_license_flag", "abstract",
]


def build_query_candidates(keywords: list[str]) -> list[str]:
    """キーワード数を段階的に減らした検索クエリ候補を、具体的なものから順に返す。"""
    candidates: list[str] = []
    for n in (4, 3, 2, 1):
        if len(keywords) >= n:
            query = " ".join(keywords[:n])
            if query not in candidates:
                candidates.append(query)
    return candidates


def search_with_fallback(
    keywords: list[str], max_results: int, min_results: int = DEFAULT_MIN_RESULTS
) -> tuple[list[dict], str]:
    """結果が少ない場合、キーワード数を減らして自動的に再検索・マージする。

    Returns:
        (レコードのリスト, 最終的に採用したクエリの説明文字列)
    """
    candidates = build_query_candidates(keywords)
    if not candidates:
        return [], "(キーワードが空のため検索できませんでした)"

    seen_titles: set[str] = set()
    merged: list[dict] = []
    tried_summary: list[str] = []

    for query in candidates:
        records = cinii_client.search_articles(query, max_results=max_results)
        new_records = [r for r in records if r["title"].strip().lower() not in seen_titles]
        for r in new_records:
            seen_titles.add(r["title"].strip().lower())
        merged.extend(new_records)
        tried_summary.append(f"「{query}」=> {len(records)}件（新規{len(new_records)}件）")

        if len(merged) >= min_results or len(merged) >= max_results:
            break

    summary = " / ".join(tried_summary)
    return merged[:max_results], summary


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
    parser.add_argument(
        "--query", help="検索クエリを直接指定（指定すると自動フォールバックは行わず、このクエリのみで検索）"
    )
    parser.add_argument("--max-results", type=int, default=30)
    parser.add_argument(
        "--min-results", type=int, default=DEFAULT_MIN_RESULTS,
        help="この件数に満たない場合、キーワード数を減らして自動的に再検索する",
    )
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

    if args.query:
        print(f"検索クエリ（手動指定・フォールバックなし）: {args.query}")
        records = cinii_client.search_articles(args.query, max_results=args.max_results)
    else:
        keywords = origin.get("keywords") or []
        if not keywords:
            parser.error("origin_paper.jsonにキーワードがありません。--query を指定してください。")
        records, summary = search_with_fallback(
            keywords, max_results=args.max_results, min_results=args.min_results
        )
        print(f"検索の試行内訳: {summary}")

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
