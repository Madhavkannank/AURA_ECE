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
                parent_id = st.text_input("Parent ID", value="parent-001")
            with c4:
                parent_name = st.text_input("Parent Name", placeholder="Contact name")
            c5, c6 = st.columns(2)
            with c5:
                parent_language = st.selectbox("Language", ["en", "es", "fr", "de", "zh", "ja"])
            with c6:
                submitted = st.form_submit_button("Add Student", use_container_width=True, type="primary")

        if submitted:
            try:
                created = api_request("POST", "/students", token=token, json={"full_name": full_name, "class_id": class_id, "parent_id": parent_id, "parent_name": parent_name, "parent_language": parent_language})
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
                            <p class="unseen-student-meta">Class: {s.get('class_id', '—')} &middot; Parent: {s.get('parent_name', '—')} &middot; {s['_id'][:8]}&hellip;</p>
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

        r1, r2, r3 = st.columns(3)
        with r1:
            role_view = st.selectbox("Role", ["teacher", "parent", "student"], key="class_role_view")
        with r2:
            role_pid = st.text_input("Parent ID", key="class_role_parent")
        with r3:
            role_sid = st.text_input("Student ID", key="class_role_student")
        if st.button("Role-Based View", use_container_width=True, key="view_class_role"):
            try:
                view = api_request("POST", f"/reports/class/{class_id.strip()}/view", token=token, json={"role": role_view, "period": period, "parent_id": role_pid.strip() or None, "student_id": role_sid.strip() or None})
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

def parent_dashboard(auth: dict[str, Any]) -> None:
    st.html(f"""
    <div class="unseen-nav">
        <span class="unseen-nav-brand">aura &mdash; ece</span>
        <div class="unseen-nav-links">
            <span style="color: var(--text-muted); font-size: 12px;">Parent Portal</span>
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

    parent_id = auth.get("parent_id") or auth["user_id"]

    st.html('<h2 class="unseen-section-title"><em>Your child\\'s</em> reports</h2>')
    st.html('<p class="unseen-section-sub">Personalized progress reports from the classroom.</p>')

    if st.button("Load My Reports", use_container_width=True, type="primary", key="load_reports"):
        try:
            with st.spinner("Loading…"):
                reports = api_request("GET", f"/parents/{parent_id}/reports", token=auth["token"])
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

    st.html('<h2 class="unseen-section-title"><em>Parent</em> tips</h2>')
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
    if not auth:
        landing_and_login()
        return

    if auth.get("role") == "teacher":
        teacher_dashboard(auth)
    else:
        parent_dashboard(auth)

if __name__ == "__main__":
    main()
