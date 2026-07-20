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


def extract_keywords(text: str, title: str = "", top_n: int = 10) -> list[str]:
    """簡易な頻度ベースのキーワード抽出。

    - 英単語（3文字以上）と日本語の連続漢字/カタカナ塊（2文字以上）をトークンとして扱う。
    - ストップワードを除外し、出現頻度順にランキングする。
    - titleを指定すると、本文から抽出したキーワードのうちタイトル文字列に
      部分一致するもの（＝論文の主題を最も端的に表す語である可能性が高い）を、
      頻度に関わらず優先的に上位へ並べ替える。

      タイトル自体を別途分かち書きしない理由: 日本語のタイトルは名詞が
      密集し助詞による区切りが少ないため、単純な正規表現分割では
      「一条院出離歌」のような長い塊になりやすく、検索語として使いにくい。
      本文側は文章中の助詞のおかげで自然に短い語へ分割されるため、
      その結果に対してタイトルとの部分一致でフィルタする方が実用的。
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
    ranked_words = [word for word, _ in ranked]

    if title:
        in_title = [w for w in ranked_words if w.lower() in title.lower()]
        not_in_title = [w for w in ranked_words if w not in in_title]
        ranked_words = in_title + not_in_title

    return ranked_words[:top_n]
