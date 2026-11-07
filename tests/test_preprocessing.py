"""
Unit tests for preprocessing and feature extraction modules.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.text_cleaner import clean_text, extract_hashtags, extract_punctuation_counts
from src.preprocessing.feature_extractor import parse_vietnam_time, compute_sentiment, extract_features_from_post


def test_text_cleaner():
    raw_text = "Tin hot hôm nay! Xem tại https://example.com/item #CongNghe  #AI???"
    cleaned = clean_text(raw_text)
    assert "https://" not in cleaned, "URL was not stripped."
    assert "#CongNghe" in cleaned, "Hashtag should be preserved."
    
    tags = extract_hashtags(cleaned)
    assert "#CongNghe" in tags and "#AI" in tags, "Failed to extract hashtags."
    
    punct = extract_punctuation_counts(cleaned)
    assert punct["question_count"] == 3, f"Expected 3 question marks, got {punct['question_count']}"
    assert punct["exclamation_count"] == 1, f"Expected 1 exclamation mark, got {punct['exclamation_count']}"
    print("test_text_cleaner: PASSED")


def test_feature_extractor():
    content = "Chiếc điện thoại này thực sự quá tuyệt vời và đỉnh chóp! Có nên mua không các bác? #Review"
    published_utc = "2026-10-25T04:30:00.000Z"  # 04:30 UTC = 11:30 Vietnam (Peak lunch hour)
    
    feat = extract_features_from_post(
        content=content,
        published_at=published_utc,
        topic_category=1,
        thumbnail_url="https://example.com/photo.jpg"
    )
    
    assert feat["hour"] == 11, f"Expected hour 11, got {feat['hour']}"
    assert feat["is_peak_hour"] == 1, "11h should be recognized as peak hour."
    assert feat["has_thumbnail"] == 1, "Thumbnail presence should be 1."
    assert feat["pos_word_count"] >= 2, "Expected positive words detected."
    assert feat["sentiment_score"] > 0, "Sentiment score should be positive."
    assert feat["topic_category"] == 1, "Topic category should match input."
    print("test_feature_extractor: PASSED")


if __name__ == "__main__":
    test_text_cleaner()
    test_feature_extractor()
    print("ALL TESTS PASSED SUCCESSFULLY.")
