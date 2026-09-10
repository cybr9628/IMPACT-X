import streamlit as st
import time

# -- MUST BE FIRST STREAMLIT COMMAND --
st.set_page_config(page_title="IMPACT-X | Intelligence", layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------
# 1. ADVANCED UI/UX & MOBILE-FIRST CSS INJECTION
# ---------------------------------------------------------
st.markdown("""
<style>
/* Base Typography & Background */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0B0F19;
    color: #E2E8F0;
}

/* Glassmorphism Cards & Animations */
.glass-card {
    background: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 24px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.glass-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(0,0,0,0.4);
    border-color: rgba(56, 189, 248, 0.3);
}

/* Pulsing Network Animation for Landing Page */
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.4); }
    70% { box-shadow: 0 0 0 15px rgba(56, 189, 248, 0); }
    100% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0); }
}
.status-indicator {
    height: 12px; width: 12px;
    background-color: #38BDF8;
    border-radius: 50%;
    display: inline-block;
    animation: pulse 2s infinite;
}

/* --- MOBILE FIRST RESPONSIVE GRID FIXES --- */
/* Forces metrics into a 2x2 grid on mobile instead of vertical stacking */
@media (max-width: 768px) {
    .metric-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .glass-card { padding: 16px; }
    /* Horizontal scroll for overflowing tables */
    [data-testid="stDataFrame"] { overflow-x: auto; }
    h1 { font-size: 2rem !important; }
    .stButton > button { width: 100% !important; padding: 12px !important; }
}

/* Hide default Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ASYNC STATE MANAGEMENT & AUTHENTICATION
# ---------------------------------------------------------
if "auth_status" not in st.session_state:
    st.session_state.auth_status = "logged_out" # States: logged_out, landing, dashboard
if "current_user" not in st.session_state:
    st.session_state.current_user = None

def login(username):
    # Simulated secure login handler
    st.session_state.current_user = username
    st.session_state.auth_status = "dashboard"

def logout():
    st.session_state.current_user = None
    st.session_state.auth_status = "landing"
    st.cache_data.clear()

# ---------------------------------------------------------
# 3. VIEWS: LANDING PAGE
# ---------------------------------------------------------
def render_landing_page():
    # Hero Section
    st.markdown("""
    <div style='text-align: center; padding: 60px 20px;'>
        <div class='status-indicator'></div>
        <h1 style='font-size: 3.5rem; font-weight: 700; margin-bottom: 10px; background: linear-gradient(90deg, #38BDF8, #818CF8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
            IMPACT-X
        </h1>
        <h3 style='color: #94A3B8; font-weight: 400;'>Contextual Risk & Automated Security Intelligence</h3>
        <p style='color: #64748B; max-width: 600px; margin: 20px auto;'>
            Move beyond alert fatigue. IMPACT-X maps your entire digital topology in real-time, instantly calculating the true blast radius of any security event.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### Secure Access")
            uname = st.text_input("Operator ID", placeholder="user@enterprise.com")
            pwd = st.text_input("Passcode", type="password")
            if st.button("Authenticate Session", type="primary", use_container_width=True):
                if uname and pwd:
                    with st.spinner("Validating credentials & establishing secure connection..."):
                        time.sleep(1) # Simulate network delay gracefully
                        login(uname)
                        st.rerun()
                else:
                    st.error("Invalid credentials.")

    # Capabilities & Why This is Best
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class='glass-card'>
            <h4>⚡ Real-Time Topology</h4>
            <p style='color: #94A3B8; font-size: 0.9rem;'>Maps relationships between identities, databases, and APIs instantly without polling delays.</p>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class='glass-card'>
            <h4>🧠 Automated Assessment</h4>
            <p style='color: #94A3B8; font-size: 0.9rem;'>Translates complex graph traversal data into clear, actionable executive summaries instantly.</p>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class='glass-card'>
            <h4>🛡️ Precision Containment</h4>
            <p style='color: #94A3B8; font-size: 0.9rem;'>Isolates exact attack paths, preventing overly broad system lockdowns that disrupt business.</p>
        </div>""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. VIEWS: DASHBOARD (Optimized & Non-Blocking)
# ---------------------------------------------------------
def render_dashboard():
    # Top Navigation Bar
    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.markdown(f"**Operator:** `{st.session_state.current_user}` | **Status:** Connected")
    with header_col2:
        if st.button("Disconnect Session", use_container_width=True):
            logout()
            st.rerun()

    st.divider()

    # Mobile-Responsive Metrics Grid
    st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Threats", "3", delta="1 High")
    m2.metric("Nodes Monitored", "1,204")
    m3.metric("System Health", "98.2%")
    m4.metric("Assessment Engine", "Online", delta="< 10ms latency", delta_color="normal")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Core Application Logic
    main_col, side_col = st.columns([2, 1])
    
    with side_col:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### Threat Queue")
        
        # Simulate lazy loading / background fetching
        with st.spinner("Fetching active alerts..."):
            time.sleep(0.5) # Simulated fast DB read
            
        incident_sel = st.selectbox("Select Event for Triage", ["INC-492: Privilege Escalation", "INC-493: Anomalous Login"])
        if st.button("Run Automated Assessment", type="primary", use_container_width=True):
            st.session_state.run_analysis = True
        st.markdown("</div>", unsafe_allow_html=True)

    with main_col:
        if st.session_state.get("run_analysis"):
            # This represents the non-blocking AI execution
            with st.status("Analyzing graph paths and synthesizing report...", expanded=True) as status:
                st.write("Querying Database...")
                time.sleep(0.5)
                st.write("Tracing Blast Radius...")
                time.sleep(0.5)
                st.write("Generating Human-Readable Assessment...")
                time.sleep(1)
                
                # In production, call your ai_analyst.py function here:
                # result = explain_incident(inc, br, risk)
                result = """
                🔴 **What happened?**
                A standard user account (jdoe_finance) triggered a privilege escalation alert.
                
                ⚠️ **Why does it matter?**
                This identity has lateral access to 14 internal systems, including the primary billing database, posing a high risk of data exfiltration.
                
                🎯 **Risk Level**
                HIGH - 85/100
                
                🔍 **What caused it?**
                Execution of an unauthorized bash script modifying local admin group permissions.
                
                🛡️ **Recommended Action**
                Suspend 'jdoe_finance' account immediately and force token rotation on all active sessions.
                
                📊 **Evidence**
                - Reachable nodes: 14
                - Critical assets exposed: 2
                
                🤖 **Confidence Score**
                High (Telemetry verified across 3 separate logs)
                """
                status.update(label="Assessment Complete", state="complete", expanded=False)
            
            # Displaying the clean, invisible AI result
            st.markdown(f"""
            <div class='glass-card' style='border-left: 4px solid #F59E0B;'>
                {result}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='glass-card' style='text-align: center; color: #64748B;'>
                <br><br>
                <h3>Select an event from the queue to generate an automated assessment.</h3>
                <br><br>
            </div>
            """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. ROUTING ENGINE
# ---------------------------------------------------------
if st.session_state.auth_status in ["logged_out", "landing"]:
    render_landing_page()
elif st.session_state.auth_status == "dashboard":
    render_dashboard()