"""
THE PULSE STUDIO - HỆ THỐNG BIỂU ĐỒ TRỰC QUAN CAO CẤP (ALTAIR & ANIMATED SVG)
- Top từ khóa TF-IDF có track nền, xếp hạng #1-#8 và nhãn % trực tiếp
- Donut sắc thái cộng đồng có KPI trung tâm & nền trong suốt hoàn toàn
- Animated SVG Radial Score Gauge đa vòng
- Interactive SVG 4-Axis Radar Chart (hỗ trợ chồng lớp v1 vs v2)
- Altair Grouped Bar 4 Trụ Cột có nhãn điểm trực tiếp + ngưỡng 85đ Hạng S
- Biểu đồ xu hướng cải thiện thực nghiệm v1 -> v2 (Tab 3)
"""

import html
import math
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import altair as alt


def build_keywords_bar_chart(keywords: List[Tuple[str, float]]) -> alt.LayerChart:
    """Biểu đồ cột ngang có track nền & nhãn trực tiếp cho Top từ khóa TF-IDF (%)."""
    records = [
        {"Nhãn": f"#{idx}. {kw}", "Từ khóa": f"#{kw}", "Độ nóng (%)": round(float(val), 1), "Hạng": idx}
        for idx, (kw, val) in enumerate(keywords[:8], start=1)
    ]
    df = pd.DataFrame(records)
    max_val = max((r["Độ nóng (%)"] for r in records), default=20.0)
    x_max = max(18.0, round(max_val * 1.25, 1))
    df["track_max"] = x_max

    hover = alt.selection_point(on="pointerover", empty=True)

    base = alt.Chart(df).encode(
        y=alt.Y(
            "Nhãn:N",
            sort=alt.SortField(field="Hạng", order="ascending"),
            title=None,
            axis=alt.Axis(
                labelLimit=165,
                labelOverlap=False,
                labelPadding=10,
                labelFont="Plus Jakarta Sans",
                labelFontSize=12,
                labelFontWeight="bold",
                labelColor="#1E293B",
                ticks=False,
                domain=False,
            ),
        )
    )

    tracks = base.mark_bar(cornerRadius=6, height=22, color="#F1F5F9").encode(
        x=alt.X("track_max:Q", scale=alt.Scale(domain=[0, x_max]), title=None)
    )

    bars = base.mark_bar(cornerRadius=6, height=22).encode(
        x=alt.X(
            "Độ nóng (%):Q",
            scale=alt.Scale(domain=[0, x_max]),
            title="Trọng số TF-IDF (%)",
            axis=alt.Axis(gridColor="#F1F5F9", labelColor="#64748B", titleColor="#64748B", titleFontSize=11),
        ),
        color=alt.Color(
            "Độ nóng (%):Q",
            scale=alt.Scale(range=["#818CF8", "#4F46E5"]),
            legend=None,
        ),
        opacity=alt.condition(hover, alt.value(1.0), alt.value(0.82)),
        tooltip=[
            alt.Tooltip("Hạng:Q", title="Xếp hạng"),
            alt.Tooltip("Từ khóa:N", title="Cụm từ khóa"),
            alt.Tooltip("Độ nóng (%):Q", format=".1f", title="Trọng số (%)"),
        ],
    ).add_params(hover)

    labels = base.mark_text(
        align="left",
        baseline="middle",
        dx=7,
        font="JetBrains Mono",
        fontSize=11,
        fontWeight="bold",
        color="#312E81",
    ).encode(
        x=alt.X("Độ nóng (%):Q"),
        text=alt.Text("Độ nóng (%):Q", format=".1f"),
    )

    return (
        alt.layer(tracks, bars, labels)
        .properties(height=max(220, len(records) * 35))
        .configure(background="transparent")
        .configure_view(strokeWidth=0)
    )


def build_sentiment_donut_chart(sentiment: Dict[str, Any]) -> alt.LayerChart:
    """Biểu đồ Donut sắc thái dư luận có KPI lớn ở tâm."""
    pos = round(float(sentiment.get("positive", 50.0)), 1)
    neu = round(float(sentiment.get("neutral", 40.0)), 1)
    neg = round(float(sentiment.get("negative", 10.0)), 1)

    df = pd.DataFrame([
        {"Sắc thái": "Tích cực", "Tỷ lệ": pos},
        {"Sắc thái": "Trung tính", "Tỷ lệ": neu},
        {"Sắc thái": "Tiêu cực", "Tỷ lệ": neg},
    ])

    dominant = max(
        [("Tích cực", pos, "#059669"), ("Trung tính", neu, "#D97706"), ("Tiêu cực", neg, "#E11D48")],
        key=lambda item: item[1],
    )
    df_center = pd.DataFrame([{"val": f"{dominant[1]:.1f}%", "lbl": dominant[0]}])

    hover = alt.selection_point(on="pointerover", empty=True)

    arc = (
        alt.Chart(df)
        .mark_arc(innerRadius=56, outerRadius=86, cornerRadius=5, padAngle=0.035)
        .encode(
            theta=alt.Theta("Tỷ lệ:Q", stack=True),
            color=alt.Color(
                "Sắc thái:N",
                scale=alt.Scale(
                    domain=["Tích cực", "Trung tính", "Tiêu cực"],
                    range=["#10B981", "#F59E0B", "#F43F5E"],
                ),
                legend=None,
            ),
            opacity=alt.condition(hover, alt.value(1.0), alt.value(0.84)),
            tooltip=["Sắc thái:N", alt.Tooltip("Tỷ lệ:Q", format=".1f", title="Tỷ lệ (%)")],
        )
        .add_params(hover)
    )

    center_val = (
        alt.Chart(df_center)
        .mark_text(font="JetBrains Mono", fontSize=19, fontWeight="bold", dy=-7, color=dominant[2])
        .encode(text="val:N")
    )
    center_lbl = (
        alt.Chart(df_center)
        .mark_text(font="Plus Jakarta Sans", fontSize=11, fontWeight="bold", dy=12, color="#64748B")
        .encode(text="lbl:N")
    )

    return (
        alt.layer(arc, center_val, center_lbl)
        .properties(height=205, padding={"left": 4, "right": 4, "top": 4, "bottom": 4})
        .configure(background="transparent")
        .configure_view(strokeWidth=0)
    )


def build_radial_gauge_html(
    score: float,
    grade: str,
    grade_title: str,
    grade_color: str,
    version_badge: str,
) -> str:
    """Tạo SVG Radial Gauge động cho điểm Viral Hero (0 - 100)."""
    clamped = max(0.0, min(100.0, float(score)))
    radius = 48.0
    circumference = 2.0 * math.pi * radius
    dashoffset = round(circumference * (1.0 - clamped / 100.0), 2)

    safe_grade = html.escape(str(grade))
    safe_title = html.escape(str(grade_title))
    safe_color = html.escape(str(grade_color))
    safe_ver = html.escape(str(version_badge))

    return f"""
    <div style="background:linear-gradient(180deg,#FFFFFF 0%,#F8FAFC 100%);border:1px solid #E2E8F0;border-radius:14px;padding:1rem 0.85rem;text-align:center;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;">
        <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.06em;color:#64748B;text-transform:uppercase;margin-bottom:0.4rem;">
            {safe_ver}
        </div>
        <div style="position:relative;width:134px;height:134px;margin:0.15rem auto;">
            <svg viewBox="0 0 120 120" width="134" height="134" style="transform:rotate(-90deg);">
                <circle cx="60" cy="60" r="56" fill="none" stroke="#E2E8F0" stroke-width="1" stroke-dasharray="2 4" />
                <circle cx="60" cy="60" r="{radius}" fill="none" stroke="#E2E8F0" stroke-width="10" />
                <circle
                    class="svg-ring-progress"
                    cx="60" cy="60" r="{radius}" fill="none"
                    stroke="{safe_color}" stroke-width="10" stroke-linecap="round"
                    stroke-dasharray="{circumference:.2f}"
                    stroke-dashoffset="{dashoffset}"
                />
            </svg>
            <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:1.88rem;font-weight:700;color:#0F172A;line-height:1;">{clamped:.1f}</span>
                <span style="font-size:0.72rem;font-weight:600;color:#64748B;margin-top:3px;">/ 100 điểm</span>
            </div>
        </div>
        <div style="margin-top:0.55rem;display:inline-block;background:{safe_color};color:#FFFFFF;font-weight:700;font-size:0.74rem;padding:4px 12px;border-radius:999px;letter-spacing:0.03em;white-space:nowrap;">
            HẠNG {safe_grade} · {safe_title}
        </div>
    </div>
    """


def build_radar_svg_html(
    breakdown_current: Dict[str, Any],
    breakdown_v1: Optional[Dict[str, Any]] = None,
) -> str:
    """Vẽ biểu đồ mạng nhện SVG 4 Trụ Cột Vàng (Hỗ trợ chồng lớp so sánh v1 vs v2)."""
    cx, cy, max_r = 165.0, 128.0, 78.0
    axes = [
        ("Hook (25%)", "hook_score", 0.0, -1.0, "middle", -11.0),
        ("Bám tin (35%)", "trend_similarity_score", 1.0, 0.0, "start", 7.0),
        ("Cấu trúc (20%)", "pacing_score", 0.0, 1.0, "middle", 15.0),
        ("CTA (20%)", "cta_score", -1.0, 0.0, "end", -7.0),
    ]

    grid_polys: List[str] = []
    for level in (25, 50, 75, 100):
        r = max_r * (level / 100.0)
        pts = " ".join(f"{cx + ax * r:.1f},{cy + ay * r:.1f}" for _, _, ax, ay, _, _ in axes)
        grid_polys.append(f'<polygon points="{pts}" fill="none" stroke="#E2E8F0" stroke-width="1" />')

    target_r = max_r * 0.85
    target_pts = " ".join(f"{cx + ax * target_r:.1f},{cy + ay * target_r:.1f}" for _, _, ax, ay, _, _ in axes)
    grid_polys.append(
        f'<polygon points="{target_pts}" fill="rgba(16, 185, 129, 0.06)" stroke="#10B981" stroke-width="1.3" stroke-dasharray="4 3" opacity="0.85" />'
    )

    axis_lines = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{cx + ax * max_r:.1f}" y2="{cy + ay * max_r:.1f}" stroke="#CBD5E1" stroke-width="1" />'
        for _, _, ax, ay, _, _ in axes
    )

    def _poly_coords(b: Dict[str, Any]) -> Tuple[str, List[Tuple[float, float, float]]]:
        pts_str_list: List[str] = []
        coords: List[Tuple[float, float, float]] = []
        for _, key, ax, ay, _, _ in axes:
            val = max(0.0, min(100.0, float(b.get(key, 0.0))))
            r = max_r * (max(6.0, val) / 100.0)
            px = cx + ax * r
            py = cy + ay * r
            pts_str_list.append(f"{px:.1f},{py:.1f}")
            coords.append((px, py, val))
        return " ".join(pts_str_list), coords

    v1_layer = ""
    if breakdown_v1 is not None:
        v1_pts, _ = _poly_coords(breakdown_v1)
        v1_layer = (
            f'<polygon points="{v1_pts}" fill="rgba(148, 163, 184, 0.18)" '
            f'stroke="#94A3B8" stroke-width="1.8" stroke-dasharray="4 3" />'
        )

    cur_color = "#10B981" if breakdown_v1 is not None else "#4F46E5"
    cur_fill = "rgba(16, 185, 129, 0.24)" if breakdown_v1 is not None else "rgba(79, 70, 229, 0.20)"
    cur_pts, cur_coords = _poly_coords(breakdown_current)
    cur_layer = f'<polygon points="{cur_pts}" fill="{cur_fill}" stroke="{cur_color}" stroke-width="2.4" />'

    dots = "".join(
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.4" fill="{cur_color}" stroke="#FFFFFF" stroke-width="1.6" />'
        for px, py, _ in cur_coords
    )

    labels_svg = ""
    for (lbl, key, ax, ay, anchor, off), (_, _, val) in zip(axes, cur_coords):
        lx = cx + ax * (max_r + 12.0)
        ly = cy + ay * (max_r + 12.0) + (off if ax == 0 else -4.0)
        if ax != 0:
            lx += off
        labels_svg += (
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'font-family="Plus Jakarta Sans, sans-serif" font-size="10.5" font-weight="600" fill="#334155">{html.escape(lbl)}</text>'
            f'<text x="{lx:.1f}" y="{ly + 12.5:.1f}" text-anchor="{anchor}" '
            f'font-family="JetBrains Mono, monospace" font-size="10.5" font-weight="700" fill="{cur_color}">{val:.0f}đ</text>'
        )

    legend_html = (
        '<span style="color:#64748B;">--- v1 Trước</span> · <span style="color:#059669;font-weight:700;">● v2 Sau</span> · <span style="color:#10B981;">┄ Vùng Hạng S (≥85đ)</span>'
        if breakdown_v1 is not None
        else '<span style="color:#4F46E5;font-weight:700;">● Điểm hiện tại</span> · <span style="color:#10B981;">┄ Vùng chuẩn 85đ (Hạng S)</span>'
    )

    return f"""
    <div style="background:linear-gradient(180deg,#FFFFFF 0%,#F8FAFC 100%);border:1px solid #E2E8F0;border-radius:14px;padding:0.7rem 0.75rem;text-align:center;height:100%;display:flex;flex-direction:column;justify-content:space-between;">
        <svg viewBox="0 0 330 258" style="width:100%;max-height:222px;overflow:visible;">
            {''.join(grid_polys)}
            {axis_lines}
            {v1_layer}
            {cur_layer}
            {dots}
            {labels_svg}
        </svg>
        <div style="font-size:0.71rem;color:#64748B;margin-top:2px;">
            {legend_html}
        </div>
    </div>
    """


def build_four_pillars_altair(
    breakdown_current: Dict[str, Any],
    breakdown_v1: Optional[Dict[str, Any]] = None,
) -> alt.LayerChart:
    """Biểu đồ Altair 4 Trụ Cột kèm nhãn điểm trực tiếp & vạch ngưỡng 85đ Hạng S."""
    standards = [
        ("1. Hook (25%)", "hook_score"),
        ("2. Độ bám tin (35%)", "trend_similarity_score"),
        ("3. Cấu trúc (20%)", "pacing_score"),
        ("4. CTA (20%)", "cta_score"),
    ]

    rule_df = pd.DataFrame([{"target": 85.0}])
    target_rule = alt.Chart(rule_df).mark_rule(
        strokeDash=[5, 4], color="#10B981", strokeWidth=1.8
    ).encode(x="target:Q")

    y_axis_cfg = alt.Axis(
        labelLimit=175,
        labelOverlap=False,
        labelPadding=8,
        labelFont="Plus Jakarta Sans",
        labelFontWeight="bold",
        labelColor="#1E293B",
        domain=False,
        ticks=False,
    )

    if breakdown_v1 is not None:
        rows = []
        for label, key in standards:
            rows.append({
                "Trụ cột": label,
                "Phiên bản": "v1 (Trước)",
                "Điểm": round(float(breakdown_v1.get(key, 0.0)), 1),
            })
            rows.append({
                "Trụ cột": label,
                "Phiên bản": "v2 (Sau tối ưu)",
                "Điểm": round(float(breakdown_current.get(key, 0.0)), 1),
            })
        df = pd.DataFrame(rows)
        bars = (
            alt.Chart(df)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                y=alt.Y("Trụ cột:N", sort=None, title=None, axis=y_axis_cfg),
                x=alt.X("Điểm:Q", scale=alt.Scale(domain=[0, 112]), title="Điểm số (0 - 100 · Vạch xanh = 85đ)"),
                color=alt.Color(
                    "Phiên bản:N",
                    scale=alt.Scale(domain=["v1 (Trước)", "v2 (Sau tối ưu)"], range=["#94A3B8", "#10B981"]),
                    legend=alt.Legend(orient="bottom", title=None),
                ),
                yOffset="Phiên bản:N",
                tooltip=["Trụ cột:N", "Phiên bản:N", alt.Tooltip("Điểm:Q", format=".1f")],
            )
        )
        labels = (
            alt.Chart(df)
            .mark_text(align="left", baseline="middle", dx=4, font="JetBrains Mono", fontSize=10, fontWeight="bold", color="#334155")
            .encode(
                y=alt.Y("Trụ cột:N", sort=None),
                yOffset="Phiên bản:N",
                x=alt.X("Điểm:Q"),
                text=alt.Text("Điểm:Q", format=".0f"),
            )
        )
        return (
            alt.layer(bars, labels, target_rule)
            .properties(height=230)
            .configure(background="transparent")
            .configure_view(strokeWidth=0)
        )

    rows = [
        {"Trụ cột": label, "Điểm": round(float(breakdown_current.get(key, 0.0)), 1)}
        for label, key in standards
    ]
    df = pd.DataFrame(rows)
    base = alt.Chart(df).encode(y=alt.Y("Trụ cột:N", sort=None, title=None, axis=y_axis_cfg))
    bars = base.mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, height=22).encode(
        x=alt.X("Điểm:Q", scale=alt.Scale(domain=[0, 110]), title="Điểm số (Vạch xanh nét đứt = 85đ Hạng S)"),
        color=alt.condition(alt.datum["Điểm"] >= 85, alt.value("#10B981"), alt.value("#4F46E5")),
        tooltip=["Trụ cột:N", alt.Tooltip("Điểm:Q", format=".1f")],
    )
    labels = base.mark_text(
        align="left", baseline="middle", dx=6, font="JetBrains Mono", fontSize=11, fontWeight="bold", color="#1E293B"
    ).encode(
        x=alt.X("Điểm:Q"),
        text=alt.Text("Điểm:Q", format=".1f"),
    )
    return (
        alt.layer(bars, labels, target_rule)
        .properties(height=188)
        .configure(background="transparent")
        .configure_view(strokeWidth=0)
    )


def build_experiment_trend_altair(history: List[Dict[str, Any]]) -> alt.LayerChart:
    """Biểu đồ tăng trưởng thực nghiệm v1 -> v2 kèm vùng Hạng S và nhãn trực tiếp (Tab 3)."""
    rows = []
    for idx, rec in enumerate(history, start=1):
        label = f"Mẫu #{idx}"
        rows.append({"Mẫu": label, "Thứ tự": idx, "Phiên bản": "Trước tối ưu (v1)", "Điểm": round(float(rec.get("score_v1", 0.0)), 1)})
        rows.append({"Mẫu": label, "Thứ tự": idx, "Phiên bản": "Sau tối ưu (v2)", "Điểm": round(float(rec.get("score_v2", 0.0)), 1)})

    df = pd.DataFrame(rows)
    order = [f"Mẫu #{i}" for i in range(1, len(history) + 1)]

    bars = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("Mẫu:N", sort=order, title="Thứ tự mẫu thực nghiệm", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Điểm:Q", scale=alt.Scale(domain=[0, 110]), title="Điểm Viral (0 - 100)"),
            color=alt.Color(
                "Phiên bản:N",
                scale=alt.Scale(domain=["Trước tối ưu (v1)", "Sau tối ưu (v2)"], range=["#94A3B8", "#4F46E5"]),
                legend=alt.Legend(orient="top", title=None),
            ),
            xOffset="Phiên bản:N",
            tooltip=["Mẫu:N", "Phiên bản:N", alt.Tooltip("Điểm:Q", format=".1f")],
        )
    )

    labels = (
        alt.Chart(df)
        .mark_text(dy=-7, font="JetBrains Mono", fontSize=10.5, fontWeight="bold", color="#1E293B")
        .encode(
            x=alt.X("Mẫu:N", sort=order),
            xOffset="Phiên bản:N",
            y=alt.Y("Điểm:Q"),
            text=alt.Text("Điểm:Q", format=".1f"),
        )
    )

    rule_s = alt.Chart(pd.DataFrame([{"y": 85.0}])).mark_rule(
        strokeDash=[5, 4], color="#10B981", strokeWidth=1.8
    ).encode(y="y:Q")

    return (
        alt.layer(bars, labels, rule_s)
        .properties(height=265)
        .configure(background="transparent")
        .configure_view(strokeWidth=0)
    )
