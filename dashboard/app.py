"""
IMPACT-X — Dashboard (Streamlit)
Full application flow: animated marketing landing page -> sign in / sign up
-> command-center dashboard tying together the graph engine, incident
simulation, blast radius calculation, risk scoring, and incident analysis.

Run with: streamlit run dashboard/app.py
(run from the project root, e.g. IMPACT-X/)
"""

import sys
import os
import time
from html import escape

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from incident_engine import simulate_incident, get_all_incidents, clear_incidents, INCIDENT_TYPES
from risk_engine import prioritize_all_open_incidents, score_incident
from graph_engine import build_graph
from ai_analyst import explain_incident
from auth import init_auth_table, create_user, verify_user, validate_signup_input

try:
    from database import get_data_version
except ImportError:
    get_data_version = None

# Auto-build the database on first run (e.g. a fresh cloud deployment where
# data/impact_x.db doesn't exist yet). Safe to call every time locally too —
# it's a fast, idempotent no-op check.
_DB_PATH = os.path.join(BACKEND_DIR, "..", "data", "impact_x.db")
if not os.path.exists(_DB_PATH):
    from database import build_database
    build_database()

# Ensure the login/sign-up accounts table exists. Independent of the
# simulated org data above; never wiped by a database rebuild.
init_auth_table()

st.set_page_config(page_title="IMPACT-X", layout="wide", page_icon="🛡", initial_sidebar_state="expanded")

# ============================================================
# DESIGN SYSTEM
# ============================================================
CRITICAL, HIGH, MEDIUM, LOW = "#FF4365", "#FF9F43", "#FFD166", "#35D48C"
RISK_COLOR = {"CRITICAL": CRITICAL, "HIGH": HIGH, "MEDIUM": MEDIUM, "LOW": LOW}
ACCENT = "#21D4E0"
ACCENT2 = "#7C6FF0"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');

#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    color: #E7ECF5;
}}

.stApp {{
    background:
        radial-gradient(ellipse 900px 500px at 15% -10%, rgba(33,212,224,0.08), transparent),
        radial-gradient(ellipse 700px 400px at 100% 0%, rgba(255,67,101,0.06), transparent),
        #090D16;
}}

section[data-testid="stSidebar"] {{
    background-color: #0C1119;
    border-right: 1px solid #1C2433;
}}

h1, h2, h3 {{ font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -0.01em; }}

.ix-eyebrow {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    color: {ACCENT};
    text-transform: uppercase;
    margin-bottom: 2px;
}}

.ix-hero-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.4rem;
    font-weight: 700;
    margin: 0 0 4px 0;
    line-height: 1.1;
}}

.ix-hero-sub {{ color: #7C879C; font-size: 0.95rem; margin-bottom: 1.4rem; }}

.ix-card {{
    background: #10151F;
    border: 1px solid #1C2433;
    border-radius: 10px;
    padding: 16px 18px;
    height: 100%;
}}

.ix-kpi-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #7C879C;
}}

.ix-kpi-value {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    margin-top: 4px;
}}

.ix-section-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.15rem;
    font-weight: 600;
    margin: 0.4rem 0 0.9rem 0;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.ix-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 20px;
    letter-spacing: 0.03em;
}}

.ix-mono {{ font-family: 'JetBrains Mono', monospace; }}

hr {{ border-color: #1C2433 !important; }}

[data-testid="stDataFrame"] {{ border: 1px solid #1C2433; border-radius: 10px; overflow: hidden; }}

div[data-testid="stMetricValue"] {{ font-family: 'Space Grotesk', sans-serif; }}

.stButton > button {{
    font-family: 'Inter', sans-serif;
    border-radius: 8px;
    border: 1px solid #1C2433;
}}

/* ============================================================
   LANDING PAGE
   ============================================================ */
@keyframes ixFadeUp {{
    from {{ opacity: 0; transform: translateY(18px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes ixFloat {{
    0%, 100% {{ transform: translateY(0px); }}
    50%      {{ transform: translateY(-14px); }}
}}
@keyframes ixPulse {{
    0%, 100% {{ opacity: 0.55; }}
    50%      {{ opacity: 1; }}
}}
@keyframes ixGradientShift {{
    0%   {{ background-position: 0% 50%; }}
    50%  {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}

.ix-fade-1 {{ animation: ixFadeUp 0.7s ease-out both; }}
.ix-fade-2 {{ animation: ixFadeUp 0.7s ease-out 0.12s both; }}
.ix-fade-3 {{ animation: ixFadeUp 0.7s ease-out 0.24s both; }}
.ix-fade-4 {{ animation: ixFadeUp 0.7s ease-out 0.36s both; }}

.ix-float {{ animation: ixFloat 5s ease-in-out infinite; }}
.ix-float-slow {{ animation: ixFloat 7s ease-in-out infinite; }}
.ix-pulse-dot {{ animation: ixPulse 2.4s ease-in-out infinite; }}

.ix-gradient-text {{
    background: linear-gradient(90deg, {ACCENT}, {ACCENT2}, {ACCENT});
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: ixGradientShift 6s ease-in-out infinite;
}}

.ix-nav {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 0 28px 0;
}}
.ix-nav-links {{ display:flex; gap: 28px; color:#7C879C; font-size:0.92rem; }}

.ix-hero-wrap {{ position: relative; padding: 3.2rem 0 2rem 0; overflow: hidden; }}

.ix-feature-card {{
    background: #10151F;
    border: 1px solid #1C2433;
    border-radius: 12px;
    padding: 22px 20px;
    transition: transform 0.25s ease, border-color 0.25s ease;
    height: 100%;
}}
.ix-feature-card:hover {{
    transform: translateY(-4px);
    border-color: {ACCENT}55;
}}

.ix-stat-num {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.1rem;
    font-weight: 700;
    color: {ACCENT};
}}
.ix-stat-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #7C879C;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}}

.ix-step-num {{
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    color: {ACCENT};
    font-size: 0.85rem;
    border: 1px solid {ACCENT}55;
    border-radius: 50%;
    width: 28px; height: 28px;
    display:flex; align-items:center; justify-content:center;
    margin-bottom: 10px;
}}

/* ============================================================
   MOBILE RESPONSIVENESS
   Everything below this line ONLY applies when the browser
   viewport is 768px wide or less (phones/small tablets).
   Desktop layout above this breakpoint is completely untouched.
   ============================================================ */
@media (max-width: 768px) {{
    .ix-hero-title {{ font-size: 1.6rem !important; }}
    .ix-hero-sub {{ font-size: 0.82rem !important; }}
    .ix-eyebrow {{ font-size: 0.62rem !important; }}
    .ix-kpi-value {{ font-size: 1.4rem !important; }}
    .ix-section-title {{ font-size: 0.98rem !important; }}
    .ix-card {{ padding: 12px 14px !important; }}
    [data-testid="stDataFrame"] {{ font-size: 0.75rem !important; }}
}}
</style>
""", unsafe_allow_html=True)


# ============================================================
# ICONS — hand-built inline SVGs (no emoji, no external icon fonts)
# ============================================================
def icon(name, size=18, color="currentColor", stroke_width=1.8):
    paths = {
        "shield": '<path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6l7-3z"/>',
        "network": '<circle cx="6" cy="6" r="2.2"/><circle cx="18" cy="6" r="2.2"/><circle cx="12" cy="18" r="2.2"/>'
                    '<path d="M7.8 7.4L11 16.2M16.2 7.4L13 16.2M8.2 6H15.8"/>',
        "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="0.6" fill="currentColor"/>',
        "chart": '<path d="M4 19V5M4 19h16M8 15l3-4 3 2 4-6"/>',
        "alert": '<path d="M12 4l9 15H3l9-15z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.6" fill="currentColor"/>',
        "layers": '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>',
        "document": '<path d="M6 3h9l3 3v15H6z"/><path d="M15 3v3h3"/><path d="M9 12h6M9 16h6"/>',
        "check": '<path d="M4 12l5 5L20 6"/>',
        "arrow-right": '<path d="M4 12h15M13 6l6 6-6 6"/>',
        "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
        "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
        "trash": '<path d="M5 7h14M9 7V5h6v2M7 7l1 13h8l1-13"/>',
        "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
        "satellite": '<path d="M13 3l3 3-5 5-3-3 5-5z"/><path d="M8 10l-4 4 3 3 4-4"/><path d="M6 18l-2 2"/><path d="M16 7l2-2"/>',
        "rocket": '<path d="M12 2c3 2 5 6 4 11l-2 2H10l-2-2c-1-5 1-9 4-11z"/><circle cx="12" cy="9" r="1.5"/><path d="M9 15l-2 5 3-1M15 15l2 5-3-1"/>',
        "cpu": '<rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M9 4v3M15 4v3M9 17v3M15 17v3M4 9h3M4 15h3M17 9h3M17 15h3"/>',
        "eye": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
    }
    p = paths.get(name, "")
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" '
            f'stroke-linejoin="round" style="vertical-align:middle;">{p}</svg>')


def risk_badge(status):
    color = RISK_COLOR.get(status, "#7C879C")
    return f'<span class="ix-badge" style="background:{color}22; color:{color}; border:1px solid {color}55;">{status}</span>'


def rate_limited(action_key, cooldown_seconds):
    """
    Simple per-session cooldown check using Streamlit's session_state.
    Returns True if the action is allowed right now (and records the
    timestamp), or False if it's still within the cooldown window.
    """
    last_key = f"_last_action_{action_key}"
    now = time.time()
    last = st.session_state.get(last_key, 0)
    if now - last < cooldown_seconds:
        return False
    st.session_state[last_key] = now
    return True


def current_data_version():
    """Return a backend revision so cached reads cannot outlive a reset."""
    if get_data_version is not None:
        try:
            return str(get_data_version())
        except Exception:
            pass
    # Compatibility fallback for older backend revisions.
    try:
        return repr([(row.get("id"), row.get("updated_at"), row.get("revision"))
                     for row in get_all_incidents()])
    except Exception:
        return "unknown"


@st.cache_resource(show_spinner=False)
def get_graph(data_version):
    """Cache topology only for the current backend data revision."""
    return build_graph()


@st.cache_data(show_spinner=False)
def get_ranked_incidents(data_version):
    """Avoid rescoring and rewriting every incident on normal reruns."""
    return prioritize_all_open_incidents()


def goto(view_name):
    st.session_state.view = view_name


# ============================================================
# SESSION STATE DEFAULTS
# ============================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "view" not in st.session_state:
    st.session_state.view = "landing"


# ============================================================
# LANDING PAGE
# ============================================================
def render_landing():
    nav_l, nav_r = st.columns([4, 1])
    with nav_l:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; padding-top:6px;">
            <span style="color:{ACCENT};">{icon('shield', 26)}</span>
            <span style="font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:700;">IMPACT-X</span>
        </div>
        """, unsafe_allow_html=True)
    with nav_r:
        if st.button("Sign In", key="nav_signin", use_container_width=True):
            goto("auth")
            st.rerun()

    st.markdown('<div class="ix-hero-wrap">', unsafe_allow_html=True)

    # Decorative floating network graphic (purely visual, CSS-animated)
    st.markdown(f"""
    <div style="position:relative; height:0;">
        <div style="position:absolute; right:2%; top:-40px; opacity:0.5;" class="ix-float">
            <span style="color:{ACCENT};">{icon('network', 70)}</span>
        </div>
        <div style="position:absolute; right:16%; top:70px; opacity:0.35;" class="ix-float-slow">
            <span style="color:{ACCENT2};">{icon('target', 44)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="ix-fade-1" style="max-width: 760px;">
        <div class="ix-eyebrow">IDENTITY-CENTRIC THREAT INTELLIGENCE</div>
        <div style="font-family:'Space Grotesk',sans-serif; font-size:3.1rem; font-weight:700; line-height:1.08; margin: 10px 0 18px 0;">
            See every path an attacker<br><span class="ix-gradient-text">could actually take.</span>
        </div>
        <div style="color:#7C879C; font-size:1.05rem; max-width:600px; line-height:1.6;">
            IMPACT-X models your organization's identities and systems as a live graph, so a single
            compromised account instantly reveals its full blast radius — not just an isolated alert.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    cta1, cta2, _ = st.columns([1.1, 1.3, 3])
    with cta1:
        if st.button("Get Started", key="hero_cta", type="primary", use_container_width=True,
                      icon=":material/arrow_forward:"):
            goto("auth")
            st.rerun()
    with cta2:
        st.link_button("View Source on GitHub", "https://github.com/cybr9628/IMPACT-X",
                        use_container_width=True, icon=":material/code:")

    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")

    # Stats row
    stat_cols = st.columns(4)
    stats = [("70", "Identities Modeled"), ("95", "Assets Tracked"),
             ("215", "Relationships Mapped"), ("6", "Weighted Risk Factors")]
    for col, (num, label) in zip(stat_cols, stats):
        with col:
            st.markdown(f"""
            <div class="ix-card ix-fade-2" style="text-align:center;">
                <div class="ix-stat-num">{num}</div>
                <div class="ix-stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    st.write("")

    # Features
    st.markdown('<div class="ix-eyebrow">CAPABILITIES</div>', unsafe_allow_html=True)
    st.markdown('<div class="ix-hero-title" style="font-size:1.8rem;">Built for real identity risk</div>', unsafe_allow_html=True)
    st.write("")

    features = [
        ("network", "Graph-Native Modeling", "Every identity, application, database, API, and service is a node in one connected, traversable graph."),
        ("target", "Instant Blast Radius", "Trace everything a compromised identity can reach, at any depth, in real time — not a static rule list."),
        ("chart", "Transparent Risk Scoring", "Six auditable, weighted factors combine into one 0-100 score, so priority reflects real impact."),
        ("document", "Plain-Language Summaries", "Every incident gets a concise, data-grounded write-up an analyst can act on immediately."),
    ]
    fcols = st.columns(4)
    for col, (ic, title, desc) in zip(fcols, features):
        with col:
            st.markdown(f"""
            <div class="ix-feature-card">
                <div style="color:{ACCENT}; margin-bottom:12px;">{icon(ic, 26)}</div>
                <div style="font-weight:600; margin-bottom:8px;">{title}</div>
                <div style="color:#7C879C; font-size:0.88rem; line-height:1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    st.write("")

    # How it works
    st.markdown('<div class="ix-eyebrow">WORKFLOW</div>', unsafe_allow_html=True)
    st.markdown('<div class="ix-hero-title" style="font-size:1.8rem;">From alert to action</div>', unsafe_allow_html=True)
    st.write("")

    steps = [
        ("1", "An incident is detected against a real identity in the graph."),
        ("2", "The engine traces every asset that identity can reach."),
        ("3", "A weighted score ranks the incident by real impact."),
        ("4", "A concise summary and recommended action are generated."),
    ]
    scols = st.columns(4)
    for col, (n, desc) in zip(scols, steps):
        with col:
            st.markdown(f"""
            <div class="ix-card">
                <div class="ix-step-num">{n}</div>
                <div style="color:#E7ECF5; font-size:0.9rem; line-height:1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    st.write("")
    st.divider()
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; color:#7C879C; font-size:0.82rem; padding: 6px 0 24px 0;">
        <div>IMPACT-X — Identity-Centric Threat Intelligence Platform</div>
        <div>Simulated demo environment · NovaTech Corporation</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# AUTH PAGE (Sign In / Create Account)
# ============================================================
def render_auth():
    if st.button("← Back to home", key="back_home"):
        goto("landing")
        st.rerun()

    st.markdown(f"""
    <div style="text-align:center; max-width: 460px; margin: 1.5rem auto 1.5rem auto;">
        <div style="color:{ACCENT};">{icon('shield', 34)}</div>
        <div style="font-family:'Space Grotesk', sans-serif; font-size:2rem; font-weight:700; color:#E7ECF5; margin-top:6px;">IMPACT-X</div>
        <div style="color:#7C879C; font-size:0.95rem; margin-top:4px;">Identity-Centric Threat Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 1.3, 1])
    with center_col:
        with st.container(border=True):
            tab_signin, tab_signup = st.tabs(["Sign In", "Create Account"])

            with tab_signin:
                with st.form("signin_form"):
                    si_username = st.text_input("Username")
                    si_password = st.text_input("Password", type="password")
                    si_submit = st.form_submit_button("Sign In", use_container_width=True)

                st.markdown(
                    f'<div style="text-align:center; color:#7C879C; font-size:0.78rem; margin-top:10px;">'
                    f'{icon("lock", 13)} Your password is hashed and encrypted — never stored in plain text.</div>',
                    unsafe_allow_html=True,
                )

                if si_submit:
                    if rate_limited("signin_attempt", cooldown_seconds=1.5):
                        ok, msg = verify_user(si_username.strip(), si_password)
                        if ok:
                            st.session_state.authenticated = True
                            st.session_state.current_user = si_username.strip()
                            goto("dashboard")
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Please wait a moment before trying again.")

            with tab_signup:
                with st.form("signup_form"):
                    su_username = st.text_input("Choose a username")
                    su_email = st.text_input("Email")
                    su_password = st.text_input("Choose a password", type="password")
                    su_confirm = st.text_input("Confirm password", type="password")
                    su_submit = st.form_submit_button("Create Account", use_container_width=True)

                st.markdown(
                    f'<div style="text-align:center; color:#7C879C; font-size:0.78rem; margin-top:10px;">'
                    f'{icon("lock", 13)} Your password is hashed and encrypted — never stored in plain text.</div>',
                    unsafe_allow_html=True,
                )

                if su_submit:
                    if rate_limited("signup_attempt", cooldown_seconds=1.5):
                        error = validate_signup_input(su_username.strip(), su_email.strip(), su_password, su_confirm)
                        if error:
                            st.error(error)
                        else:
                            ok, msg = create_user(su_username.strip(), su_email.strip(), su_password)
                            if ok:
                                st.success(f"{msg} You can now sign in from the Sign In tab.")
                            else:
                                st.error(msg)
                    else:
                        st.warning("Please wait a moment before trying again.")


# ============================================================
# ROUTER (unauthenticated views)
# ============================================================
if not st.session_state.authenticated:
    if st.session_state.view == "auth":
        render_auth()
    else:
        render_landing()
    st.stop()


# ============================================================
# SIDEBAR (authenticated)
# ============================================================
with st.sidebar:
    st.markdown(
        f'<div class="ix-eyebrow">SIGNED IN AS {st.session_state.get("current_user", "").upper()}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:8px; margin: 2px 0 4px 0;">
        <span style="color:{ACCENT};">{icon('shield', 22)}</span>
        <span style="font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:700;">IMPACT-X</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Identity-Centric Threat Intelligence Platform")
    st.divider()

    st.markdown("**Simulate an Incident**")
    sim_privilege = st.selectbox("Force identity privilege", ["Random", "standard", "elevated", "admin"])
    sim_type = st.selectbox("Incident type", ["Random"] + INCIDENT_TYPES)

    if st.button("Simulate Incident", use_container_width=True, icon=":material/bolt:"):
        if rate_limited("simulate_incident", cooldown_seconds=2):
            privilege_arg = None if sim_privilege == "Random" else sim_privilege
            type_arg = None if sim_type == "Random" else sim_type
            incident = simulate_incident(privilege_level=privilege_arg, incident_type=type_arg)
            st.success(f"Incident #{incident['incident_id']} logged: {incident['entity_name']}")
        else:
            st.warning("Please wait a moment before simulating another incident.")

    if st.button("Reset All Incidents", use_container_width=True, icon=":material/restart_alt:"):
        if rate_limited("reset_incidents", cooldown_seconds=3):
            clear_incidents()
            get_graph.clear()
            get_ranked_incidents.clear()
            st.info("All incidents cleared.")
        else:
            st.warning("Please wait a moment before resetting again.")

    st.divider()
    st.caption("Simulated demo data — no real infrastructure is represented.")
    st.caption("NovaTech Corporation")

    st.divider()
    if st.button("Log Out", use_container_width=True, icon=":material/logout:"):
        st.session_state.authenticated = False
        st.session_state.pop("current_user", None)
        goto("landing")
        st.rerun()

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="ix-eyebrow">THREAT INTELLIGENCE COMMAND CENTER</div>', unsafe_allow_html=True)

head_l, head_r = st.columns([3, 1.4])
with head_l:
    st.markdown('<div class="ix-hero-title">IMPACT-X Dashboard</div>', unsafe_allow_html=True)
with head_r:
    st.markdown(f"""
    <div style="text-align:right; padding-top:14px;">
        <div class="ix-mono" style="font-size:0.8rem; color:#7C879C;">{st.session_state.get('current_user','')}</div>
        <div class="ix-mono" style="font-size:0.75rem; color:{ACCENT};">NovaTech Corporation</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown(
    '<div class="ix-hero-sub">Something happened &rarr; here\'s what it could reach &rarr; '
    'here\'s the blast radius &rarr; here\'s what matters most.</div>',
    unsafe_allow_html=True
)

incidents = get_all_incidents()

if not incidents:
    st.markdown(f"""
    <div class="ix-card" style="text-align:center; padding: 48px 20px;">
        <div style="color:{ACCENT}; margin-bottom:10px;">{icon('satellite', 34)}</div>
        <div class="ix-section-title" style="justify-content:center;">No active incidents</div>
        <div style="color:#7C879C;">Use <b>Simulate Incident</b> in the sidebar to trigger the first alert
        and populate the threat picture.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

data_version = current_data_version()
graph = get_graph(data_version)
ranked = get_ranked_incidents(data_version)
open_ids = {r["incident"]["id"] for r in ranked}
for inc in incidents:
    if inc["id"] not in open_ids:
        ranked.append(score_incident(inc["id"], graph=graph))
ranked.sort(key=lambda r: r["risk"]["score"], reverse=True)

avg_score = sum(r["risk"]["score"] for r in ranked) / len(ranked)
critical_n = sum(1 for r in ranked if r["risk"]["status"] == "CRITICAL")
high_n = sum(1 for r in ranked if r["risk"]["status"] == "HIGH")
services_at_risk = len({svc["id"] for r in ranked for svc in r["blast_radius"]["business_services_affected"]})
total_assets_monitored = sum(1 for _, d in graph.nodes(data=True) if d.get("node_type") != "user")

st.write("")

# ============================================================
# RISK POSTURE GAUGE + KPI CARDS
# ============================================================
gauge_col, kpi_col = st.columns([1.1, 2])

with gauge_col:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_score,
        number={"suffix": "/100", "font": {"family": "Space Grotesk", "size": 34, "color": "#E7ECF5"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#7C879C", "tickfont": {"size": 10}},
            "bar": {"color": ACCENT, "thickness": 0.25},
            "bgcolor": "#10151F",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": "#35D48C33"},
                {"range": [30, 60], "color": "#FFD16633"},
                {"range": [60, 85], "color": "#FF9F4333"},
                {"range": [85, 100], "color": "#FF436533"},
            ],
        },
        title={"text": "ORGANIZATIONAL RISK POSTURE", "font": {"family": "JetBrains Mono", "size": 12, "color": "#7C879C"}},
    ))
    fig.update_layout(
        height=230, margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="#10151F", font_color="#E7ECF5",
    )
    st.markdown('<div class="ix-card">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with kpi_col:
    k1, k2, k3, k4 = st.columns(4)
    kpis = [
        (k1, "Open Incidents", len(ranked), None),
        (k2, "Critical", critical_n, CRITICAL if critical_n else None),
        (k3, "High", high_n, HIGH if high_n else None),
        (k4, "Services at Risk", services_at_risk, CRITICAL if services_at_risk else None),
    ]
    for col, label, value, color in kpis:
        c = color or "#E7ECF5"
        col.markdown(f"""
        <div class="ix-card">
            <div class="ix-kpi-label">{label}</div>
            <div class="ix-kpi-value" style="color:{c};">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    a1, a2 = st.columns(2)
    a1.markdown(f"""
    <div class="ix-card">
        <div class="ix-kpi-label">Assets Monitored</div>
        <div class="ix-kpi-value" style="font-size:1.5rem;">{total_assets_monitored}</div>
    </div>""", unsafe_allow_html=True)
    a2.markdown(f"""
    <div class="ix-card">
        <div class="ix-kpi-label">Identities Tracked</div>
        <div class="ix-kpi-value" style="font-size:1.5rem;">{sum(1 for _,d in graph.nodes(data=True) if d.get('node_type')=='user')}</div>
    </div>""", unsafe_allow_html=True)

st.write("")
st.write("")

# ============================================================
# ATTACK PATTERN ANALYTICS
# ============================================================
st.markdown(f'<div class="ix-section-title">{icon("chart", 20)} Attack Pattern Analytics</div>', unsafe_allow_html=True)

chart_rows = []
for r in ranked:
    inc = r["incident"]
    chart_rows.append({
        "id": inc["id"], "risk_status": r["risk"]["status"], "score": r["risk"]["score"],
        "department": inc["department"], "incident_type": inc["incident_type"],
        "reachable": r["blast_radius"]["reachable_count"], "entity": inc["user_name"],
        "privilege": inc["privilege_level"],
    })
cdf = pd.DataFrame(chart_rows)

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown('<div class="ix-card">', unsafe_allow_html=True)
    st.markdown("**Risk Level Distribution**")
    dist = cdf["risk_status"].value_counts().reindex(["CRITICAL", "HIGH", "MEDIUM", "LOW"]).fillna(0)
    fig1 = go.Figure(go.Bar(
        x=dist.index, y=dist.values,
        marker_color=[RISK_COLOR[s] for s in dist.index],
        text=dist.values.astype(int), textposition="outside",
    ))
    fig1.update_layout(
        height=280, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E7ECF5", family="Inter"),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#1C2433"),
    )
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with chart_col2:
    st.markdown('<div class="ix-card">', unsafe_allow_html=True)
    st.markdown("**Attack Surface vs. Impact** — reachable assets vs. risk score")
    fig2 = px.scatter(
        cdf, x="reachable", y="score", color="risk_status",
        color_discrete_map=RISK_COLOR, hover_data=["entity", "incident_type"],
        labels={"reachable": "Reachable Assets", "score": "Risk Score"},
    )
    fig2.update_traces(marker=dict(size=13, line=dict(width=1, color="#090D16")))
    fig2.update_layout(
        height=280, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E7ECF5", family="Inter"), legend_title_text="",
        xaxis=dict(showgrid=True, gridcolor="#1C2433"), yaxis=dict(showgrid=True, gridcolor="#1C2433"),
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    st.markdown('<div class="ix-card">', unsafe_allow_html=True)
    st.markdown("**Exposure by Department**")
    dept = cdf.groupby("department")["score"].mean().sort_values(ascending=True)
    fig3 = go.Figure(go.Bar(
        x=dept.values, y=dept.index, orientation="h",
        marker_color=ACCENT,
    ))
    fig3.update_layout(
        height=280, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E7ECF5", family="Inter"),
        xaxis=dict(title="Avg Risk Score", showgrid=True, gridcolor="#1C2433"), yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with chart_col4:
    st.markdown('<div class="ix-card">', unsafe_allow_html=True)
    st.markdown("**Most Common Attack Patterns**")
    itype = cdf["incident_type"].value_counts()
    fig4 = go.Figure(go.Bar(
        x=itype.values, y=itype.index, orientation="h",
        marker_color=ACCENT2,
    ))
    fig4.update_layout(
        height=280, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E7ECF5", family="Inter"),
        xaxis=dict(title="Occurrences", showgrid=True, gridcolor="#1C2433"), yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")
st.write("")

# ============================================================
# PRIORITIZED INCIDENT QUEUE
# ============================================================
st.markdown(f'<div class="ix-section-title">{icon("layers", 20)} Prioritized Incident Queue</div>', unsafe_allow_html=True)

table_rows = []
for r in ranked:
    inc = r["incident"]
    table_rows.append({
        "ID": inc["id"], "Risk": r["risk"]["status"], "Score": r["risk"]["score"],
        "Entity": inc["user_name"], "Role": inc["role"], "Department": inc["department"],
        "Incident Type": inc["incident_type"], "Reachable Assets": r["blast_radius"]["reachable_count"],
        "Services Affected": r["blast_radius"]["business_services_count"],
    })
df = pd.DataFrame(table_rows)
st.dataframe(
    df, use_container_width=True, hide_index=True,
    column_config={
        "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
    },
)

st.write("")

# ============================================================
# BLAST RADIUS EXPLORER
# ============================================================
st.markdown(f'<div class="ix-section-title">{icon("target", 20)} Blast Radius Explorer</div>', unsafe_allow_html=True)

incident_options = {f"#{r['incident']['id']} — {r['incident']['user_name']} ({r['incident']['incident_type']})": r
                     for r in ranked}
selected_label = st.selectbox("Select an incident to investigate:", list(incident_options.keys()))
selected = incident_options[selected_label]

inc = selected["incident"]
br = selected["blast_radius"]
risk = selected["risk"]

colA, colB = st.columns([1, 2])

with colA:
    st.markdown(f"""
    <div class="ix-card">
        <div style="margin-bottom:10px;">{risk_badge(risk['status'])} <span class="ix-mono" style="font-size:1.3rem; margin-left:8px;">{risk['score']}/100</span></div>
        <div style="color:#7C879C; font-size:0.85rem;">ENTITY</div>
        <div style="font-weight:600; margin-bottom:8px;">{inc['user_name']} — {inc['role']}, {inc['department']}</div>
        <div style="color:#7C879C; font-size:0.85rem;">PRIVILEGE</div>
        <div style="font-weight:600; margin-bottom:8px;">{inc['privilege_level']}</div>
        <div style="color:#7C879C; font-size:0.85rem;">INCIDENT</div>
        <div style="font-weight:600; margin-bottom:8px;">{inc['incident_type']}</div>
        <hr>
        <div class="ix-mono" style="font-size:0.85rem; line-height:1.8;">
        Reachable Assets: <b>{br['reachable_count']}</b><br>
        Critical Assets: <b>{br['critical_count']}</b><br>
        Sensitive Data: <b>{br['sensitive_count']}</b><br>
        Business Services: <b>{br['business_services_count']}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Risk Score Breakdown"):
        for factor, val in risk["breakdown"].items():
            st.write(f"- {factor.replace('_', ' ').title()}: {val}")

with colB:
    st.markdown("#### Directly Accessible Assets")
    if br["directly_accessible"]:
        st.dataframe(pd.DataFrame([
            {"Asset": d["label"], "Type": d["node_type"], "Via": d["via"]} for d in br["directly_accessible"]
        ]), use_container_width=True, hide_index=True)
    else:
        st.caption("None")

    st.markdown("#### Affected Business Services & Attack Paths")
    if br["business_services_affected"]:
        for svc in br["business_services_affected"]:
            path_str = " → ".join(svc["attack_path"]) if svc["attack_path"] else "N/A"
            st.markdown(f"**{svc['label']}** ({svc['criticality']}) &nbsp; `{path_str}`")
    else:
        st.caption("None reachable — low-impact incident.")

    st.markdown("#### All Reachable Assets")
    if br["all_reachable"]:
        st.dataframe(pd.DataFrame([
            {"Asset": n["label"], "Type": n["node_type"], "Sensitivity": n.get("data_sensitivity") or "-"}
            for n in br["all_reachable"]
        ]), use_container_width=True, hide_index=True)

st.write("")

# ============================================================
# INCIDENT ANALYSIS
# ============================================================
st.markdown(f'<div class="ix-section-title">{icon("document", 20)} Incident Analysis</div>', unsafe_allow_html=True)

ai_key = f"ai_explanation_{inc['id']}"

if st.button("Generate Summary", key=f"explain_btn_{inc['id']}", icon=":material/summarize:"):
    if rate_limited(f"explain_{inc['id']}", cooldown_seconds=5):
        with st.spinner("Analyzing incident context..."):
            st.session_state[ai_key] = explain_incident(inc, br, risk)
    else:
        st.warning("Please wait a few seconds before requesting another summary.")

if ai_key in st.session_state:
    result = st.session_state[ai_key]
    st.markdown(f"""
    <div class="ix-card" style="border-left: 3px solid {ACCENT};">
        <div class="ix-kpi-label" style="margin-bottom:8px;">SUMMARY</div>
        <div style="line-height:1.6;">{escape(str(result.get('explanation', '')))}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.caption("Click above to generate a concise summary of this incident's impact.")