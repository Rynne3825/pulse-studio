# ⚡ The Pulse Studio — Phân Tích Xu Hướng & Tối Ưu Hóa Bài Đăng AI

Ứng dụng Streamlit theo phong cách **Swiss Bento Light** giúp thu thập xu hướng báo chí Việt Nam, soạn bài đăng **Facebook / Threads** bằng **Gemini 3.8 Flash**, chấm điểm Viral 4 trụ cột minh bạch (XAI) và chạy tối ưu hóa khép kín (v1 → v2) phục vụ thực nghiệm đồ án.

## Luồng xử lý

```
RSS 4 chuyên mục → TF-IDF N-grams (Từ khóa + Sắc thái) → Gemini 3.8 Flash (v1)
→ PostViralEvaluator (Hook 25% · Cosine 35% · Cấu trúc 20% · CTA 20%)
→ Checklist phản hồi → refine_post (v2) → Thống kê Δ Score & Xuất CSV/Markdown
```

## Cấu trúc mã nguồn

| Thư mục / File | Vai trò |
|---|---|
| `app/app.py` | Điểm khởi chạy ứng dụng Streamlit (Header, KPI Ribbon & 3 Tabs) |
| `app/components/styles.py` | Hệ thống CSS Swiss Bento Light & micro-interactions |
| `app/components/header.py` | Thanh trạng thái LIVE, Stepper 3 bước, Popover công thức toán & 4 KPI Cards |
| `app/components/charts.py` | Biểu đồ Altair (Bar, Donut, 4 Trụ Cột, Xu hướng Lab) & SVG (Gauge, Radar) |
| `app/components/editor.py` | Tab 1 Radar RSS & Cột trái Tab 2 (Biên tập + Live Social Preview tương tác) |
| `app/components/curator.py` | Cột phải Tab 2 (Giám tuyển XAI + Tối ưu v2) & Tab 3 (Nhật ký thực nghiệm) |
| `app/components/utils.py` | Kiểm tra an toàn URL, render HTML sạch & hàm đánh giá trạng thái |
| `src/rss/scraper.py` | Cào tin RSS 4 tòa soạn (GenK, Kenh14, VnExpress, Tuổi Trẻ) + ảnh gốc |
| `src/nlp/trends.py` | Chuẩn hóa văn bản & khai phá từ khóa TF-IDF + sắc thái |
| `src/ai/generator.py` | Giao tiếp Gemini 3.8 Flash qua 9Router, parser JSON 7 tầng tự phục hồi |
| `src/eval/scorer.py` | Chấm điểm Viral đa tiêu chí 4 trụ cột & sinh danh sách khuyến nghị |
| `tests/` | Bộ kiểm thử đơn vị, kiểm thử đối kháng (adversarial) & sanity UI |

## Cài đặt & chạy ứng dụng

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # cấu hình ROUTER_API_KEY
run_app.bat                 # hoặc: .venv\Scripts\python.exe -m streamlit run app/app.py
```

## Chạy kiểm thử

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```
