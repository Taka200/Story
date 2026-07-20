"""CiNii Research OpenSearch API クライアント。

2026-07-20にPC環境で実際にAPIへ接続し確認したレスポンス形式に基づく
（サンドボックス環境からはCiNiiへ接続できないため、このモジュールの
ネットワーク部分はPC環境でのテストで検証すること）。

確認できたレスポンス構造の要点:
    {
      "opensearch:totalResults": 131,
      "items": [
        {
          "@id": "https://cir.nii.ac.jp/crid/...",
          "title": "...",
          "dc:creator": ["著者名", ...],
          "prism:publicationName": "誌名",
          "prism:publicationDate": "2019-04" or "2006",
          "description": "抄録...",            # 無い場合もある
          "abstractLicenseFlag": "disallow",   # 抄録の再配布可否。無い場合もある
          "dc:identifier": [{"@type": "cir:DOI", "@value": "..."}, ...],
          "dc:source": [{"@id": "..."}, ...],
          "dc:subject": ["キーワード", ...],    # 無い場合もある
        },
        ...
      ]
    }

注意: このAPIレスポンスには本文（OA PDF等）への直接リンクは含まれて
いない。含まれるのはNDL（国立国会図書館）の書誌・検索ページへのリンクと、
DOIなどの識別子のみ。本文の所在確認はDOI解決など別の手段が必要。
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

ENDPOINT = "https://cir.nii.ac.jp/opensearch/articles"
USER_AGENT = "research-map-pipeline/0.2 (+https://github.com/taka200/story)"
REQUEST_INTERVAL_SEC = 1.0
REQUEST_TIMEOUT_SEC = 20


def _fetch_json(query: str, count: int, start: int, timeout: int = REQUEST_TIMEOUT_SEC) -> Optional[dict]:
    params = {"q": query, "format": "json", "count": count, "start": start}
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.URLError as exc:
        logger.warning("CiNii APIリクエスト失敗: %s", exc)
        return None

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        logger.warning("CiNii APIレスポンスをJSONとして解析できませんでした")
        return None


def _extract_identifiers(item: dict) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"doi": [], "naid": [], "uri": [], "ndl_bib_id": []}
    for ident in item.get("dc:identifier") or []:
        if not isinstance(ident, dict):
            continue
        type_ = (ident.get("@type") or "").lower()
        value = ident.get("@value")
        if not value:
            continue
        if "doi" in type_:
            result["doi"].append(value)
        elif "naid" in type_:
            result["naid"].append(value)
        elif "ndl_bib_id" in type_:
            result["ndl_bib_id"].append(value)
        elif "uri" in type_:
            result["uri"].append(value)
    return result


def _extract_year(publication_date: Optional[str]) -> Optional[int]:
    if not publication_date:
        return None
    match = re.search(r"(19|20)\d{2}", publication_date)
    return int(match.group(0)) if match else None


def normalize_record(item: dict) -> Optional[dict]:
    """CiNii Research APIの1レコードを、扱いやすいdictに変換する。タイトルが無ければNone。"""
    title = item.get("title")
    if not title:
        return None

    identifiers = _extract_identifiers(item)
    source_links = [
        s.get("@id") for s in (item.get("dc:source") or [])
        if isinstance(s, dict) and s.get("@id")
    ]
    ndl_links = list(dict.fromkeys(identifiers["uri"] + source_links))

    return {
        "title": title,
        "authors": item.get("dc:creator") or [],
        "publication_date_raw": item.get("prism:publicationDate"),
        "year": _extract_year(item.get("prism:publicationDate")),
        "journal": item.get("prism:publicationName"),
        "publisher": item.get("dc:publisher"),
        "volume": item.get("prism:volume"),
        "number": item.get("prism:number"),
        "start_page": item.get("prism:startingPage"),
        "end_page": item.get("prism:endingPage"),
        "abstract": item.get("description") or "",
        "abstract_license_flag": item.get("abstractLicenseFlag"),
        "subject_keywords": item.get("dc:subject") or [],
        "crid_url": item.get("@id"),
        "doi": identifiers["doi"][0] if identifiers["doi"] else None,
        "naid": identifiers["naid"][0] if identifiers["naid"] else None,
        "ndl_links": ndl_links,
    }


def search_articles(
    query: str,
    max_results: int = 30,
    page_size: int = 20,
    request_interval: float = REQUEST_INTERVAL_SEC,
) -> list[dict]:
    """CiNii Researchをキーワード検索し、正規化済みレコードのリストを返す。"""
    records: list[dict] = []
    start = 1
    total_results: Optional[int] = None

    while len(records) < max_results:
        count = min(page_size, max_results - len(records))
        data = _fetch_json(query, count=count, start=start)
        if not data:
            break

        if total_results is None:
            total_results = data.get("opensearch:totalResults")
            logger.info("CiNii Research 総件数: %s", total_results)

        items = data.get("items") or []
        if not items:
            break

        for item in items:
            record = normalize_record(item)
            if record:
                records.append(record)

        start += len(items)
        if total_results is not None and start > total_results:
            break
        time.sleep(request_interval)

    return records
