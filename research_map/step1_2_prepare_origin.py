"""Step1 + Step2: 起点論文のテキスト貼り付け入力 と キーワード抽出。

使い方（リポジトリのルートディレクトリで実行すること。-m での実行が必須）:
    # ファイルから読み込む場合
    python -m research_map.step1_2_prepare_origin --file paper.txt \\
        --title "論文タイトル" --authors "著者A,著者B" --pub-date 2021

    # 標準入力に貼り付ける場合（貼り付け後、Windowsは Ctrl+Z→Enter、
    # Mac/LinuxはCtrl+D で入力終了）
    python -m research_map.step1_2_prepare_origin \\
        --title "論文タイトル" --authors "著者A" --pub-date 2021

出力:
    research_map/origin_paper.json に起点論文の情報とキーワードを保存する。
    このファイルをStep3（CiNii Research検索）が読み込んで使う想定。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

from research_map import text_extract

DEFAULT_OUT = Path(__file__).parent / "origin_paper.json"


def _parse_year(pub_date: Optional[str]) -> Optional[int]:
    if not pub_date:
        return None
    match = re.search(r"(19|20)\d{2}", pub_date)
    return int(match.group(0)) if match else None


def read_text(file_path: Optional[str]) -> str:
    if file_path:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {path}")
        return path.read_text(encoding="utf-8")

    print(
        "論文本文を貼り付けてください。貼り付け終わったら、"
        "Windowsは Ctrl+Z の後Enter、Mac/Linuxは Ctrl+D を押してください。",
        file=sys.stderr,
    )
    return sys.stdin.read()


def build_search_query(keywords: list[str], max_keywords: int = 3) -> str:
    """CiNii検索クエリの初期案を組み立てる。

    CiNii ResearchのOpenSearchはスペース区切りの語をAND検索するため、
    論文タイトル全文＋多数のキーワードを渡すと必須条件が増えすぎて
    ヒット件数がほぼ0（起点論文自身しか一致しない）になる。
    そのため、タイトル全文は含めず、キーワードも少数（デフォルト3件）に絞る。
    実際の検索（Step3）では、これでも件数が少ない場合にさらに語数を
    減らして自動的に再検索する。
    """
    terms = keywords[:max_keywords]
    return " ".join(dict.fromkeys(t for t in terms if t))


def main() -> None:
    parser = argparse.ArgumentParser(description="Step1+2: 起点論文の入力とキーワード抽出")
    parser.add_argument("--file", help="論文本文のテキストファイル（未指定なら標準入力から読む）")
    parser.add_argument("--title", required=True, help="論文タイトル")
    parser.add_argument("--authors", help="著者名（カンマ区切り）")
    parser.add_argument("--pub-date", help="出版日（例: 2021-04-01 / 2021）")
    parser.add_argument("--top-n", type=int, default=10, help="抽出するキーワード数")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="出力JSONのパス")
    args = parser.parse_args()

    fulltext = read_text(args.file)
    if not fulltext.strip():
        parser.error("論文本文が空です。--file を指定するか、標準入力に貼り付けてください。")

    keywords = text_extract.extract_keywords(fulltext, top_n=args.top_n)
    authors = [a.strip() for a in args.authors.split(",")] if args.authors else []

    origin = {
        "title": args.title,
        "authors": authors,
        "year": _parse_year(args.pub_date),
        "keywords": keywords,
        "search_query": build_search_query(keywords),
        "fulltext_text": fulltext,
        "fulltext_chars": len(fulltext),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(origin, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=== 起点論文の読み込み結果 ===")
    print(f"タイトル: {origin['title']}")
    print(f"著者: {', '.join(authors) if authors else '(未指定)'}")
    print(f"出版年: {origin['year']}")
    print(f"本文文字数: {origin['fulltext_chars']}")
    print(f"抽出キーワード: {keywords}")
    print(f"CiNii検索クエリ（案）: {origin['search_query']}")
    print()
    print(f"=> {out_path} に保存しました。次のStep3でこのファイルを使用します。")


if __name__ == "__main__":
    main()
