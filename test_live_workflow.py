import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, ".")

from src.scraper.rss_scraper import fetch_trending_news
from src.ai.generator import generate_tiktok_script
from src.models.content_evaluator import evaluate_tiktok_script
from src.video.muse_integration import generate_tiktok_video, find_ffmpeg_binary

print("=== BƯỚC 1: CÀO TIN TỨC NÓNG THỰC TẾ ===")
articles = fetch_trending_news("CongNghe", limit=5)
if not articles:
    articles = fetch_trending_news("GiaiTri", limit=5)

if not articles:
    print("ERROR: Không lấy được bài báo nào từ RSS.")
    sys.exit(1)

article = articles[0]
print(f"Tiêu đề: {article['title']}")
print(f"Nguồn: {article.get('source', 'GenK')}")
print(f"Link: {article.get('link', '')}")
print(f"Tóm tắt: {article.get('summary', '')[:140]}...")
print(f"Ảnh thumbnail: {article.get('thumbnail')}")

print("\n=== BƯỚC 2: TẠO KỊCH BẢN VIRAL TIKTOK ===")
script = generate_tiktok_script(
    title=article["title"],
    summary=article.get("summary", ""),
    engine="gemini",
    safe_fallback=True
)
print(f"Hook (0-3s): {script.get('hook')}")
print(f"Body (4-15s): {script.get('body')}")
print(f"CTA (16-20s): {script.get('cta')}")
print(f"Hashtags: {script.get('hashtags')}")
print(f"Theme gợi ý: {script.get('recommended_theme', 'tech')}")

print("\n=== BƯỚC 3: ĐÁNH GIÁ NỘI DUNG VIRAL BẰNG THUẬT TOÁN NLP ===")
source_full = f"{article['title']} {article.get('summary', '')}"
eval_report = evaluate_tiktok_script(script, source_full)
print(f"Tổng điểm Viral: {eval_report['overall_score']}/100")
print(f"Xếp hạng: Hạng {eval_report['grade']} - {eval_report['grade_title']}")
print(f"Chi tiết điểm: {json.dumps(eval_report['breakdown'], ensure_ascii=False)}")
print("Checklist khuyến nghị:")
for c in eval_report["actionable_checklist"]:
    print(f" - {c}")

print("\n=== BƯỚC 4: RENDER VIDEO DỌC TIKTOK 9:16 (THEME TECH / 20S) ===")
theme_choice = script.get("recommended_theme", "tech") or "tech"
thumb_url = article.get("thumbnail_url") or article.get("thumbnail")
video_res = generate_tiktok_video(
    visual_prompt=script.get("muse_visual_prompt", ""),
    reference_image_url=thumb_url,
    script_data=script,
    mode="fallback",
    duration=20,
    voice="vi-VN-HoaiMyNeural",
    theme=theme_choice
)
print("Kết quả kết xuất video:")
print(json.dumps(video_res, indent=2, ensure_ascii=False))

video_file = Path(video_res["video_path"])
if video_file.exists():
    print(f"\n=== BƯỚC 5: TRÍCH XUẤT 4 KHUNG HÌNH PHÂN CẢNH ĐỂ ĐÁNH GIÁ THỊ GIÁC ===")
    artifact_dir = Path(os.getenv("ARTIFACT_DIR", r"C:\Users\Rynne\.gemini\antigravity\brain\e0e8d16e-233e-4cba-b992-59812b7f024c"))
    ffmpeg_bin = find_ffmpeg_binary()
    
    scene_sample_times = [
        (1, 1.5),
        (2, 6.0),
        (3, 12.0),
        (4, 18.0)
    ]
    for s_idx, t_sec in scene_sample_times:
        out_jpg = Path(f"frame_scene{s_idx}.jpg")
        cmd = [
            ffmpeg_bin, "-y",
            "-ss", str(t_sec),
            "-i", str(video_file),
            "-frames:v", "1",
            "-q:v", "2",
            str(out_jpg)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        print(f" - Phân cảnh {s_idx} ({t_sec}s): {out_jpg.name} ({out_jpg.stat().st_size} bytes)")
        if artifact_dir.exists():
            shutil.copy2(out_jpg, artifact_dir / out_jpg.name)
            print(f"   -> Đã copy vào Artifact: {artifact_dir / out_jpg.name}")

