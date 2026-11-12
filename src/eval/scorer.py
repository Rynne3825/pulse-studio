"""Bộ chấm điểm tiềm năng Viral 4 trụ cột (M3): Hook 25% · Cosine 35% · Cấu trúc 20% · CTA 20%."""

import logging
import re
from typing import Any, Dict, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

VIRAL_HOOK_KEYWORDS = [
    "sự thật", "bóc mẽ", "cảnh báo", "đừng vội", "ai ngờ", "bí mật",
    "chấn động", "kinh hoàng", "lừa đảo", "vạch trần", "chú ý", "tiết lộ",
    "tin sốc", "độc lạ", "nguy hiểm", "chưa từng thấy", "sai lầm", "tại sao",
    "bất ngờ", "không thể tin", "cẩn thận", "điểm tin", "nóng", "hé lộ",
]

VIRAL_CTA_KEYWORDS = [
    "bình luận", "comment", "nghĩ sao", "ý kiến", "chia sẻ", "follow",
    "theo dõi", "thả tim", "tranh luận", "đồng tình", "bạn có", "để lại",
    "cho mình biết", "bấm vào", "lưu lại", "thảo luận", "bạn thấy", "theo bạn", "quan điểm",
]

VIETNAMESE_STOPWORDS = [
    "là", "của", "và", "những", "các", "có", "được", "trong", "cho", "với",
    "đã", "khi", "tại", "sẽ", "đến", "từ", "này", "về", "như", "theo", "sau",
    "một", "hai", "nên", "phải", "thể", "rất", "còn", "nhưng", "nếu",
]


class PostViralEvaluator:
    """Đánh giá bài đăng mạng xã hội đa nền tảng (Facebook / Threads) thang 0 - 100."""

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words=VIETNAMESE_STOPWORDS, max_features=200)

    def calculate_hook_score(self, hook_text: str) -> Dict[str, Any]:
        clean = hook_text.strip().lower()
        if not clean:
            return {"score": 0.0, "matched_keywords": [], "word_count": 0, "feedback": ["Thiếu câu mở đầu (Hook)."]}

        score = 50.0
        fb: List[str] = []

        if any(q in clean for q in ("?", "tại sao", "liệu", "vì sao", "sao", "thế nào", "ai")):
            score += 20.0
            fb.append("Có câu hỏi hoặc nghi vấn kích thích tò mò người đọc.")
        else:
            fb.append("Gợi ý: Thêm câu hỏi nghi vấn để kích thích người đọc dừng ngón tay.")

        matched = [kw for kw in VIRAL_HOOK_KEYWORDS if kw in clean]
        if matched:
            score += 20.0
            fb.append(f"Chứa từ khóa thu hút chú ý mạnh: '{matched[0]}'.")
        else:
            fb.append("Gợi ý: Dùng từ ngữ gợi mở hoặc mang tính cảnh báo/điểm nhấn (ví dụ: 'sự thật', 'cảnh báo', 'bất ngờ').")

        words = len(clean.split())
        if words <= 15:
            score += 10.0
            fb.append("Độ dài Hook súc tích, nhịp điệu nhanh gây ấn tượng ngay.")
        else:
            score -= min(25.0, (words - 15) * 2.5)
            fb.append(f"Hook hơi dài ({words} từ), nên cô đọng dưới 15 từ.")

        return {
            "score": round(float(np.clip(score, 0.0, 100.0)), 1),
            "matched_keywords": matched,
            "word_count": words,
            "feedback": fb,
        }

    def calculate_trend_similarity(self, source_text: str, post_text: str) -> Dict[str, Any]:
        if not source_text.strip() or not post_text.strip():
            return {"score": 0.0, "cosine_raw": 0.0, "feedback": ["Thiếu nội dung nguồn để so khớp."]}

        try:
            mat = self.vectorizer.fit_transform([source_text, post_text])
            cos_sim = float(cosine_similarity(mat[0:1], mat[1:2])[0][0])
        except Exception as exc:
            logger.warning("Lỗi tính TF-IDF Cosine Similarity: %s", exc)
            cos_sim = 0.0

        score = round(float(np.clip(min(100.0, cos_sim * 160.0), 0.0, 100.0)), 1)
        if score >= 70:
            fb = ["Bám sát tuyệt đối sự kiện và số liệu từ tin thời sự gốc."]
        elif score >= 50:
            fb = ["Bám sát chủ đề chính của bài báo."]
        else:
            fb = ["Bài viết hơi xa rời các từ khóa cốt lõi của bài báo nguồn."]

        return {"score": score, "cosine_raw": round(cos_sim, 3), "feedback": fb}

    def calculate_pacing_score(self, full_text: str, platform: str = "facebook") -> Dict[str, Any]:
        clean = re.sub(r"\s+", " ", full_text).strip()
        wc = len(clean.split())
        if wc == 0:
            return {"score": 0.0, "word_count": 0, "estimated_duration": 0.0, "feedback": ["Chưa có nội dung bài viết để tính nhịp điệu và độ dài."]}

        est_sec = round(wc / 2.8, 1)
        fb: List[str] = []
        plat = (platform or "facebook").lower().strip()

        if plat == "threads":
            if 35 <= wc <= 85:
                score, fb = 100.0, [f"Độ dài Threads hoàn hảo ({wc} từ), cô đọng, sắc bén, kích thích đọc lướt."]
            elif 20 <= wc < 35:
                score, fb = 80.0, [f"Hơi ngắn cho Threads ({wc} từ), nên bổ sung thêm 1 góc nhìn lập luận."]
            elif 85 < wc <= 120:
                score, fb = 75.0, [f"Hơi dài cho Threads ({wc} từ), nên tinh gọn dưới 85 từ để tối ưu tương tác."]
            elif wc < 20:
                score, fb = 40.0, [f"Quá ngắn ({wc} từ), chưa đủ truyền tải thông điệp thảo luận."]
            else:
                score = max(30.0, 65.0 - min(50.0, (wc - 120) * 0.8))
                fb = [f"Quá dài cho Threads ({wc} từ), vượt ngưỡng 120 từ khiến người đọc dễ lướt qua."]
        else:
            paras = [p.strip() for p in full_text.split("\n") if p.strip()]
            if 75 <= wc <= 220:
                score, fb = 100.0, [f"Độ dài lý tưởng cho Facebook ({wc} từ), tối ưu tỷ lệ đọc hết (Dwell Time)."]
            elif 60 <= wc < 75:
                score, fb = 85.0, [f"Hơi ngắn cho Facebook ({wc} từ), nên triển khai thêm 1 góc nhìn cụ thể."]
            elif 220 < wc <= 300:
                score, fb = 80.0, [f"Hơi dài ({wc} từ), nên cô đọng lại để tránh người đọc bấm 'Xem thêm' rồi bỏ ngang."]
            elif wc < 60:
                score, fb = max(30.0, 40.0 + (wc / 60.0) * 25.0), [f"Quá ngắn cho Facebook ({wc} từ), chưa đủ chiều sâu cho người đọc."]
            else:
                score, fb = max(35.0, 75.0 - (wc - 300) * 0.3), [f"Quá dài ({wc} từ), vượt quá dung lượng giữ chân người dùng Facebook trung bình."]

            if len(paras) < 2 and wc >= 100:
                score = max(30.0, score - 10.0)
                fb.append("Bài viết thiếu ngắt đoạn; nên chia thành 2-3 đoạn ngắn để dễ theo dõi trên mobile.")
            elif len(paras) >= 3:
                fb.append("Bố cục phân đoạn mạch lạc, dễ quét mắt trên màn hình điện thoại.")

        return {"score": round(float(np.clip(score, 0.0, 100.0)), 1), "word_count": wc, "estimated_duration": est_sec, "feedback": fb}

    def calculate_cta_score(self, cta_text: str) -> Dict[str, Any]:
        clean = cta_text.strip().lower()
        if not clean:
            return {"score": 20.0, "matched_keywords": [], "feedback": ["Thiếu câu kêu gọi tương tác (CTA) ở đoạn kết."]}

        score = 40.0
        matched = [kw for kw in VIRAL_CTA_KEYWORDS if kw in clean]
        fb: List[str] = []
        if matched:
            score += 40.0
            fb.append(f"Kêu gọi tương tác rõ ràng với từ khóa: '{matched[0]}'.")
        else:
            fb.append("Gợi ý: Thêm lời kêu gọi bình luận cụ thể ('Bạn nghĩ sao?', 'Để lại quan điểm').")

        if "?" in clean:
            score += 20.0
            fb.append("Đặt câu hỏi mở giúp tăng mạnh lượng bình luận tranh luận.")

        return {"score": round(float(np.clip(score, 0.0, 100.0)), 1), "matched_keywords": matched, "feedback": fb}

    def evaluate(self, post_data: Dict[str, Any], source_text: str, platform: str = "facebook") -> Dict[str, Any]:
        plat = str(post_data.get("platform") or platform or "facebook").lower().strip()
        hook = str(post_data.get("hook", ""))
        body = str(post_data.get("body", ""))
        cta = str(post_data.get("cta", ""))
        full_post = str(post_data.get("full_post") or f"{hook}\n\n{body}\n\n{cta}")

        h_res = self.calculate_hook_score(hook)
        t_res = self.calculate_trend_similarity(source_text, full_post)
        p_res = self.calculate_pacing_score(full_post, platform=plat)
        c_res = self.calculate_cta_score(cta)

        overall = round(
            float(np.clip(h_res["score"] * 0.25 + t_res["score"] * 0.35 + p_res["score"] * 0.20 + c_res["score"] * 0.20, 0.0, 100.0)),
            1,
        )

        tiers = (
            (85, "S", "SIÊU TIỀM NĂNG VIRAL", "#22C55E"),
            (70, "A", "KHẢ NĂNG LÊN XU HƯỚNG CAO", "#3B82F6"),
            (50, "B", "TIỀM NĂNG TRUNG BÌNH", "#F59E0B"),
            (0, "C", "CẦN TỐI ƯU LẠI BÀI VIẾT", "#EF4444"),
        )
        _, grade, grade_title, grade_color = next(t for t in tiers if overall >= t[0])

        feedback: List[str] = []
        for res in (h_res, t_res, p_res, c_res):
            raw_fb = res.get("feedback", [])
            if isinstance(raw_fb, list):
                feedback.extend(str(x) for x in raw_fb if str(x).strip())
            elif isinstance(raw_fb, str) and raw_fb.strip():
                feedback.append(raw_fb.strip())

        return {
            "overall_score": overall,
            "grade": grade,
            "grade_title": grade_title,
            "grade_color": grade_color,
            "breakdown": {
                "hook_score": h_res["score"],
                "trend_similarity_score": t_res["score"],
                "pacing_score": p_res["score"],
                "cta_score": c_res["score"],
            },
            "metrics": {
                "word_count": p_res["word_count"],
                "estimated_duration_sec": p_res["estimated_duration"],
                "platform": plat,
                "hook_keywords": h_res["matched_keywords"],
                "cta_keywords": c_res["matched_keywords"],
                "cosine_raw": t_res["cosine_raw"],
            },
            "actionable_checklist": feedback,
        }


def evaluate_post(post_data: Dict[str, Any], source_text: str, platform: str = "facebook") -> Dict[str, Any]:
    """Hàm tiện ích đánh giá bài đăng Facebook / Threads."""
    return PostViralEvaluator().evaluate(post_data, source_text, platform=platform)
