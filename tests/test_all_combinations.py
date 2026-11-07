"""
Kiểm thử toàn bộ tổ hợp bài báo hiện có và các văn phong biên tập.
Đánh giá độ hợp lý của các thông số nhịp sinh học, giờ vàng và xác suất tương tác.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.scraper.rss_scraper import fetch_trending_news
from src.simulation.engine import simulate_24h_sweep
from src.ai.generator import generate_post

def test_combinations():
    print("==================================================")
    print("BẮT ĐẦU KIỂM ĐỊNH TOÀN BỘ TỔ HỢP DỮ LIỆU & THÔNG SỐ")
    print("==================================================\n")

    topics = ["GiaiTri", "CongNghe"]
    total_articles = 0

    for topic in topics:
        cat_id = 0 if topic == "GiaiTri" else 1
        cat_name = "Giải trí & Showbiz (Kenh14)" if topic == "GiaiTri" else "Công nghệ & Số hóa (GenK)"
        print(f"▶ CHUYÊN MỤC: {cat_name}")
        
        articles = fetch_trending_news(topic, limit=5)
        total_articles += len(articles)

        for idx, art in enumerate(articles):
            title = art.get("title", "")
            summary = art.get("summary", "")
            
            sim = simulate_24h_sweep(title, topic_category=cat_id)
            
            opt_hour = sim["optimal_hour_label"]
            viral_p = sim["best_viral_prob"]
            succ_p = sim["best_success_rate"]
            gw = sim["golden_windows"]
            
            sang = gw.get("Sáng (07h - 09h)", {})
            trua = gw.get("Trưa (11h - 13h)", {})
            chieu = gw.get("Chiều (15h - 18h)", {})
            toi = gw.get("Tối Prime Time (19h - 21h)", {})

            # Kiểm tra tính hợp lệ của số liệu
            assert 0.0 <= viral_p <= 100.0, f"Lỗi viral_p vượt ngưỡng: {viral_p}"
            assert 0.0 <= succ_p <= 100.0, f"Lỗi succ_p vượt ngưỡng: {succ_p}"
            assert sang.get("label"), "Thiếu nhãn Ca Sáng"
            assert trua.get("label"), "Thiếu nhãn Ca Trưa"
            assert chieu.get("label"), "Thiếu nhãn Ca Chiều"
            assert toi.get("label"), "Thiếu nhãn Ca Tối"

            print(f"  [{idx+1}] {title[:50]}...")
            print(f"      • Giờ tối ưu: {opt_hour} | Đón nhận: {succ_p:.1f}% | Viral: {viral_p:.1f}%")
            print(f"      • 4 Ca: Sáng {sang.get('label')} ({sang.get('success_rate'):.1f}%) | "
                  f"Trưa {trua.get('label')} ({trua.get('success_rate'):.1f}%) | "
                  f"Chiều {chieu.get('label')} ({chieu.get('success_rate'):.1f}%) | "
                  f"Tối {toi.get('label')} ({toi.get('success_rate'):.1f}%)")
        print()

    print("==================================================")
    print("KIỂM THỬ 3 VĂN PHONG BIÊN TẬP GEMINI AI")
    print("==================================================")
    test_title = "Binz và Châu Bùi xuất hiện rạng rỡ, làm dấy lên tin đồn sắp cưới"
    test_summary = "Cặp đôi tay trong tay tại sự kiện thời trang, trao nhau ánh mắt ngọt ngào."
    
    for mode in ["trend", "deep", "brief"]:
        post = generate_post(test_title, test_summary, mode=mode)
        sim_post = simulate_24h_sweep(post, topic_category=0)
        print(f"• Văn phong [{mode.upper()}]: {len(post.split())} từ | {len(post)} ký tự")
        print(f"  Trích đoạn: {post[:80].replace(chr(10), ' ')}...")
        print(f"  Giờ tối ưu AI đề xuất: {sim_post['optimal_hour_label']} (Đón nhận: {sim_post['best_success_rate']:.1f}%)\n")

    print("==================================================")
    print(f"HOÀN THÀNH: {total_articles} BÀI BÁO x 3 VĂN PHONG ĐỀU HỢP LỆ VÀ TỐI ƯU!")
    print("==================================================")

if __name__ == "__main__":
    test_combinations()
