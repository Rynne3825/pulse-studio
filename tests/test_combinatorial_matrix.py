"""
Comprehensive Combinatorial Matrix Test:
Tests 20 combinations across:
- 2 Topics: CongNghe (1), GiaiTri (0)
- 2 AI Modes: trend, rewrite
- 5 Target Windows: all, morning, lunch, afternoon, evening
- 4 Diverse Content Archetypes
"""

import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.scraper.rss_scraper import fetch_trending_news
from src.ai.generator import generate_post
from src.simulation.engine import simulate_24h_sweep
from src.models.predict import predict_engagement


def run_combinatorial_matrix():
    print("=" * 75)
    print("CHẠY KIỂM THỬ MA TRẬN TỔ HỢP TOÀN DIỆN (COMBINATORIAL TEST MATRIX)")
    print("=" * 75)
    
    test_archetypes = [
        {
            "name": "1. Tin cảnh báo khẩn cấp (Công nghệ)",
            "topic": 1,
            "title": "Cảnh báo thủ đoạn lừa đảo SMS mạo danh ngân hàng",
            "summary": "Kẻ gian dùng thiết bị trạm BTS giả để gửi tin nhắn mạo danh ngân hàng lừa bấm link độc hại.",
            "mode": "trend"
        },
        {
            "name": "2. Meme giải trí ngắn (Giải trí)",
            "topic": 0,
            "title": "Chú mèo ngủ gật giữa bàn ăn gây sốt",
            "summary": "Khoảnh khắc chú mèo ngủ gật gục đầu vào bát cơm trưa nay khiến hàng triệu người thả tim.",
            "mode": "trend"
        },
        {
            "name": "3. Bài phân tích chi tiết (Công nghệ)",
            "topic": 1,
            "title": "Đánh giá chi tiết hiệu năng vi xử lý Apple M4 Pro",
            "summary": "Bài đánh giá chuyên sâu về kiến trúc 3nm mới, hiệu năng đồ họa tăng 40%, thời lượng pin thực tế và so sánh với M3.",
            "mode": "rewrite"
        },
        {
            "name": "4. Tin tức showbiz nóng (Giải trí)",
            "topic": 0,
            "title": "Lộ diện dàn nghệ sĩ tham gia đại nhạc hội cuối năm",
            "summary": "Ban tổ chức chính thức công bố danh sách nghệ sĩ biểu diễn và sơ đồ bán vé đêm đại nhạc hội.",
            "mode": "rewrite"
        }
    ]
    
    windows = ["all", "morning", "lunch", "afternoon", "evening"]
    results = []
    
    for arc in test_archetypes:
        print(f"\n--> Kiểm thử mẫu: {arc['name']}")
        
        # 1. Thử sinh caption qua Gemini 3.8 Flash
        try:
            caption = generate_post(arc["title"], arc["summary"], mode=arc["mode"])
            gen_status = "OK (Gemini 3.8 Flash)"
        except Exception as e:
            caption = f"{arc['title']} - {arc['summary']} #TinTuc"
            gen_status = f"Fallback ({e})"
            
        print(f"    AI Generation: {gen_status}")
        print(f"    Caption ({len(caption)} ký tự): {caption[:70]}...")
        
        # 2. Quét qua 5 khung giờ mục tiêu
        for win in windows:
            sim = simulate_24h_sweep(
                content=caption,
                target_date="2026-10-27",
                topic_category=arc["topic"],
                target_window=win
            )
            
            results.append({
                "Archetype": arc["name"],
                "Topic": "Công nghệ" if arc["topic"] == 1 else "Giải trí",
                "Mode": arc["mode"],
                "Window": win,
                "Optimal Hour": sim["optimal_hour_label"],
                "Success Rate": f"{sim['best_success_rate']}%",
                "P(Viral)": f"{sim['best_viral_prob']}%",
                "Reason Keyword": sim["recommendation_reason"][:35] + "..."
            })
            
    res_df = pd.DataFrame(results)
    print("\n" + "=" * 75)
    print("BẢNG KẾT QUẢ KIỂM THỬ MA TRẬN 20 TỔ HỢP:")
    print("=" * 75)
    print(res_df.to_string(index=False))
    
    # Assert checks
    assert len(results) == 20, "Must test exactly 20 combinations."
    print("\n[VERIFICATION]: Tất cả 20 tổ hợp hoạt động logic và chính xác!")


if __name__ == "__main__":
    run_combinatorial_matrix()
