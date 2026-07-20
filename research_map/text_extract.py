"""貼り付けテキストからの簡易キーワード抽出。

外部の形態素解析器（MeCab等）に依存しない、軽量な頻度ベースの実装。
CiNii Research検索クエリ生成の補助が目的であり、厳密なNLPの代替ではない。
"""

from __future__ import annotations

import re

_STOPWORDS_EN = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was",
    "were", "have", "has", "not", "but", "can", "our", "which", "into",
    "using", "based", "study", "paper", "article", "results", "method",
    "methods", "abstract", "introduction", "conclusion", "figure", "table",
}
_STOPWORDS_JA = {
    "こと", "これ", "それ", "ため", "よう", "また", "および", "する",
    "した", "して", "ある", "いる", "です", "ます", "本論文", "本研究",
    "について", "における", "による", "とき", "場合", "それぞれ", "しかし",
    "そして", "および", "おいて", "による", "ながら", "という", "として",
}


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """簡易な頻度ベースのキーワード抽出。

    - 英単語（3文字以上）と日本語の連続漢字/カタカナ塊（2文字以上）をトークンとして扱う。
    - ストップワードを除外し、出現頻度順に上位N件を返す。
    """
    if not text:
        return []

    en_tokens = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text)
    ja_tokens = re.findall(r"[一-龥ァ-ヶー]{2,}", text)

    freq: dict[str, int] = {}
    for tok in en_tokens:
        low = tok.lower()
        if low in _STOPWORDS_EN:
            continue
        freq[low] = freq.get(low, 0) + 1
    for tok in ja_tokens:
        if tok in _STOPWORDS_JA:
            continue
        freq[tok] = freq.get(tok, 0) + 1

    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    return [word for word, _ in ranked[:top_n]]
