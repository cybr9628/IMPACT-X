"""
IMPACT-X — Phase 8: Dashboard (Streamlit)
Command-center style dashboard tying together Phases 2-7:
- Trigger a simulated incident
- Organizational risk posture gauge
- Attack pattern analytics (risk distribution, attack surface vs impact,
  department exposure, incident type frequency)
- Prioritized, risk-scored incident queue
- Blast Radius Explorer — drill into any incident's full attack path

Run with: streamlit run dashboard/app.py
(run from the project root, e.g. IMPACT-X/)
"""

import sys
import os

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

# Auto-build the database on first run (e.g. a fresh cloud deployment where
# data/impact_x.db doesn't exist yet). Safe to call every time locally too —
# it's a fast, idempotent no-op check.
_DB_PATH = os.path.join(BACKEND_DIR, "..", "data", "impact_x.db")
if not os.path.exists(_DB_PATH):
    from database import build_database
    build_database()

st.set_page_config(page_title="IMPACT-X", layout="wide", page_icon="🛰️", initial_sidebar_state="expanded")

# ============================================================
# DESIGN SYSTEM
# ============================================================
# Palette:
#   bg        #090D16   panel     #10151F   panel-border #1C2433
#   text      #E7ECF5   muted     #7C879C   accent (cyan) #21D4E0
#   critical  #FF4365   high      #FF9F43   medium #FFD166   low #35D48C
# Type: Space Grotesk (display) / Inter (body) / JetBrains Mono (data)

CRITICAL, HIGH, MEDIUM, LOW = "#FF4365", "#FF9F43", "#FFD166", "#35D48C"
RISK_COLOR = {"CRITICAL": CRITICAL, "HIGH": HIGH, "MEDIUM": MEDIUM, "LOW": LOW}
ACCENT = "#21D4E0"

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
</style>
""", unsafe_allow_html=True)


def risk_badge(status):
    color = RISK_COLOR.get(status, "#7C879C")
    return f'<span class="ix-badge" style="background:{color}22; color:{color}; border:1px solid {color}55;">{status}</span>'


@st.cache_resource
def get_graph():
    return build_graph()


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown('<div class="ix-eyebrow">NOVATECH CORPORATION</div>', unsafe_allow_html=True)
    st.markdown('<div class="ix-hero-title" style="font-size:1.6rem;">🛰️ IMPACT-X</div>', unsafe_allow_html=True)
    st.caption("Cyber Blast Radius Prediction & Attack Path Analysis")
    st.divider()

    st.markdown("**Simulate an Incident**")
    sim_privilege = st.selectbox("Force identity privilege", ["Random", "standard", "elevated", "admin"])
    sim_type = st.selectbox("Incident type", ["Random"] + INCIDENT_TYPES)

    if st.button("🚨  Simulate Incident", use_container_width=True):
        privilege_arg = None if sim_privilege == "Random" else sim_privilege
        type_arg = None if sim_type == "Random" else sim_type
        incident = simulate_incident(privilege_level=privilege_arg, incident_type=type_arg)
        st.success(f"Incident #{incident['incident_id']} logged: {incident['entity_name']}")

    if st.button("🗑️  Reset All Incidents", use_container_width=True):
        clear_incidents()
        st.info("All incidents cleared.")

    st.divider()
    st.caption("Simulated demo data — no real infrastructure is represented.")

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="ix-eyebrow">THREAT INTELLIGENCE COMMAND CENTER</div>', unsafe_allow_html=True)
st.markdown('<div class="ix-hero-title">IMPACT-X Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ix-hero-sub">Something happened &rarr; here\'s what it could reach &rarr; '
    'here\'s the blast radius &rarr; here\'s what matters most.</div>',
    unsafe_allow_html=True
)

incidents = get_all_incidents()

if not incidents:
    st.markdown("""
    <div class="ix-card" style="text-align:center; padding: 48px 20px;">
        <div style="font-size:2rem;">🛰️</div>
        <div class="ix-section-title" style="justify-content:center;">No active incidents</div>
        <div style="color:#7C879C;">Use <b>Simulate Incident</b> in the sidebar to trigger the first alert
        and populate the threat picture.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

graph = get_graph()
ranked = prioritize_all_open_incidents()
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
st.markdown('<div class="ix-section-title">📡 Attack Pattern Analytics</div>', unsafe_allow_html=True)

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
        marker_color="#7C6FF0",
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
st.markdown('<div class="ix-section-title">📋 Prioritized Incident Queue</div>', unsafe_allow_html=True)

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
st.markdown('<div class="ix-section-title">🔥 Blast Radius Explorer</div>', unsafe_allow_html=True)

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
# AI SECURITY ANALYST
# ============================================================
st.markdown('<div class="ix-section-title">🧠 AI Security Analyst</div>', unsafe_allow_html=True)

ai_key = f"ai_explanation_{inc['id']}"

if st.button("💬  Explain this incident", key=f"explain_btn_{inc['id']}"):
    with st.spinner("Analyzing incident context..."):
        st.session_state[ai_key] = explain_incident(inc, br, risk)

if ai_key in st.session_state:
    result = st.session_state[ai_key]
    source_label = "🤖 Groq-generated" if result["source"] == "ai" else "📋 Template-based (no API key set)"
    st.markdown(f"""
    <div class="ix-card" style="border-left: 3px solid {ACCENT};">
        <div class="ix-kpi-label" style="margin-bottom:8px;">{source_label}</div>
        <div style="line-height:1.6;">{result['explanation']}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.caption("Click above to generate a plain-language explanation of this incident's impact.")