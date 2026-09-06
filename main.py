"""
IMPACT-X — main.py
Final orchestrator (Phase 10). Ties together every phase into one runnable
entry point:

  Phase 2  seed_data.py       -> simulated NovaTech Corporation
  Phase 3  database.py        -> SQLite schema + data load
  Phase 4  graph_engine.py    -> relationship graph
  Phase 5  incident_engine.py -> incident simulation
  Phase 6  blast_radius.py    -> blast radius + attack path calculation
  Phase 7  risk_engine.py     -> risk scoring + prioritization
  Phase 9  ai_analyst.py      -> plain-language incident explanation

Run this file directly for a full terminal walkthrough of the whole
pipeline, end to end, with no dashboard needed:

    python main.py

For the visual dashboard (Phase 8), run separately:

    streamlit run dashboard/app.py
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from database import build_database
from graph_engine import build_graph, graph_summary
from incident_engine import clear_incidents, simulate_incident, get_all_incidents
from risk_engine import prioritize_all_open_incidents, print_priority_list
from ai_analyst import explain_incident


def banner(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def run_full_demo():
    # --- Check AI Analyst configuration up front ---
    banner("CHECKING AI ANALYST CONFIGURATION")
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        print("GEMINI_API_KEY found — AI explanations will use Gemini.")
    else:
        print("No GEMINI_API_KEY found in this environment.")
        print("AI explanations will use the deterministic template fallback instead.")
        print("(This is not an error — the demo works fine either way.)")

    # --- Phase 2 + 3: rebuild a clean simulated organization ---
    banner("PHASE 2 + 3 — Rebuilding NovaTech Corporation database")
    build_database()

    # --- Phase 4: build the relationship graph ---
    banner("PHASE 4 — Building the relationship graph")
    graph = build_graph()
    summary = graph_summary(graph)
    print(f"Nodes: {summary['total_nodes']} | Edges: {summary['total_edges']}")
    for t, count in summary["nodes_by_type"].items():
        print(f"  {t}: {count}")

    # --- Phase 5: simulate a handful of demo incidents ---
    banner("PHASE 5 — Simulating incidents")
    clear_incidents()
    simulate_incident(privilege_level="admin", incident_type="Impossible Travel Login")
    simulate_incident(privilege_level="elevated", incident_type="Unusual Privilege Change")
    simulate_incident(privilege_level="standard", incident_type="Unexpected Access Pattern")
    simulate_incident(privilege_level="admin", incident_type="Abnormal API Activity")
    simulate_incident(privilege_level="standard", incident_type="Suspicious Login")
    incidents = get_all_incidents()
    print(f"{len(incidents)} incidents logged.")

    # --- Phase 6 + 7: blast radius + risk scoring, ranked ---
    banner("PHASE 6 + 7 — Blast radius & prioritized risk queue")
    ranked = prioritize_all_open_incidents()
    print_priority_list(ranked)

    # --- Phase 9: AI explanation for the single highest-risk incident ---
    top = ranked[0]
    banner(f"PHASE 9 — AI Security Analyst: top incident (#{top['incident']['id']})")
    result = explain_incident(top["incident"], top["blast_radius"], top["risk"])
    print(f"[source: {result['source']}]\n")
    print(result["explanation"])

    # --- Wrap-up ---
    banner("DEMO PIPELINE COMPLETE")
    print("All phases ran successfully against a fresh, clean dataset.")
    print("\nLaunching the IMPACT-X dashboard in your browser...")


def launch_dashboard():
    """Launches the Streamlit dashboard using an absolute path, so this
    works correctly no matter what directory the terminal is in when
    main.py is run (e.g. clicking VS Code's Run button)."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(project_root, "dashboard", "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


if __name__ == "__main__":
    run_full_demo()
    if "--no-dashboard" not in sys.argv:
        launch_dashboard()
    else:
        print("\n(--no-dashboard flag set: skipping browser launch — pipeline-only run, e.g. for CI.)")