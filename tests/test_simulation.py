"""
Unit test for 24-Hour Grid Simulation Engine (Smart Context-Aware Edition).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.engine import simulate_24h_sweep, analyze_content_affinity


def test_analyze_content_affinity():
    # 1. Tin sáng cảnh báo khẩn cấp
    morning_text = "CẢNH BÁO LỪA ĐẢO SÁNG NAY: Tin nhắn SMS mạo danh ngân hàng xuất hiện diện rộng!"
    m_aff = analyze_content_affinity(morning_text)
    assert m_aff["morning_boost"] > m_aff["evening_boost"], "Morning boost should dominate for morning warning."
    
    # 2. Meme hài hước buổi trưa
    lunch_text = "Góc thư giãn trưa nay: Chú mèo đáng yêu ngủ gật giữa bàn ăn khiến ai cũng phì cười! #HaiHuoc"
    l_aff = analyze_content_affinity(lunch_text)
    assert l_aff["lunch_boost"] > m_aff["evening_boost"], "Lunch boost should be high for noon meme."
    
    print("test_analyze_content_affinity: PASSED")


def test_simulate_24h_sweep():
    test_content = "CẢNH BÁO LỪA ĐẢO SÁNG NAY: Kẻ gian dùng tin nhắn SMS mạo danh ngân hàng!"
    res = simulate_24h_sweep(test_content, target_date="2026-10-27", topic_category=1)
    
    # 1. Kiểm tra đủ 24 khung giờ
    assert len(res["hourly_results"]) == 24, "Simulation must return 24 hours."
    
    # 2. Kiểm tra giờ vàng hợp lệ (0 đến 23)
    assert 0 <= res["optimal_hour"] <= 23, "Invalid optimal hour."
    assert "optimal_hour_label" in res, "Missing optimal_hour_label."
    
    # 3. Kiểm tra 4 khung giờ vàng (golden_windows)
    gw = res["golden_windows"]
    assert "Sáng (07h - 09h)" in gw, "Missing morning window."
    assert "Trưa (11h - 13h)" in gw, "Missing lunch window."
    assert "Chiều (15h - 18h)" in gw, "Missing afternoon window."
    assert "Tối Prime Time (19h - 21h)" in gw, "Missing evening window."
    
    # 4. Kiểm tra lý do gợi ý (recommendation_reason)
    assert "recommendation_reason" in res and len(res["recommendation_reason"]) > 10, "Missing recommendation reason."
    
    # 5. Bài tin sáng phải đề xuất giờ sáng (6h - 9h)
    assert 6 <= res["optimal_hour"] <= 9, f"Morning news should peak in morning (6h-9h), got {res['optimal_hour']}h"
    
    print("test_simulate_24h_sweep: PASSED")


if __name__ == "__main__":
    test_analyze_content_affinity()
    test_simulate_24h_sweep()
    print("ALL SIMULATION TESTS PASSED SUCCESSFULLY.")
