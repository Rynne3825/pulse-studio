"""
THE PULSE STUDIO - HỆ THỐNG DESIGN TOKENS & CSS MICRO-INTERACTIONS
- Phong cách Swiss Bento Light (#F8FAFC canvas, #FFFFFF thẻ nổi, #4F46E5 Electric Indigo, #10B981 Emerald)
- Typography: Space Grotesk (Tiêu đề) + Plus Jakarta Sans (Nội dung) + JetBrains Mono (Số liệu)
"""

import streamlit as st


def apply_studio_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root {
            --bg-canvas: #F8FAFC;
            --bg-surface: #FFFFFF;
            --bg-subtle: #F1F5F9;
            --border-hairline: #E2E8F0;
            --border-strong: #CBD5E1;
            --ink-primary: #0F172A;
            --ink-secondary: #475569;
            --ink-muted: #64748B;
            --accent-indigo: #4F46E5;
            --accent-indigo-hover: #4338CA;
            --accent-emerald: #10B981;
            --accent-amber: #F59E0B;
            --accent-rose: #F43F5E;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background-color: var(--bg-canvas) !important;
            background-image:
                radial-gradient(ellipse 85% 42% at 88% -8%, rgba(79, 70, 229, 0.07), transparent),
                radial-gradient(ellipse 65% 38% at 8% 0%, rgba(16, 185, 129, 0.05), transparent) !important;
            color: var(--ink-primary) !important;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }

        header[data-testid="stHeader"], footer, #MainMenu {
            display: none !important;
        }

        .block-container {
            max-width: 1440px !important;
            padding-top: 1.15rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }

        *:focus, *:focus-visible {
            outline: none !important;
        }

        div[data-testid="column"] {
            border: none !important;
            box-shadow: none !important;
        }

        /* BENTO ELEVATED CARDS */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: var(--bg-surface) !important;
            border: 1px solid var(--border-hairline) !important;
            border-radius: 16px !important;
            padding: 1.25rem 1.4rem !important;
            margin-bottom: 1rem !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03), 0 6px 18px rgba(15, 23, 42, 0.03) !important;
            transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.22s ease, border-color 0.22s ease !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: #CBD5E1 !important;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.06), 0 14px 30px rgba(15, 23, 42, 0.05) !important;
        }

        /* HEADINGS */
        .panel-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--ink-primary);
            margin-bottom: 0.2rem;
            padding-top: 3px;
            line-height: 1.42;
            letter-spacing: -0.02em;
        }
        .panel-subtitle {
            font-size: 0.8125rem;
            color: var(--ink-muted);
            margin-bottom: 0.85rem;
            line-height: 1.45;
        }

        /* LIVE BADGE & STEPPER */
        @keyframes pulse-live {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.55); }
            70% { box-shadow: 0 0 0 7px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        .live-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: #ECFDF5;
            color: #047857;
            border: 1px solid #A7F3D0;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .live-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10B981;
            animation: pulse-live 2s infinite;
        }

        .stepper-bar {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            flex-wrap: wrap;
        }
        .step-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            border: 1px solid var(--border-hairline);
            background: var(--bg-surface);
            color: var(--ink-muted);
            transition: all 0.2s ease;
        }
        .step-pill.active {
            background: #EEF2FF;
            border-color: #C7D2FE;
            color: #4338CA;
            box-shadow: 0 2px 6px rgba(79, 70, 229, 0.12);
        }
        .step-pill.done {
            background: #ECFDF5;
            border-color: #A7F3D0;
            color: #047857;
        }
        .step-arrow {
            color: #94A3B8;
            font-size: 0.75rem;
            font-weight: 600;
        }

        /* KPI BENTO GRID */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.9rem;
            margin-bottom: 1.05rem;
        }
        @media (max-width: 960px) {
            .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        .kpi-card {
            position: relative;
            background: var(--bg-surface);
            border: 1px solid var(--border-hairline);
            border-radius: 14px;
            padding: 0.95rem 1.15rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
            overflow: hidden;
        }
        .kpi-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--kpi-accent, #4F46E5);
            opacity: 0.78;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: #C7D2FE;
            box-shadow: 0 8px 20px rgba(79, 70, 229, 0.08);
        }
        .kpi-label {
            font-size: 0.74rem;
            font-weight: 600;
            color: var(--ink-muted);
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.35rem;
        }
        .kpi-tag {
            font-size: 0.68rem;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 999px;
            background: #F1F5F9;
        }
        .kpi-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.42rem;
            font-weight: 700;
            color: var(--ink-primary);
            line-height: 1.18;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .kpi-sub {
            font-size: 0.73rem;
            color: var(--ink-secondary);
            margin-top: 0.3rem;
        }

        /* FLOATING PILL TABS */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            background: #F1F5F9;
            padding: 5px;
            border-radius: 12px;
            gap: 6px;
            border: 1px solid var(--border-hairline);
            margin-bottom: 0.75rem;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
        div[data-testid="stTabs"] [data-baseweb="tab-border"] {
            display: none !important;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 0.9rem !important;
            font-weight: 600 !important;
            color: var(--ink-secondary) !important;
            padding: 0.55rem 1.15rem !important;
            border-radius: 9px !important;
            border: 1px solid transparent !important;
            transition: all 0.18s ease !important;
        }
        div[data-testid="stTabs"] button[role="tab"]:hover {
            color: var(--accent-indigo) !important;
            background: rgba(255, 255, 255, 0.65) !important;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: var(--accent-indigo) !important;
            background: #FFFFFF !important;
            border-color: #E2E8F0 !important;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06) !important;
        }

        /* PRIMARY & SECONDARY BUTTONS */
        @keyframes shimmer-sweep {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(110deg, #4F46E5 0%, #4338CA 45%, #6366F1 55%, #4F46E5 100%) !important;
            background-size: 220% 100% !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.6rem 1.25rem !important;
            font-size: 0.88rem !important;
            font-weight: 700 !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            box-shadow: 0 3px 10px rgba(79, 70, 229, 0.28) !important;
            transition: transform 0.16s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.16s ease !important;
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 22px rgba(79, 70, 229, 0.36) !important;
            animation: shimmer-sweep 2.2s linear infinite !important;
        }
        div[data-testid="stButton"] > button[kind="primary"]:active {
            transform: translateY(0) scale(0.985) !important;
        }
        div[data-testid="stButton"] > button[kind="secondary"],
        div[data-testid="stDownloadButton"] > button {
            background: #FFFFFF !important;
            color: var(--ink-primary) !important;
            border: 1px solid var(--border-strong) !important;
            border-radius: 10px !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
            transition: all 0.16s ease !important;
        }
        div[data-testid="stButton"] > button[kind="secondary"]:hover,
        div[data-testid="stDownloadButton"] > button:hover {
            background: #F8FAFC !important;
            border-color: var(--accent-indigo) !important;
            color: var(--accent-indigo) !important;
        }

        /* INPUTS & TEXTAREA */
        div[data-testid="stTextArea"] textarea {
            background-color: #F8FAFC !important;
            border: 1.5px solid var(--border-hairline) !important;
            border-radius: 12px !important;
            color: var(--ink-primary) !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 0.92rem !important;
            line-height: 1.62 !important;
            padding: 0.85rem 1rem !important;
            transition: border-color 0.18s ease, background-color 0.18s ease, box-shadow 0.18s ease !important;
        }
        div[data-testid="stTextArea"] textarea:focus {
            background-color: #FFFFFF !important;
            border-color: var(--accent-indigo) !important;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12) !important;
        }
        div[data-testid="stSelectbox"] > div > div {
            background-color: #FFFFFF !important;
            border: 1px solid var(--border-strong) !important;
            border-radius: 10px !important;
            color: var(--ink-primary) !important;
            font-size: 0.875rem !important;
        }
        div[data-testid="stSelectbox"] > div > div:hover {
            border-color: var(--accent-indigo) !important;
        }

        /* HIDE VEGA-LITE TOOLBAR DROPDOWN */
        .vega-actions, [data-testid="stVegaLiteChart"] summary, .vega-embed summary, [data-testid="stVegaLiteChart"] details {
            display: none !important;
        }

        /* SENTIMENT PILLS & TELEMETRY MINI GRID */
        .sentiment-pills-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.5rem;
            margin-top: 0.4rem;
        }
        .sentiment-pill {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 0.45rem 0.55rem;
            text-align: center;
        }
        .sentiment-pill-val {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.88rem;
            font-weight: 700;
        }
        .sentiment-pill-lbl {
            font-size: 0.7rem;
            color: #64748B;
            font-weight: 600;
        }

        .telemetry-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.55rem;
            margin-top: 0.65rem;
        }
        .telemetry-tile {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 0.55rem 0.75rem;
        }
        .telemetry-k {
            font-size: 0.71rem;
            color: #64748B;
            font-weight: 600;
        }
        .telemetry-v {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.84rem;
            color: #0F172A;
            font-weight: 700;
            margin-top: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* ARTICLE PREVIEW CARD */
        .article-quote-card {
            display: flex;
            gap: 1.15rem;
            align-items: center;
            padding: 1rem 1.15rem;
            margin-top: 0.65rem;
            background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
            border-radius: 14px;
            border: 1px solid var(--border-hairline);
            border-left: 4px solid var(--accent-indigo);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .article-quote-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
        }
        .article-quote-thumb {
            width: 210px;
            height: 126px;
            object-fit: cover;
            object-position: center;
            border-radius: 10px;
            border: 1px solid var(--border-hairline);
            background: #F1F5F9;
            flex-shrink: 0;
        }
        .article-quote-body {
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .article-quote-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1rem;
            font-weight: 700;
            color: var(--ink-primary);
            margin-bottom: 0.35rem;
            line-height: 1.38;
        }
        .article-quote-text {
            font-size: 0.86rem;
            color: var(--ink-secondary);
            line-height: 1.5;
        }
        .article-quote-meta {
            margin-top: 0.55rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.5rem;
            font-size: 0.76rem;
        }

        /* WORD COUNT METER */
        .word-meter-wrap {
            margin-top: 0.2rem;
            margin-bottom: 0.3rem;
        }
        .word-meter-bar-bg {
            width: 100%;
            height: 6px;
            background: #E2E8F0;
            border-radius: 999px;
            overflow: hidden;
            margin-top: 4px;
        }
        .word-meter-bar-fill {
            height: 100%;
            border-radius: 999px;
            transition: width 0.3s ease;
        }

        /* CELEBRATION & GAUGE ANIMATION */
        @keyframes glow-s-banner {
            0%, 100% { box-shadow: 0 4px 16px rgba(16, 185, 129, 0.16); }
            50% { box-shadow: 0 6px 26px rgba(16, 185, 129, 0.34); }
        }
        .grade-s-celebration {
            background: linear-gradient(120deg, #ECFDF5 0%, #D1FAE5 50%, #ECFDF5 100%);
            border: 1.5px solid #10B981;
            border-radius: 12px;
            padding: 0.7rem 1rem;
            margin-bottom: 0.85rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            animation: glow-s-banner 2.8s ease-in-out infinite;
        }
        @keyframes ring-draw {
            from { stroke-dashoffset: 314.16; }
        }
        .svg-ring-progress {
            animation: ring-draw 1.1s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }

        .checklist-pill {
            padding: 0.56rem 0.85rem;
            margin-bottom: 0.45rem;
            border-radius: 10px;
            font-size: 0.82rem;
            line-height: 1.45;
            transition: transform 0.15s ease;
        }
        .checklist-pill:hover {
            transform: translateX(3px);
        }

        .delta-pill-pos {
            display: inline-block;
            background: #DCFCE7;
            color: #15803D;
            border: 1px solid #86EFAC;
            padding: 3px 11px;
            border-radius: 999px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .delta-pill-neutral {
            display: inline-block;
            background: #F1F5F9;
            color: #475569;
            border: 1px solid #CBD5E1;
            padding: 3px 11px;
            border-radius: 999px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            font-weight: 700;
        }

        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #F8FAFC; }
        ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #94A3B8; }
        </style>
        """,
        unsafe_allow_html=True,
    )
