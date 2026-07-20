"""CiNii Research API の疎通確認・レスポンス形式確認用の最小スクリプト。

このリポジトリを開発しているサンドボックス環境からはCiNii Research
(cir.nii.ac.jp) への接続がブロックされているため、実際のAPIレスポンス
形式を確認できていない。このスクリプトをネットワーク接続可能な環境
（あなたのPCなど）で実行し、出力されたJSON/レスポンスの中身を教えて
もらうことで、本実装（検索クライアント）のパース処理を実データに
合わせて設計する。

標準ライブラリのみで動作する（requestsのインストール不要）。

使い方:
    python research_map/probe_cinii.py "検索したいキーワード"

出力:
    - コンソールにHTTPステータス・Content-Type・レスポンス冒頭を表示
    - research_map/cinii_probe_result.json に完全なレスポンスを保存
      （このファイルの中身をそのまま貼り付けて共有してください）
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://cir.nii.ac.jp/opensearch/articles"
USER_AGENT = "research-map-pipeline-probe/0.1 (+https://github.com/taka200/story)"


def fetch(query: str, fmt: str) -> tuple[int, str, bytes]:
    params = {"q": query, "format": fmt, "count": "5"}
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            return resp.status, resp.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as e:
        body = e.read()
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", body
    except urllib.error.URLError as e:
        print(f"接続エラー: {e}")
        sys.exit(1)


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "画像分類"
    print(f"クエリ: {query!r}")
    print(f"エンドポイント: {ENDPOINT}")
    print()

    for fmt in ("json", "rss"):
        print(f"--- format={fmt} で試行 ---")
        status, content_type, body = fetch(query, fmt)
        print(f"HTTP status: {status}")
        print(f"Content-Type: {content_type}")
        print(f"body length: {len(body)} bytes")
        preview = body[:1000].decode("utf-8", errors="replace")
        print("body先頭1000文字:")
        print(preview)
        print()

        if status == 200 and fmt == "json":
            out_path = Path(__file__).parent / "cinii_probe_result.json"
            try:
                parsed = json.loads(body)
                out_path.write_text(
                    json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"=> JSONとして解析成功。整形して保存しました: {out_path}")
            except json.JSONDecodeError:
                out_path = out_path.with_suffix(".raw.txt")
                out_path.write_bytes(body)
                print(f"=> JSONとして解析できなかったため、生のレスポンスを保存しました: {out_path}")
            print()


if __name__ == "__main__":
    main()
