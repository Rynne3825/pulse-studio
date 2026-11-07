"""
Module trích xuất từ khóa xu hướng và phân tích sắc thái cảm xúc tổng thể (M1).
Sử dụng TF-IDF N-grams (1, 2) và bộ từ vựng sắc thái tiếng Việt.
Tuân thủ Hợp đồng Giao diện Contract 1 trong PROJECT.md.
"""

import re
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from src.preprocessing.text_cleaner import clean_text
from src.preprocessing.feature_extractor import POSITIVE_WORDS, NEGATIVE_WORDS

# Danh sách từ dừng tiếng Việt thông dụng (42 từ phổ biến, >= 25 từ theo yêu cầu)
VIETNAMESE_STOPWORDS = {
    # Quan hệ từ & liên từ
    "và", "của", "cho", "với", "trong", "tại", "từ", "đến", "về", "như", "theo",
    "sau", "khi", "do", "bởi", "vì", "để", "mà", "thì", "hay", "cùng", "qua",
    # Đại từ & từ chỉ định
    "này", "đây", "đó", "kia", "người", "các", "những", "mỗi", "mọi", "việc",
    # Phó từ & trợ từ
    "đã", "đang", "sẽ", "lại", "ra", "vào", "lên", "ở", "cũng", "được", "bị", "có", "là", "nhiều"
}


def extract_trending_topics(articles: List[Dict[str, Any]], top_n: int = 8) -> Dict[str, Any]:
    """
    Trích xuất top từ khóa thịnh hành bằng TF-IDF N-grams (1, 2) và phân tích sắc thái cảm xúc.

    Tham số:
    - articles: Danh sách bài báo từ scraper (chứa 'title' và 'summary')
    - top_n: Số lượng từ khóa thịnh hành cần lấy (mặc định 8)

    Trả về:
    - Dict chứa:
        + 'keywords': Danh sách Tuple[từ khóa, điểm độ nóng %]
        + 'sentiment': Dict tỷ lệ {'positive': float, 'neutral': float, 'negative': float} (tổng = 100.0)
        + 'overall_tone': Tông giọng chung của chuyên mục
    """
    # 1. Kiểm tra danh sách bài báo rỗng
    if not articles:
        return {
            "keywords": [],
            "sentiment": {"positive": 50.0, "neutral": 50.0, "negative": 0.0},
            "overall_tone": "Chưa có dữ liệu"
        }

    # 2. Tiền xử lý và chuẩn hóa văn bản
    docs: List[str] = []
    combined_texts: List[str] = []
    for a in articles:
        title = clean_text(str(a.get("title", "") or ""))
        summary = clean_text(str(a.get("summary", "") or ""))
        full_doc = f"{title} {summary}".strip()
        # Chỉ nhận tài liệu có chứa ký tự chữ/số thực tế
        if full_doc and re.search(r"\w+", full_doc):
            docs.append(full_doc)
            combined_texts.append(full_doc)

    # Nếu không có bài báo nào chứa nội dung hợp lệ
    if not docs:
        return {
            "keywords": [],
            "sentiment": {"positive": 50.0, "neutral": 50.0, "negative": 0.0},
            "overall_tone": "Chưa có dữ liệu"
        }

    # 3. Trích xuất từ khóa xu hướng bằng TF-IDF N-grams (1, 2)
    keywords: List[Tuple[str, float]] = []
    try:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words=list(VIETNAMESE_STOPWORDS),
            max_features=100
        )
        tfidf_matrix = vectorizer.fit_transform(docs)
        mean_scores = np.asarray(tfidf_matrix.mean(axis=0)).ravel()
        feature_names = vectorizer.get_feature_names_out()

        limit = min(top_n, len(feature_names))
        if limit > 0:
            top_indices = mean_scores.argsort()[::-1][:limit]
            keywords = [
                (str(feature_names[i]), round(float(mean_scores[i]) * 100, 1))
                for i in top_indices
            ]
    except ValueError:
        # Bắt trường hợp ngoại lệ empty vocabulary (văn bản chỉ toàn stop words)
        keywords = []

    # 4. Phân tích sắc thái cảm xúc (Sentiment Polarity)
    corpus_lower = " ".join(combined_texts).lower()
    pos_count = sum(corpus_lower.count(w) for w in POSITIVE_WORDS)
    neg_count = sum(corpus_lower.count(w) for w in NEGATIVE_WORDS)

    if pos_count + neg_count == 0:
        sentiment = {"positive": 50.0, "neutral": 50.0, "negative": 0.0}
        overall_tone = "Sôi động / Thu hút tương tác cao"
    else:
        neutral_base = max(2.0, (pos_count + neg_count) * 0.5)
        total = pos_count + neg_count + neutral_base
        pos_pct = round((pos_count / total) * 100, 1)
        neg_pct = round((neg_count / total) * 100, 1)
        neu_pct = round(100.0 - pos_pct - neg_pct, 1)
        sentiment = {
            "positive": pos_pct,
            "neutral": neu_pct,
            "negative": neg_pct
        }

        # Xác định tông giọng chung
        if pos_pct > 60.0:
            overall_tone = "Tích cực / Hào hứng đón nhận"
        elif neg_pct > 30.0:
            overall_tone = "Nóng bỏng / Nhiều tranh cãi trái chiều"
        else:
            overall_tone = "Sôi động / Thu hút tương tác cao"

    return {
        "keywords": keywords,
        "sentiment": sentiment,
        "overall_tone": overall_tone
    }
