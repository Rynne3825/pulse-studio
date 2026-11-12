"""Chuẩn hóa văn bản, trích xuất từ khóa TF-IDF N-grams (1, 3) & phân tích sắc thái (M1)."""

import re
import unicodedata
from typing import Any, Dict, List, Set, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

VIETNAMESE_STOPWORDS: Set[str] = {
    "và", "của", "cho", "với", "trong", "tại", "từ", "đến", "tới", "về", "như", "theo",
    "sau", "trước", "khi", "do", "bởi", "vì", "để", "mà", "thì", "hay", "hoặc", "cùng",
    "qua", "vào", "ra", "lên", "xuống", "ở", "nhưng", "nếu", "tuy", "dù", "bằng", "giữa",
    "trên", "dưới", "ngoài", "bên", "cạnh", "nên", "vậy", "song", "rằng", "nhờ", "dựa",
    "sang", "đi", "lại", "tuy nhiên", "vì vậy", "cho nên", "mặc dù", "nhiên", "mặc",
    "này", "đây", "đó", "kia", "ấy", "nọ", "người", "các", "những", "mỗi", "mọi", "vài",
    "cả", "tất", "nhiều", "ít", "hơn", "kém", "nhất", "một", "hai", "ba", "bốn", "năm",
    "sáu", "bảy", "tám", "chín", "mười", "trăm", "nghìn", "gì", "sao", "nào", "đâu",
    "nơi", "họ", "tôi", "mình", "chúng", "ta", "nhau", "tự", "riêng", "chung", "thế",
    "đã", "đang", "sẽ", "vừa", "mới", "sắp", "cũng", "đều", "vẫn", "còn", "chỉ", "rất",
    "quá", "lắm", "khá", "hơi", "chưa", "không", "chẳng", "đừng", "hãy", "cứ", "được",
    "bị", "có", "là", "phải", "cần", "thể", "khiến", "làm", "gây", "nói", "biết", "thấy",
    "xem", "từng", "luôn", "ngay", "thường", "xong", "rồi", "thêm", "bớt", "hết", "vốn",
    "việc", "sự", "án", "phí", "bài", "tin", "ảnh", "clip", "video", "lúc", "ngày",
    "tháng", "giờ", "phút", "tuần", "hôm", "nay", "mai", "sáng", "trưa", "chiều", "tối",
    "đêm", "lần", "cách", "điều", "loại", "mức", "liên", "quan", "chính", "thức", "hiện",
    "thực", "tế", "tình", "hình", "vụ", "lời", "câu", "chữ", "phía", "mặt", "nửa",
    "đáng", "chú", "ý", "mới nhất", "hôm nay", "vừa qua",
}

POSITIVE_WORDS: Set[str] = {
    "tuyệt", "tuyệt vời", "đẹp", "thích", "yêu", "hay", "xịn", "xịn sò", "đỉnh",
    "đỉnh chóp", "ưu đãi", "thắng", "hot", "bùng nổ", "ấn tượng", "mê", "chuẩn",
    "chất", "hào hứng", "vui", "thành công", "tự hào", "xuất sắc", "khen", "được mùa",
    "chúc mừng", "hạnh phúc", "đột phá", "siêu phẩm", "hấp dẫn", "yêu thích", "tinh tế",
}

NEGATIVE_WORDS: Set[str] = {
    "tệ", "xấu", "ghét", "chán", "buồn", "lỗi", "hỏng", "sốc", "bất ngờ", "thất vọng",
    "bức xúc", "tranh cãi", "phốt", "cảnh báo", "nguy hiểm", "chỉ trích", "bê bối",
    "bị bắt", "tai nạn", "phạt", "chê", "giả mạo", "lừa đảo", "sập",
    "khủng hoảng", "đình chỉ", "sa thải", "thảm họa", "bất ổn", "hoang mang",
}


def clean_text(text: str) -> str:
    """Loại bỏ URL, chuẩn hóa Unicode NFC và thu gọn khoảng trắng thừa."""
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r"https?://\S+|www\.\S+", "", text)
    cleaned = unicodedata.normalize("NFC", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def extract_trending_topics(articles: List[Dict[str, Any]], top_n: int = 8) -> Dict[str, Any]:
    """Trích xuất top từ khóa TF-IDF (1, 3) & phân tích sắc thái dư luận (tổng 100%)."""
    empty_res = {
        "keywords": [],
        "sentiment": {"positive": 50.0, "neutral": 50.0, "negative": 0.0},
        "overall_tone": "Chưa có dữ liệu",
    }
    if not articles:
        return empty_res

    docs: List[str] = []
    for art in articles:
        full_doc = f"{clean_text(str(art.get('title', '') or ''))} {clean_text(str(art.get('summary', '') or ''))}".strip()
        if full_doc and re.search(r"\w+", full_doc):
            docs.append(full_doc)

    if not docs:
        return empty_res

    keywords: List[Tuple[str, float]] = []
    if top_n > 0:
        acronyms = {
            tok.lower()
            for doc in docs
            for tok in re.findall(r"\b[A-Za-z0-9]{2,}\b", doc)
            if sum(1 for ch in tok if ch.isupper()) >= 2
        }
        try:
            vec = TfidfVectorizer(
                ngram_range=(1, 3),
                stop_words=list(VIETNAMESE_STOPWORDS),
                sublinear_tf=True,
                max_features=300,
            )
            mean_scores = np.asarray(vec.fit_transform(docs).mean(axis=0)).ravel()
            scored: List[Tuple[str, float]] = []
            for idx, raw_term in enumerate(vec.get_feature_names_out()):
                term = str(raw_term).strip()
                parts = term.split()
                if not parts or all(p.isdigit() for p in parts):
                    continue
                if len(parts) >= 2:
                    weight = 2.5 if len(parts) >= 3 else 2.0
                elif term in acronyms:
                    weight = 1.0
                else:
                    continue
                score = min(100.0, round(float(mean_scores[idx]) * weight * 100.0, 1))
                if score > 0.0:
                    scored.append((term, score))
            scored.sort(key=lambda item: item[1], reverse=True)
            keywords = scored[:top_n]
        except ValueError:
            keywords = []

    corpus_lower = " ".join(docs).lower()
    pos_cnt = sum(corpus_lower.count(w) for w in POSITIVE_WORDS)
    neg_cnt = sum(corpus_lower.count(w) for w in NEGATIVE_WORDS)

    if pos_cnt + neg_cnt == 0:
        sentiment = {"positive": 50.0, "neutral": 50.0, "negative": 0.0}
        overall_tone = "Sôi động / Thu hút tương tác cao"
    else:
        total = pos_cnt + neg_cnt + max(2.0, (pos_cnt + neg_cnt) * 0.5)
        pos_pct = round((pos_cnt / total) * 100, 1)
        neg_pct = round((neg_cnt / total) * 100, 1)
        sentiment = {"positive": pos_pct, "neutral": round(100.0 - pos_pct - neg_pct, 1), "negative": neg_pct}
        overall_tone = (
            "Tích cực / Hào hứng đón nhận"
            if pos_pct > 60.0
            else ("Nóng bỏng / Nhiều tranh cãi trái chiều" if neg_pct > 30.0 else "Sôi động / Thu hút tương tác cao")
        )

    return {"keywords": keywords, "sentiment": sentiment, "overall_tone": overall_tone}
