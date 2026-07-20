import unittest

from research_map import text_extract

SAMPLE_TEXT = """
深層学習を用いた画像分類における転移学習の有効性に関する研究

要旨
本研究では、畳み込みニューラルネットワーク（CNN）を用いた画像分類タスクにおいて、
転移学習が少量データ環境下での分類精度に与える影響を検証する。事前学習済みモデルを
ベースとしたファインチューニング手法を提案し、従来のスクラッチ学習と比較した。
実験の結果、転移学習を用いた手法は少量データにおいても高い分類精度を達成することが
確認された。
"""


class TestExtractKeywords(unittest.TestCase):
    def test_extracts_meaningful_terms(self):
        keywords = text_extract.extract_keywords(SAMPLE_TEXT, top_n=10)
        self.assertIn("転移学習", keywords)

    def test_excludes_stopwords(self):
        keywords = text_extract.extract_keywords(SAMPLE_TEXT, top_n=20)
        for stopword in ("こと", "ため", "について", "study", "based"):
            self.assertNotIn(stopword, keywords)

    def test_empty_text_returns_empty_list(self):
        self.assertEqual(text_extract.extract_keywords(""), [])

    def test_top_n_limits_result_count(self):
        keywords = text_extract.extract_keywords(SAMPLE_TEXT, top_n=3)
        self.assertLessEqual(len(keywords), 3)


if __name__ == "__main__":
    unittest.main()
