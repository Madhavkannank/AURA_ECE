import re

path = 'e:/AURA-ECE/streamlit_app.py'
with open(path, 'r', encoding='utf-8') as f:
    t = f.read()

# 1. Update colors
t = t.replace('--bg-cream: #FAF7F2;', '--bg-cream: #efe6dd;')
t = t.replace('--bg-glass: rgba(255, 252, 248, 0.72);', '--bg-glass: rgba(239, 230, 221, 0.72);')
t = t.replace('--bg-glass-strong: rgba(255, 252, 248, 0.88);', '--bg-glass-strong: rgba(239, 230, 221, 0.88);')

# 2. Rename landing_and_login to landing_page
t = t.replace('def landing_and_login() -> None:', 'def landing_page() -> None:')

# 3. Split landing_page and login_page
split_marker = """    st.html('<h2 class="unseen-section-title"><em>Sign in</em> to your workspace</h2>')
    st.html('<p class="unseen-section-sub">Choose your role and access the right tools for your needs.</p>')"""

replacement = """    st.html('<h2 class="unseen-section-title">Ready to get started?</h2>')
    if st.button("Go to Sign In", use_container_width=True, type="primary"):
        st.session_state["page"] = "login"
        st.rerun()

    st.html(\"\"\"
    <div class="unseen-footer">
        <p>AURA-ECE &middot; An AI-powered education platform &middot; &copy;2026</p>
    </div>
    \"\"\")

def login_page() -> None:
    st.html(\"\"\"
    <div class="unseen-nav">
        <span class="unseen-nav-brand">aura &mdash; ece</span>
    </div>
    <div class="page-spacer"></div>
    \"\"\")

    if st.button("&larr; Back to Home"):
        st.session_state["page"] = "landing"
        st.rerun()

    st.html('<h2 class="unseen-section-title" style="margin-top:24px;"><em>Sign in</em> to your workspace</h2>')
    st.html('<p class="unseen-section-sub">Choose your role and access the right tools for your needs.</p>')"""

t = t.replace(split_marker, replacement)

# 4. Update the main() router
main_marker = """    auth = st.session_state.get("auth")
    if not auth:
        landing_and_login()
        return"""

main_replacement = """    auth = st.session_state.get("auth")
    if not auth:
        page = st.session_state.get("page", "landing")
        if page == "landing":
            landing_page()
        else:
            login_page()
        return"""

t = t.replace(main_marker, main_replacement)

# 5. Replace "parent" with "student" in roles and UI texts
# "I'm a Parent" -> "I'm a Student"
t = t.replace('"I\'m a Parent"', '"I\'m a Student"')
t = t.replace('role_parent', 'role_student')
t = t.replace('st.session_state["selected_role"] = "parent"', 'st.session_state["selected_role"] = "student"')
t = t.replace('selected_role == "parent"', 'selected_role == "student"')
t = t.replace('parent-001', 'student-001')
t = t.replace('parent123', 'student123')
t = t.replace('Parent', 'Student') # Note: This might replace Parent Portal, Parent Dashboard, etc., which is what we want!
t = t.replace('parent_dashboard', 'student_dashboard')
t = t.replace('parent_id', 'student_id')
t = t.replace('parents', 'students')

with open(path, 'w', encoding='utf-8') as f:
    f.write(t)

print("UI Refactoring applied successfully.")
