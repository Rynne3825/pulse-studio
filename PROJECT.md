# Project: Pulse Studio — Social Media Trend & Post Optimization Studio

Đồ án: Radar xu hướng tin tức Việt Nam → soạn bài đăng Facebook / Threads bằng Gemini 3.8 Flash → chấm điểm Viral 4 trụ cột → tối ưu khép kín (closed-loop) và ghi nhận thực nghiệm v1 vs v2.

## Kiến trúc 4 tầng

1. **M1 – Trend Radar** (`src/rss/scraper.py`, `src/nlp/trends.py`)
   - 4 chuyên mục RSS (`RSS_CONFIG`): `CongNghe` (GenK), `GiaiTri` (Kenh14), `KinhDoanh` (VnExpress), `DoiSong` (Tuổi Trẻ), tự động chuẩn hóa URL ảnh phân giải cao.
   - `extract_trending_topics`: TF-IDF n-gram (1, 3), danh sách từ dừng tiếng Việt, tách cụm từ ghép & từ viết tắt, phân tích tỷ lệ sắc thái cộng đồng (tổng 100%).
2. **M2 – AI Post Generator** (`src/ai/generator.py`)
   - Sử dụng duy nhất mô hình Gemini 3.8 Flash qua Router (`ROUTER_BASE_URL`, mặc định `http://127.0.0.1:20128/v1`).
   - `generate_social_post(title, summary, platform, style, safe_fallback)`: Facebook (~90–220 từ) và Threads (~35–85 từ).
   - `refine_post(original_post, feedback_checklist, platform, title, summary)`: tối ưu dựa trên lỗi từ bộ đánh giá.
   - `self_healing_json_parser` 7 tầng kết hợp fallback an toàn khi gateway ngắt kết nối.
3. **M3 – Viral Evaluator** (`src/eval/scorer.py`)
   - `PostViralEvaluator` / `evaluate_post(post_data, source_text, platform)`: chấm điểm 0–100, xếp hạng S/A/B/C từ 4 trụ cột: Hook (25%) · Độ bám tin Cosine (35%) · Cấu trúc (20%) · CTA (20%).
4. **M4 – UI Studio (`app/`)**
   - `app/app.py`: Điểm khởi chạy kiến trúc Swiss Bento Light 3 Tabs (`Radar Xu Hướng`, `Xưởng Biên Tập & Giám Tuyển`, `Phòng Thí Nghiệm Khóa Luận`).
   - `app/components/`: Tách module rõ ràng `styles.py`, `header.py`, `charts.py`, `editor.py`, `curator.py`, `utils.py`.

## Cấu hình & Kiểm thử

- Cấu hình `.env` theo `.env.example` (`ROUTER_BASE_URL`, `ROUTER_API_KEY`, `ROUTER_MODEL=ag/gemini-3.8-flash-medium`).
- Kiểm thử: `.venv\Scripts\python.exe -m pytest tests/ -v`.
