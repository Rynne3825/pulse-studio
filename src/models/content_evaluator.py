"""
Tầng Đo Lường & Tối Ưu Nội Dung: Bộ Chấm Điểm Tiềm Năng Viral Kịch Bản TikTok (0 - 100 Điểm).
Thay thế toàn bộ mô hình 24h cũ bằng 4 chỉ số vàng minh bạch:
1. Hook Strength (25%)
2. Trend Alignment / Cosine Similarity (35%)
3. Pacing & Length (20%)
4. Call-To-Action & Engagement (20%)
"""

import re
from typing import Dict, List, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Từ khóa giật gân, nghi vấn cho câu mở đầu (Hook 3s)
VIRAL_HOOK_KEYWORDS = [
    "sự thật", "bóc mẽ", "cảnh báo", "đừng vội", "ai ngờ", "bí mật",
    "chấn động", "kinh hoàng", "lừa đảo", "vạch trần", "chú ý", "tiết lộ",
    "tin sốc", "độc lạ", "nguy hiểm", "chưa từng thấy", "sai lầm", "tại sao",
    "bất ngờ", "không thể tin", "cẩn thận"
]

# Từ khóa kêu gọi hành động / tranh luận (CTA)
VIRAL_CTA_KEYWORDS = [
    "bình luận", "comment", "nghĩ sao", "ý kiến", "chia sẻ", "follow",
    "theo dõi", "thả tim", "tranh luận", "đồng tình", "bạn có", "để lại",
    "cho mình biết", "bấm vào", "lưu lại"
]

VIETNAMESE_STOPWORDS = [
    "là", "của", "và", "những", "các", "có", "được", "trong", "cho", "với",
    "đã", "khi", "tại", "sẽ", "đến", "từ", "này", "về", "như", "theo", "sau"
]


class TikTokViralEvaluator:
    """Bộ đánh giá chất lượng và tiềm năng Viral của kịch bản TikTok."""

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words=VIETNAMESE_STOPWORDS,
            max_features=200
        )

    def calculate_hook_score(self, hook_text: str) -> Dict[str, Any]:
        """Đánh giá sức mạnh câu mở đầu 3 giây (Thang điểm 0 - 100)."""
        clean_hook = hook_text.strip().lower()
        if not clean_hook:
            return {
                "score": 0.0,
                "matched_keywords": [],
                "word_count": 0,
                "feedback": ["Thiếu câu mở đầu (Hook)."]
            }

        score = 50.0  # Điểm cơ sở
        feedback_items: List[str] = []

        # 1. Kiểm tra dấu hỏi hoặc từ nghi vấn kích thích tò mò (+20 điểm)
        if "?" in clean_hook or "tại sao" in clean_hook or "liệu có" in clean_hook or "vì sao" in clean_hook:
            score += 20.0
            feedback_items.append("Có câu hỏi kích thích tò mò người xem.")
        else:
            feedback_items.append("Gợi ý: Thêm câu hỏi nghi vấn để giữ chân người xem 3s đầu.")

        # 2. Kiểm tra từ khóa giật gân, bóc mẽ (+20 điểm)
        matched_keywords = [kw for kw in VIRAL_HOOK_KEYWORDS if kw in clean_hook]
        if matched_keywords:
            score += 20.0
            feedback_items.append(f"Chứa từ khóa giật gân mạnh: '{matched_keywords[0]}'.")
        else:
            feedback_items.append("Gợi ý: Dùng từ ngữ mang tính cảnh báo hoặc vạch trần (ví dụ: 'sự thật', 'đừng vội').")

        # 3. Phạt độ dài: Câu mở đầu tối ưu là dưới 15 từ
        word_count = len(clean_hook.split())
        if word_count <= 15:
            score += 10.0
            feedback_items.append("Độ dài Hook súc tích, nhịp điệu nhanh chuẩn TikTok.")
        else:
            penalty = min(25.0, (word_count - 15) * 2.5)
            score -= penalty
            feedback_items.append(f"Hook hơi dài ({word_count} từ), nên cô đọng dưới 15 từ.")

        final_score = float(np.clip(score, 0.0, 100.0))
        return {
            "score": round(final_score, 1),
            "matched_keywords": matched_keywords,
            "word_count": word_count,
            "feedback": feedback_items
        }

    def calculate_trend_similarity(self, source_text: str, script_text: str) -> Dict[str, Any]:
        """Tính độ tương đồng ngữ nghĩa Cosine Similarity giữa bài báo gốc và kịch bản (0 - 100)."""
        if not source_text.strip() or not script_text.strip():
            return {
                "score": 0.0,
                "cosine_raw": 0.0,
                "feedback": ["Thiếu nội dung nguồn để so khớp."]
            }

        try:
            tfidf_matrix = self.vectorizer.fit_transform([source_text, script_text])
            cos_sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        except Exception:
            cos_sim = 0.5  # Dự phòng

        # Cosine similarity thường nằm trong khoảng 0.15 - 0.7 cho tóm tắt
        # Scale về thang điểm 0 - 100
        score = min(100.0, cos_sim * 160.0)
        feedback_items: List[str] = []
        if score >= 70:
            feedback_items.append("Bám sát tuyệt đối sự kiện và số liệu từ tin thời sự gốc.")
        elif score >= 50:
            feedback_items.append("Bám sát chủ đề chính của bài báo.")
        else:
            feedback_items.append("Kịch bản hơi xa rời các từ khóa cốt lõi của bài báo nguồn.")

        return {
            "score": round(float(np.clip(score, 0.0, 100.0)), 1),
            "cosine_raw": round(cos_sim, 3),
            "feedback": feedback_items
        }

    def calculate_pacing_score(self, full_script: str) -> Dict[str, Any]:
        """Đo lường nhịp điệu thoại và thời lượng lý tưởng cho video ngắn TikTok (0 - 100)."""
        clean_text = re.sub(r"\s+", " ", full_script).strip()
        words = clean_text.split()
        word_count = len(words)

        if word_count == 0:
            return {
                "score": 0.0,
                "word_count": 0,
                "estimated_duration": 0.0,
                "feedback": ["Chưa có nội dung kịch bản để tính nhịp điệu."]
            }

        # Chuẩn TikTok: 60 - 110 từ (khoảng 20 - 40 giây nói với tốc độ trung bình 2.8 - 3 từ/giây)
        estimated_duration = round(word_count / 2.8, 1)

        feedback_items: List[str] = []
        if 60 <= word_count <= 110:
            score = 100.0
            feedback_items.append(f"Thời lượng hoàn hảo ({word_count} từ ~ {estimated_duration}s), giữ trọn tỷ lệ xem hết (Completion Rate).")
        elif 40 <= word_count < 60:
            score = 80.0
            feedback_items.append(f"Hơi ngắn ({word_count} từ ~ {estimated_duration}s), nên thêm 1 tình tiết để video sâu sắc hơn.")
        elif 110 < word_count <= 150:
            score = 75.0
            feedback_items.append(f"Hơi dài ({word_count} từ ~ {estimated_duration}s), người xem có thể lướt qua nếu nhịp chậm.")
        elif word_count < 40:
            score = 45.0
            feedback_items.append(f"Quá ngắn ({word_count} từ), chưa đủ truyền tải sự thật bóc mẽ.")
        else:
            score = 40.0
            feedback_items.append(f"Quá dài ({word_count} từ ~ {estimated_duration}s), vượt quá thời lượng giữ chân tối ưu.")

        return {
            "score": round(score, 1),
            "word_count": word_count,
            "estimated_duration": estimated_duration,
            "feedback": feedback_items
        }

    def calculate_cta_score(self, cta_text: str) -> Dict[str, Any]:
        """Đánh giá lời kêu gọi hành động (CTA) kích thích bình luận và tương tác (0 - 100)."""
        clean_cta = cta_text.strip().lower()
        if not clean_cta:
            return {
                "score": 20.0,
                "matched_keywords": [],
                "feedback": ["Thiếu câu kêu gọi hành động ở đoạn kết."]
            }

        score = 40.0
        feedback_items: List[str] = []
        matched_keywords = [kw for kw in VIRAL_CTA_KEYWORDS if kw in clean_cta]

        if matched_keywords:
            score += 40.0
            feedback_items.append(f"Kêu gọi tương tác rõ ràng với từ khóa: '{matched_keywords[0]}'.")
        else:
            feedback_items.append("Gợi ý: Kêu gọi bình luận hoặc tranh luận cụ thể ('Bạn nghĩ sao?', 'Để lại ý kiến').")

        # Có câu hỏi ở đoạn kết giúp tăng 300% lượng comment trên TikTok
        if "?" in clean_cta:
            score += 20.0
            feedback_items.append("Đặt câu hỏi mở giúp kích thích người xem tranh luận sôi nổi.")

        return {
            "score": round(float(np.clip(score, 0.0, 100.0)), 1),
            "matched_keywords": matched_keywords,
            "feedback": feedback_items
        }

    def evaluate(self, script_data: Dict[str, Any], source_text: str) -> Dict[str, Any]:
        """
        Đánh giá tổng hợp toàn diện kịch bản TikTok.
        script_data chứa: hook, body, cta, hashtags, full_script.
        source_text: Tiêu đề + nội dung bài báo xu hướng gốc.
        """
        hook_text = str(script_data.get("hook", ""))
        body_text = str(script_data.get("body", ""))
        cta_text = str(script_data.get("cta", ""))
        full_script = str(script_data.get("full_script", f"{hook_text} {body_text} {cta_text}"))

        hook_res = self.calculate_hook_score(hook_text)
        trend_res = self.calculate_trend_similarity(source_text, full_script)
        pacing_res = self.calculate_pacing_score(full_script)
        cta_res = self.calculate_cta_score(cta_text)

        # Tổng hợp trọng số: Hook (25%), Trend (35%), Pacing (20%), CTA (20%)
        overall = (
            hook_res["score"] * 0.25
            + trend_res["score"] * 0.35
            + pacing_res["score"] * 0.20
            + cta_res["score"] * 0.20
        )
        overall_score = round(float(np.clip(overall, 0.0, 100.0)), 1)

        # Xếp hạng Tier
        if overall_score >= 85:
            grade = "S"
            grade_title = "SIÊU TIỀM NĂNG VIRAL"
            grade_color = "#22C55E"  # Xanh lá
        elif overall_score >= 70:
            grade = "A"
            grade_title = "KHẢ NĂNG LÊN XU HƯỚNG CAO"
            grade_color = "#3B82F6"  # Xanh dương
        elif overall_score >= 50:
            grade = "B"
            grade_title = "TIỀM NĂNG TRUNG BÌNH"
            grade_color = "#F59E0B"  # Vàng hổ phách
        else:
            grade = "C"
            grade_title = "CẦN TỐI ƯU LẠI KỊCH BẢN"
            grade_color = "#EF4444"  # Đỏ

        # Chuẩn hóa feedback an toàn thành List[str]
        def _ensure_list(val: Any) -> List[str]:
            if isinstance(val, list):
                return [str(x) for x in val if str(x).strip()]
            if isinstance(val, str) and val.strip():
                return [val.strip()]
            return []

        # Tổng hợp danh sách checklist hành động
        all_feedback = (
            _ensure_list(hook_res.get("feedback"))
            + _ensure_list(trend_res.get("feedback"))
            + _ensure_list(pacing_res.get("feedback"))
            + _ensure_list(cta_res.get("feedback"))
        )

        return {
            "overall_score": overall_score,
            "grade": grade,
            "grade_title": grade_title,
            "grade_color": grade_color,
            "breakdown": {
                "hook_score": hook_res.get("score", 0.0),
                "trend_similarity_score": trend_res.get("score", 0.0),
                "pacing_score": pacing_res.get("score", 0.0),
                "cta_score": cta_res.get("score", 0.0)
            },
            "metrics": {
                "word_count": pacing_res.get("word_count", 0),
                "estimated_duration_sec": pacing_res.get("estimated_duration", 0.0),
                "hook_keywords": hook_res.get("matched_keywords", []),
                "cta_keywords": cta_res.get("matched_keywords", []),
                "cosine_raw": trend_res.get("cosine_raw", 0.0)
            },
            "actionable_checklist": all_feedback
        }


def evaluate_tiktok_script(script_data: Dict[str, Any], source_text: str) -> Dict[str, Any]:
    """Hàm tiện ích cấp cao để đánh giá kịch bản TikTok."""
    evaluator = TikTokViralEvaluator()
    return evaluator.evaluate(script_data, source_text)
