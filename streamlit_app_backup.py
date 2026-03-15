import base64
import os
from pathlib import Path
from textwrap import dedent
from typing import Any
from urllib.parse import quote_plus

import requests
import streamlit as st

API_BASE = os.getenv("AURA_API_BASE", "http://localhost:8000")


class ApiError(Exception):
    pass


def api_request(method: str, path: str, token: str | None = None, json: dict | None = None, files: dict | None = None, data: dict | None = None) -> Any:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if files:
        response = requests.request(method, f"{API_BASE}{path}", headers=headers, files=files, data=data, timeout=120)
    else:
        response = requests.request(method, f"{API_BASE}{path}", headers=headers, json=json, timeout=120)

    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise ApiError(str(detail))

    if not response.text:
        return {}
    return response.json()


def init_state() -> None:
    st.session_state.setdefault("auth", None)


def logout() -> None:
    st.session_state["auth"] = None
    st.rerun()


def bootstrap_demo_users() -> None:
    try:
        requests.post(f"{API_BASE}/auth/bootstrap", timeout=20)
    except Exception:
        pass


def sign_in_with_google_id_token(id_token: str, requested_role: str) -> dict[str, Any]:
    payload = {
        "id_token": id_token,
        "requested_role": requested_role,
    }
    return api_request("POST", "/auth/firebase-google", json=payload)


def get_google_popup_redirect_url(requested_role: str) -> str:
    frontend_return = os.getenv("AURA_FRONTEND_BASE", "http://127.0.0.1:8501")
    safe_role = requested_role if requested_role in {"teacher", "parent"} else "teacher"
    return (
        f"{API_BASE}/auth/firebase-google-popup"
        f"?role={quote_plus(safe_role)}&return_to={quote_plus(frontend_return)}"
    )


def get_landing_bg_src() -> str:
    candidates = [
        Path("assets/bg/bg.png"),
        Path("assets/bg/bg.jpg"),
        Path("assets/bg/bg.jpeg"),
        Path("assets/bg/bg.webp"),
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            suffix = path.suffix.lower().lstrip(".")
            mime = "image/jpeg" if suffix == "jpg" else f"image/{suffix}"
            encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
            return f"data:{mime};base64,{encoded}"
    return "https://images.pexels.com/photos/3807517/pexels-photo-3807517.jpeg?auto=compress&cs=tinysrgb&w=1600"


def render_global_css() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Manrope:wght@400;500;600;700;800&display=swap');

            .stApp {
                background: #f8f6f2;
                font-family: 'Manrope', sans-serif;
                color: #223247;
            }
            [data-testid="stAppViewContainer"],
            [data-testid="stAppViewContainer"] p,
            [data-testid="stAppViewContainer"] label,
            [data-testid="stAppViewContainer"] span,
            [data-testid="stAppViewContainer"] li {
                color: #223247;
            }
            .stMarkdown, .stMarkdown p, .stMarkdown li {
                color: #223247;
            }
            [data-testid="stAppViewContainer"] h1,
            [data-testid="stAppViewContainer"] h2,
            [data-testid="stAppViewContainer"] h3,
            [data-testid="stAppViewContainer"] h4,
            [data-testid="stAppViewContainer"] h5,
            [data-testid="stAppViewContainer"] h6 {
                color: #111111 !important;
            }
            .stTextInput label,
            .stTextArea label,
            .stSelectbox label,
            .stRadio label,
            .stCheckbox label,
            .stFileUploader label,
            .stNumberInput label {
                color: #223247 !important;
                font-weight: 600;
            }
            [data-baseweb="input"] input,
            [data-baseweb="textarea"] textarea {
                color: #1f2d42 !important;
                background: #ffffff !important;
            }
            [data-baseweb="input"] input::placeholder,
            [data-baseweb="textarea"] textarea::placeholder {
                color: #6a7888 !important;
            }
            [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {
                display: none;
            }
            .block-container {
                max-width: 1280px;
                padding-top: 0.25rem;
                padding-left: 2rem;
                padding-right: 2rem;
                padding-bottom: 2rem;
            }
            .brainy-shell {
                background: #f8f6f2;
                border: none;
                border-radius: 0;
                overflow: hidden;
                position: relative;
            }
            .fixed-nav {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                z-index: 1000;
                max-width: 1280px;
                margin: 0 auto;
                background: #2d3f5b;
                border: none;
                border-bottom: 2px solid #1e2a3a;
                padding: 0.6rem 1.2rem;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            }
            @media (max-width: 1300px) {
                .fixed-nav {
                    left: 0;
                    right: 0;
                    padding: 0.6rem 0.8rem;
                }
            }
            .page-under-nav {
                padding-top: 88px;
            }
            .nav-brand {
                font-family: 'DM Serif Display', serif;
                font-size: 28px;
                font-weight: 700;
                color: #ffffff;
                margin: 0;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .nav-links {
                font-size: 13px;
                color: #c4cdd5;
                margin-top: 12px;
                letter-spacing: 0.5px;
            }
            .nav-links a {
                color: #ffffff;
                text-decoration: none;
                margin: 0 12px;
                transition: color 0.2s;
            }
            .nav-links a:hover {
                color: #6dd5ff;
            }
            .nav-btn {
                padding: 8px 16px;
                font-size: 13px;
                border-radius: 6px;
                border: 1px solid #4a5f7a;
                background: transparent;
                color: #ffffff;
                cursor: pointer;
                transition: all 0.2s;
            }
            .nav-btn:hover {
                background: #3d5273;
                border-color: #6dd5ff;
            }
            .hero-section {
                background: linear-gradient(135deg, #2d3f5b 0%, #3d5273 100%);
                padding: 60px 40px;
                border-radius: 12px;
                color: white;
                margin-bottom: 40px;
            }
            .hero-title {
                font-family: 'DM Serif Display', serif;
                font-size: 52px;
                line-height: 1.1;
                color: #ffffff;
                margin: 0 0 16px 0;
                font-weight: 700;
            }
            .hero-subtitle {
                font-size: 18px;
                color: #c4cdd5;
                margin: 0 0 24px 0;
                line-height: 1.5;
            }
            .section-title {
                font-family: 'DM Serif Display', serif;
                font-size: 36px;
                line-height: 1;
                color: #111111;
                margin: 32px 0 24px 0;
                font-weight: 700;
            }
            .subsection-title {
                font-family: 'Manrope', sans-serif;
                font-size: 18px;
                font-weight: 700;
                color: #111111;
                margin: 24px 0 16px 0;
            }
            .feature-card {
                background: #ffffff;
                border: 1px solid #e5ddd3;
                border-radius: 10px;
                padding: 24px;
                margin-bottom: 16px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
                transition: all 0.3s;
            }
            .feature-card:hover {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                border-color: #2d3f5b;
            }
            .feature-icon {
                font-size: 32px;
                margin-bottom: 12px;
            }
            .feature-title {
                font-weight: 700;
                font-size: 16px;
                color: #111111;
                margin-bottom: 8px;
            }
            .feature-desc {
                font-size: 14px;
                color: #2f2f2f;
                line-height: 1.5;
            }
            .dashboard-header {
                background: #ffffff;
                border-bottom: 2px solid #e5ddd3;
                padding: 20px;
                border-radius: 10px 10px 0 0;
                margin-bottom: -1px;
            }
            .dashboard-title {
                font-family: 'DM Serif Display', serif;
                font-size: 28px;
                color: #111111;
                margin: 0;
                font-weight: 700;
            }
            .dashboard-subtitle {
                font-size: 13px;
                color: #333333;
                margin: 8px 0 0 0;
            }
            .student-card {
                background: #ffffff;
                border: 1px solid #e5ddd3;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                gap: 16px;
                transition: all 0.2s;
            }
            .student-card:hover {
                border-color: #2d3f5b;
                box-shadow: 0 4px 10px rgba(45, 63, 91, 0.1);
            }
            .student-avatar {
                width: 48px;
                height: 48px;
                border-radius: 50%;
                background: linear-gradient(135deg, #6dd5ff 0%, #2d3f5b 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 700;
                font-size: 18px;
                flex-shrink: 0;
            }
            .student-info {
                flex: 1;
            }
            .student-name {
                font-weight: 700;
                color: #111111;
                margin: 0;
            }
            .student-meta {
                font-size: 12px;
                color: #333333;
                margin: 4px 0 0 0;
            }
            .insight-tag {
                display: inline-block;
                background: #e8f1f7;
                color: #2d3f5b;
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 11px;
                font-weight: 600;
                margin-top: 8px;
            }
            .tag {
                border: 1px solid #d4c9b8;
                border-radius: 999px;
                padding: 6px 14px;
                font-size: 13px;
                display: inline-block;
                margin-right: 6px;
                margin-bottom: 6px;
                background: #f5f1e6;
                color: #4a4037;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 12px;
                margin: 20px 0;
            }
            .stat-box {
                background: #ffffff;
                border: 1px solid #e5ddd3;
                border-radius: 8px;
                padding: 14px;
                text-align: center;
                transition: all 0.2s;
            }
            .stat-box:hover {
                border-color: #2d3f5b;
            }
            .stat-value {
                font-family: 'DM Serif Display', serif;
                font-size: 28px;
                color: #2d3f5b;
                font-weight: 700;
                margin: 0;
            }
            .stat-label {
                font-size: 12px;
                color: #7a8a99;
                margin: 6px 0 0 0;
                font-weight: 600;
            }
            .action-button {
                background: #2d3f5b;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 13px;
            }
            .action-button:hover {
                background: #1e2a3a;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            }
            .form-group {
                background: #ffffff;
                border: 1px solid #e5ddd3;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
            }
            .form-label {
                font-weight: 600;
                color: #111111;
                font-size: 13px;
                margin-bottom: 6px;
                display: block;
            }
            .report-card {
                background: #ffffff;
                border-left: 4px solid #2d3f5b;
                border-radius: 8px;
                padding: 18px;
                margin-bottom: 14px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            }
            .report-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }
            .report-title {
                font-weight: 700;
                color: #111111;
                margin: 0;
            }
            .landing-hero-content h1,
            .landing-hero-content p {
                color: #ffffff !important;
            }
            .report-status {
                display: inline-block;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 999px;
                background: #e8f1f7;
                color: #2d3f5b;
            }
            .observation-box {
                background: #f5f9fc;
                border-left: 3px solid #6dd5ff;
                border-radius: 6px;
                padding: 14px;
                margin: 12px 0;
                font-size: 13px;
                line-height: 1.6;
                color: #3f5068;
            }
            .tab-indicator {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 8px 16px;
                background: #e8f1f7;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                color: #2d3f5b;
            }
            .loading-spinner {
                display: inline-block;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            /* Dark pastel theme overrides */
            :root {
                --bg-deep: #12111d;
                --bg-surface: #1b1a2b;
                --bg-card: #232238;
                --line-soft: #3a3956;
                --text-main: #f4f0ff;
                --text-muted: #c5bddf;
                --pastel-mint: #9fe3d3;
                --pastel-lav: #cdb8ff;
                --pastel-peach: #ffc7a6;
                --pastel-blue: #a7d2ff;
            }

            .stApp {
                background: radial-gradient(circle at 12% 10%, #2a2843 0%, var(--bg-deep) 40%, #0f0e18 100%) !important;
                color: var(--text-main) !important;
            }

            [data-testid="stAppViewContainer"],
            [data-testid="stAppViewContainer"] p,
            [data-testid="stAppViewContainer"] label,
            [data-testid="stAppViewContainer"] span,
            [data-testid="stAppViewContainer"] li,
            [data-testid="stAppViewContainer"] h1,
            [data-testid="stAppViewContainer"] h2,
            [data-testid="stAppViewContainer"] h3,
            [data-testid="stAppViewContainer"] h4,
            [data-testid="stAppViewContainer"] h5,
            [data-testid="stAppViewContainer"] h6 {
                color: var(--text-main) !important;
            }

            .block-container {
                max-width: 1280px;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
            }

            .brainy-shell {
                background: transparent !important;
            }

            .fixed-nav {
                background: rgba(19, 18, 30, 0.9) !important;
                border-bottom: 1px solid var(--line-soft) !important;
                backdrop-filter: blur(10px);
            }

            .nav-links,
            .dashboard-subtitle,
            .stat-label,
            .feature-desc,
            .student-meta {
                color: var(--text-muted) !important;
            }

            .section-title,
            .subsection-title,
            .dashboard-title,
            .feature-title,
            .student-name,
            .report-title,
            .form-label {
                color: var(--text-main) !important;
            }

            .feature-card,
            .student-card,
            .report-card,
            .form-group,
            .stat-box,
            .dashboard-header,
            .observation-box {
                background: linear-gradient(180deg, rgba(41, 39, 64, 0.94) 0%, rgba(30, 29, 48, 0.95) 100%) !important;
                border: 1px solid var(--line-soft) !important;
                color: var(--text-main) !important;
                box-shadow: 0 8px 28px rgba(5, 4, 12, 0.28);
            }

            .report-card {
                border-left: 4px solid var(--pastel-lav) !important;
            }

            .insight-tag,
            .report-status,
            .tab-indicator,
            .tag,
            .chip {
                background: rgba(205, 184, 255, 0.14) !important;
                border: 1px solid rgba(205, 184, 255, 0.35) !important;
                color: #eee5ff !important;
            }

            [data-baseweb="input"] input,
            [data-baseweb="textarea"] textarea,
            .stSelectbox [data-baseweb="select"] > div {
                background: #1a1a2a !important;
                color: var(--text-main) !important;
                border: 1px solid var(--line-soft) !important;
            }

            [data-baseweb="input"] input::placeholder,
            [data-baseweb="textarea"] textarea::placeholder {
                color: #a39aba !important;
            }

            .stButton > button,
            .action-button,
            .nav-btn {
                background: linear-gradient(135deg, var(--pastel-lav) 0%, var(--pastel-blue) 100%) !important;
                color: #171327 !important;
                border: none !important;
                font-weight: 700 !important;
            }

            .stButton > button:hover,
            .action-button:hover,
            .nav-btn:hover {
                filter: brightness(1.04);
                transform: translateY(-1px);
            }

            .landing-hero {
                background-color: #171529 !important;
            }

            .landing-hero-content h1,
            .landing-hero-content p {
                color: #ffffff !important;
            }

            [data-testid="stAlert"] {
                background: rgba(255, 199, 166, 0.12) !important;
                border: 1px solid rgba(255, 199, 166, 0.4) !important;
                color: #ffe7d8 !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def landing_and_login() -> None:
    # Handle Google popup callback token (set via query params by frontend JS).
    google_token = st.query_params.get("g_id_token")
    if google_token:
        requested_role = st.query_params.get("g_role", "teacher")
        try:
            data = sign_in_with_google_id_token(google_token, requested_role)
            st.session_state["auth"] = {
                "token": data["access_token"],
                "role": data["role"],
                "user_id": data["user_id"],
                "parent_id": data.get("parent_id"),
            }
            st.query_params.clear()
            st.success("Signed in with Google")
            st.rerun()
        except Exception as exc:
            st.query_params.clear()
            st.error(f"Google sign in failed: {exc}")

    st.markdown('<div class="brainy-shell">', unsafe_allow_html=True)

    # Fixed Navigation
    st.markdown('<div class="fixed-nav">', unsafe_allow_html=True)
    header_left, header_mid, header_right = st.columns([1.2, 2.5, 1.0])
    
    with header_left:
        st.markdown('<div class="nav-brand">📊 AURA-ECE</div>', unsafe_allow_html=True)
    
    with header_mid:
        st.markdown(
            '<div class="nav-links">Features &nbsp;&nbsp;&nbsp;| &nbsp;&nbsp;&nbsp; How It Works &nbsp;&nbsp;&nbsp;| &nbsp;&nbsp;&nbsp; For Teachers &nbsp;&nbsp;&nbsp;| &nbsp;&nbsp;&nbsp; For Parents</div>',
            unsafe_allow_html=True,
        )
    
    with header_right:
        st.markdown(
            '<div style="display:flex; justify-content:flex-end; gap:8px; margin-top:4px;"><button class="nav-btn">Sign Up</button><button class="nav-btn" style="background:#6dd5ff; border-color:#6dd5ff; color:#1e2a3a;">Sign In</button></div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="page-under-nav">', unsafe_allow_html=True)

    # Full-page landing background without container feel.
    hero_image_url = get_landing_bg_src()
    st.markdown(
        dedent(
            f"""
            <style>
                .block-container {{
                    max-width: 1280px !important;
                    padding-left: 2rem !important;
                    padding-right: 2rem !important;
                    padding-top: 0.25rem !important;
                }}
                .fixed-nav {{
                    max-width: 100% !important;
                    left: 0 !important;
                    right: 0 !important;
                    border-radius: 0 !important;
                }}
                .page-under-nav {{
                    padding-top: 88px !important;
                }}
                .landing-hero {{
                    position: relative;
                    width: 100vw;
                    min-height: calc(100vh - 88px);
                    margin-left: calc(-50vw + 50%);
                    overflow: hidden;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background-color: #1f2d42;
                    background-image: linear-gradient(180deg, rgba(0,0,0,0.08) 0%, rgba(0,0,0,0.28) 100%), url('{hero_image_url}');
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                }}
                .landing-hero-brand {{
                    position: absolute;
                    bottom: -128px;
                    left: 50%;
                    transform: translateX(-50%);
                    z-index: 1;
                    opacity: 0.22;
                    pointer-events: none;
                    font-family: 'DM Serif Display', serif;
                    font-size: clamp(150px, 24vw, 380px);
                    font-weight: 700;
                    color: #ffffff;
                    line-height: 0.84;
                    white-space: nowrap;
                }}
                .landing-hero-content {{
                    position: relative;
                    z-index: 2;
                    text-align: center;
                    color: #ffffff;
                    max-width: 780px;
                    padding: 40px 24px;
                }}
                .landing-hero-actions {{
                    display: flex;
                    gap: 12px;
                    justify-content: center;
                    flex-wrap: wrap;
                }}
                @media (max-width: 820px) {{
                    .landing-hero-brand {{
                        bottom: -74px;
                    }}
                    .landing-hero-content h1 {{
                        font-size: 44px !important;
                    }}
                }}
            </style>
            <div class="landing-hero">
                <div class="landing-hero-brand">AURA-ECE</div>
                <div class="landing-hero-content">
                    <h1 style="font-family: 'DM Serif Display', serif; font-size: 64px; font-weight: 700; margin: 0 0 20px 0; line-height: 1.1; text-shadow: 0 2px 8px rgba(0,0,0,0.35);">Observe. Understand. Grow.</h1>
                    <p style="font-size: 18px; margin: 0 0 30px 0; line-height: 1.6; color: rgba(255,255,255,0.96); text-shadow: 0 1px 4px rgba(0,0,0,0.3);">AI-powered insights for early childhood education. Capture detailed observations of student development, generate actionable insights, and keep families engaged with personalized reports.</p>
                    <div class="landing-hero-actions">
                        <button class="action-button" style="background: #6dd5ff; color: #1e2a3a; font-weight: 700; padding: 14px 32px; font-size: 15px; border-radius: 8px; border: none; cursor: pointer; box-shadow: 0 4px 12px rgba(109, 213, 255, 0.3);">Get Started Free</button>
                        <button class="action-button" style="background: rgba(255,255,255,0.15); border: 2px solid #6dd5ff; color: #ffffff; padding: 12px 30px; font-size: 15px; border-radius: 8px; cursor: pointer; backdrop-filter: blur(10px);">Watch Demo (3:20)</button>
                    </div>
                </div>
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)

    # Quick Stats
    st.markdown('<h2 class="section-title">Trusted by educators worldwide</h2>', unsafe_allow_html=True)
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    with stat_col1:
        st.markdown('<div class="stat-box"><p class="stat-value">15K+</p><p class="stat-label">Teachers</p></div>', unsafe_allow_html=True)
    with stat_col2:
        st.markdown('<div class="stat-box"><p class="stat-value">250K+</p><p class="stat-label">Students</p></div>', unsafe_allow_html=True)
    with stat_col3:
        st.markdown('<div class="stat-box"><p class="stat-value">1.2M</p><p class="stat-label">Observations</p></div>', unsafe_allow_html=True)
    with stat_col4:
        st.markdown('<div class="stat-box"><p class="stat-value">4.8★</p><p class="stat-label">User Rating</p></div>', unsafe_allow_html=True)

    # Features Section
    st.markdown('<h2 class="section-title">Everything you need for student success</h2>', unsafe_allow_html=True)
    
    feat_col1, feat_col2, feat_col3 = st.columns(3)
    
    with feat_col1:
        st.markdown(
            '''
            <div class="feature-card">
                <div class="feature-icon">📝</div>
                <div class="feature-title">Rich Observations</div>
                <div class="feature-desc">Capture observations with text, audio notes, and photo evidence. AI transcribes and analyzes all content automatically.</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    
    with feat_col2:
        st.markdown(
            '''
            <div class="feature-card">
                <div class="feature-icon">🧠</div>
                <div class="feature-title">AI Insights</div>
                <div class="feature-desc">Generate meaningful insights from observations. Understand development trends, identify strengths, and track growth areas.</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    
    with feat_col3:
        st.markdown(
            '''
            <div class="feature-card">
                <div class="feature-icon">👨‍👩‍👧</div>
                <div class="feature-title">Parent Reports</div>
                <div class="feature-desc">Automated, personalized reports sent to families. Multi-language support keeps all caregivers informed of progress.</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    feat_col4, feat_col5, feat_col6 = st.columns(3)
    
    with feat_col4:
        st.markdown(
            '''
            <div class="feature-card">
                <div class="feature-icon">🔎</div>
                <div class="feature-title">Smart Search</div>
                <div class="feature-desc">Search through all student notes and observations instantly. Powered by AI to find relevant information in seconds.</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    
    with feat_col5:
        st.markdown(
            '''
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Batch Reporting</div>
                <div class="feature-desc">Generate weekly or monthly reports for all students at once. Customize report content and schedule automatic delivery.</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    
    with feat_col6:
        st.markdown(
            '''
            <div class="feature-card">
                <div class="feature-icon">🔒</div>
                <div class="feature-title">Secure & Private</div>
                <div class="feature-desc">FERPA-compliant data handling. Encryption, audit logs, and role-based access control protect sensitive student information.</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    # Login Section
    st.markdown('<h2 class="section-title">Start managing your classroom today</h2>', unsafe_allow_html=True)
    
    login_col1, login_col2 = st.columns([1.0, 1.4])
    
    with login_col1:
        st.markdown(
            '''
            <div style="background: #e8f1f7; border-radius: 10px; padding: 24px; border-left: 4px solid #2d3f5b;">
                <h3 style="margin: 0 0 12px 0; color: #2d3f5b; font-size: 18px; font-weight: 700;">Who are you?</h3>
                <p style="margin: 0; color: #5f707f; font-size: 13px; line-height: 1.6;">Choose your role to access the right tools and dashboard for your needs.</p>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    
    with login_col2:
        pass

    st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)

    role_col1, role_col2 = st.columns(2)
    
    with role_col1:
        if st.button("👨‍🏫 I'm a Teacher", use_container_width=True, key="role_teacher"):
            st.session_state["selected_role"] = "teacher"
    
    with role_col2:
        if st.button("👨‍👩‍👧 I'm a Parent", use_container_width=True, key="role_parent"):
            st.session_state["selected_role"] = "parent"

    selected_role = st.session_state.get("selected_role", "teacher")

    st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        st.markdown(f'<div class="form-label">Sign in as {"Teacher" if selected_role == "teacher" else "Parent"}</div>', unsafe_allow_html=True)
        
        user_id_default = "teacher-001" if selected_role == "teacher" else "parent-001"
        password_default = "teacher123" if selected_role == "teacher" else "parent123"
        
        user_id = st.text_input("User ID", value=user_id_default, placeholder="Enter your user ID")
        password = st.text_input("Password", value=password_default, type="password", placeholder="Enter your password")
        
        col_submit, col_demo = st.columns([1, 1])
        with col_submit:
            submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
        with col_demo:
            use_demo = st.form_submit_button("Use Demo Account", use_container_width=True)

    if submit:
        try:
            bootstrap_demo_users()
            data = api_request("POST", "/auth/login", json={"user_id": user_id, "password": password})
            st.session_state["auth"] = {
                "token": data["access_token"],
                "role": data["role"],
                "user_id": data["user_id"],
                "parent_id": data.get("parent_id"),
            }
            st.success("✅ Signed in successfully!")
            st.rerun()
        except Exception as exc:
            st.error(f"❌ Login failed: {exc}")

    if use_demo:
        try:
            bootstrap_demo_users()
            data = api_request("POST", "/auth/login", json={"user_id": user_id, "password": password})
            st.session_state["auth"] = {
                "token": data["access_token"],
                "role": data["role"],
                "user_id": data["user_id"],
                "parent_id": data.get("parent_id"),
            }
            st.success("✅ Demo sign in successful!")
            st.rerun()
        except Exception as exc:
            st.error(f"❌ Demo sign in failed: {exc}")

    st.markdown('<div style="height: 14px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="form-label">Or continue with Google</div>', unsafe_allow_html=True)
    google_redirect_url = get_google_popup_redirect_url(selected_role)
    st.link_button("Sign in with Google", google_redirect_url, use_container_width=True)
    st.caption("Google sign-in runs in a secure top-level page, then returns to this app.")

    # Footer Section
    st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)
    st.markdown(
        '''
        <div style="background: #f0f4f9; padding: 32px 24px; border-radius: 10px; text-align: center;">
            <h3 style="margin: 0 0 16px 0; color: #2d3f5b; font-family: 'DM Serif Display', serif; font-size: 24px;">Ready to transform your classroom?</h3>
            <p style="margin: 0 0 16px 0; color: #5f707f; font-size: 14px;">Join thousands of educators creating meaningful learning experiences.</p>
            <button class="action-button" style="background: #2d3f5b; padding: 12px 32px; font-size: 14px;">Start Your Free Trial</button>
            <p style="margin: 16px 0 0 0; color: #7a8a99; font-size: 12px;">No credit card required. 14-day free trial.</p>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def teacher_dashboard(auth: dict[str, Any]) -> None:
    # Dashboard Header
    st.markdown(
        f'''
        <div class="dashboard-header">
            <p class="dashboard-title">👨‍🏫 Teacher Workspace</p>
            <p class="dashboard-subtitle">Welcome back, {auth['user_id']}. Manage students, observations, and generate insights.</p>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    token = auth["token"]

    # Top Control Bar
    col_system, col_logout = st.columns([8, 1])
    with col_system:
        st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True)
    with col_logout:
        if st.button("🚪 Logout", key="logout_teacher", use_container_width=True):
            logout()

    st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)

    # Tab Navigation with Icons
    tab_students, tab_observations, tab_insights, tab_reports, tab_notes = st.tabs([
        "👥 Students",
        "📝 Observations", 
        "🧠 Insights",
        "📊 Reports",
        "📚 Notes"
    ])

    # ============ STUDENTS TAB ============
    with tab_students:
        st.markdown('<h3 class="subsection-title">👥 Manage Your Students</h3>', unsafe_allow_html=True)
        
        # Create Student Section
        st.markdown('<div class="form-group"><div class="form-label">➕ Add a New Student</div></div>', unsafe_allow_html=True)
        
        with st.form("add_student"):
            col_name, col_class = st.columns(2)
            with col_name:
                full_name = st.text_input("Student Name", placeholder="Enter full name")
            with col_class:
                class_id = st.text_input("Class ID", value="class-a", placeholder="e.g., class-a")
            
            col_parent_id, col_parent_name = st.columns(2)
            with col_parent_id:
                parent_id = st.text_input("Parent ID", value="parent-001", placeholder="Family ID")
            with col_parent_name:
                parent_name = st.text_input("Parent Name", placeholder="Contact name")
            
            col_lang, col_submit = st.columns([1, 1])
            with col_lang:
                parent_language = st.selectbox("Parent Language", ["en", "es", "fr", "de", "zh", "ja"], index=0)
            with col_submit:
                submitted = st.form_submit_button("✅ Add Student", use_container_width=True, type="primary")
        
        if submitted:
            try:
                created = api_request(
                    "POST",
                    "/students",
                    token=token,
                    json={
                        "full_name": full_name,
                        "class_id": class_id,
                        "parent_id": parent_id,
                        "parent_name": parent_name,
                        "parent_language": parent_language,
                    },
                )
                st.success(f"✅ Student '{created['full_name']}' added successfully!")
            except Exception as exc:
                st.error(f"❌ Error: {exc}")

        st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)

        # Students List Section
        st.markdown('<h3 class="subsection-title">📋 Active Students</h3>', unsafe_allow_html=True)
        try:
            students_data = api_request("GET", "/students", token=token)
            if students_data:
                for student in students_data:
                    st.markdown(
                        f'''
                        <div class="student-card">
                            <div class="student-avatar">{student['full_name'][0].upper()}</div>
                            <div class="student-info">
                                <p class="student-name">{student['full_name']}</p>
                                <p class="student-meta">Class: {student.get('class_id', 'N/A')} • Parent: {student.get('parent_name', 'N/A')} • ID: {student['_id']}</p>
                            </div>
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("📭 No students yet. Add one to get started!")
        except Exception as exc:
            st.error(f"❌ Error loading students: {exc}")

    # ============ OBSERVATIONS TAB ============
    with tab_observations:
        st.markdown('<h3 class="subsection-title">📝 Record Student Observation</h3>', unsafe_allow_html=True)
        st.markdown('Capture detailed observations with text, audio notes, and attach evidence. Our AI will analyze and index the content.', unsafe_allow_html=True)
        
        try:
            students_data = api_request("GET", "/students", token=token)
            student_map = {f"{s['full_name']} ({s['_id'][:8]}...)": s["_id"] for s in students_data}
        except Exception as exc:
            st.error(f"❌ Error loading students: {exc}")
            student_map = {}

        if not student_map:
            st.warning("⚠️ No students available. Please add students in the Students tab first.")
        else:
            with st.form("observation_form"):
                col_student, col_type = st.columns(2)
                with col_student:
                    choice = st.selectbox("Select Student", list(student_map.keys()))
                with col_type:
                    obs_type = st.selectbox("Observation Type", ["Development", "Behavior", "Academic", "Social", "Physical", "Other"])

                st.markdown('<div class="form-label">Observation Details</div>', unsafe_allow_html=True)
                text = st.text_area("📝 What did you observe? (Be specific and detailed)", placeholder="Describe the observation, context, and why it's significant...", height=100)
                
                st.markdown('<div class="form-label">Optional: Add Audio Note</div>', unsafe_allow_html=True)
                audio = st.file_uploader("🎤 Record or upload audio", type=["wav", "mp3", "m4a"], help="AI will transcribe your voice notes")
                st.markdown('<div class="form-label">Optional: Add Video Clip</div>', unsafe_allow_html=True)
                video = st.file_uploader("🎬 Upload classroom clip", type=["mp4", "mov", "avi", "mkv", "webm", "m4v"], help="Video will be analyzed into behavioral micro-moments")
                
                col_submit = st.columns([1])[0]
                with col_submit:
                    process_btn = st.form_submit_button("✅ Process Observation", use_container_width=True, type="primary")

                if process_btn:
                    if not text and not audio and not video:
                        st.error("❌ Please provide text, audio, or a video observation")
                    else:
                        try:
                            with st.spinner("🔄 Processing observation..."):
                                if video is not None:
                                    payload = {
                                        "student_id": student_map[choice],
                                        "video_base64": base64.b64encode(video.read()).decode("utf-8"),
                                        "video_mime_type": video.type or "video/mp4",
                                        "teacher_note": text or None,
                                    }
                                    result = api_request("POST", "/observations/video-process", token=token, json=payload)
                                else:
                                    payload = {
                                        "student_id": student_map[choice],
                                        "text": text or None,
                                        "audio_base64": None,
                                        "audio_mime_type": "audio/wav",
                                    }
                                    if audio is not None:
                                        payload["audio_base64"] = base64.b64encode(audio.read()).decode("utf-8")
                                        payload["audio_mime_type"] = audio.type or "audio/wav"

                                    result = api_request("POST", "/observations/process", token=token, json=payload)
                                
                                st.success("✅ Observation processed successfully!")
                                st.markdown('<div class="observation-box">', unsafe_allow_html=True)
                                st.json(result)
                                st.markdown('</div>', unsafe_allow_html=True)
                        except Exception as exc:
                            st.error(f"❌ Error processing observation: {exc}")

    # ============ INSIGHTS TAB ============
    with tab_insights:
        st.markdown('<h3 class="subsection-title">🧠 Student Development Insights</h3>', unsafe_allow_html=True)
        st.markdown('View AI-generated insights based on collected observations and development trends.', unsafe_allow_html=True)
        
        try:
            students_data = api_request("GET", "/students", token=token)
            student_map = {f"{s['full_name']} ({s['_id'][:8]}...)": s["_id"] for s in students_data}
        except Exception as exc:
            st.error(f"❌ Error loading students: {exc}")
            student_map = {}

        if not student_map:
            st.warning("⚠️ No students available.")
        else:
            ins_choice = st.selectbox("Select Student", list(student_map.keys()), key="insights_student")
            
            col_load, col_refresh = st.columns([1, 1])
            with col_load:
                if st.button("📊 Load Insights", use_container_width=True, type="primary"):
                    try:
                        with st.spinner("🔄 Analyzing observations..."):
                            data = api_request("GET", f"/students/{student_map[ins_choice]}/insights", token=token)
                            st.success("✅ Insights loaded!")
                            st.json(data)
                    except Exception as exc:
                        st.error(f"❌ Error: {exc}")
            
            with col_refresh:
                st.info("💡 Insights refresh automatically as new observations are added")

    # ============ REPORTS TAB ============
    with tab_reports:
        st.markdown('<h3 class="subsection-title">📊 Generate & Manage Reports</h3>', unsafe_allow_html=True)
        st.markdown('Create reports for individual students or run a batch cycle for all students.', unsafe_allow_html=True)
        
        try:
            students_data = api_request("GET", "/students", token=token)
            student_map = {f"{s['full_name']} ({s['_id'][:8]}...)": s["_id"] for s in students_data}
        except Exception as exc:
            st.error(f"❌ Error loading students: {exc}")
            student_map = {}

        # Report Generation Options
        col_period, col_type = st.columns(2)
        with col_period:
            period = st.selectbox("Report Period", ["weekly", "monthly"], help="How frequently reports are generated")
        with col_type:
            report_type = st.selectbox("Report Focus", ["Development", "Academic Progress", "Social Emotional", "Comprehensive"])

        col_feat1, col_feat2, col_feat3, col_feat4 = st.columns(4)
        with col_feat1:
            include_trends = st.checkbox("Include trends", value=True)
        with col_feat2:
            include_activity_suggestions = st.checkbox("Include activities", value=True)
        with col_feat3:
            include_parent_translation = st.checkbox("Translate for parent", value=True)
        with col_feat4:
            max_observations = st.number_input("Max observations", min_value=5, max_value=50, value=15, step=1)

        report_payload = {
            "period": period,
            "include_trends": include_trends,
            "include_activity_suggestions": include_activity_suggestions,
            "include_parent_translation": include_parent_translation,
            "max_observations": int(max_observations),
        }

        st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)

        # Individual Report Section
        st.markdown('<h4 style="color: #2d3f5b; margin-bottom: 12px;">📄 Generate Individual Report</h4>', unsafe_allow_html=True)
        
        if not student_map:
            st.warning("⚠️ No students available.")
        else:
            rep_choice = st.selectbox("Select Student", list(student_map.keys()), key="report_student")
            
            col_gen, col_preview = st.columns([1, 1])
            with col_gen:
                if st.button("✍️ Generate Report", use_container_width=True, type="primary", key="gen_report"):
                    try:
                        with st.spinner("🔄 Generating report..."):
                            report = api_request("POST", f"/reports/generate/{student_map[rep_choice]}", token=token, json=report_payload)
                            st.success("✅ Report generated!")
                            st.json(report)
                    except Exception as exc:
                        st.error(f"❌ Error: {exc}")
            
            with col_preview:
                st.info("ℹ️ Reports are sent to parent contacts automatically")

        st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)

        # Batch Report Section
        st.markdown('<h4 style="color: #2d3f5b; margin-bottom: 12px;">📋 Batch Report Cycle</h4>', unsafe_allow_html=True)
        st.markdown('Generate reports for all students in your class at once.', unsafe_allow_html=True)
        
        col_cycle, col_info = st.columns([1, 2])
        with col_cycle:
            if st.button("🔄 Run Report Cycle", use_container_width=True, type="primary", key="cycle_btn"):
                try:
                    with st.spinner("⏳ Running batch cycle..."):
                        cycle = api_request("POST", "/reports/run-cycle", token=token, json=report_payload)
                        st.success("✅ Batch cycle completed!")
                        st.json(cycle)
                except Exception as exc:
                    st.error(f"❌ Error: {exc}")
        with col_info:
            st.caption("💡 This generates reports for all students and schedules delivery to parents")

        st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)

        # Master Class Intelligence Section
        st.markdown('<h4 style="color: #2d3f5b; margin-bottom: 12px;">🏫 Master Class Intelligence Report</h4>', unsafe_allow_html=True)
        class_id = st.text_input("Class ID", value="class-a", key="class_report_class_id")

        col_class_gen, col_class_view = st.columns(2)
        with col_class_gen:
            if st.button("🧠 Generate Class Intelligence", use_container_width=True, type="primary", key="gen_class_report"):
                try:
                    with st.spinner("🔄 Generating class report..."):
                        class_report = api_request(
                            "POST",
                            f"/reports/class/generate/{class_id.strip()}",
                            token=token,
                            json={"period": period},
                        )
                        st.success("✅ Class intelligence report generated!")
                        st.json(class_report)
                except Exception as exc:
                    st.error(f"❌ Error: {exc}")

        with col_class_view:
            if st.button("👁️ View Latest Class Report", use_container_width=True, key="view_class_report"):
                try:
                    with st.spinner("📚 Loading class report..."):
                        class_report = api_request(
                            "GET",
                            f"/reports/class/{class_id.strip()}?period={period}",
                            token=token,
                        )
                        st.success("✅ Class report loaded!")
                        st.json(class_report)
                except Exception as exc:
                    st.error(f"❌ Error: {exc}")

        role_col1, role_col2, role_col3 = st.columns(3)
        with role_col1:
            role_view = st.selectbox("Role View", ["teacher", "parent", "student"], key="class_role_view")
        with role_col2:
            role_parent_id = st.text_input("Parent ID (optional)", key="class_role_parent")
        with role_col3:
            role_student_id = st.text_input("Student ID (optional)", key="class_role_student")

        if st.button("🔍 Generate Role-Based View", use_container_width=True, key="view_class_role"):
            try:
                with st.spinner("🔄 Building role-specific view..."):
                    view = api_request(
                        "POST",
                        f"/reports/class/{class_id.strip()}/view",
                        token=token,
                        json={
                            "role": role_view,
                            "period": period,
                            "parent_id": role_parent_id.strip() or None,
                            "student_id": role_student_id.strip() or None,
                        },
                    )
                    st.success("✅ Role-based report view ready!")
                    st.json(view)
            except Exception as exc:
                st.error(f"❌ Error: {exc}")

        st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)

        # Report Approval Section
        st.markdown('<h4 style="color: #2d3f5b; margin-bottom: 12px;">✅ Approve Report for Delivery</h4>', unsafe_allow_html=True)
        
        report_id = st.text_input("📌 Report ID", placeholder="Paste the report ID to approve...", help="ID from generated report above")
        
        if st.button("✓ Approve & Send", use_container_width=True, type="primary", key="approve_btn"):
            if report_id.strip():
                try:
                    with st.spinner("📤 Approving report..."):
                        approved = api_request("POST", f"/reports/{report_id.strip()}/approve", token=token, json={"approved": True})
                        st.success("✅ Report approved and sent to parents!")
                        st.json(approved)
                except Exception as exc:
                    st.error(f"❌ Error: {exc}")
            else:
                st.error("❌ Please enter a report ID")

    # ============ NOTES TAB ============
    with tab_notes:
        st.markdown('<h3 class="subsection-title">📚 Note Management & AI Search</h3>', unsafe_allow_html=True)
        st.markdown('Upload student notes, lesson documents, or planning sheets. Search through all notes using AI-powered search.', unsafe_allow_html=True)
        
        # Upload Section
        st.markdown('<h4 style="color: #2d3f5b; margin-bottom: 12px;">📤 Upload & Index Notes</h4>', unsafe_allow_html=True)
        
        col_owner_type, col_owner_id = st.columns(2)
        with col_owner_type:
            owner_type = st.selectbox("Note Owner Type", ["student", "teacher"], key="notes_owner_type")
        with col_owner_id:
            if owner_type == "teacher":
                owner_id = auth["user_id"]
                st.caption(f"📝 Owner: {owner_id}")
            else:
                try:
                    students_data = api_request("GET", "/students", token=token)
                    student_options = {f"{s['full_name']} ({s['_id'][:8]}...)": s["_id"] for s in students_data}
                    owner_id = st.selectbox("Select Student", list(student_options.values()) if student_options else [], key="notes_student")
                except:
                    owner_id = ""

        embed_metadata = st.checkbox("✓ Include metadata in analysis", value=True, help="Improves search accuracy")
        note_file = st.file_uploader(
            "📎 Upload file",
            type=["pdf", "docx", "txt", "md", "csv", "log", "png", "jpg", "jpeg", "bmp", "tiff", "webp", "wav", "mp3", "m4a", "aac", "ogg", "flac", "mp4", "mov", "avi", "mkv", "webm", "m4v"],
            help="Supported: documents, images, audio, and video evidence files."
        )

        if st.button("🚀 Analyze & Index", use_container_width=True, type="primary", key="upload_btn"):
            if note_file is None:
                st.error("❌ Please select a file to upload")
            elif not owner_id:
                st.error("❌ Please select an owner")
            else:
                try:
                    with st.spinner("🔄 Processing and indexing..."):
                        files = {"file": (note_file.name, note_file.read(), note_file.type or "application/octet-stream")}
                        data = {
                            "owner_type": owner_type,
                            "owner_id": owner_id.strip() if isinstance(owner_id, str) else str(owner_id),
                            "embed_metadata": str(embed_metadata).lower(),
                        }
                        out = api_request("POST", "/notes/analyze-upload", token=token, files=files, data=data)
                        st.success("✅ File indexed successfully!")
                        st.json(out)
                except Exception as exc:
                    st.error(f"❌ Error: {exc}")

        st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)

        # Search Section
        st.markdown('<h4 style="color: #2d3f5b; margin-bottom: 12px;">🔍 AI-Powered Search</h4>', unsafe_allow_html=True)
        st.markdown('Search through all notes and documents using natural language.', unsafe_allow_html=True)
        
        search_owner_type = st.selectbox("Search in", ["student", "teacher"], key="search_owner_type")
        search_owner_id = st.text_input("🔑 Search Owner ID", value=auth["user_id"] if search_owner_type == "teacher" else "", key="search_owner_id")
        search_file_kind = st.selectbox("File Type", ["all", "document", "image", "audio", "video", "other"], key="search_file_kind")
        
        col_query, col_search = st.columns([3, 1])
        with col_query:
            q = st.text_input("🔎 What are you looking for?", placeholder="E.g., 'behavior observations about sharing'", key="search_query")
        with col_search:
            search_btn = st.button("Search", use_container_width=True, type="primary", key="search_btn")

        if search_btn:
            if not q.strip():
                st.error("❌ Please enter a search query")
            else:
                try:
                    with st.spinner("🔍 Searching..."):
                        params = f"?q={q}&owner_type={search_owner_type}&owner_id={search_owner_id.strip()}"
                        if search_file_kind != "all":
                            params += f"&file_kind={search_file_kind}"
                        notes = api_request("GET", f"/notes/search{params}", token=token)
                        st.success(f"✅ Found results!")
                        st.json(notes)
                except Exception as exc:
                    st.error(f"❌ Error: {exc}")


def parent_dashboard(auth: dict[str, Any]) -> None:
    # Dashboard Header
    st.markdown(
        f'''
        <div class="dashboard-header">
            <p class="dashboard-title">👨‍👩‍👧 Parent Portal</p>
            <p class="dashboard-subtitle">Welcome! Stay informed about your child's progress and development.</p>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # Top Control Bar
    col_info, col_logout = st.columns([8, 1])
    with col_info:
        st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True)
    with col_logout:
        if st.button("🚪 Logout", key="logout_parent", use_container_width=True):
            logout()

    st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)

    parent_id = auth.get("parent_id") or auth["user_id"]
    
    # Reports Section
    st.markdown('<h2 class="section-title">📊 Your Child\'s Reports</h2>', unsafe_allow_html=True)
    st.markdown('Personalized progress reports sent from the classroom. See what your child is learning and growing in.', unsafe_allow_html=True)

    col_load, col_info = st.columns([1, 3])
    with col_load:
        if st.button("🔄 Load My Reports", use_container_width=True, type="primary", key="load_reports"):
            try:
                with st.spinner("📚 Loading reports..."):
                    reports = api_request("GET", f"/parents/{parent_id}/reports", token=auth["token"])
                    
                    if not reports:
                        st.info("📭 No approved reports available yet. Check back soon!")
                    else:
                        for idx, report in enumerate(reports):
                            # Report Card
                            period_name = report.get('period', 'Report').title()
                            report_id = report.get('_id', f'report-{idx}')
                            
                            st.markdown(
                                f'''
                                <div class="report-card">
                                    <div class="report-header">
                                        <h4 class="report-title">{period_name} Report</h4>
                                        <span class="report-status">✓ Approved</span>
                                    </div>
                                    <div style="font-size: 13px; line-height: 1.6; color: #3f5068;">
                                        {report.get('translated_parent_summary', 'No summary available')}
                                    </div>
                                </div>
                                ''',
                                unsafe_allow_html=True,
                            )

                            # Activities Section
                            activities = report.get("activity_suggestions") or []
                            if activities:
                                st.markdown(
                                    '''
                                    <div style="margin-top: 12px; padding: 12px; background: #f0f4f9; border-radius: 6px; border-left: 3px solid #6dd5ff;">
                                        <p style="color: #2d3f5b; font-weight: 600; margin: 0 0 8px 0;">🏠 Try These Activities at Home</p>
                                        <ul style="margin: 0; padding-left: 16px;color: #3f5068; font-size: 13px;">
                                    ''',
                                    unsafe_allow_html=True,
                                )
                                for act in activities:
                                    st.markdown(f'<li style="margin-bottom: 6px;">{act}</li>', unsafe_allow_html=True)
                                st.markdown(
                                    '</ul></div>',
                                    unsafe_allow_html=True,
                                )
                            
                            st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)

            except Exception as exc:
                st.error(f"❌ Error loading reports: {exc}")
    
    with col_info:
        st.info("💡 Reports are generated regularly by your child's teacher and shared with families to maintain communication and celebrate progress!")

    st.markdown('<div style="height: 32px;"></div>', unsafe_allow_html=True)

    # Learning Areas Overview
    st.markdown('<h2 class="section-title">🎯 Development Areas</h2>', unsafe_allow_html=True)
    st.markdown('Common learning focus areas tracked for your child.', unsafe_allow_html=True)

    dev_col1, dev_col2, dev_col3 = st.columns(3)
    
    with dev_col1:
        st.markdown(
            '''
            <div class="report-card">
                <h4 style="color: #2d3f5b; margin: 0 0 8px 0;">📚 Academic</h4>
                <p style="font-size: 13px; color: #5f707f; margin: 0;">Letter recognition, counting, early writing skills</p>
                <div class="insight-tag" style="margin-top: 10px;">In Progress</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    
    with dev_col2:
        st.markdown(
            '''
            <div class="report-card">
                <h4 style="color: #2d3f5b; margin: 0 0 8px 0;">🤝 Social</h4>
                <p style="font-size: 13px; color: #5f707f; margin: 0;">Sharing, cooperation, making friends, listening skills</p>
                <div class="insight-tag" style="margin-top: 10px;">Developing</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    
    with dev_col3:
        st.markdown(
            '''
            <div class="report-card">
                <h4 style="color: #2d3f5b; margin: 0 0 8px 0;">🎨 Creative</h4>
                <p style="font-size: 13px; color: #5f707f; margin: 0;">Art, music, imaginative play, self-expression</p>
                <div class="insight-tag" style="margin-top: 10px;">Exploring</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height: 32px;"></div>', unsafe_allow_html=True)

    # Tips Section
    st.markdown('<h2 class="section-title">💡 Parent Tips</h2>', unsafe_allow_html=True)
    st.markdown('Ways to support your child\'s learning at home.', unsafe_allow_html=True)

    tip_col1, tip_col2 = st.columns(2)
    
    with tip_col1:
        st.markdown(
            '''
            <div class="feature-card">
                <div class="feature-icon">🗣️</div>
                <div class="feature-title">Talk About Their Day</div>
                <div class="feature-desc">Ask open-ended questions about what they played, learned, and who they played with. This helps reinforce learning and shows interest.</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    
    with tip_col2:
        st.markdown(
            '''
            <div class="feature-card">
                <div class="feature-icon">📖</div>
                <div class="feature-title">Read Together</div>
                <div class="feature-desc">Reading daily builds language skills and creates quality time. Let them pick books they're interested in.</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    tip_col3, tip_col4 = st.columns(2)
    
    with tip_col3:
        st.markdown(
            '''
            <div class="feature-card">
                <div class="feature-icon">🎮</div>
                <div class="feature-title">Learning Through Play</div>
                <div class="feature-desc">The best learning happens through play. Building, cooking, gardening, and imaginative games all build skills.</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    
    with tip_col4:
        st.markdown(
            '''
            <div class="feature-card">
                <div class="feature-icon">🤗</div>
                <div class="feature-title">Celebrate Progress</div>
                <div class="feature-desc">Praise effort over results. "You worked really hard on that!" builds confidence and a love of learning.</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )


def main() -> None:
    st.set_page_config(page_title="AURA-ECE", page_icon="A", layout="wide")
    init_state()
    render_global_css()

    auth = st.session_state.get("auth")
    if not auth:
        landing_and_login()
        return

    if auth.get("role") == "teacher":
        teacher_dashboard(auth)
    else:
        parent_dashboard(auth)


if __name__ == "__main__":
    main()
