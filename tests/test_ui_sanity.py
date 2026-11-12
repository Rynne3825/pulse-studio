"""UI sanity tests: import/syntax, offline AppTest render, charts, zero legacy code."""

import ast
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

APP_FILES = sorted((PROJECT_ROOT / "app").rglob("*.py"))
SRC_FILES = sorted((PROJECT_ROOT / "src").rglob("*.py"))
FORBIDDEN = ("lightgbm", "joblib", "edge_tts", "PIL", "src.video", "src.simulation", "muse_integration")


def _imports(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("path", APP_FILES + SRC_FILES, ids=lambda p: p.name)
def test_syntax_and_no_legacy_imports(path):
    imports = _imports(path)
    for name in imports:
        assert not any(name == f or name.startswith(f + ".") for f in FORBIDDEN), f"{path.name} imports {name}"


def test_legacy_modules_removed():
    removed = (
        "src/video",
        "src/simulation",
        "src/models",
        "src/preprocessing",
        "src/scraper",
        "models_saved",
        "docs/architecture.html",
    )
    for rel in removed:
        assert not (PROJECT_ROOT / rel).exists(), rel


def test_codebase_has_no_legacy_video_or_argon_text():
    for path in APP_FILES + SRC_FILES:
        text = path.read_text(encoding="utf-8").lower()
        assert "tiktok" not in text and "argon" not in text, path.name


def test_components_import():
    import importlib

    for mod in (
        "app.components.charts",
        "app.components.curator",
        "app.components.editor",
        "app.components.header",
        "app.components.styles",
        "app.components.utils",
    ):
        importlib.import_module(mod)


def test_charts_build_valid_specs():
    from app.components.charts import (
        build_keywords_bar_chart,
        build_sentiment_donut_chart,
        build_radial_gauge_html,
        build_radar_svg_html,
        build_four_pillars_altair,
        build_experiment_trend_altair,
    )

    kw_chart = build_keywords_bar_chart([("ai", 24.5), ("congnghe", 18.2)])
    assert kw_chart is not None and kw_chart.to_dict() is not None

    donut = build_sentiment_donut_chart({"positive": 60.0, "neutral": 30.0, "negative": 10.0})
    assert donut is not None and donut.to_dict() is not None

    gauge_html = build_radial_gauge_html(88.5, "S", "SIÊU TIỀM NĂNG", "#10B981", "v2 · ĐÃ TỐI ƯU")
    assert "88.5" in gauge_html and "HẠNG S" in gauge_html

    b1 = {"hook_score": 70, "trend_similarity_score": 75, "pacing_score": 68, "cta_score": 65}
    b2 = {"hook_score": 92, "trend_similarity_score": 95, "pacing_score": 88, "cta_score": 90}
    radar_svg = build_radar_svg_html(b2, breakdown_v1=b1)
    assert "<svg" in radar_svg and "polygon" in radar_svg

    pillars_chart = build_four_pillars_altair(b2, breakdown_v1=b1)
    assert pillars_chart is not None and pillars_chart.to_dict() is not None

    history = [
        {"timestamp": "10:00", "score_v1": 72.0, "score_v2": 88.0},
        {"timestamp": "10:05", "score_v1": 75.0, "score_v2": 91.0},
    ]
    trend_chart = build_experiment_trend_altair(history)
    assert trend_chart is not None and trend_chart.to_dict() is not None


def test_initial_render_offline():
    from streamlit.testing.v1 import AppTest

    with patch("src.rss.scraper.fetch_trending_news", return_value=[]), \
         patch("app.components.editor.fetch_trending_news", return_value=[]):
        at = AppTest.from_file(str(PROJECT_ROOT / "app" / "app.py"), default_timeout=60)
        at.run()
    assert len(at.exception) == 0, [e.message for e in at.exception]


def test_security_url_and_csv_sanitization():
    from app.components.utils import is_safe_url
    from app.components.curator import _sanitize_csv_cell

    assert is_safe_url("https://genk.vn/news.jpg")
    assert not is_safe_url("http://127.0.0.2:20128/v1")
    assert not is_safe_url("http://10.0.0.1/admin")
    assert not is_safe_url("http://[::1]:8501/")
    assert not is_safe_url("https://user:pass@example.com/a.jpg")
    assert not is_safe_url("javascript:alert(1)")

    assert _sanitize_csv_cell("=CMD|'/C calc'!A0") == "'=CMD|'/C calc'!A0"
    assert _sanitize_csv_cell("+SUM(A1:A2)") == "'+SUM(A1:A2)"
    assert _sanitize_csv_cell("Tiêu đề bình thường") == "Tiêu đề bình thường"
