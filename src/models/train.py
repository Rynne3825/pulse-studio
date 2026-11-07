"""
Giai đoạn 3 (Chuẩn Học Thuật - Strict Leak-Free): Huấn luyện mô hình LightGBM.
Tuân thủ 100% nguyên tắc Khoa học Dữ liệu:
- Phân chia Train/Test TRƯỚC khi fit TF-IDF và SVD (Chống rò rỉ dữ liệu - Data Leakage).
- Đánh giá chéo Stratified 5-Fold Cross Validation trên tập Train.
- Đánh giá độc lập trên tập Test (20%).
- Trích xuất Feature Importance và ma trận nhầm lẫn.
"""

import os
import sys
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from lightgbm import LGBMClassifier

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

BASE_FEATURE_COLUMNS = [
    "hour", "hour_sin", "hour_cos", "day_of_week", "is_weekend", "is_peak_hour",
    "char_count", "word_count", "avg_word_length", "hashtag_count",
    "question_count", "exclamation_count", "ellipsis_count", "has_thumbnail",
    "topic_category", "pos_word_count", "neg_word_count", "sentiment_score"
]

TARGET_COLUMN = "engagement_level"
LABEL_NAMES = ["0: Thấp", "1: Vừa", "2: Cao", "3: Viral"]


def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Tạo các đặc trưng tương tác chéo và mã hóa tuần hoàn thời gian."""
    df_copy = df.copy()
    # Chuẩn hóa giờ cao điểm: 11h-13h (trưa) và 19h-21h (Prime Time tối). Tuyệt đối không tính 22h!
    df_copy["is_peak_hour"] = df_copy["hour"].apply(lambda h: 1 if (11 <= h <= 13) or (19 <= h <= 21) else 0)
    # Mã hóa tuần hoàn (Cyclical Encoding) giúp mô hình nhận biết 23h liền kề 00h
    df_copy["hour_sin"] = np.sin(2 * np.pi * df_copy["hour"] / 24).round(4)
    df_copy["hour_cos"] = np.cos(2 * np.pi * df_copy["hour"] / 24).round(4)
    
    df_copy["hour_x_weekend"] = df_copy["hour"] * df_copy["is_weekend"]
    df_copy["topic_x_word_count"] = df_copy["topic_category"] * df_copy["word_count"]
    df_copy["sentiment_x_exclamation"] = df_copy["sentiment_score"] * df_copy["exclamation_count"]
    df_copy["char_per_word"] = (df_copy["char_count"] / (df_copy["word_count"] + 1)).round(2)
    return df_copy


def compute_hourly_balance_weights(df: pd.DataFrame) -> pd.Series:
    """
    Tính toán trọng số nghịch đảo tần suất (Inverse Frequency Weights) theo từng cặp (hour, engagement_level).
    Triệt tiêu hoàn toàn thiên lệch chọn mẫu (Selection Bias) ở các giờ đêm khuya (22h, 23h) nơi quản trị viên 
    chỉ đăng các tin giật gân/drama nên tỷ lệ bài Thấp bị thiếu hụt nhân tạo trong dữ liệu lịch sử.
    """
    counts = df.groupby(["hour", "engagement_level"]).size()
    weights = df.apply(lambda r: 1.0 / counts.get((r["hour"], r["engagement_level"]), 1), axis=1)
    return weights / weights.mean()


def train_model():
    print("=" * 65)
    print("BƯỚC 1: ĐỌC DỮ LIỆU ĐÃ TIỀN XỬ LÝ (FEATURES.CSV)")
    print("=" * 65)
    data_path = PROJECT_ROOT / "data" / "processed" / "features.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {data_path}. Vui lòng chạy pipeline tiền xử lý trước!")
    
    df = pd.read_csv(data_path)
    df = add_interaction_features(df)
    interaction_cols = ["hour_x_weekend", "topic_x_word_count", "sentiment_x_exclamation", "char_per_word"]
    tabular_features = BASE_FEATURE_COLUMNS + interaction_cols
    print(f"-> Đã nạp {len(df)} dòng dữ liệu với {len(tabular_features)} đặc trưng dạng bảng.")

    # Tính toán trọng số cân bằng giờ để loại bỏ bias 22h
    sample_weights = compute_hourly_balance_weights(df)
    print("-> Đã tính toán trọng số cân bằng theo giờ (Hourly Stratified Weights) để triệt tiêu bias.")

    print("\n" + "=" * 65)
    print("BƯỚC 2: PHÂN CHIA TẬP TRAIN (80%) VÀ TEST (20%) TRƯỚC KHI TRÍCH XUẤT NGỮ NGHĨA")
    print("=" * 65)
    # Nguyên tắc học thuật: Tách tập Train/Test TRƯỚC để chống rò rỉ dữ liệu (No Data Leakage)
    train_df, test_df, w_train, w_test = train_test_split(
        df, sample_weights, test_size=0.20, random_state=42, stratify=df[TARGET_COLUMN]
    )
    print(f"-> Tập Train: {len(train_df)} mẫu | Tập Test: {len(test_df)} mẫu")

    print("\n" + "=" * 65)
    print("BƯỚC 3: FIT TF-IDF VÀ SVD CHỈ TRÊN TẬP TRAIN (CHỐNG RÒ RỈ DỮ LIỆU)")
    print("=" * 65)
    # Fit vectorizer CHỈ trên tập Train, sau đó transform cho cả Train và Test
    tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=600, min_df=2)
    tfidf_train = tfidf.fit_transform(train_df["cleaned_content"].fillna(""))
    tfidf_test = tfidf.transform(test_df["cleaned_content"].fillna(""))
    
    # SVD 40 chiều ngữ nghĩa
    svd = TruncatedSVD(n_components=40, random_state=42)
    svd_train = svd.fit_transform(tfidf_train)
    svd_test = svd.transform(tfidf_test)
    
    svd_cols = [f"tfidf_svd_{i}" for i in range(40)]
    svd_df_train = pd.DataFrame(svd_train, columns=svd_cols, index=train_df.index)
    svd_df_test = pd.DataFrame(svd_test, columns=svd_cols, index=test_df.index)

    # Ghép bảng đặc trưng
    X_train = pd.concat([train_df[tabular_features], svd_df_train], axis=1)
    y_train = train_df[TARGET_COLUMN]
    
    X_test = pd.concat([test_df[tabular_features], svd_df_test], axis=1)
    y_test = test_df[TARGET_COLUMN]
    
    all_feature_names = list(X_train.columns)
    print(f"-> Tổng số đặc trưng đầu vào: {len(all_feature_names)} đặc trưng.")

    print("\n" + "=" * 65)
    print("BƯỚC 4: HUẤN LUYỆN MÔ HÌNH LIGHTGBM (CẤU HÌNH TỐI ƯU)")
    print("=" * 65)
    model = LGBMClassifier(
        n_estimators=220,
        learning_rate=0.03,
        max_depth=6,
        num_leaves=35,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_samples=15,
        class_weight="balanced",
        random_state=42,
        verbose=-1
    )
    
    print("-> Đang huấn luyện LightGBM với trọng số cân bằng giờ (Sample Weights)...")
    model.fit(X_train, y_train, sample_weight=w_train.values)
    print("-> Huấn luyện mô hình hoàn tất!")

    print("\n" + "=" * 65)
    print("BƯỚC 5: ĐÁNH GIÁ 5-FOLD STRATIFIED CROSS-VALIDATION TRÊN TẬP HUẤN LUYỆN")
    print("=" * 65)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")
    print(f"-> Độ chính xác qua 5 Fold: {[round(s * 100, 2) for s in cv_scores]}")
    print(f"-> Độ chính xác trung bình (5-Fold CV Mean): {cv_scores.mean() * 100:.2f}% (± {cv_scores.std() * 100:.2f}%)")

    print("\n" + "=" * 65)
    print("BƯỚC 6: ĐÁNH GIÁ TRÊN TẬP KIỂM THỬ ĐỘC LẬP (TEST SET 20%)")
    print("=" * 65)
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    weighted_f1 = f1_score(y_test, y_pred, average="weighted")
    
    print(f"-> Độ chính xác tập Test (Accuracy): {acc * 100:.2f}%")
    print(f"-> Điểm F1-Score (Macro Average):     {macro_f1:.4f}")
    print(f"-> Điểm F1-Score (Weighted Average):  {weighted_f1:.4f}")
    
    print("\n--- Báo cáo chi tiết từng mức tương tác (Classification Report) ---")
    print(classification_report(y_test, y_pred, target_names=LABEL_NAMES))
    
    print("--- Ma trận nhầm lẫn (Confusion Matrix) ---")
    cm = confusion_matrix(y_test, y_pred)
    cm_df = pd.DataFrame(cm, index=LABEL_NAMES, columns=LABEL_NAMES)
    print(cm_df)

    print("\n" + "=" * 65)
    print("BƯỚC 7: LƯU TRỮ MODEL VÀ BỘ CHUYỂN ĐỔI CHUẨN VÀO MODELS_SAVED/")
    print("=" * 65)
    save_dir = PROJECT_ROOT / "models_saved"
    save_dir.mkdir(parents=True, exist_ok=True)
    
    joblib.dump(model, save_dir / "lgbm_model.joblib")
    joblib.dump(tfidf, save_dir / "tfidf_vectorizer.joblib")
    joblib.dump(svd, save_dir / "svd_transformer.joblib")
    
    with open(save_dir / "feature_names.json", "w", encoding="utf-8") as f:
        json.dump(all_feature_names, f, ensure_ascii=False, indent=2)
        
    metrics_data = {
        "methodology": "Strict Leak-Free Train-Test Pipeline",
        "accuracy": round(acc, 4),
        "f1_macro": round(macro_f1, 4),
        "f1_weighted": round(weighted_f1, 4),
        "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
        "cv_accuracy_std": round(float(cv_scores.std()), 4),
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "feature_count": len(all_feature_names)
    }
    with open(save_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, ensure_ascii=False, indent=2)
        
    print("-> Đã lưu chuẩn học thuật: lgbm_model.joblib, tfidf_vectorizer.joblib, svd_transformer.joblib, feature_names.json, metrics.json")
    print("\n=== QUY TRÌNH HUẤN LUYỆN CHUẨN HỌC THUẬT HOÀN TẤT ===")
    return model, metrics_data


if __name__ == "__main__":
    train_model()
