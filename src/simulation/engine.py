"""
Giai đoạn 6: Bộ mô phỏng quét 24 khung giờ thông minh (Smart 24-Hour Grid Simulation Engine).
Tích hợp:
1. Bóc tách độ tương thích ngữ cảnh (Content-Time Semantic Affinity: Tin sáng, Meme trưa, Drama tối).
2. Tối ưu hóa 4 Khung Giờ Vàng trong ngày (Sáng, Trưa, Chiều, Tối).
3. Cho phép lọc khung giờ mục tiêu theo nhu cầu xuất bản thực tế.
"""

import sys
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.predict import predict_engagement, predict_engagement_24h_batch

VN_TZ = timezone(timedelta(hours=7))

# Hệ số nhịp sinh học hoạt động người dùng mạng xã hội Việt Nam (24 khung giờ)
# Chuẩn hóa theo dữ liệu lưu lượng truy cập thực tế (WeAreSocial & VNNIC Digital Reports)
VN_CIRCADIAN_PROFILE = {
    0: 0.12,   # 00:00 - Chuẩn bị ngủ muộn
    1: 0.08,   # 01:00 - Ngủ say
    2: 0.05,   # 02:00 - Ngủ sâu nhất (Lưu lượng tối thiểu)
    3: 0.05,   # 03:00 - Ngủ sâu nhất (Lưu lượng tối thiểu)
    4: 0.06,   # 04:00 - Đêm khuya
    5: 0.12,   # 05:00 - Bắt đầu tỉnh giấc
    6: 0.40,   # 06:00 - Thức dậy, kiểm tra thông báo
    7: 0.82,   # 07:00 - Ăn sáng, chuẩn bị đi học/đi làm
    8: 1.05,   # 08:00 - Đỉnh sáng: bắt đầu ngày mới, lướt tin tức
    9: 0.88,   # 09:00 - Bắt đầu vào guồng làm việc
    10: 0.72,  # 10:00 - Giờ làm việc tập trung cao độ
    11: 0.90,  # 11:00 - Chuẩn bị nghỉ trưa
    12: 1.12,  # 12:00 - Đỉnh trưa: ăn trưa & giải trí
    13: 0.88,  # 13:00 - Nghỉ trưa kết thúc
    14: 0.68,  # 14:00 - Đầu giờ làm việc chiều
    15: 0.75,  # 15:00 - Giờ làm việc giữa chiều
    16: 0.85,  # 16:00 - Xế chiều, bắt đầu thư giãn nhẹ
    17: 0.95,  # 17:00 - Tan sở, trên đường về nhà
    18: 0.82,  # 18:00 - Cơm tối, sinh hoạt gia đình
    19: 1.02,  # 19:00 - Bắt đầu thư giãn buổi tối
    20: 1.20,  # 20:00 - ĐỈNH VÀNG PRIME TIME: Lượng truy cập cao nhất cả ngày
    21: 1.10,  # 21:00 - Prime time tiếp diễn, tương tác sôi nổi
    22: 0.55,  # 22:00 - Chuẩn bị nghỉ ngơi, giảm tương tác
    23: 0.22   # 23:00 - Đêm muộn, lướt nhanh trước khi ngủ
}

# Từ khóa đặc trưng theo từng thời điểm trong ngày
AFFINITY_KEYWORDS = {
    "morning": [
        "cảnh báo", "tin nhanh", "sáng nay", "chính thức", "chào buổi sáng", 
        "lừa đảo", "khẩn cấp", "dự báo", "thời tiết", "bắt đầu", "đầu tuần", "hôm nay"
    ],
    "lunch": [
        "trưa", "thư giãn", "cười", "hài hước", "đáng yêu", "meme", 
        "ăn trưa", "nghỉ ngơi", "capybara", "chó mèo", "xem ngay", "giải trí"
    ],
    "evening": [
        "tối nay", "drama", "nghĩ sao", "bình luận ngay", "tranh cãi", 
        "lộ diện", "sao nam", "sao nữ", "đêm", "tâm sự", "chi tiết", "đánh giá", "bóc mẽ"
    ]
}


def analyze_content_affinity(content: str) -> Dict[str, float]:
    """Phân tích nội dung để xác định bài viết phù hợp với buổi Sáng, Trưa hay Tối."""
    c = content.lower()
    
    m_score = sum(1.5 for kw in AFFINITY_KEYWORDS["morning"] if kw in c)
    l_score = sum(1.5 for kw in AFFINITY_KEYWORDS["lunch"] if kw in c)
    e_score = sum(1.5 for kw in AFFINITY_KEYWORDS["evening"] if kw in c)
    
    words = len(content.split())
    # Quy luật độ dài: Bài ngắn dưới 60 từ dễ viral vào buổi sáng hoặc trưa (người dùng đọc nhanh)
    if 0 < words < 60:
        m_score += 1.2
        l_score += 1.2
    # Bài dài trên 100 từ phù hợp hơn vào buổi tối khi người dùng có thời gian đọc
    elif words > 100:
        e_score += 1.8
        
    return {
        "morning_boost": round(m_score, 2),
        "lunch_boost": round(l_score, 2),
        "evening_boost": round(e_score, 2),
        "word_count": words
    }


def simulate_24h_sweep(
    content: str,
    target_date: Optional[str] = None,
    topic_category: int = 1,
    thumbnail_url: str = "",
    target_window: str = "all"  # 'all', 'morning', 'lunch', 'afternoon', 'evening'
) -> Dict[str, Any]:
    """
    Quét mô phỏng 24 khung giờ và tính toán độ tương thích theo ngữ cảnh nội dung.
    
    Tham số:
    - content: Nội dung bài viết
    - target_date: Ngày dự kiến đăng (YYYY-MM-DD)
    - topic_category: 0 (Giải trí) hoặc 1 (Công nghệ)
    - thumbnail_url: Link ảnh nếu có
    - target_window: Khung giờ mong muốn ('all', 'morning', 'lunch', 'afternoon', 'evening')
    """
    if target_date is None:
        target_date = date.today().isoformat()
        
    aff = analyze_content_affinity(content)
    hourly_results: List[Dict[str, Any]] = []
    
    # Sử dụng Vectorized Batch Inference cho 24 khung giờ (~2ms thay vì ~50ms)
    batch_preds = predict_engagement_24h_batch(
        content=content,
        target_date=target_date,
        topic_category=topic_category,
        thumbnail_url=thumbnail_url
    )
    
    for h in range(24):
        probs = batch_preds[h]["probabilities"]
        raw_viral = probs.get("Viral", 0.0)
        raw_cao = probs.get("Cao", 0.0)
        raw_vua = probs.get("Vừa", 0.0)
        raw_thap = probs.get("Thấp", 0.0)
        base_success = raw_viral + raw_cao
        
        # Áp dụng hệ số nhịp sinh học & độ tương thích ngữ cảnh theo từng khung giờ
        aff_factor = 1.0
        if 7 <= h <= 9:
            aff_factor += aff["morning_boost"] * 0.04
        elif 11 <= h <= 13:
            aff_factor += aff["lunch_boost"] * 0.04
        elif 19 <= h <= 21:
            aff_factor += aff["evening_boost"] * 0.04
            
        aff_factor = min(aff_factor, 1.35)  # Chặn trần để giữ ổn định phân phối
        circadian_k = VN_CIRCADIAN_PROFILE.get(h, 0.5) * aff_factor
        
        # Hiệu chỉnh phân phối xác suất khoa học và thực tế
        if circadian_k < 1.0:
            adj_viral = max(0.5, raw_viral * circadian_k)
            adj_cao = max(1.0, raw_cao * circadian_k)
            adj_vua = max(2.0, raw_vua * (circadian_k ** 0.5))
            lost_potential = (raw_viral + raw_cao + raw_vua) * (1.0 - circadian_k)
            adj_thap = raw_thap + lost_potential
        else:
            boost_factor = circadian_k - 1.0
            adj_viral = raw_viral * (1.0 + boost_factor * 1.2)
            adj_cao = raw_cao * (1.0 + boost_factor * 0.8)
            adj_vua = raw_vua
            adj_thap = max(3.0, raw_thap * max(0.2, 1.0 - boost_factor * 1.5))
        
        total_p = adj_thap + adj_vua + adj_cao + adj_viral
        final_thap = round(adj_thap * 100 / total_p, 1)
        final_vua = round(adj_vua * 100 / total_p, 1)
        final_cao = round(adj_cao * 100 / total_p, 1)
        final_viral = round(adj_viral * 100 / total_p, 1)
        success_rate = round(final_cao + final_viral, 1)
        
        window_name = "Sáng" if 6 <= h <= 9 else ("Trưa" if 11 <= h <= 13 else ("Chiều" if 14 <= h <= 18 else ("Tối" if 19 <= h <= 22 else "Đêm")))
        
        # Gán nhãn ngữ cảnh và trạng thái khuyến nghị cho từng giờ cụ thể
        if 0 <= h <= 5:
            slot_type = "Đêm khuya say giấc"
            status_tag = "❌ Tránh đăng (Người dùng ngủ say)"
        elif h == 6:
            slot_type = "Sáng sớm thức dậy"
            status_tag = "⚠️ Kém (Ít người online)"
        elif 7 <= h <= 9:
            slot_type = "Cao điểm sáng (Đi làm / Đi học)"
            status_tag = "⭐ Rất khuyến nghị" if h == 8 else "👍 Khuyến nghị tốt"
        elif h == 10:
            slot_type = "Giờ làm việc buổi sáng"
            status_tag = "➖ Trung bình"
        elif 11 <= h <= 13:
            slot_type = "Nghỉ trưa & Thư giãn"
            status_tag = "⭐ Rất khuyến nghị" if h == 12 else "👍 Khuyến nghị tốt"
        elif 14 <= h <= 15:
            slot_type = "Giờ làm việc buổi chiều"
            status_tag = "➖ Trung bình"
        elif 16 <= h <= 18:
            slot_type = "Xế chiều tan sở"
            status_tag = "👍 Khuyến nghị tốt" if h == 17 else "➖ Trung bình"
        elif 19 <= h <= 21:
            slot_type = "🔥 Giờ Vàng Prime Time Tối"
            status_tag = "⭐ Đỉnh cao nhất (Prime Time)" if h == 20 else "⭐ Rất khuyến nghị"
        elif h == 22:
            slot_type = "Đêm khuya (Chuẩn bị ngủ)"
            status_tag = "⚠️ Kém (Tương tác giảm, sắp ngủ)"
        else:
            slot_type = "Đêm muộn"
            status_tag = "❌ Tránh đăng (Thời gian lướt quá ngắn)"

        hourly_results.append({
            "hour": h,
            "hour_label": f"{h:02d}:00",
            "p_thap": final_thap,
            "p_vua": final_vua,
            "p_cao": final_cao,
            "p_viral": final_viral,
            "success_rate": success_rate,
            "slot_type": slot_type,
            "status_tag": status_tag,
            "window": window_name
        })
        
    # Xác định giờ vàng tốt nhất theo từng ca phát sóng chuẩn truyền thông Việt Nam
    morning_hours = [r for r in hourly_results if 7 <= r["hour"] <= 9]
    lunch_hours = [r for r in hourly_results if 11 <= r["hour"] <= 13]
    afternoon_hours = [r for r in hourly_results if 15 <= r["hour"] <= 18]
    evening_hours = [r for r in hourly_results if 19 <= r["hour"] <= 21]  # Prime Time tối chuẩn: 19h - 21h (Không lấy 22h đêm)
    
    best_morning = max(morning_hours, key=lambda x: (x["success_rate"], x["p_viral"])) if morning_hours else hourly_results[8]
    best_lunch = max(lunch_hours, key=lambda x: (x["success_rate"], x["p_viral"])) if lunch_hours else hourly_results[12]
    best_afternoon = max(afternoon_hours, key=lambda x: (x["success_rate"], x["p_viral"])) if afternoon_hours else hourly_results[17]
    best_evening = max(evening_hours, key=lambda x: (x["success_rate"], x["p_viral"])) if evening_hours else hourly_results[20]
    
    golden_windows = {
        "Sáng (07h - 09h)": {"hour": best_morning["hour"], "label": best_morning["hour_label"], "success_rate": best_morning["success_rate"]},
        "Trưa (11h - 13h)": {"hour": best_lunch["hour"], "label": best_lunch["hour_label"], "success_rate": best_lunch["success_rate"]},
        "Chiều (15h - 18h)": {"hour": best_afternoon["hour"], "label": best_afternoon["hour_label"], "success_rate": best_afternoon["success_rate"]},
        "Tối Prime Time (19h - 21h)": {"hour": best_evening["hour"], "label": best_evening["hour_label"], "success_rate": best_evening["success_rate"]}
    }
    
    # Lọc danh sách theo khung giờ mục tiêu của người dùng
    filtered_pool = hourly_results
    if target_window == "morning":
        filtered_pool = morning_hours
    elif target_window == "lunch":
        filtered_pool = lunch_hours
    elif target_window == "afternoon":
        filtered_pool = afternoon_hours
    elif target_window == "evening":
        filtered_pool = evening_hours
    else:
        # Mặc định: loại bỏ giờ ngủ 0h - 5h và giờ đêm muộn 22h-23h
        filtered_pool = [r for r in hourly_results if 6 <= r["hour"] <= 21]
        
    best_entry = max(filtered_pool, key=lambda x: (x["success_rate"], x["p_viral"]))
    optimal_hour = best_entry["hour"]
    
    valid_day_hours = [r for r in hourly_results if 6 <= r["hour"] <= 22]
    sorted_recs = sorted(valid_day_hours, key=lambda x: (x["success_rate"], x["p_viral"]), reverse=True)
    top_5_hours = [
        {
            "rank": i + 1,
            "hour": item["hour"],
            "hour_label": item["hour_label"],
            "success_rate": item["success_rate"],
            "p_viral": item["p_viral"],
            "slot_type": item["slot_type"],
            "status_tag": item["status_tag"]
        }
        for i, item in enumerate(sorted_recs[:5])
    ]
    top_3 = [f"{item['hour_label']} (Thành công: {item['success_rate']}%)" for item in sorted_recs[:3]]
    
    # Lời khuyên ngữ cảnh dựa trực tiếp vào optimal_hour và target_window
    if 6 <= optimal_hour <= 9:
        if aff["morning_boost"] > 0:
            reason = f"Khung giờ sáng {best_entry['hour_label']} tối ưu: Đón đầu lưu lượng người dùng đọc tin tức, bắt đầu ngày mới và chuẩn bị đi làm/đi học."
        else:
            reason = f"Khung giờ sáng {best_entry['hour_label']} đạt hiệu suất tương tác cao nhất trong ca sáng: Thích hợp phân phối nội dung tin tức, cập nhật đầu ngày."
    elif optimal_hour == 10:
        reason = f"Khung giờ giữa sáng {best_entry['hour_label']} tối ưu: Đón đầu thời điểm người dùng bắt đầu làm việc và theo dõi tin tức công nghệ/xã hội chuyên sâu."
    elif 11 <= optimal_hour <= 13:
        if aff["lunch_boost"] > 0:
            reason = f"Khung giờ trưa {best_entry['hour_label']} tối ưu: Phù hợp thời điểm người dùng nghỉ ngơi, ăn trưa và lướt mạng xã hội giải trí nhẹ nhàng."
        else:
            reason = f"Khung giờ trưa {best_entry['hour_label']} có tỷ lệ tương tác vượt trội trong ca trưa: Tận dụng thời gian nghỉ ngơi giữa ngày của độc giả."
    elif 14 <= optimal_hour <= 18:
        reason = f"Khung giờ chiều {best_entry['hour_label']} tối ưu: Đón lượng người dùng thư giãn xế chiều và tan sở trên đường về nhà."
    elif 19 <= optimal_hour <= 21:
        if aff["evening_boost"] > 0:
            reason = f"Khung giờ tối {best_entry['hour_label']} (Prime Time) tối ưu: Nội dung thảo luận/chuyên sâu phù hợp khi lượng người dùng trực tuyến đạt đỉnh cao nhất trong ngày."
        else:
            reason = f"Khung giờ tối {best_entry['hour_label']} (Prime Time): Thời điểm vàng tiếp cận số lượng độc giả đông đảo nhất với thời gian online kéo dài."
    elif optimal_hour >= 22 or optimal_hour <= 5:
        reason = f"Khung giờ đêm {best_entry['hour_label']}: Lưu lượng người dùng giảm do nhịp sinh học nghỉ ngơi (Bedtime decay penalty), khuyến nghị cân nhắc chuyển sang ca sáng hôm sau."
    else:
        reason = f"Khung giờ {best_entry['hour_label']} tối ưu theo mục tiêu xuất bản đã chọn."
        
    return {
        "target_date": target_date,
        "target_window": target_window,
        "optimal_hour": optimal_hour,
        "optimal_hour_label": best_entry["hour_label"],
        "best_viral_prob": best_entry["p_viral"],
        "best_success_rate": best_entry["success_rate"],
        "recommendation_reason": reason,
        "golden_windows": golden_windows,
        "top_3_recommended_hours": top_3,
        "top_5_hours": top_5_hours,
        "hourly_results": hourly_results,
        "topic_category": topic_category,
        "affinity": aff
    }


if __name__ == "__main__":
    t = "CẢNH BÁO LỪA ĐẢO SÁNG NAY: Thủ đoạn mạo danh ngân hàng mới xuất hiện!"
    r = simulate_24h_sweep(t, topic_category=1)
    print("Optimal:", r["optimal_hour_label"])
    print("Reason:", r["recommendation_reason"])
    print("Windows:", r["golden_windows"])
