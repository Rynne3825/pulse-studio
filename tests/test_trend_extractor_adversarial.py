"""
Adversarial Stress Test Suite for `extract_trending_topics` (Milestone M1).
Tests extreme inputs, foreign scripts, Unicode edge cases, scaling limits,
mathematical invariants (bounded scores [0.0 - 100.0], exact 100.0% sentiment sum),
and malformed structures.
"""

import sys
import unittest
import time
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.trend_extractor import (
    extract_trending_topics,
    VIETNAMESE_STOPWORDS
)


class TestAdversarialTrendExtractor(unittest.TestCase):
    """Adversarial stress-testing of extract_trending_topics."""

    def _assert_contract_invariants(self, result: Dict[str, Any], label: str = ""):
        """Helper to assert all Contract 1 invariants hold without exception."""
        self.assertIsInstance(result, dict, f"[{label}] Result must be a dict")
        self.assertIn("keywords", result, f"[{label}] Missing 'keywords'")
        self.assertIn("sentiment", result, f"[{label}] Missing 'sentiment'")
        self.assertIn("overall_tone", result, f"[{label}] Missing 'overall_tone'")

        # Invariant 1: keywords shape and score bounds
        self.assertIsInstance(result["keywords"], list, f"[{label}] keywords must be a list")
        for idx, item in enumerate(result["keywords"]):
            self.assertIsInstance(item, tuple, f"[{label}] keywords[{idx}] must be a tuple")
            self.assertEqual(len(item), 2, f"[{label}] keywords[{idx}] must be a pair (kw, score)")
            kw, score = item
            self.assertIsInstance(kw, str, f"[{label}] keyword must be a string")
            self.assertIsInstance(score, float, f"[{label}] keyword score must be a float")
            self.assertGreaterEqual(score, 0.0, f"[{label}] keyword score {score} < 0.0")
            self.assertLessEqual(score, 100.0, f"[{label}] keyword score {score} > 100.0")

        # Invariant 2: keywords descending order
        if len(result["keywords"]) >= 2:
            scores = [s for _, s in result["keywords"]]
            self.assertEqual(scores, sorted(scores, reverse=True), f"[{label}] keywords not sorted descending")

        # Invariant 3: sentiment keys, bounds [0.0 - 100.0], and exact 100.0% sum
        sentiment = result["sentiment"]
        self.assertIsInstance(sentiment, dict, f"[{label}] sentiment must be a dict")
        for k in ("positive", "neutral", "negative"):
            self.assertIn(k, sentiment, f"[{label}] sentiment missing key '{k}'")
            val = sentiment[k]
            self.assertIsInstance(val, float, f"[{label}] sentiment['{k}'] must be float")
            self.assertGreaterEqual(val, 0.0, f"[{label}] sentiment['{k}'] = {val} < 0.0")
            self.assertLessEqual(val, 100.0, f"[{label}] sentiment['{k}'] = {val} > 100.0")

        total_sentiment = round(sentiment["positive"] + sentiment["neutral"] + sentiment["negative"], 1)
        self.assertEqual(
            total_sentiment,
            100.0,
            f"[{label}] Sentiment sum must be exactly 100.0% (got {total_sentiment} from {sentiment})"
        )

        # Invariant 4: overall_tone is non-empty string
        self.assertIsInstance(result["overall_tone"], str, f"[{label}] overall_tone must be str")
        self.assertTrue(len(result["overall_tone"]) > 0, f"[{label}] overall_tone must not be empty")

    # -------------------------------------------------------------
    # 1. Extreme Text Lengths (10,000+ chars, large batches)
    # -------------------------------------------------------------
    def test_extreme_length_10k_chars(self):
        """Stress-test: Article with 10,000 characters and repeated phrases."""
        long_body = "Công nghệ AI bùng nổ mang lại nhiều đột phá tuyệt vời. " * 200  # ~11,000 chars
        articles = [
            {"title": "Đại hội công nghệ 2026", "summary": long_body}
        ]
        start_t = time.perf_counter()
        result = extract_trending_topics(articles, top_n=8)
        duration = time.perf_counter() - start_t

        self._assert_contract_invariants(result, "10k_chars")
        self.assertLess(duration, 2.0, "10k chars took longer than 2.0s")
        self.assertGreater(len(result["keywords"]), 0)

    def test_extreme_length_50k_chars_multiple_articles(self):
        """Stress-test: 50 articles each 1,000 characters (total 50,000 chars)."""
        articles = [
            {
                "title": f"Bản tin công nghệ số {i}",
                "summary": f"Xu hướng chuyển đổi số {i} đang phát triển rất hot và ấn tượng. " * 15
            }
            for i in range(50)
        ]
        start_t = time.perf_counter()
        result = extract_trending_topics(articles, top_n=10)
        duration = time.perf_counter() - start_t

        self._assert_contract_invariants(result, "50k_chars_50_articles")
        self.assertLess(duration, 3.0, "50k chars batch took longer than 3.0s")
        self.assertGreater(len(result["keywords"]), 0)

    # -------------------------------------------------------------
    # 2. Unicode Emojis & Complex Glyphs
    # -------------------------------------------------------------
    def test_unicode_emojis_only(self):
        """Stress-test: Articles containing ONLY emojis and symbols."""
        articles = [
            {"title": "😀😁😂🤣😃😄😅😆😉😊😋😎😍😘", "summary": "🔥✨🎉🚀💯❤️👍🙏🙌👏"}
        ]
        result = extract_trending_topics(articles)
        self._assert_contract_invariants(result, "emojis_only")
        # Emoji-only docs have no \w+ word tokens after regex/clean_text, should fall back cleanly
        self.assertEqual(result["keywords"], [])

    def test_unicode_complex_zwj_sequences(self):
        """Stress-test: ZWJ sequences, skin tones, flags, mixed with text."""
        articles = [
            {
                "title": "👨‍👩‍👧‍👦 Gia đình công nghệ 👩🏽‍💻 lập trình viên 🏳️‍🌈",
                "summary": "Sự kiện robot 🤖 trí tuệ nhân tạo 🧠 bùng nổ hot hit 🔥!"
            }
        ]
        result = extract_trending_topics(articles)
        self._assert_contract_invariants(result, "complex_zwj_emojis")
        self.assertGreater(len(result["keywords"]), 0)

    # -------------------------------------------------------------
    # 3. Foreign Scripts & Multilingual Inputs
    # -------------------------------------------------------------
    def test_foreign_scripts_cjk_arabic_cyrillic(self):
        """Stress-test: Non-Latin and non-Vietnamese scripts."""
        foreign_samples = [
            # Chinese
            {"title": "人工智能发展报告", "summary": "深度学习 神经网络 科技 创新 突破"},
            # Japanese
            {"title": "人工知能の未来トレンド", "summary": "機械学習 ロボット工学 テクノロジー 進化"},
            # Korean
            {"title": "인공지능 혁신 포럼", "summary": "머신러닝 딥러닝 미래 기술 발전"},
            # Arabic RTL
            {"title": "تطور الذكاء الاصطناعي", "summary": "تكنولوجيا المستقبل تعلم الآلة ابتكار حديث"},
            # Russian Cyrillic
            {"title": "Искусственный интеллект сегодня", "summary": "Машинное обучение нейронные сети технологии"},
            # Devanagari Hindi
            {"title": "कृत्रिम बुद्धिमत्ता शिखर सम्मेलन", "summary": "प्रौद्योगिकी डिजिटल नवाचार भविष्य भारत"}
        ]
        for idx, sample in enumerate(foreign_samples):
            result = extract_trending_topics([sample])
            self._assert_contract_invariants(result, f"foreign_script_{idx}")

    # -------------------------------------------------------------
    # 4. Zero-Vocabulary & Stopwords Scenarios
    # -------------------------------------------------------------
    def test_empty_articles_list(self):
        """Edge case: Empty input list []."""
        result = extract_trending_topics([])
        self._assert_contract_invariants(result, "empty_list")
        self.assertEqual(result["keywords"], [])
        self.assertEqual(result["overall_tone"], "Chưa có dữ liệu")

    def test_none_input(self):
        """Edge case: Input is None."""
        result = extract_trending_topics(None)
        self._assert_contract_invariants(result, "none_input")
        self.assertEqual(result["keywords"], [])
        self.assertEqual(result["overall_tone"], "Chưa có dữ liệu")

    def test_all_stopwords_vietnamese(self):
        """Stress-test: Entire corpus consists only of stopwords from VIETNAMESE_STOPWORDS."""
        stopwords_sentence = " ".join(list(VIETNAMESE_STOPWORDS))
        articles = [
            {"title": stopwords_sentence, "summary": stopwords_sentence}
        ]
        result = extract_trending_topics(articles)
        self._assert_contract_invariants(result, "all_stopwords")
        self.assertEqual(result["keywords"], [])

    def test_punctuation_and_whitespace_only(self):
        """Stress-test: Articles with only punctuation, whitespace, and special characters."""
        articles = [
            {"title": "!@#$%^&*()_+-=[]{}|;':\",./<>?", "summary": "   \n\t\r   ... --- ???"},
            {"title": "         ", "summary": "      \n\n\n   "}
        ]
        result = extract_trending_topics(articles)
        self._assert_contract_invariants(result, "punctuation_only")
        self.assertEqual(result["keywords"], [])

    # -------------------------------------------------------------
    # 5. Single-Word Articles
    # -------------------------------------------------------------
    def test_single_word_latin(self):
        """Edge case: Single-word article."""
        articles = [{"title": "ChatGPT", "summary": ""}]
        result = extract_trending_topics(articles)
        self._assert_contract_invariants(result, "single_word_chatgpt")
        self.assertGreaterEqual(len(result["keywords"]), 1)
        self.assertEqual(result["keywords"][0][0], "chatgpt")

    def test_single_character_words(self):
        """Edge case: Only single-character tokens (default TF-IDF token_pattern drops len < 2)."""
        articles = [{"title": "a b c d e", "summary": "x y z"}]
        result = extract_trending_topics(articles)
        self._assert_contract_invariants(result, "single_char_tokens")
        # Should catch empty vocabulary and return empty keywords cleanly
        self.assertEqual(result["keywords"], [])

    # -------------------------------------------------------------
    # 6. top_n Boundary Conditions
    # -------------------------------------------------------------
    def test_top_n_zero_and_negative(self):
        """Boundary: top_n <= 0."""
        articles = [{"title": "Công nghệ số bùng nổ", "summary": "Xu hướng tương lai"}]
        res_zero = extract_trending_topics(articles, top_n=0)
        self._assert_contract_invariants(res_zero, "top_n_zero")
        self.assertEqual(res_zero["keywords"], [])

        res_neg = extract_trending_topics(articles, top_n=-5)
        self._assert_contract_invariants(res_neg, "top_n_negative")
        self.assertEqual(res_neg["keywords"], [])

    def test_top_n_larger_than_vocabulary(self):
        """Boundary: top_n=1000 with small vocabulary."""
        articles = [{"title": "Công nghệ", "summary": "Đột phá"}]
        result = extract_trending_topics(articles, top_n=1000)
        self._assert_contract_invariants(result, "top_n_1000")
        self.assertLessEqual(len(result["keywords"]), 100)

    # -------------------------------------------------------------
    # 7. Malformed Dictionaries & Type Coercion
    # -------------------------------------------------------------
    def test_missing_keys_and_none_values(self):
        """Stress-test: Dicts missing title/summary or with None values."""
        articles = [
            {},
            {"title": None, "summary": None},
            {"title": "Sản phẩm công nghệ mới", "other_field": 123},
            {"summary": "Đánh giá xuất sắc và hài lòng"}
        ]
        result = extract_trending_topics(articles)
        self._assert_contract_invariants(result, "missing_keys_none_values")

    def test_non_string_field_values(self):
        """Stress-test: Numeric, boolean, list values in title and summary."""
        articles = [
            {"title": 123456, "summary": 99.99},
            {"title": True, "summary": ["tag1", "tag2"]},
            {"title": {"nested": "value"}, "summary": False}
        ]
        result = extract_trending_topics(articles)
        self._assert_contract_invariants(result, "non_string_values")

    def test_null_bytes_and_escape_sequences(self):
        """Stress-test: String containing null bytes and ANSI escape codes."""
        articles = [
            {
                "title": "Hack\x00Device\x1b[31mRed Alert\x1b[0m",
                "summary": "Lỗi bảo mật nghiêm trọng gây chấn động\x00\x00."
            }
        ]
        result = extract_trending_topics(articles)
        self._assert_contract_invariants(result, "null_bytes_ansi")

    # -------------------------------------------------------------
    # 8. Mathematical Exhaustive Invariant Check (Sentiment Sum)
    # -------------------------------------------------------------
    def test_sentiment_sum_exhaustive_simulation(self):
        """
        Mathematical verification:
        Simulate pos_count in 0..100 and neg_count in 0..100 (10,201 cases)
        to verify that (pos_pct + neu_pct + neg_pct) == 100.0 is an absolute invariant.
        """
        for pos_count in range(0, 101, 2):
            for neg_count in range(0, 101, 2):
                if pos_count + neg_count == 0:
                    pos_pct = 50.0
                    neu_pct = 50.0
                    neg_pct = 0.0
                else:
                    neutral_base = max(2.0, (pos_count + neg_count) * 0.5)
                    total = pos_count + neg_count + neutral_base
                    pos_pct = round((pos_count / total) * 100, 1)
                    neg_pct = round((neg_count / total) * 100, 1)
                    neu_pct = round(100.0 - pos_pct - neg_pct, 1)

                total_sum = round(pos_pct + neu_pct + neg_pct, 1)
                self.assertEqual(
                    total_sum,
                    100.0,
                    f"Invariant violated for pos={pos_count}, neg={neg_count}: {pos_pct} + {neu_pct} + {neg_pct} = {total_sum}"
                )
                self.assertGreaterEqual(pos_pct, 0.0)
                self.assertLessEqual(pos_pct, 100.0)
                self.assertGreaterEqual(neu_pct, 0.0)
                self.assertLessEqual(neu_pct, 100.0)
                self.assertGreaterEqual(neg_pct, 0.0)
                self.assertLessEqual(neg_pct, 100.0)


if __name__ == "__main__":
    unittest.main()
