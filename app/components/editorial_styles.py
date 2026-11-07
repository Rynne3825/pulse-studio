"""
THE PULSE EDITORIAL - STYLING & DESIGN SYSTEM
Định hình thẩm mỹ Editorial Minimalist:
- Bảng màu: Warm Ivory Paper (#FAF8F5), Deep Charcoal Ink (#18181B), Terracotta (#C2410C), Hairline (#EAE6DF).
- Typography: Tiêu đề Serif 'Newsreader' + Thao tác Sans 'Plus Jakarta Sans'.
- Xử lý triệt để viền lỗi, outline thừa, container React trong Streamlit 1.66.
"""

import streamlit as st

def apply_editorial_styles() -> None:
    st.markdown(
        """
        <style>
        /* 1. NẠP PHÔNG CHỮ GOOGLE FONTS */
        @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

        /* 2. THIẾT LẬP NỀN & KHÔNG GIAN TỔNG THỂ */
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #FAF8F5 !important;
            color: #18181B !important;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }

        /* Ẩn header mặc định và thanh footer của Streamlit */
        header[data-testid="stHeader"], footer, #MainMenu {
            display: none !important;
        }

        /* Không gian nội dung chính */
        .block-container {
            max-width: 1440px !important;
            padding-top: 1.5rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }

        /* 3. KHỬ TRIỆT ĐỂ VIỀN TRẮNG LỖI, OUTLINE THÔ KỆCH */
        *:focus, *:focus-visible {
            outline: none !important;
            box-shadow: none !important;
        }

        div[data-testid="column"] {
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }

        /* 4. CONTAINER CARD CHUẨN TÒA SOẠN (DÙNG CHO st.container(border=True)) */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border: 1px solid #EAE6DF !important;
            border-radius: 8px !important;
            padding: 1.25rem 1.5rem !important;
            margin-bottom: 1.25rem !important;
            box-shadow: 0 1px 3px rgba(24, 24, 27, 0.03) !important;
        }

        /* 5. TYPOGRAPHY TIÊU ĐỀ & PHÂN KHU */
        .editorial-panel-title {
            font-family: 'Newsreader', Georgia, serif;
            font-size: 1.25rem;
            font-weight: 500;
            color: #18181B;
            margin-bottom: 0.2rem;
            letter-spacing: -0.01em;
        }

        .editorial-panel-subtitle {
            font-size: 0.8125rem;
            color: #71717A;
            margin-bottom: 0.95rem;
            line-height: 1.4;
        }

        /* Đường kẻ hairline ngăn cách thanh nhã */
        .editorial-divider {
            border: none;
            border-top: 1px solid #EAE6DF;
            margin: 1.25rem 0;
        }

        /* Khung trích dẫn báo chí (Editorial Pullquote) */
        .editorial-quote {
            border-left: 2px solid #C2410C;
            padding: 0.65rem 1rem;
            margin: 0.85rem 0;
            font-style: italic;
            font-size: 0.875rem;
            color: #52525B;
            line-height: 1.5;
            background: #FDFBF9;
            border-radius: 0 6px 6px 0;
            border-top: 1px solid #F4F1EA;
            border-bottom: 1px solid #F4F1EA;
            border-right: 1px solid #F4F1EA;
        }

        /* 6. TÙY CHỈNH NÚT BẤM (BUTTONS) */
        div[data-testid="stButton"] > button {
            background-color: #18181B !important;
            color: #FAF8F5 !important;
            border: 1px solid #18181B !important;
            border-radius: 6px !important;
            padding: 0.5rem 1.25rem !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            transition: all 0.15s ease-in-out !important;
            box-shadow: 0 1px 2px rgba(24, 24, 27, 0.06) !important;
        }
        div[data-testid="stButton"] > button:hover {
            background-color: #C2410C !important;
            border-color: #C2410C !important;
            color: #FFFFFF !important;
            transform: translateY(-1px);
            box-shadow: 0 3px 8px rgba(194, 65, 12, 0.18) !important;
        }
        div[data-testid="stButton"] > button:active {
            transform: translateY(0);
        }

        /* 7. TÙY CHỈNH KHUNG GÕ CHỮ (TEXTAREA) */
        div[data-testid="stTextArea"] textarea {
            background-color: #FFFFFF !important;
            border: 1px solid #E4E0D6 !important;
            border-radius: 6px !important;
            color: #18181B !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 0.9375rem !important;
            line-height: 1.6 !important;
            padding: 0.85rem 1rem !important;
            box-shadow: none !important;
            transition: border-color 0.15s ease !important;
        }
        div[data-testid="stTextArea"] textarea:focus {
            border-color: #C2410C !important;
            box-shadow: 0 0 0 1px #C2410C !important;
        }

        /* 8. TÙY CHỈNH HỘP CHỌN (SELECTBOX & DATEPICKER) */
        div[data-testid="stSelectbox"] > div > div {
            background-color: #FFFFFF !important;
            border: 1px solid #E4E0D6 !important;
            border-radius: 6px !important;
            color: #18181B !important;
            font-size: 0.875rem !important;
            box-shadow: none !important;
        }
        div[data-testid="stSelectbox"] > div > div:hover {
            border-color: #C2410C !important;
        }

        /* 9. ẨN HOÀN TOÀN VEGA ACTION MENU ĐỂ TRÁNH ĐÈ LÊN CÁC THẺ PHÍA TRÊN */
        .vega-actions, [data-testid="stVegaLiteChart"] summary, .vega-embed summary, [data-testid="stVegaLiteChart"] details {
            display: none !important;
        }

        /* Thanh cuộn tối giản */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #FAF8F5;
        }
        ::-webkit-scrollbar-thumb {
            background: #D4CEBF;
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #A8A29E;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
