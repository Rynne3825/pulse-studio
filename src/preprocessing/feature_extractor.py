"""
Feature extraction module for Vietnamese social media posts.
Extracts temporal, structural, linguistic, and sentiment features.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from .text_cleaner import clean_text, extract_hashtags, extract_punctuation_counts

import numpy as np

# Vietnam timezone is UTC+7
VN_TIMEZONE = timezone(timedelta(hours=7))

# Curated Vietnamese social media sentiment lexicon
POSITIVE_WORDS = {
    "tuyệt", "tuyệt vời", "đẹp", "thích", "yêu", "hay", "xịn", "xịn sò", "đỉnh", 
    "đỉnh chóp", "ưu đãi", "thắng", "hot", "bùng nổ", "ấn tượng", "mê", "chuẩn", 
    "chất", "hào hứng", "vui", "thành công", "tự hào", "xuất sắc", "khen", "được mùa", 
    "chúc mừng", "hạnh phúc", "đột phá", "siêu phẩm", "hấp dẫn", "yêu thích", "tinh tế"
}

NEGATIVE_WORDS = {
    "tệ", "xấu", "ghét", "chán", "buồn", "lỗi", "hỏng", "sốc", "bất ngờ", "thất vọng", 
    "bức xúc", "tranh cãi", "phốt", "cảnh báo", "nguy hiểm", "chỉ trích", "bê bối", 
    "bị bắt", "tai nạn", "phạt", "bức xúc", "chê", "giả mạo", "lừa đảo", "sập", 
    "khủng hoảng", "đình chỉ", "sa thải", "thảm họa", "bất ổn", "hoang mang"
}


def parse_vietnam_time(time_str: str) -> datetime:
    """Parse UTC/ISO timestamp and convert to Vietnam time (UTC+7)."""
    if not isinstance(time_str, str) or not time_str:
        return datetime.now(VN_TIMEZONE)
    
    clean_str = time_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(VN_TIMEZONE)
    except Exception:
        return datetime.now(VN_TIMEZONE)


def compute_sentiment(text: str) -> Dict[str, float]:
    """Calculate normalized sentiment score using curated Vietnamese lexicon."""
    text_lower = text.lower()
    
    pos_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
    neg_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)
    total = pos_count + neg_count
    
    # Normalized score between -1.0 and +1.0
    sentiment_score = (pos_count - neg_count) / (total + 1.0)
    
    return {
        "pos_word_count": pos_count,
        "neg_word_count": neg_count,
        "sentiment_score": round(sentiment_score, 4)
    }


def extract_features_from_post(
    content: str,
    published_at: str,
    topic_category: int,
    thumbnail_url: str = ""
) -> Dict[str, Any]:
    """Extract full vector of numerical and categorical features for a single post."""
    # 1. Clean Text
    cleaned_content = clean_text(content)
    
    # 2. Temporal Features (UTC+7)
    dt_vn = parse_vietnam_time(published_at)
    hour = dt_vn.hour
    day_of_week = dt_vn.weekday()  # 0=Monday, 6=Sunday
    is_weekend = 1 if day_of_week >= 5 else 0
    # Giờ cao điểm mạng xã hội Việt Nam: Trưa (11h - 13h) và Tối Prime Time (19h - 21h). Tuyệt đối không tính 22h!
    is_peak_hour = 1 if (11 <= hour <= 13) or (19 <= hour <= 21) else 0
    hour_sin = round(float(np.sin(2 * np.pi * hour / 24)), 4)
    hour_cos = round(float(np.cos(2 * np.pi * hour / 24)), 4)
    
    # 3. Structural Features
    char_count = len(cleaned_content)
    words = cleaned_content.split()
    word_count = len(words)
    avg_word_length = round(char_count / word_count, 2) if word_count > 0 else 0.0
    
    hashtags = extract_hashtags(cleaned_content)
    hashtag_count = len(hashtags)
    
    punct_counts = extract_punctuation_counts(cleaned_content)
    has_thumbnail = 1 if (isinstance(thumbnail_url, str) and len(thumbnail_url.strip()) > 5) else 0
    
    # 4. Sentiment Features
    sentiment = compute_sentiment(cleaned_content)
    
    return {
        "cleaned_content": cleaned_content,
        "hour": hour,
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "is_peak_hour": is_peak_hour,
        "char_count": char_count,
        "word_count": word_count,
        "avg_word_length": avg_word_length,
        "hashtag_count": hashtag_count,
        "question_count": punct_counts["question_count"],
        "exclamation_count": punct_counts["exclamation_count"],
        "ellipsis_count": punct_counts["ellipsis_count"],
        "has_thumbnail": has_thumbnail,
        "topic_category": int(topic_category),
        "pos_word_count": sentiment["pos_word_count"],
        "neg_word_count": sentiment["neg_word_count"],
        "sentiment_score": sentiment["sentiment_score"]
    }
