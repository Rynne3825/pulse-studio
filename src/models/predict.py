"""
Module dự đoán mức độ tương tác cho bài viết mới (Bản tối ưu hoàn chỉnh).
Tự động nạp:
- Model LightGBM (lgbm_model.joblib)
- Vectorizer N-grams TF-IDF (tfidf_vectorizer.joblib)
- Giảm chiều SVD (svd_transformer.joblib)
- Danh sách đặc trưng (feature_names.json)
"""

import sys
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.feature_extractor import extract_features_from_post

LABEL_NAMES = {0: "Thấp", 1: "Vừa", 2: "Cao", 3: "Viral"}

# Cache bộ nhớ để tránh đọc lại đĩa liên tục khi chạy Streamlit hoặc quét 24 giờ
_MODEL = None
_TFIDF = None
_SVD = None
_FEATURE_NAMES = None


def load_artifacts():
    """Tự động nạp toàn bộ các artifact từ models_saved/."""
    global _MODEL, _TFIDF, _SVD, _FEATURE_NAMES
    if _MODEL is None:
        save_dir = PROJECT_ROOT / "models_saved"
        model_path = save_dir / "lgbm_model.joblib"
        tfidf_path = save_dir / "tfidf_vectorizer.joblib"
        svd_path = save_dir / "svd_transformer.joblib"
        feat_path = save_dir / "feature_names.json"
        
        if not model_path.exists() or not tfidf_path.exists():
            raise FileNotFoundError("Chưa tìm thấy đầy đủ file mô hình. Vui lòng chạy train.py trước!")
        
        _MODEL = joblib.load(model_path)
        _TFIDF = joblib.load(tfidf_path)
        _SVD = joblib.load(svd_path)
        with open(feat_path, "r", encoding="utf-8") as f:
            _FEATURE_NAMES = json.load(f)
            
    return _MODEL, _TFIDF, _SVD, _FEATURE_NAMES


def predict_engagement(
    content: str,
    published_at: str,
    topic_category: int,
    thumbnail_url: str = ""
) -> Dict[str, Any]:
    """
    Dự đoán mức độ tương tác cho 1 bài viết mới với đầy đủ đặc trưng ngữ nghĩa.
    
    Tham số:
    - content: Nội dung bài viết (caption)
    - published_at: Thời gian dự kiến đăng (chuỗi ISO / UTC / YYYY-MM-DD HH:MM)
    - topic_category: 0 (Giải trí) hoặc 1 (Công nghệ)
    - thumbnail_url: Link ảnh thumbnail kèm bài
    
    Trả về:
    - predicted_level: 0, 1, 2, 3
    - predicted_label: "Thấp", "Vừa", "Cao", "Viral"
    - probabilities: Phân bố xác suất 4 lớp (%)
    """
    model, tfidf, svd, feature_names = load_artifacts()
    
    # 1. Trích xuất đặc trưng hình thái, cấu trúc và thời gian
    extracted = extract_features_from_post(
        content=content,
        published_at=published_at,
        topic_category=topic_category,
        thumbnail_url=thumbnail_url
    )
    
    # 2. Bổ sung các đặc trưng tương tác chéo
    extracted["hour_x_weekend"] = extracted["hour"] * extracted["is_weekend"]
    extracted["topic_x_word_count"] = extracted["topic_category"] * extracted["word_count"]
    extracted["sentiment_x_exclamation"] = extracted["sentiment_score"] * extracted["exclamation_count"]
    extracted["char_per_word"] = round(extracted["char_count"] / (extracted["word_count"] + 1), 2)
    
    # 3. Trích xuất 40 chiều vector ngữ nghĩa TF-IDF + SVD từ văn bản bài viết
    cleaned_text = extracted.get("cleaned_content", "")
    tfidf_vec = tfidf.transform([cleaned_text])
    svd_vec = svd.transform(tfidf_vec)[0]
    for i, val in enumerate(svd_vec):
        extracted[f"tfidf_svd_{i}"] = float(val)
        
    # 4. Xếp theo đúng thứ tự các cột mô hình yêu cầu
    input_row = {col: extracted[col] for col in feature_names}
    input_df = pd.DataFrame([input_row])
    
    # 5. Thực hiện dự đoán
    predicted_level = int(model.predict(input_df)[0])
    probabilities = model.predict_proba(input_df)[0]
    
    prob_dict = {
        LABEL_NAMES[i]: round(float(probabilities[i]) * 100, 2)
        for i in range(len(probabilities))
    }
    
    return {
        "predicted_level": predicted_level,
        "predicted_label": LABEL_NAMES[predicted_level],
        "probabilities": prob_dict,
        "features_summary": {
            "hour": extracted["hour"],
            "day_of_week": extracted["day_of_week"],
            "word_count": extracted["word_count"],
            "char_count": extracted["char_count"],
            "sentiment_score": extracted["sentiment_score"],
            "is_peak_hour": extracted["is_peak_hour"]
        }
    }


def predict_engagement_24h_batch(
    content: str,
    target_date: str,
    topic_category: int,
    thumbnail_url: str = ""
) -> List[Dict[str, Any]]:
    """
    Dự đoán đồng thời xác suất tương tác cho toàn bộ 24 khung giờ trong ngày (Vectorized Batch Inference).
    Tối ưu hóa: Trích xuất TF-IDF và SVD một lần duy nhất, tăng tốc độ tính toán gấp ~25 lần.
    """
    model, tfidf, svd, feature_names = load_artifacts()

    base_extracted = extract_features_from_post(
        content=content,
        published_at=f"{target_date}T00:00:00+07:00",
        topic_category=topic_category,
        thumbnail_url=thumbnail_url
    )

    cleaned_text = base_extracted.get("cleaned_content", "")
    tfidf_vec = tfidf.transform([cleaned_text])
    svd_vec = svd.transform(tfidf_vec)[0]
    for i, val in enumerate(svd_vec):
        base_extracted[f"tfidf_svd_{i}"] = float(val)

    base_extracted["topic_x_word_count"] = base_extracted["topic_category"] * base_extracted["word_count"]
    base_extracted["sentiment_x_exclamation"] = base_extracted["sentiment_score"] * base_extracted["exclamation_count"]
    base_extracted["char_per_word"] = round(base_extracted["char_count"] / (base_extracted["word_count"] + 1), 2)

    is_weekend = base_extracted["is_weekend"]

    rows = []
    for h in range(24):
        row = dict(base_extracted)
        row["hour"] = h
        row["hour_sin"] = round(float(np.sin(2 * np.pi * h / 24)), 4)
        row["hour_cos"] = round(float(np.cos(2 * np.pi * h / 24)), 4)
        row["is_peak_hour"] = 1 if (11 <= h <= 13) or (19 <= h <= 21) else 0
        row["hour_x_weekend"] = h * is_weekend
        rows.append({col: row[col] for col in feature_names})

    batch_df = pd.DataFrame(rows)
    all_probs = model.predict_proba(batch_df)

    results = []
    for h in range(24):
        probs = all_probs[h]
        prob_dict = {
            LABEL_NAMES[i]: round(float(probs[i]) * 100, 2)
            for i in range(len(probs))
        }
        results.append({
            "hour": h,
            "probabilities": prob_dict
        })
    return results


if __name__ == "__main__":
    sample_content = "Đánh giá chi tiết iPhone 16 Pro Max sau 1 tháng sử dụng: Pin có thực sự trâu? #CongNghe #Apple"
    sample_time = "2026-10-27T12:00:00.000Z"
    sample_topic = 1
    
    print("Chạy thử dự đoán bài viết mới:")
    res = predict_engagement(sample_content, sample_time, sample_topic, "https://example.com/thumb.jpg")
    print(json.dumps(res, ensure_ascii=False, indent=2))
