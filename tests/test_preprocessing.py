"""Unit tests for Vietnamese text normalization and NLP trend preprocessing."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.nlp.trends import clean_text, extract_trending_topics


def test_text_cleaner():
    raw_text = "Tin hot hôm nay! Xem tại https://example.com/item #CongNghe  #AI???"
    cleaned = clean_text(raw_text)
    assert "https://" not in cleaned
    assert "#CongNghe" in cleaned
    assert "#AI???" in cleaned
    assert clean_text(None) == ""  # type: ignore[arg-type]


def test_trend_extractor_positive_and_keywords():
    articles = [
        {
            "title": "Trí tuệ nhân tạo đột phá tuyệt vời trong lĩnh vực công nghệ Việt Nam",
            "summary": "Xu hướng trí tuệ nhân tạo đang mang lại thành công ấn tượng và hào hứng cho doanh nghiệp.",
        }
    ]
    res = extract_trending_topics(articles, top_n=5)
    assert res["keywords"]
    assert res["sentiment"]["positive"] > res["sentiment"]["negative"]
    assert round(sum(res["sentiment"].values()), 1) == 100.0
