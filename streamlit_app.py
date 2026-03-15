import base64
import mimetypes
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
import requests
import streamlit as st
import streamlit.components.v1 as components

API_BASE = os.getenv("AURA_API_BASE", "http://localhost:8000")

class ApiError(Exception):
    pass

def _wait_for_api_ready(max_wait_seconds: int = 12) -> bool:
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        try:
            response = requests.get(f"{API_BASE}/health", timeout=3)
            if response.ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.8)
    return False

def api_request(method: str, path: str, token: str | None = None, json: dict | None = None, files: dict | None = None, data: dict | None = None) -> Any:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    last_error: Exception | None = None
    for _ in range(3):
        try:
            if files:
                response = requests.request(method, f"{API_BASE}{path}", headers=headers, files=files, data=data, timeout=120)
            else:
                response = requests.request(method, f"{API_BASE}{path}", headers=headers, json=json, timeout=120)
            break
        except requests.ConnectionError as exc:
            last_error = exc
            if not _wait_for_api_ready(max_wait_seconds=5):
                continue
            time.sleep(0.3)
        except requests.RequestException as exc:
            raise ApiError(f"Network error contacting API: {exc}") from exc
    else:
        raise ApiError("API is unreachable at http://localhost:8000. Start backend: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000") from last_error

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
    st.session_state.setdefault("page", "login")
    st.session_state.setdefault("show_feature_showcase", False)

def logout() -> None:
    st.session_state["auth"] = None
    st.session_state["page"] = "login"
    st.session_state["show_feature_showcase"] = False
    st.rerun()

def bootstrap_demo_users() -> None:
    try:
        requests.post(f"{API_BASE}/auth/bootstrap", timeout=20)
    except Exception:
        pass

def sign_in_with_google_id_token(id_token: str, requested_role: str) -> dict[str, Any]:
    return api_request("POST", "/auth/firebase-google", json={"id_token": id_token, "requested_role": requested_role})


def handle_google_callback() -> bool:
    google_token = st.query_params.get("g_id_token")
    if not google_token:
        return False

    requested_role = st.query_params.get("g_role", "teacher")
    try:
        data = sign_in_with_google_id_token(google_token, requested_role)
        st.session_state["auth"] = {
            "token": data["access_token"],
            "role": data["role"],
            "user_id": data["user_id"],
            "student_id": data.get("student_id"),
            "parent_id": data.get("parent_id"),
        }
        st.session_state["page"] = "landing"
        st.query_params.clear()
        st.rerun()
    except Exception as exc:
        st.query_params.clear()
        st.error(f"Google sign in failed: {exc}")
    return True

def get_google_popup_redirect_url(requested_role: str) -> str:
    configured_return = os.getenv("AURA_FRONTEND_BASE")
    if configured_return:
        frontend_return = configured_return
    else:
        server_address = st.get_option("server.address") or "localhost"
        server_port = st.get_option("server.port") or 8501
        frontend_return = f"http://{server_address}:{server_port}"
    safe_role = requested_role if requested_role in {"teacher", "student", "parent"} else "teacher"
    popup_base = os.getenv("AURA_POPUP_BASE", "http://localhost:8000")
    return f"{popup_base}/auth/firebase-google-popup?role={quote_plus(safe_role)}&return_to={quote_plus(frontend_return)}"


def render_google_popup_button(redirect_url: str) -> None:
    safe_url = redirect_url.replace("&", "&amp;").replace("'", "&#39;")
    components.html(
        f"""
        <div style=\"width:100%;\">
            <button id=\"aura-google-popup\" style=\"
                width:100%;
                height: 48px;
                border:none;
                border-radius: 999px;
                font-weight: 500;
                font-size: 15px;
                cursor: pointer;
                color: #fff;
                background: #1a1a1a;
            \">Sign in with Google</button>
        </div>
        <script>
            (function() {{
                const btn = document.getElementById('aura-google-popup');
                const authUrl = '{safe_url}';
                btn.addEventListener('click', function() {{
                    const width = 520;
                    const height = 740;
                    const left = Math.max(0, (window.screen.width - width) / 2);
                    const top = Math.max(0, (window.screen.height - height) / 2);
                    const features = `popup=yes,width=${{width}},height=${{height}},left=${{left}},top=${{top}}`;
                    const popup = window.open(authUrl, 'aura_google_auth', features);
                    if (!popup) {{
                        window.location.href = authUrl;
                        return;
                    }}
                    popup.focus();
                }});
            }})();
        </script>
        """,
        height=58,
    )

def get_landing_bg_src() -> str:
    candidates = [Path("assets/bg/bg.png"), Path("assets/bg/bg.jpg"), Path("assets/bg/bg.jpeg"), Path("assets/bg/bg.webp")]
    for path in candidates:
        if path.exists() and path.is_file():
            suffix = path.suffix.lower().lstrip(".")
            mime = "image/jpeg" if suffix == "jpg" else f"image/{suffix}"
            encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
            return f"data:{mime};base64,{encoded}"
    return "https://images.pexels.com/photos/3807517/pexels-photo-3807517.jpeg?auto=compress&cs=tinysrgb&w=1600"

UNSEEN_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600;1,700&family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-cream: #efe6dd;
        --bg-warm: #F5F0EA;
        --bg-blush: #F0E8E0;
        --bg-glass: rgba(239, 230, 221, 0.72);
        --bg-glass-strong: rgba(239, 230, 221, 0.88);
        --text-primary: #1a1a1a;
        --text-secondary: #6b6b6b;
        --text-muted: #9a9a9a;
        --border-light: rgba(0, 0, 0, 0.06);
        --border-medium: rgba(0, 0, 0, 0.12);
        --accent-black: #1a1a1a;
        --accent-warm: #c4a882;
        --radius-pill: 999px;
        --radius-card: 16px;
        --radius-input: 12px;
        --shadow-soft: 0 4px 24px rgba(0, 0, 0, 0.04);
        --shadow-hover: 0 8px 40px rgba(0, 0, 0, 0.08);
        --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        --font-serif: 'Playfair Display', Georgia, 'Times New Roman', serif;
        --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background: var(--bg-cream) !important;
        font-family: var(--font-sans) !important;
        color: var(--text-primary) !important;
    }

    .stApp::after {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        pointer-events: none;
        z-index: 9999;
        opacity: 0.035;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
        background-repeat: repeat;
        background-size: 256px 256px;
    }

    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
    #MainMenu, footer, .stDeployButton { display: none !important; }

    .block-container {
        max-width: 1100px !important;
        padding: 0 2rem 3rem 2rem !important;
    }

    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3,
    [data-testid="stAppViewContainer"] h4 {
        font-family: var(--font-serif) !important;
        color: var(--text-primary) !important;
        font-weight: 500 !important;
    }

    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] span,
    [data-testid="stAppViewContainer"] li,
    .stMarkdown, .stMarkdown p {
        font-family: var(--font-sans) !important;
        color: var(--text-primary) !important;
    }

    .stButton > button,
    .stFormSubmitButton > button,
    button[kind="primary"],
    button[kind="primaryFormSubmit"] {
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        border-radius: var(--radius-pill) !important;
        padding: 10px 28px !important;
        border: 1.5px solid var(--accent-black) !important;
        background: var(--accent-black) !important;
        color: #ffffff !important;
        transition: var(--transition) !important;
        letter-spacing: 0.01em !important;
    }
    
    .stButton > button p,
    .stFormSubmitButton > button p,
    button[kind="primary"] p,
    button[kind="primaryFormSubmit"] p {
        color: #ffffff !important;
    }

    .stButton > button:hover,
    .stFormSubmitButton > button:hover,
    button[kind="primary"]:hover,
    button[kind="primaryFormSubmit"]:hover {
        background: #333333 !important;
        border-color: #333333 !important;
        transform: translateY(-1px) !important;
        box-shadow: var(--shadow-hover) !important;
    }

    .stLinkButton > a {
        font-family: var(--font-sans) !important;
        font-size: 14px !important;
        border-radius: var(--radius-pill) !important;
        border: 1.5px solid var(--border-medium) !important;
        background: transparent !important;
        color: var(--text-primary) !important;
        transition: var(--transition) !important;
    }

    .stLinkButton > a p {
        color: var(--text-primary) !important;
    }

    .stLinkButton > a:hover {
        border-color: var(--accent-black) !important;
    }

    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {
        font-family: var(--font-sans) !important;
        color: var(--text-primary) !important;
        background: rgba(255, 255, 255, 0.7) !important;
        border: 1px solid var(--border-medium) !important;
        border-radius: var(--radius-input) !important;
        backdrop-filter: blur(8px) !important;
        transition: var(--transition) !important;
    }
    [data-baseweb="input"] input:focus,
    [data-baseweb="textarea"] textarea:focus {
        border-color: var(--accent-black) !important;
        box-shadow: 0 0 0 1px var(--accent-black) !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label,
    .stRadio label, .stCheckbox label, .stFileUploader label, .stNumberInput label {
        color: var(--text-secondary) !important;
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
    }

    .stSelectbox [data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.7) !important;
        border: 1px solid var(--border-medium) !important;
        border-radius: var(--radius-input) !important;
        backdrop-filter: blur(8px) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background: transparent !important;
        border-bottom: none !important;
        padding: 4px 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: var(--font-sans) !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 8px 20px !important;
        border-radius: var(--radius-pill) !important;
        border: 1.5px solid var(--border-medium) !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
        transition: var(--transition) !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        border-color: var(--accent-black) !important;
        color: var(--text-primary) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--accent-black) !important;
        color: #ffffff !important;
        border-color: var(--accent-black) !important;
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    [data-testid="stFileUploader"] {
        border: 1.5px dashed var(--border-medium) !important;
        border-radius: var(--radius-card) !important;
        background: rgba(255, 255, 255, 0.5) !important;
        padding: 16px !important;
    }

    [data-testid="stAlert"] {
        background: var(--bg-glass) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-card) !important;
        backdrop-filter: blur(12px) !important;
        color: var(--text-primary) !important;
    }

    .stJson { border-radius: var(--radius-card) !important; }

    .unseen-nav {
        position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
        background: rgba(250, 247, 242, 0.82);
        backdrop-filter: blur(20px) saturate(1.4);
        -webkit-backdrop-filter: blur(20px) saturate(1.4);
        border-bottom: 1px solid var(--border-light);
        padding: 18px 40px;
        display: flex; align-items: center; justify-content: space-between;
    }
    .unseen-nav-brand {
        font-family: var(--font-sans);
        font-size: 18px; font-weight: 600; letter-spacing: -0.02em;
        color: var(--text-primary); text-decoration: none;
    }
    .unseen-nav-links {
        display: flex; align-items: center; gap: 32px;
        font-family: var(--font-sans); font-size: 14px; color: var(--text-secondary);
    }
    /* override streamlit main container for full edge-to-edge */
    .unseen-hero {
        width: 100vw !important;
        position: relative;
        left: 50%;
        right: 50%;
        margin-left: -50vw !important;
        margin-right: -50vw !important;
    }
    .landing-content-wrapper {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 40px;
    }
</style>
"""

def render_global_css() -> None:
    st.html(UNSEEN_CSS)

UNSEEN_CSS_2 = """
<style>
    .unseen-hero {
        min-height: calc(100vh - 80px);
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        text-align: center; padding: 120px 24px 80px 24px;
        position: relative; overflow: hidden;
    }
    .unseen-hero-label {
        font-family: var(--font-sans); font-size: 12px; font-weight: 500;
        letter-spacing: 0.18em; text-transform: uppercase;
        color: var(--text-muted); margin-bottom: 24px;
    }
    .unseen-hero h1 {
        font-family: var(--font-serif) !important; font-size: clamp(48px, 8vw, 82px);
        font-weight: 400 !important; line-height: 1.08;
        color: var(--text-primary) !important; margin: 0 0 16px 0;
        max-width: 800px;
    }
    .unseen-hero h1 em {
        font-style: italic; font-weight: 400;
    }
    .unseen-hero-sub {
        font-family: var(--font-sans); font-size: 17px;
        color: var(--text-secondary); line-height: 1.6;
        max-width: 520px; margin: 0 auto 40px auto;
    }
    .unseen-pill-btn {
        display: inline-flex; align-items: center; gap: 8px;
        font-family: var(--font-sans); font-size: 14px; font-weight: 500;
        padding: 14px 32px; border-radius: var(--radius-pill);
        text-decoration: none; transition: var(--transition); cursor: pointer;
    }
    span.unseen-pill-solid {
        background: var(--accent-black); color: #ffffff !important; border: 1.5px solid var(--accent-black);
    }
    span.unseen-pill-solid:hover {
        background: #333; transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        color: #ffffff !important;
    }
    .unseen-pill-outline {
        background: transparent; color: var(--text-primary);
        border: 1.5px solid var(--border-medium);
    }
    .unseen-pill-outline:hover {
        border-color: var(--accent-black); transform: translateY(-2px);
    }

    .unseen-card {
        background: var(--bg-glass);
        backdrop-filter: blur(16px) saturate(1.2);
        -webkit-backdrop-filter: blur(16px) saturate(1.2);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-card); padding: 28px;
        transition: var(--transition);
    }
    .unseen-card:hover {
        box-shadow: var(--shadow-hover);
        border-color: var(--border-medium);
        transform: translateY(-2px);
    }
    .unseen-card-icon {
        font-size: 28px;
        margin-bottom: 16px;
        color: var(--text-primary);
        line-height: 1;
    }
    .unseen-card-title {
        font-family: var(--font-sans); font-size: 16px;
        font-weight: 600; color: var(--text-primary); margin-bottom: 8px;
    }
    .unseen-card-desc {
        font-family: var(--font-sans); font-size: 14px;
        color: var(--text-secondary); line-height: 1.6;
    }

    @keyframes blob-drift {
        0% { transform: translate(0, 0) rotate(0deg) scale(1); }
        33% { transform: translate(3vw, -4vh) rotate(10deg) scale(1.1); }
        66% { transform: translate(-2vw, 2vh) rotate(-5deg) scale(0.95); }
        100% { transform: translate(0, 0) rotate(0deg) scale(1); }
    }
    .unseen-blob {
        position: absolute; filter: blur(90px); z-index: 0; opacity: 0.6;
        animation: blob-drift 25s infinite ease-in-out; pointer-events: none;
    }
    .unseen-blob-1 {
        width: 45vw; height: 45vw; border-radius: 50%;
        background: radial-gradient(circle, rgba(230,200,180,0.85) 0%, rgba(230,200,180,0) 70%);
        top: -10%; left: -10%; animation-delay: 0s;
    }
    .unseen-blob-2 {
        width: 55vw; height: 55vw; border-radius: 50%;
        background: radial-gradient(circle, rgba(180,210,230,0.85) 0%, rgba(180,210,230,0) 70%);
        bottom: -15%; right: -5%; animation-delay: -7s;
    }

    .unseen-stat-grid {
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 24px; background: transparent;
        margin: -80px auto 80px auto; max-width: 1100px;
        position: relative; z-index: 20; padding: 0 24px;
    }
    .unseen-stat {
        background: rgba(255, 255, 255, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.7);
        border-radius: 24px; padding: 36px 24px; text-align: center;
        backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        transform: translateY(0); transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        box-shadow: 0 12px 40px rgba(0,0,0,0.04);
    }
    .unseen-stat:hover {
        transform: translateY(-8px) scale(1.02);
        background: rgba(255, 255, 255, 0.7);
        box-shadow: 0 24px 60px rgba(0,0,0,0.08);
        border-color: rgba(255, 255, 255, 0.9);
    }
    .unseen-stat-value {
        font-family: var(--font-serif); font-size: 46px;
        font-weight: 400; color: var(--text-primary); margin: 0; line-height: 1;
    }
    .unseen-stat-label {
        font-family: var(--font-sans); font-size: 13px;
        font-weight: 600; letter-spacing: 0.12em;
        text-transform: uppercase; color: var(--text-muted);
        margin: 12px 0 0 0;
    }

    .unseen-section-title {
        font-family: var(--font-serif); font-size: 36px;
        font-weight: 400; color: var(--text-primary);
        margin: 56px 0 12px 0; line-height: 1.15;
    }
    .unseen-section-sub {
        font-family: var(--font-sans); font-size: 15px;
        color: var(--text-secondary); margin: 0 0 32px 0;
    }

    .unseen-form-section {
        background: var(--bg-glass);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-card);
        padding: 32px; margin-bottom: 24px;
    }
    .unseen-form-label {
        font-family: var(--font-sans); font-size: 12px;
        font-weight: 600; letter-spacing: 0.1em;
        text-transform: uppercase; color: var(--text-muted);
        margin-bottom: 12px;
    }

    .unseen-student-card {
        background: var(--bg-glass);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-card);
        padding: 20px 24px; margin-bottom: 10px;
        display: flex; align-items: center; gap: 16px;
        transition: var(--transition);
    }
    .unseen-student-card:hover {
        border-color: var(--border-medium);
        box-shadow: var(--shadow-soft);
        transform: translateY(-1px);
    }
    .unseen-avatar {
        width: 44px; height: 44px; border-radius: 50%;
        background: linear-gradient(135deg, #e8ddd2 0%, #d4c4b0 100%);
        display: flex; align-items: center; justify-content: center;
        color: var(--text-primary); font-family: var(--font-serif);
        font-size: 18px; font-weight: 500; flex-shrink: 0;
    }
    .unseen-student-name {
        font-family: var(--font-sans); font-weight: 600;
        font-size: 15px; color: var(--text-primary); margin: 0;
    }
    .unseen-student-meta {
        font-family: var(--font-sans); font-size: 12px;
        color: var(--text-muted); margin: 3px 0 0 0;
    }

    .unseen-report-card {
        background: var(--bg-glass);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border-light);
        border-left: 3px solid var(--accent-warm);
        border-radius: var(--radius-card);
        padding: 24px; margin-bottom: 16px;
        transition: var(--transition);
    }
    .unseen-report-card:hover {
        box-shadow: var(--shadow-soft);
    }
    .unseen-report-header {
        display: flex; justify-content: space-between;
        align-items: center; margin-bottom: 14px;
    }
    .unseen-report-title {
        font-family: var(--font-serif); font-size: 18px;
        font-weight: 500; color: var(--text-primary); margin: 0;
    }
    .unseen-badge {
        font-family: var(--font-sans); font-size: 11px;
        font-weight: 600; letter-spacing: 0.06em;
        padding: 5px 14px; border-radius: var(--radius-pill);
        background: rgba(196, 168, 130, 0.12);
        color: #8a7050; border: 1px solid rgba(196, 168, 130, 0.25);
    }

    .unseen-chip {
        display: inline-block; font-family: var(--font-sans);
        font-size: 12px; font-weight: 500;
        padding: 5px 14px; border-radius: var(--radius-pill);
        border: 1px solid var(--border-medium);
        color: var(--text-secondary); margin: 3px 4px 3px 0;
    }

    .unseen-dashboard-header {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-card);
        padding: 28px 32px; margin-bottom: 8px;
    }
    .unseen-dashboard-title {
        font-family: var(--font-serif); font-size: 28px;
        font-weight: 400; color: var(--text-primary); margin: 0;
    }
    .unseen-dashboard-sub {
        font-family: var(--font-sans); font-size: 14px;
        color: var(--text-muted); margin: 6px 0 0 0;
    }

    .page-spacer { padding-top: 80px; }

    .unseen-activity-box {
        background: rgba(196, 168, 130, 0.06);
        border: 1px solid rgba(196, 168, 130, 0.15);
        border-radius: var(--radius-card);
        padding: 20px; margin-top: 12px;
    }

    .unseen-footer {
        text-align: center; padding: 48px 24px;
        border-top: 1px solid var(--border-light);
        margin-top: 64px;
    }
    .unseen-footer p {
        font-size: 12px; color: var(--text-muted);
        letter-spacing: 0.06em;
    }
    .unseen-google-btn {
        width: 100%; border: 1.5px solid var(--border-light); border-radius: var(--radius-pill); 
        padding: 10px 24px; text-align: center; cursor: pointer; font-family: var(--font-sans); 
        font-size: 14px; font-weight: 500; transition: var(--transition); background: transparent;
        color: var(--text-primary);
    }
    .unseen-google-btn:hover {
        border-color: var(--text-primary);
        background: rgba(0,0,0,0.02);
    }

    .unseen-showcase-wrap {
        margin-top: 28px;
        padding: 26px;
        border-radius: 22px;
        border: 1px solid var(--border-light);
        background: linear-gradient(160deg, rgba(255,255,255,0.62) 0%, rgba(239,230,221,0.8) 100%);
        backdrop-filter: blur(16px);
    }

    .unseen-capability-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 16px;
    }

    .unseen-capability-chip {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 7px 12px;
        border-radius: 999px;
        border: 1px solid rgba(26, 26, 26, 0.14);
        background: rgba(255, 255, 255, 0.72);
        color: var(--text-primary);
    }

    .unseen-role-card {
        margin-bottom: 14px;
        border-radius: 18px;
        border: 1px solid var(--border-light);
        background: rgba(255, 255, 255, 0.58);
        box-shadow: 0 8px 30px rgba(0,0,0,0.04);
        padding: 20px;
    }

    .unseen-role-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 12px;
    }

    .unseen-role-title {
        font-size: 22px;
        font-family: var(--font-serif);
        margin: 0;
        color: var(--text-primary);
    }

    .unseen-role-tag {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 5px 10px;
        border-radius: 999px;
        border: 1px solid rgba(196, 168, 130, 0.35);
        color: #735638;
        background: rgba(196, 168, 130, 0.12);
    }

    .unseen-role-abstract {
        margin: 0 0 10px 0;
        font-size: 13px;
        color: var(--text-muted);
        line-height: 1.5;
    }

    .unseen-role-list {
        margin: 0;
        padding-left: 18px;
        color: var(--text-secondary);
        line-height: 1.65;
        font-size: 14px;
    }

    .unseen-test-card {
        margin-top: 14px;
        border: 1px solid var(--border-light);
        border-radius: 16px;
        padding: 18px;
        background: rgba(255, 255, 255, 0.62);
    }
    .unseen-test-title {
        margin: 0;
        font-family: var(--font-serif);
        font-size: 24px;
        color: var(--text-primary);
    }
    .unseen-test-desc {
        margin: 8px 0 0 0;
        font-size: 14px;
        color: var(--text-secondary);
        line-height: 1.6;
    }
    .unseen-selected-box {
        margin-top: 8px;
        border: 1px solid rgba(26, 26, 26, 0.14);
        border-radius: 14px;
        padding: 12px 14px;
        background: rgba(255, 255, 255, 0.75);
    }
    .unseen-selected-label {
        margin: 0;
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-muted);
    }
    .unseen-selected-file {
        margin: 4px 0 0 0;
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
    }
    .unseen-selected-meta {
        margin: 4px 0 0 0;
        font-size: 13px;
        color: var(--text-secondary);
    }
    .unseen-selected-path {
        margin: 6px 0 0 0;
        font-size: 12px;
        color: var(--text-muted);
    }
    .unseen-pipeline-box {
        margin-top: 8px;
        border: 1px solid var(--border-light);
        border-radius: 14px;
        padding: 12px 14px;
        background: rgba(239, 230, 221, 0.66);
    }
    .unseen-pipeline-title {
        margin: 0;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-muted);
    }
    .unseen-pipeline-list {
        margin: 8px 0 0 0;
        padding-left: 18px;
        font-size: 13px;
        color: var(--text-secondary);
        line-height: 1.6;
    }
    .unseen-submit-note {
        margin-top: 8px;
        font-size: 12px;
        color: var(--text-muted);
    }
    .unseen-exec-report {
        margin-top: 10px;
        border: 1px solid var(--border-light);
        border-radius: 14px;
        padding: 14px;
        background: rgba(255, 255, 255, 0.78);
    }
    .unseen-exec-title {
        margin: 0;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-muted);
    }
    .unseen-exec-meta {
        margin: 8px 0 0 0;
        font-size: 13px;
        color: var(--text-secondary);
        line-height: 1.6;
    }
    .unseen-exec-list {
        margin: 10px 0 0 0;
        padding-left: 18px;
        font-size: 13px;
        color: var(--text-secondary);
        line-height: 1.6;
    }

    @media (max-width: 768px) {
        .unseen-stat-grid { grid-template-columns: repeat(2, 1fr); }
        .unseen-hero h1 { font-size: 40px !important; }
        .unseen-showcase-wrap { padding: 18px; }
        .unseen-role-head { flex-direction: column; align-items: flex-start; }
    }
</style>
"""

def render_global_css_2() -> None:
    st.html(UNSEEN_CSS_2)


def _build_test_execution_report(section: dict[str, Any], selected: dict[str, str], result: dict[str, Any]) -> str:
    selected_path = Path(selected["path"])
    exists = selected_path.exists()
    if exists and selected_path.is_file():
        size_kb = max(1, int(selected_path.stat().st_size / 1024))
        file_status = f"Available ({size_kb} KB)"
    else:
        file_status = "Not found in workspace"

    steps_html = "".join(f"<li>{step}</li>" for step in result.get("steps", section["pipeline"]))
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    status_line = result.get("status", "not-run")
    summary_line = result.get("summary", "No execution summary available.")
    return f"""
    <div class="unseen-exec-report">
        <p class="unseen-exec-title">Submission Report</p>
        <p class="unseen-exec-meta"><strong>Time:</strong> {timestamp}<br>
        <strong>Status:</strong> {status_line}<br>
        <strong>Feature:</strong> {section['title']}<br>
        <strong>Selected File:</strong> {selected['label']} ({selected['path']})<br>
        <strong>File Check:</strong> {file_status}<br>
        <strong>Summary:</strong> {summary_line}</p>
        <ol class="unseen-exec-list">{steps_html}</ol>
    </div>
    """


def _ensure_teacher(auth: dict[str, Any]) -> None:
    if auth.get("role") != "teacher":
        raise ApiError("This automated test flow requires a teacher account.")


def _read_test_file(path_str: str) -> tuple[bytes, str]:
    path = Path(path_str)
    if not path.exists() or not path.is_file():
        raise ApiError(f"Test file not found: {path_str}")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return path.read_bytes(), mime


def _create_test_student(token: str) -> dict[str, Any]:
    suffix = str(int(time.time() * 1000))[-6:]
    return api_request(
        "POST",
        "/students",
        token=token,
        json={
            "full_name": f"UI Test Student {suffix}",
            "class_id": f"ui-test-class-{suffix}",
            "parent_id": "parent-001",
            "parent_name": "UI Test Parent",
            "parent_language": "en",
        },
    )


def _run_feature_test(section_key: str, selected: dict[str, str], auth: dict[str, Any]) -> dict[str, Any]:
    token = auth.get("token")
    if not token:
        raise ApiError("Missing auth token. Sign in again.")

    if section_key in {"test_audio", "test_video", "test_reports", "test_class_intel", "test_search", "test_ocr_notes"}:
        _ensure_teacher(auth)

    if section_key == "test_ocr_notes":
        file_bytes, mime = _read_test_file(selected["path"])
        files = {"file": (Path(selected["path"]).name, file_bytes, mime)}
        data = {"owner_type": "teacher", "owner_id": auth["user_id"], "embed_metadata": "true"}
        note = api_request("POST", "/notes/analyze-upload", token=token, files=files, data=data)
        return {
            "status": "success",
            "summary": f"Note indexed as category '{note.get('category', 'unknown')}'.",
            "steps": [
                "Uploaded selected file to /notes/analyze-upload.",
                "Content extraction and metadata classification completed.",
                "Index entry created for later search/retrieval.",
            ],
        }

    if section_key == "test_audio":
        student = _create_test_student(token)
        file_bytes, mime = _read_test_file(selected["path"])
        obs = api_request(
            "POST",
            "/observations/process",
            token=token,
            json={
                "student_id": student["_id"],
                "audio_base64": base64.b64encode(file_bytes).decode("utf-8"),
                "audio_mime_type": mime,
            },
        )
        return {
            "status": "success",
            "summary": f"Audio processed; domain={obs.get('domain', 'unknown')}.",
            "steps": [
                "Created a test student for isolated processing.",
                "Uploaded selected audio to /observations/process.",
                "Transcription, masking, correction, and classification completed.",
            ],
        }

    if section_key == "test_video":
        student = _create_test_student(token)
        file_bytes, mime = _read_test_file(selected["path"])
        video = api_request(
            "POST",
            "/observations/video-process",
            token=token,
            json={
                "student_id": student["_id"],
                "video_base64": base64.b64encode(file_bytes).decode("utf-8"),
                "video_mime_type": mime,
                "teacher_note": "UI-triggered video test run",
            },
        )
        timeline = len(video.get("behavior_timeline") or [])
        return {
            "status": "success",
            "summary": f"Video processed; timeline events={timeline}.",
            "steps": [
                "Created a test student for video flow.",
                "Submitted selected clip to /observations/video-process.",
                "Timeline extraction and insight synthesis completed.",
            ],
        }

    if section_key == "test_reports":
        student = _create_test_student(token)
        api_request(
            "POST",
            "/observations/process",
            token=token,
            json={"student_id": student["_id"], "text": "Student collaborated and communicated clearly."},
        )
        report = api_request("POST", f"/reports/generate/{student['_id']}", token=token, json={"period": "weekly"})
        return {
            "status": "success",
            "summary": f"Report generated: {report.get('_id', 'created')}",
            "steps": [
                "Created test student and seed observation.",
                "Triggered /reports/generate/{student_id}.",
                "Teacher and parent summary artifacts were generated.",
            ],
        }

    if section_key == "test_class_intel":
        student = _create_test_student(token)
        class_id = student.get("class_id")
        api_request(
            "POST",
            "/observations/process",
            token=token,
            json={"student_id": student["_id"], "text": "Student showed progress in social-emotional interaction."},
        )
        class_report = api_request("POST", f"/reports/class/generate/{class_id}", token=token, json={"period": "weekly"})
        view = api_request(
            "POST",
            f"/reports/class/{class_id}/view",
            token=token,
            json={"role": "teacher", "period": "weekly"},
        )
        student_count = (view.get("class_overview") or {}).get("student_count", "n/a")
        return {
            "status": "success",
            "summary": f"Class report generated: {class_report.get('_id', 'created')} with student_count={student_count}.",
            "steps": [
                "Created class-scoped test student and seed observation.",
                "Generated class intelligence report.",
                "Validated role-based teacher view retrieval.",
            ],
        }

    if section_key == "test_search":
        file_bytes, mime = _read_test_file(selected["path"])
        files = {"file": (Path(selected["path"]).name, file_bytes, mime)}
        data = {"owner_type": "teacher", "owner_id": auth["user_id"], "embed_metadata": "true"}
        indexed = api_request("POST", "/notes/analyze-upload", token=token, files=files, data=data)
        query = (indexed.get("keywords") or [Path(selected["path"]).stem.split("_")[0]])[0]
        results = api_request("GET", f"/notes/search?q={query}&owner_type=teacher&owner_id={auth['user_id']}", token=token)
        count = len(results) if isinstance(results, list) else 0
        return {
            "status": "success",
            "summary": f"Search query '{query}' returned {count} result(s).",
            "steps": [
                "Indexed selected note/document asset.",
                "Executed keyword search on /notes/search.",
                "Verified retrieval from indexed metadata/content.",
            ],
        }

    return {"status": "skipped", "summary": "No runnable test mapped for this section.", "steps": ["Section mapping missing."]}


def render_feature_showcase(auth: dict[str, Any]) -> None:
    st.html('<h2 class="unseen-section-title">Role Feature Abstraction</h2>')
    st.html('<p class="unseen-section-sub">All implemented capabilities, revealed in role order: Teacher, Student, Parent.</p>')

    st.html("""
    <div class="unseen-showcase-wrap">
        <div class="unseen-capability-row">
            <span class="unseen-capability-chip">Multimodal Input</span>
            <span class="unseen-capability-chip">OCR + Metadata Indexing</span>
            <span class="unseen-capability-chip">Class Intelligence</span>
            <span class="unseen-capability-chip">Role-Based Reports</span>
            <span class="unseen-capability-chip">Parent Translation</span>
            <span class="unseen-capability-chip">Privacy-Aware AI</span>
        </div>
    </div>
    """)

    role_specs = [
        (
            "Teacher",
            "Full instructional control over student records, multimodal observations, and report generation workflows.",
            [
                "Student management with class assignment and multilingual parent preferences.",
                "Multimodal observations: text, audio transcription, and video behavior timeline extraction.",
                "Insights and trend analysis across developmental domains.",
                "Individual reports, batch report cycles, and class-intelligence synthesis.",
                "Role-based class report abstraction (teacher, student, parent views).",
                "Notes and document indexing with OCR/metadata extraction and semantic search.",
            ],
        ),
        (
            "Student",
            "Learner-focused view with scoped access to growth summaries and age-appropriate report visibility.",
            [
                "Personal report access experience for student-linked accounts.",
                "Development-area summaries and progress-oriented guidance.",
                "Role-filtered class insights scoped to learner context.",
            ],
        ),
        (
            "Parent",
            "Caregiver abstraction layer with privacy boundaries and actionable home guidance.",
            [
                "Parent-specific report access with approved summaries.",
                "Home activity suggestions aligned with classroom observations.",
                "Abstraction layer that limits visibility to the parent's children only.",
            ],
        ),
    ]

    for role_name, abstract_line, features in role_specs:
        items = "".join(f"<li>{f}</li>" for f in features)
        st.html(
            f"""
            <div class="unseen-role-card">
                <div class="unseen-role-head">
                    <p class="unseen-role-title">{role_name}</p>
                    <span class="unseen-role-tag">Role Abstraction</span>
                </div>
                <p class="unseen-role-abstract">{abstract_line}</p>
                <ul class="unseen-role-list">
                    {items}
                </ul>
            </div>
            """
        )

    st.html('<h2 class="unseen-section-title" style="margin-top: 40px;">Feature Test File Dropdowns</h2>')
    st.html('<p class="unseen-section-sub">Each feature has a dedicated test asset dropdown, selected-state preview, and full pipeline steps.</p>')

    test_sections = [
        {
            "key": "test_ocr_notes",
            "title": "1) Notes + OCR + Metadata",
            "description": "Use these assets to validate OCR extraction, metadata classification, and indexed note search.",
            "options": [
                {"label": "OCR Image Probe", "path": "scripts/ocr_probe.png", "desc": "Image file used for OCR text extraction tests."},
                {"label": "Metadata DOCX Probe", "path": "scripts/metadata_probe.docx", "desc": "Document for metadata and keyword indexing."},
                {"label": "Metadata TXT Probe", "path": "scripts/metadata_probe.txt", "desc": "Plain text metadata classification sample."},
                {"label": "Sample Note", "path": "sample_note.txt", "desc": "Simple note text for upload and retrieval checks."},
            ],
            "pipeline": [
                "Pick a file from the dropdown and confirm the selected asset card updates.",
                "Upload via Notes tab Analyze & Index endpoint.",
                "Text extraction runs (OCR for images, parser for doc/text).",
                "AI classification adds category, summary, and keyword metadata.",
                "Embedding and metadata are stored in notes index.",
                "Search endpoint retrieves the file by keywords or semantic match.",
            ],
        },
        {
            "key": "test_audio",
            "title": "2) Audio Observation Pipeline",
            "description": "Validate speech transcription and downstream classroom classification from audio evidence.",
            "options": [
                {"label": "TTS Probe WAV", "path": "scripts/tts_probe.wav", "desc": "Generated WAV used for transcription validation."},
                {"label": "Sample Audio WAV", "path": "sample_audio.wav", "desc": "Additional sample for observation processing."},
            ],
            "pipeline": [
                "Select an audio file and verify selected card reflects the file.",
                "Upload in Observation form as audio note.",
                "Whisper transcription converts audio to text.",
                "PII masking and correction run against roster context.",
                "Reasoning service classifies developmental domain and tags.",
                "Observation is saved and appears in insights/report flows.",
            ],
        },
        {
            "key": "test_video",
            "title": "3) Video Observation Pipeline",
            "description": "Validate behavior timeline extraction and video insight enrichment.",
            "options": [
                {"label": "Real MP4 Probe", "path": "scripts/real_probe.mp4", "desc": "MP4 clip used for timeline and event extraction."},
            ],
            "pipeline": [
                "Select the test clip and verify selected state card.",
                "Upload in Observation form as video clip.",
                "Video service derives behavior timeline and event signals.",
                "Optional AI refinement improves behavioral interpretation.",
                "Output stores modality, timeline, and insight metadata.",
                "Results feed reports and class-level intelligence.",
            ],
        },
        {
            "key": "test_reports",
            "title": "4) Student + Parent Report Pipeline",
            "description": "Use prepared text assets as context references while validating report generation and translations.",
            "options": [
                {"label": "Sample Note Context", "path": "sample_note.txt", "desc": "Reference context for report content checks."},
                {"label": "Metadata TXT Context", "path": "scripts/metadata_probe.txt", "desc": "Additional context for summary and trend checks."},
            ],
            "pipeline": [
                "Choose a context file and confirm it appears as selected.",
                "Generate individual report from Reports tab.",
                "Parent summary and optional translation are produced.",
                "Teacher approval controls parent visibility.",
                "Parent or student role reads scoped report output.",
            ],
        },
        {
            "key": "test_class_intel",
            "title": "5) Class Intelligence + Role Views",
            "description": "Use these seed files as optional references while validating class-level aggregation and role abstraction.",
            "options": [
                {"label": "Metadata DOCX Reference", "path": "scripts/metadata_probe.docx", "desc": "Reference file for class synthesis scenarios."},
                {"label": "Metadata TXT Reference", "path": "scripts/metadata_probe.txt", "desc": "Reference text for class role-view verification."},
            ],
            "pipeline": [
                "Select a reference file and validate selected-state panel.",
                "Run class report generation for target class and period.",
                "Service aggregates student observations and trends.",
                "Role view endpoint abstracts output for teacher, student, and parent.",
                "Parent scope only exposes linked children in summaries.",
            ],
        },
        {
            "key": "test_search",
            "title": "6) Notes Search + Retrieval Pipeline",
            "description": "Validate keyword and semantic retrieval behavior using indexed test assets.",
            "options": [
                {"label": "Metadata TXT Probe", "path": "scripts/metadata_probe.txt", "desc": "Primary keyword retrieval test file."},
                {"label": "Metadata DOCX Probe", "path": "scripts/metadata_probe.docx", "desc": "DOCX retrieval and metadata query test."},
                {"label": "Sample Note", "path": "sample_note.txt", "desc": "Simple retrieval baseline sample."},
            ],
            "pipeline": [
                "Pick one indexed file and verify the selected display updates.",
                "Run Notes search using keywords in file metadata/content.",
                "System applies owner filters and query matching.",
                "Results return ranked note cards with summary and keywords.",
                "Open specific note endpoint for full detail verification.",
            ],
        },
    ]

    section_map = {s["key"]: s for s in test_sections}
    pending_job = st.session_state.pop("pending_test_job", None)
    if pending_job:
        job_key = pending_job.get("section_key")
        selected_label = pending_job.get("selected_label")
        section = section_map.get(job_key)
        if section:
            labels = [f"{opt['label']}  ({opt['path']})" for opt in section["options"]]
            idx = labels.index(selected_label) if selected_label in labels else 0
            selected = section["options"][idx]
            with st.spinner("Processing selected test file..."):
                try:
                    execution = _run_feature_test(section["key"], selected, auth)
                    st.session_state[f"{section['key']}_report_html"] = _build_test_execution_report(section, selected, execution)
                    st.session_state[f"{section['key']}_run_status"] = ("success", "Processed successfully. See report below.")
                except Exception as exc:
                    failed = {
                        "status": "failed",
                        "summary": str(exc),
                        "steps": [
                            "Submission received via Enter button.",
                            "Pipeline attempted to execute backend test flow.",
                            "Execution failed before completion; see summary for error detail.",
                        ],
                    }
                    st.session_state[f"{section['key']}_report_html"] = _build_test_execution_report(section, selected, failed)
                    st.session_state[f"{section['key']}_run_status"] = ("error", f"Processing failed: {exc}")

    for section in test_sections:
        st.html(
            f"""
            <div class="unseen-test-card">
                <p class="unseen-test-title">{section['title']}</p>
                <p class="unseen-test-desc">{section['description']}</p>
            </div>
            """
        )

        labels = [f"{opt['label']}  ({opt['path']})" for opt in section["options"]]
        active_key = f"{section['key']}_active_label"
        pending_key = f"{section['key']}_pending_label"
        if active_key not in st.session_state:
            st.session_state[active_key] = labels[0]
        if pending_key not in st.session_state:
            st.session_state[pending_key] = st.session_state[active_key]

        st.selectbox("Select test file", labels, key=pending_key)
        current_pending = st.session_state.get(pending_key, labels[0])
        st.caption(f"Current selection: {current_pending}")
        submit = st.button("Enter", key=f"{section['key']}_enter_button", use_container_width=True, type="primary")

        st.html('<p class="unseen-submit-note">Selection updates immediately. Press Enter only to run processing.</p>')

        if submit:
            st.session_state[active_key] = current_pending
            st.session_state["pending_test_job"] = {
                "section_key": section["key"],
                "selected_label": current_pending,
            }
            st.rerun()

        effective_label = st.session_state.get(active_key, labels[0])
        effective_idx = labels.index(effective_label) if effective_label in labels else 0
        selected = section["options"][effective_idx]

        run_status = st.session_state.pop(f"{section['key']}_run_status", None)
        if run_status:
            level, message = run_status
            if level == "success":
                st.success(message)
            else:
                st.error(message)

        st.html(
            f"""
            <div class="unseen-selected-box">
                <p class="unseen-selected-label">Selected Test File</p>
                <p class="unseen-selected-file">{selected['label']}</p>
                <p class="unseen-selected-meta">{selected['desc']}</p>
                <p class="unseen-selected-path">Path: {selected['path']}</p>
            </div>
            """
        )

        pipeline_html = "".join(f"<li>{step}</li>" for step in section["pipeline"])
        st.html(
            f"""
            <div class="unseen-pipeline-box">
                <p class="unseen-pipeline-title">How It Works Pipeline</p>
                <ol class="unseen-pipeline-list">
                    {pipeline_html}
                </ol>
            </div>
            """
        )

        report_html = st.session_state.get(f"{section['key']}_report_html")
        if report_html:
            st.html(report_html)

def landing_page() -> None:
    st.html("""
    <div class="unseen-nav">
        <span class="unseen-nav-brand">aura &mdash; ece</span>
        <div class="unseen-nav-links">
            <span>Platform</span>
            <span>Features</span>
            <span>For Educators</span>
        </div>
    </div>
    """)

    hero_bg = get_landing_bg_src()
    st.html(f"""
    <div class="unseen-hero" style="background-color: #efe6dd; min-height: 130vh; padding: 0;">
        <div style="
            position: absolute; top: 0; left: 0; right: 0; bottom: 0;
            background-image: url('{hero_bg}');
            background-size: cover; background-repeat: no-repeat; background-position: center; z-index: 1; opacity: 0.85;
        "></div>
        <div class="unseen-blob unseen-blob-1" style="z-index: 2;"></div>
        <div class="unseen-blob unseen-blob-2" style="z-index: 2;"></div>
        <div style="
            position: absolute; top: 0; left: 0; right: 0; bottom: -100px;
            background-image: linear-gradient(180deg, rgba(239,230,221,0) 0%, rgba(239,230,221,0) 40%, rgba(239,230,221,0.6) 70%, rgba(239,230,221,1) 90%, rgba(239,230,221,1) 100%);
            z-index: 3;
        "></div>
        <div style="position: relative; z-index: 10; display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; padding: 12vh 24px 80px 24px; box-sizing: border-box;">
            <div class="unseen-hero-label">AN AI-POWERED EDUCATION PLATFORM</div>
            <h1><em>Observe.</em> Understand.<br>Grow.</h1>
            <p class="unseen-hero-sub">Transform classroom observations into structured developmental insights. Privacy-aware AI that keeps families engaged with personalized, multilingual reports.</p>
            <div style="display: flex; gap: 12px; flex-wrap: wrap; justify-content: center;">
                <span class="unseen-pill-btn unseen-pill-solid">Explore the platform &rarr;</span>
                <span class="unseen-pill-btn unseen-pill-outline">How it works</span>
            </div>
        </div>
    </div>
    """)

    st.html("""
    <div class="unseen-stat-grid">
        <div class="unseen-stat"><p class="unseen-stat-value">15K+</p><p class="unseen-stat-label">Educators</p></div>
        <div class="unseen-stat"><p class="unseen-stat-value">250K</p><p class="unseen-stat-label">Students</p></div>
        <div class="unseen-stat"><p class="unseen-stat-value">1.2M</p><p class="unseen-stat-label">Observations</p></div>
        <div class="unseen-stat"><p class="unseen-stat-value">4.8</p><p class="unseen-stat-label">Rating</p></div>
    </div>
    """)

    st.html('<h2 class="unseen-section-title">Everything you need</h2>')
    st.html('<p class="unseen-section-sub">Tools designed for the way educators actually work.</p>')

    features = [
        ("&#9670;", "Multimodal Capture", "Capture teacher observations from text, audio, and video with unified AI processing."),
        ("&#9651;", "Audio Intelligence", "Whisper-powered transcription with correction and domain-aware classification."),
        ("&#9642;", "Video Insights", "Behavior timeline extraction from classroom clips with optional AI refinement."),
        ("&#10070;", "Student + Parent Reports", "Generate individual, translated, and activity-ready reports for family communication."),
        ("&#9632;", "Class Intelligence", "Build class-level weekly/monthly summaries with role-based abstraction views."),
        ("&#9906;", "Notes OCR + Search", "Upload docs/images/audio/video, index metadata, and retrieve insights with semantic search."),
        ("&#9633;", "Role Access Control", "Teacher, student, and parent scopes enforced across report and class visibility."),
        ("&#9675;", "Trend Tracking", "Track domain progression outcomes and generate actionable developmental insights."),
        ("&#10022;", "Automation Ready", "Run batch report cycles and scheduler-based operations for recurring workflows."),
    ]

    cols = st.columns(3)
    for i, (icon, title, desc) in enumerate(features):
        with cols[i % 3]:
            st.html(f"""
            <div class="unseen-card">
                <div class="unseen-card-icon">{icon}</div>
                <div class="unseen-card-title">{title}</div>
                <div class="unseen-card-desc">{desc}</div>
            </div>
            """)

    st.html('<h2 class="unseen-section-title">Ready to get started?</h2>')
    auth = st.session_state.get("auth")
    if auth:
        render_feature_showcase(auth)
        nav_c1, nav_c2 = st.columns(2)
        with nav_c1:
            if st.button("Open Workspace", use_container_width=True):
                st.session_state["page"] = "workspace"
                st.rerun()
        with nav_c2:
            if st.button("Sign out", use_container_width=True):
                logout()
    else:
        if st.button("Go to Sign In", use_container_width=True, type="primary"):
            st.session_state["page"] = "login"
            st.rerun()

    st.html("""
    <div class="unseen-footer">
        <p>AURA-ECE &middot; An AI-powered education platform &middot; &copy;2026</p>
    </div>
    """)

def login_page() -> None:
    st.html("""
    <div class="unseen-nav">
        <span class="unseen-nav-brand">aura &mdash; ece</span>
    </div>
    <div class="page-spacer"></div>
    """)

    st.html('<h2 class="unseen-section-title" style="margin-top:24px;"><em>Sign in</em> to your workspace</h2>')
    st.html('<p class="unseen-section-sub">Start here with Google popup sign-in, then continue to your landing page.</p>')

    role_col1, role_col2, role_col3 = st.columns(3)
    with role_col1:
        if st.button("I'm a Teacher", use_container_width=True, key="role_teacher"):
            st.session_state["selected_role"] = "teacher"
    with role_col2:
        if st.button("I'm a Student", use_container_width=True, key="role_student"):
            st.session_state["selected_role"] = "student"
    with role_col3:
        if st.button("I'm a Parent", use_container_width=True, key="role_parent"):
            st.session_state["selected_role"] = "parent"

    selected_role = st.session_state.get("selected_role", "teacher")
    role_label = selected_role.title()

    with st.form("login_form", clear_on_submit=False):
        st.html(f'<div class="unseen-form-label">Signing in as {role_label}</div>')
        user_id = st.text_input("User ID / Email", placeholder="Enter your user ID or email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")

    if submit:
        try:
            data = api_request("POST", "/auth/login", json={"user_id": user_id, "password": password})
            st.session_state["auth"] = {
                "token": data["access_token"],
                "role": data["role"],
                "user_id": data["user_id"],
                "student_id": data.get("student_id"),
                "parent_id": data.get("parent_id"),
            }
            st.session_state["page"] = "landing"
            st.rerun()
        except Exception as exc:
            st.error(f"Sign in failed: {exc}")

    google_redirect_url = get_google_popup_redirect_url(selected_role)
    render_google_popup_button(google_redirect_url)

    st.html("""
    <div class="unseen-footer">
        <p>AURA-ECE &middot; An AI-powered early childhood education platform &middot; &copy;2026</p>
    </div>
    """)

def teacher_dashboard(auth: dict[str, Any]) -> None:
    st.html(f"""
    <div class="unseen-nav">
        <span class="unseen-nav-brand">aura &mdash; ece</span>
        <div class="unseen-nav-links">
            <span style="color: var(--text-muted); font-size: 12px;">Signed in as {auth['user_id']}</span>
        </div>
    </div>
    <div class="page-spacer"></div>
    """)

    token = auth["token"]

    st.html(f"""
    <div class="unseen-dashboard-header">
        <p class="unseen-dashboard-title"><em>Teacher</em> Workspace</p>
        <p class="unseen-dashboard-sub">Manage students, record observations, and generate developmental insights.</p>
    </div>
    """)

    col_space, col_logout = st.columns([8, 1])
    with col_logout:
        if st.button("Sign out", key="logout_teacher", use_container_width=True):
            logout()

    tab_students, tab_observations, tab_insights, tab_reports, tab_notes = st.tabs([
        "Students", "Observations", "Insights", "Reports", "Notes"
    ])

    with tab_students:
        st.html('<h3 class="unseen-section-title" style="font-size: 28px; margin-top: 24px;">Manage Students</h3>')
        st.html('<div class="unseen-form-label">Add a new student</div>')

        with st.form("add_student"):
            c1, c2 = st.columns(2)
            with c1:
                full_name = st.text_input("Student Name", placeholder="Full name")
            with c2:
                class_id = st.text_input("Class ID", value="class-a")
            c3, c4 = st.columns(2)
            with c3:
                student_id = st.text_input("Student ID", value="student-001")
            with c4:
                parent_name = st.text_input("Student Name", placeholder="Contact name")
            c5, c6 = st.columns(2)
            with c5:
                parent_language = st.selectbox("Language", ["en", "es", "fr", "de", "zh", "ja"])
            with c6:
                submitted = st.form_submit_button("Add Student", use_container_width=True, type="primary")

        if submitted:
            try:
                created = api_request("POST", "/students", token=token, json={"full_name": full_name, "class_id": class_id, "student_id": student_id, "parent_name": parent_name, "parent_language": parent_language})
                st.success(f"Student '{created['full_name']}' added.")
            except Exception as exc:
                st.error(f"Error: {exc}")

        st.html('<div class="unseen-form-label" style="margin-top: 32px;">Active students</div>')
        try:
            students_data = api_request("GET", "/students", token=token)
            if students_data:
                for s in students_data:
                    st.html(f"""
                    <div class="unseen-student-card">
                        <div class="unseen-avatar">{s['full_name'][0].upper()}</div>
                        <div>
                            <p class="unseen-student-name">{s['full_name']}</p>
                            <p class="unseen-student-meta">Class: {s.get('class_id', '—')} &middot; Student: {s.get('parent_name', '—')} &middot; {s['_id'][:8]}&hellip;</p>
                        </div>
                    </div>""")
            else:
                st.info("No students yet. Add one above to get started.")
        except Exception as exc:
            st.error(f"Error loading students: {exc}")

    with tab_observations:
        st.html('<h3 class="unseen-section-title" style="font-size: 28px; margin-top: 24px;"><em>Record</em> Observation</h3>')
        st.html('<p class="unseen-section-sub">Capture observations with text, audio, or video. AI classifies and indexes everything.</p>')

        try:
            students_data = api_request("GET", "/students", token=token)
            student_map = {f"{s['full_name']} ({s['_id'][:8]}…)": s["_id"] for s in students_data}
        except Exception:
            student_map = {}

        if not student_map:
            st.warning("No students available. Add students first.")
        else:
            with st.form("observation_form"):
                choice = st.selectbox("Select Student", list(student_map.keys()))
                text = st.text_area("What did you observe?", placeholder="Describe the observation in detail…", height=100)
                audio = st.file_uploader("Audio note (optional)", type=["wav", "mp3", "m4a"])
                video = st.file_uploader("Video clip (optional)", type=["mp4", "mov", "avi", "mkv", "webm", "m4v"])
                process_btn = st.form_submit_button("Process Observation", use_container_width=True, type="primary")

                if process_btn:
                    if not text and not audio and not video:
                        st.error("Please provide text, audio, or video.")
                    else:
                        try:
                            with st.spinner("Processing…"):
                                if video is not None:
                                    payload = {"student_id": student_map[choice], "video_base64": base64.b64encode(video.read()).decode("utf-8"), "video_mime_type": video.type or "video/mp4", "teacher_note": text or None}
                                    result = api_request("POST", "/observations/video-process", token=token, json=payload)
                                else:
                                    payload = {"student_id": student_map[choice], "text": text or None, "audio_base64": None, "audio_mime_type": "audio/wav"}
                                    if audio is not None:
                                        payload["audio_base64"] = base64.b64encode(audio.read()).decode("utf-8")
                                        payload["audio_mime_type"] = audio.type or "audio/wav"
                                    result = api_request("POST", "/observations/process", token=token, json=payload)
                                st.success("Observation processed.")
                                st.json(result)
                        except Exception as exc:
                            st.error(f"Error: {exc}")

    with tab_insights:
        st.html('<h3 class="unseen-section-title" style="font-size: 28px; margin-top: 24px;"><em>Development</em> Insights</h3>')
        try:
            students_data = api_request("GET", "/students", token=token)
            student_map = {f"{s['full_name']} ({s['_id'][:8]}…)": s["_id"] for s in students_data}
        except Exception:
            student_map = {}

        if not student_map:
            st.warning("No students available.")
        else:
            ins_choice = st.selectbox("Select Student", list(student_map.keys()), key="insights_student")
            if st.button("Load Insights", type="primary", use_container_width=True):
                try:
                    with st.spinner("Analyzing…"):
                        data = api_request("GET", f"/students/{student_map[ins_choice]}/insights", token=token)
                        st.json(data)
                except Exception as exc:
                    st.error(f"Error: {exc}")

    with tab_reports:
        st.html('<h3 class="unseen-section-title" style="font-size: 28px; margin-top: 24px;"><em>Generate</em> Reports</h3>')

        try:
            students_data = api_request("GET", "/students", token=token)
            student_map = {f"{s['full_name']} ({s['_id'][:8]}…)": s["_id"] for s in students_data}
        except Exception:
            student_map = {}

        c1, c2 = st.columns(2)
        with c1:
            period = st.selectbox("Period", ["weekly", "monthly"])
        with c2:
            max_obs = st.number_input("Max observations", min_value=5, max_value=50, value=15)

        c3, c4, c5 = st.columns(3)
        with c3:
            inc_trends = st.checkbox("Trends", value=True)
        with c4:
            inc_act = st.checkbox("Activities", value=True)
        with c5:
            inc_trans = st.checkbox("Translate", value=True)

        report_payload = {"period": period, "include_trends": inc_trends, "include_activity_suggestions": inc_act, "include_parent_translation": inc_trans, "max_observations": int(max_obs)}

        st.html('<div class="unseen-form-label" style="margin-top: 24px;">Individual report</div>')
        if student_map:
            rep_choice = st.selectbox("Student", list(student_map.keys()), key="report_student")
            if st.button("Generate Report", type="primary", use_container_width=True, key="gen_report"):
                try:
                    with st.spinner("Generating…"):
                        report = api_request("POST", f"/reports/generate/{student_map[rep_choice]}", token=token, json=report_payload)
                        st.success("Report generated.")
                        st.json(report)
                except Exception as exc:
                    st.error(f"Error: {exc}")

        st.html('<div class="unseen-form-label" style="margin-top: 24px;">Batch cycle</div>')
        if st.button("Run Report Cycle", use_container_width=True, key="cycle_btn"):
            try:
                with st.spinner("Running cycle…"):
                    cycle = api_request("POST", "/reports/run-cycle", token=token, json=report_payload)
                    st.success("Cycle complete.")
                    st.json(cycle)
            except Exception as exc:
                st.error(f"Error: {exc}")

        st.html('<div class="unseen-form-label" style="margin-top: 24px;">Class intelligence</div>')
        class_id = st.text_input("Class ID", value="class-a", key="class_report_class_id")
        c_gen, c_view = st.columns(2)
        with c_gen:
            if st.button("Generate Class Report", use_container_width=True, type="primary", key="gen_class_report"):
                try:
                    with st.spinner("Generating…"):
                        cr = api_request("POST", f"/reports/class/generate/{class_id.strip()}", token=token, json={"period": period})
                        st.json(cr)
                except Exception as exc:
                    st.error(f"Error: {exc}")
        with c_view:
            if st.button("View Latest", use_container_width=True, key="view_class_report"):
                try:
                    cr = api_request("GET", f"/reports/class/{class_id.strip()}?period={period}", token=token)
                    st.json(cr)
                except Exception as exc:
                    st.error(f"Error: {exc}")

        r1, r2 = st.columns(2)
        with r1:
            role_view = st.selectbox("Role", ["teacher", "student"], key="class_role_view")
        with r2:
            role_sid = st.text_input("Student ID", placeholder="Required for student view", key="class_role_student")
        if st.button("Role-Based View", use_container_width=True, key="view_class_role"):
            try:
                view = api_request("POST", f"/reports/class/{class_id.strip()}/view", token=token, json={"role": role_view, "period": period, "student_id": role_sid.strip() or None})
                st.json(view)
            except Exception as exc:
                st.error(f"Error: {exc}")

        st.html('<div class="unseen-form-label" style="margin-top: 24px;">Approve report</div>')
        report_id = st.text_input("Report ID", placeholder="Paste report ID…")
        if st.button("Approve & Send", use_container_width=True, type="primary", key="approve_btn"):
            if report_id.strip():
                try:
                    approved = api_request("POST", f"/reports/{report_id.strip()}/approve", token=token, json={"approved": True})
                    st.success("Report approved.")
                    st.json(approved)
                except Exception as exc:
                    st.error(f"Error: {exc}")

    with tab_notes:
        st.html('<h3 class="unseen-section-title" style="font-size: 28px; margin-top: 24px;"><em>Notes</em> & Documents</h3>')
        st.html('<p class="unseen-section-sub">Upload files for AI classification and search through indexed notes.</p>')

        st.html('<div class="unseen-form-label">Upload & index</div>')
        n1, n2 = st.columns(2)
        with n1:
            owner_type = st.selectbox("Owner type", ["student", "teacher"], key="notes_owner_type")
        with n2:
            if owner_type == "teacher":
                owner_id = auth["user_id"]
                st.caption(f"Owner: {owner_id}")
            else:
                try:
                    sd = api_request("GET", "/students", token=token)
                    so = {f"{s['full_name']} ({s['_id'][:8]}…)": s["_id"] for s in sd}
                    owner_id = st.selectbox("Student", list(so.values()) if so else [], key="notes_student")
                except Exception:
                    owner_id = ""

        embed_meta = st.checkbox("Embed metadata", value=True)
        note_file = st.file_uploader("Upload file", type=["pdf","docx","txt","md","csv","log","png","jpg","jpeg","bmp","tiff","webp","wav","mp3","m4a","aac","ogg","flac","mp4","mov","avi","mkv","webm","m4v"])

        if st.button("Analyze & Index", use_container_width=True, type="primary", key="upload_btn"):
            if note_file and owner_id:
                try:
                    with st.spinner("Processing…"):
                        files = {"file": (note_file.name, note_file.read(), note_file.type or "application/octet-stream")}
                        fd = {"owner_type": owner_type, "owner_id": str(owner_id).strip(), "embed_metadata": str(embed_meta).lower()}
                        out = api_request("POST", "/notes/analyze-upload", token=token, files=files, data=fd)
                        st.success("Indexed.")
                        st.json(out)
                except Exception as exc:
                    st.error(f"Error: {exc}")

        st.html('<div class="unseen-form-label" style="margin-top: 32px;">Search notes</div>')
        sq = st.text_input("Search query", placeholder="e.g., 'behavior observations about sharing'", key="search_query")
        if st.button("Search", use_container_width=True, type="primary", key="search_btn"):
            if sq.strip():
                try:
                    params = f"?q={sq}&owner_type={owner_type}&owner_id={str(owner_id).strip()}"
                    notes = api_request("GET", f"/notes/search{params}", token=token)
                    st.json(notes)
                except Exception as exc:
                    st.error(f"Error: {exc}")

def student_dashboard(auth: dict[str, Any]) -> None:
    role_name = "Parent" if auth.get("role") == "parent" else "Student"
    st.html(f"""
    <div class="unseen-nav">
        <span class="unseen-nav-brand">aura &mdash; ece</span>
        <div class="unseen-nav-links">
            <span style="color: var(--text-muted); font-size: 12px;">{role_name} Portal</span>
        </div>
    </div>
    <div class="page-spacer"></div>
    """)

    st.html("""
    <div class="unseen-dashboard-header">
        <p class="unseen-dashboard-title"><em>Welcome</em> back</p>
        <p class="unseen-dashboard-sub">Stay informed about your child's growth and development journey.</p>
    </div>
    """)

    col_s, col_l = st.columns([8, 1])
    with col_l:
        if st.button("Sign out", key="logout_parent", use_container_width=True):
            logout()

    student_id = auth.get("student_id") or auth["user_id"]
    parent_id = auth.get("parent_id") or auth["user_id"]

    st.html('<h2 class="unseen-section-title"><em>Your child\'s</em> reports</h2>')
    st.html('<p class="unseen-section-sub">Personalized progress reports from the classroom.</p>')

    if st.button("Load My Reports", use_container_width=True, type="primary", key="load_reports"):
        try:
            with st.spinner("Loading…"):
                if auth.get("role") == "parent":
                    reports = api_request("GET", f"/parents/{parent_id}/reports", token=auth["token"])
                else:
                    reports = api_request("GET", f"/students/{student_id}/reports", token=auth["token"])
                if not reports:
                    st.info("No approved reports yet. Check back soon.")
                else:
                    for report in reports:
                        period_name = report.get('period', 'Report').title()
                        st.html(f"""
                        <div class="unseen-report-card">
                            <div class="unseen-report-header">
                                <p class="unseen-report-title">{period_name} Report</p>
                                <span class="unseen-badge">Approved</span>
                            </div>
                            <p style="font-size: 14px; line-height: 1.7; color: var(--text-secondary); margin: 0;">
                                {report.get('translated_parent_summary', 'No summary available')}
                            </p>
                        </div>
                        """)

                        activities = report.get("activity_suggestions") or []
                        if activities:
                            act_html = "".join(f"<li style='margin-bottom: 6px;'>{a}</li>" for a in activities)
                            st.html(f"""
                            <div class="unseen-activity-box">
                                <p style="font-weight: 600; font-size: 13px; color: var(--text-primary); margin: 0 0 10px 0; letter-spacing: 0.04em;">HOME ACTIVITIES</p>
                                <ul style="margin: 0; padding-left: 18px; font-size: 14px; color: var(--text-secondary); line-height: 1.7;">{act_html}</ul>
                            </div>
                            """)
        except Exception as exc:
            st.error(f"Error: {exc}")

    st.html('<h2 class="unseen-section-title"><em>Development</em> areas</h2>')
    st.html('<p class="unseen-section-sub">Core learning focus areas tracked for your child.</p>')

    areas = [
        ("&#10047;", "Academic", "Letter recognition, counting, early writing skills"),
        ("&#10023;", "Social", "Sharing, cooperation, making friends, listening"),
        ("&#9830;", "Creative", "Art, music, imaginative play, self-expression"),
    ]
    cols = st.columns(3)
    for i, (icon, title, desc) in enumerate(areas):
        with cols[i]:
            st.html(f"""
            <div class="unseen-card">
                <div class="unseen-card-icon">{icon}</div>
                <div class="unseen-card-title">{title}</div>
                <div class="unseen-card-desc">{desc}</div>
                <div class="unseen-chip" style="margin-top: 12px;">In Progress</div>
            </div>
            """)

    st.html('<h2 class="unseen-section-title"><em>Student</em> tips</h2>')
    st.html('<p class="unseen-section-sub">Simple ways to reinforce learning at home.</p>')

    tips = [
        ("&#10148;", "Talk About Their Day", "Ask open-ended questions about what they played, learned, and who they interacted with."),
        ("&#9827;", "Read Together", "Daily reading builds language skills and creates quality time. Let them choose the books."),
        ("&#10047;", "Learning Through Play", "Building, cooking, gardening, and imaginative games all build cognitive and motor skills."),
        ("&#10084;", "Celebrate Progress", "Praise effort over results. 'You worked really hard on that!' builds confidence and love of learning."),
    ]
    tc1, tc2 = st.columns(2)
    for i, (icon, title, desc) in enumerate(tips):
        with [tc1, tc2][i % 2]:
            st.html(f"""
            <div class="unseen-card">
                <div class="unseen-card-icon">{icon}</div>
                <div class="unseen-card-title">{title}</div>
                <div class="unseen-card-desc">{desc}</div>
            </div>
            """)

    st.html("""
    <div class="unseen-footer">
        <p>AURA-ECE &middot; Supporting your child's growth journey &middot; &copy;2026</p>
    </div>
    """)

def main() -> None:
    st.set_page_config(page_title="AURA-ECE", page_icon="&#9679;", layout="wide")
    init_state()
    render_global_css()
    render_global_css_2()

    auth = st.session_state.get("auth")
    if handle_google_callback():
        return

    if not auth:
        login_page()
        return

    page = st.session_state.get("page", "workspace")
    if page == "landing":
        landing_page()
        return

    if auth.get("role") == "teacher":
        teacher_dashboard(auth)
    else:
        student_dashboard(auth)

if __name__ == "__main__":
    main()
