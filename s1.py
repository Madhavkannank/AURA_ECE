import base64
import os
from pathlib import Path
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
    return api_request("POST", "/auth/firebase-google", json={"id_token": id_token, "requested_role": requested_role})

def get_google_popup_redirect_url(requested_role: str) -> str:
    frontend_return = os.getenv("AURA_FRONTEND_BASE", "http://127.0.0.1:8501")
    safe_role = requested_role if requested_role in {"teacher", "parent"} else "teacher"
    return f"{API_BASE}/auth/firebase-google-popup?role={quote_plus(safe_role)}&return_to={quote_plus(frontend_return)}"

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
        --bg-cream: #FAF7F2;
        --bg-warm: #F5F0EA;
        --bg-blush: #F0E8E0;
        --bg-glass: rgba(255, 252, 248, 0.72);
        --bg-glass-strong: rgba(255, 252, 248, 0.88);
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
</style>
"""

def render_global_css() -> None:
    st.html(UNSEEN_CSS)
