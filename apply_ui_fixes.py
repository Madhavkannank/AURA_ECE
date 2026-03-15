path_main = 'e:/AURA-ECE/backend/app/main.py'
with open(path_main, 'r', encoding='utf-8') as f:
    t = f.read()

style_old = """        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #0f1322; color: #f4f7ff; }
            .card { max-width: 460px; margin: 48px auto; background: #1a2033; border: 1px solid #2f3b5f; border-radius: 14px; padding: 20px; }
            h2 { margin: 0 0 10px 0; }
            p { color: #bcc6df; }
            button { width: 100%; height: 44px; border: none; border-radius: 10px; font-weight: 700; cursor: pointer; color: #171327; background: linear-gradient(135deg,#cdb8ff 0%,#a7d2ff 100%); }
        </style>"""

style_new = """        <style>
            body { font-family: 'Inter', Arial, sans-serif; margin: 0; padding: 24px; background: #efe6dd; color: #1a1a1a; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
            .card { max-width: 460px; width: 100%; background: rgba(239, 230, 221, 0.72); border: 1px solid rgba(0,0,0,0.12); border-radius: 16px; padding: 32px; box-shadow: 0 4px 24px rgba(0,0,0,0.04); text-align: center; }
            h2 { margin: 0 0 12px 0; font-family: 'Playfair Display', serif; font-weight: 500; font-size: 28px; color: #1a1a1a; }
            p { color: #6b6b6b; font-size: 15px; margin-bottom: 24px; }
            button { width: 100%; height: 48px; border: none; border-radius: 999px; font-weight: 500; font-size: 15px; cursor: pointer; color: #fff; background: #1a1a1a; transition: all 0.3s ease; }
            button:disabled { opacity: 0.7; cursor: not-allowed; }
            #status { margin-top: 16px; font-size: 13px; color: #9a9a9a; margin-bottom: 0; text-align: center; }
        </style>"""

t = t.replace(style_old, style_new)

with open(path_main, 'w', encoding='utf-8') as f:
    f.write(t)


path_app = 'e:/AURA-ECE/streamlit_app.py'
with open(path_app, 'r', encoding='utf-8') as f:
    t2 = f.read()

hero_old = """    .unseen-hero-label {
        font-family: var(--font-sans); font-size: 12px; font-weight: 500;
        letter-spacing: 0.15em; text-transform: uppercase;
        color: var(--accent-black); margin-bottom: 120px;
    }
    .unseen-hero h1 {
        font-size: 84px !important; margin: 0 0 24px 0 !important;
        line-height: 1.05 !important; color: var(--text-primary) !important;
        letter-spacing: -0.02em !important; max-width: 900px !important;
    }"""

hero_new = """    .unseen-hero-label {
        font-family: var(--font-sans); font-size: 12px; font-weight: 500;
        letter-spacing: 0.15em; text-transform: uppercase;
        color: var(--accent-black); margin-bottom: 24px;
    }
    .unseen-hero h1 {
        font-size: clamp(48px, 6vw, 76px) !important;
        margin: 0 0 24px 0 !important;
        line-height: 1.1 !important; color: var(--text-primary) !important;
        letter-spacing: -0.02em !important;
        max-width: 900px !important;
    }"""

t2 = t2.replace(hero_old, hero_new)

with open(path_app, 'w', encoding='utf-8') as f:
    f.write(t2)

print("Updates applied successfully.")
