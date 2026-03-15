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
    .unseen-pill-solid {
        background: var(--accent-black); color: #ffffff; border: 1.5px solid var(--accent-black);
    }
    .unseen-pill-solid:hover {
        background: #333; transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
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
    .unseen-card-icon { font-size: 28px; margin-bottom: 16px; }
    .unseen-card-title {
        font-family: var(--font-sans); font-size: 16px;
        font-weight: 600; color: var(--text-primary); margin-bottom: 8px;
    }
    .unseen-card-desc {
        font-family: var(--font-sans); font-size: 14px;
        color: var(--text-secondary); line-height: 1.6;
    }

    .unseen-stat-grid {
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 1px; background: var(--border-light);
        border-radius: var(--radius-card); overflow: hidden;
        margin: 48px 0;
    }
    .unseen-stat {
        background: var(--bg-glass-strong);
        backdrop-filter: blur(12px);
        padding: 28px 20px; text-align: center;
    }
    .unseen-stat-value {
        font-family: var(--font-serif); font-size: 36px;
        font-weight: 400; color: var(--text-primary); margin: 0;
    }
    .unseen-stat-label {
        font-family: var(--font-sans); font-size: 12px;
        font-weight: 500; letter-spacing: 0.1em;
        text-transform: uppercase; color: var(--text-muted);
        margin: 8px 0 0 0;
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

    @media (max-width: 768px) {
        .unseen-stat-grid { grid-template-columns: repeat(2, 1fr); }
        .unseen-hero h1 { font-size: 40px !important; }
    }
</style>
"""

def render_global_css_2() -> None:
    st.html(UNSEEN_CSS_2)

def landing_and_login() -> None:
    google_token = st.query_params.get("g_id_token")
    if google_token:
        requested_role = st.query_params.get("g_role", "teacher")
        try:
            data = sign_in_with_google_id_token(google_token, requested_role)
            st.session_state["auth"] = {"token": data["access_token"], "role": data["role"], "user_id": data["user_id"], "parent_id": data.get("parent_id")}
            st.query_params.clear()
            st.rerun()
        except Exception as exc:
            st.query_params.clear()
            st.error(f"Google sign in failed: {exc}")

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
    <div class="unseen-hero" style="
        background-image: linear-gradient(180deg, rgba(250,247,242,0.55) 0%, rgba(250,247,242,0.7) 60%, rgba(250,247,242,0.95) 100%), url('{hero_bg}');
        background-size: cover; background-position: center;
    ">
        <div class="unseen-hero-label">AN AI-POWERED EDUCATION PLATFORM</div>
        <h1><em>Observe.</em> Understand.<br>Grow.</h1>
        <p class="unseen-hero-sub">Transform classroom observations into structured developmental insights. Privacy-aware AI that keeps families engaged with personalized, multilingual reports.</p>
        <div style="display: flex; gap: 12px; flex-wrap: wrap; justify-content: center;">
            <span class="unseen-pill-btn unseen-pill-solid">Explore the platform &rarr;</span>
            <span class="unseen-pill-btn unseen-pill-outline">How it works</span>
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
        ("&#9998;", "Rich Observations", "Capture observations with text, audio notes, and video evidence. AI transcribes and classifies everything automatically."),
        ("&#9670;", "AI Insights", "Generate meaningful developmental insights. Understand trends across domains, identify strengths, and track growth areas."),
        ("&#10070;", "Parent Reports", "Automated, personalized reports for families. Multi-language support ensures every caregiver stays informed."),
        ("&#9906;", "Smart Search", "Search through all student notes and observations instantly. AI-powered retrieval finds relevant information in seconds."),
        ("&#9632;", "Batch Reporting", "Generate weekly or monthly reports for all students at once. Schedule automatic delivery with customizable content."),
        ("&#9679;", "Secure & Private", "Privacy-first architecture. PII masking before AI processing, role-based access control, and encrypted data handling."),
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

    st.html('<h2 class="unseen-section-title"><em>Sign in</em> to your workspace</h2>')
    st.html('<p class="unseen-section-sub">Choose your role and access the right tools for your needs.</p>')

    role_col1, role_col2 = st.columns(2)
    with role_col1:
        if st.button("I'm a Teacher", use_container_width=True, key="role_teacher"):
            st.session_state["selected_role"] = "teacher"
    with role_col2:
        if st.button("I'm a Parent", use_container_width=True, key="role_parent"):
            st.session_state["selected_role"] = "parent"

    selected_role = st.session_state.get("selected_role", "teacher")

    with st.form("login_form", clear_on_submit=False):
        st.html(f'<div class="unseen-form-label">Signing in as {"Teacher" if selected_role == "teacher" else "Parent"}</div>')
        user_id_default = "teacher-001" if selected_role == "teacher" else "parent-001"
        password_default = "teacher123" if selected_role == "teacher" else "parent123"
        user_id = st.text_input("User ID", value=user_id_default, placeholder="Enter your user ID")
        password = st.text_input("Password", value=password_default, type="password", placeholder="Enter your password")
        col_submit, col_demo = st.columns(2)
        with col_submit:
            submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
        with col_demo:
            use_demo = st.form_submit_button("Use Demo Account", use_container_width=True)

    if submit or use_demo:
        try:
            bootstrap_demo_users()
            data = api_request("POST", "/auth/login", json={"user_id": user_id, "password": password})
            st.session_state["auth"] = {"token": data["access_token"], "role": data["role"], "user_id": data["user_id"], "parent_id": data.get("parent_id")}
            st.rerun()
        except Exception as exc:
            st.error(f"Sign in failed: {exc}")

    st.html('<div class="unseen-form-label" style="margin-top: 20px;">Or continue with Google</div>')
    google_redirect_url = get_google_popup_redirect_url(selected_role)
    st.link_button("Sign in with Google", google_redirect_url, use_container_width=True)
    st.caption("Google sign-in opens a secure page, then returns here.")

    st.html("""
    <div class="unseen-footer">
        <p>AURA-ECE &middot; An AI-powered early childhood education platform &middot; &copy;2026</p>
    </div>
    """)
