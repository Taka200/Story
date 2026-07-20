"""パイプライン内で受け渡しするデータ構造。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PaperRecord:
    """1本の論文を表すレコード（起点論文・関連論文の両方に使う想定）。"""

    title: str
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)

    # "origin"（入力論文） or "related"（CiNiiで見つかった関連論文）
    source: str = "related"

    fulltext_text: str = ""

    def display_authors(self) -> str:
        return ", ".join(self.authors) if self.authors else "(著者不明)"
