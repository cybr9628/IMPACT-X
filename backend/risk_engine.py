"""
IMPACT-X — Phase 7: Risk Scoring & Prioritization
Combines incident severity, identity privilege, asset criticality, data
sensitivity, and blast radius size into one 0-100 risk score, so incidents
can be ranked by real business impact instead of raw alert type.
"""

import sqlite3
import os
from blast_radius import calculate_blast_radius
from graph_engine import build_graph
from incident_engine import get_connection

# --- Scoring weights (each capped individually, then summed and capped at 100) ---

INCIDENT_SEVERITY_SCORE = {
    "LOW": 10,
    "MEDIUM": 20,
    "HIGH": 30,
    "CRITICAL": 35,
}

PRIVILEGE_SCORE = {
    "standard": 5,
    "elevated": 15,
    "admin": 25,
}


def _capped(value, cap):
    return min(value, cap)


def calculate_risk_score(incident_type, incident_base_risk, privilege_level, blast_report):
    """
    Returns {"score": int (0-100), "status": str}.

    Factors combined:
      + Incident Severity        (up to 35)
      + Identity Privilege       (up to 25)
      + Critical Assets Reached  (up to 20)
      + Business Services Hit    (up to 15)
      + Reachable Asset Volume   (up to 15)
      + Sensitive Data Exposure  (up to 10)
    """
    severity_score = INCIDENT_SEVERITY_SCORE.get(incident_base_risk, 15)
    privilege_score = PRIVILEGE_SCORE.get(privilege_level, 5)
    critical_score = _capped(blast_report["critical_count"] * 10, 20)
    service_score = _capped(blast_report["business_services_count"] * 8, 15)
    volume_score = _capped(blast_report["reachable_count"], 15)
    sensitivity_score = _capped(blast_report["sensitive_count"] * 2, 10)

    raw_total = (severity_score + privilege_score + critical_score +
                 service_score + volume_score + sensitivity_score)
    score = min(raw_total, 100)

    if score >= 85:
        status = "CRITICAL"
    elif score >= 60:
        status = "HIGH"
    elif score >= 30:
        status = "MEDIUM"
    else:
        status = "LOW"

    return {
        "score": score,
        "status": status,
        "breakdown": {
            "incident_severity": severity_score,
            "identity_privilege": privilege_score,
            "critical_assets": critical_score,
            "business_services": service_score,
            "reachable_volume": volume_score,
            "sensitive_data": sensitivity_score,
        },
    }


def score_incident(incident_id, graph=None):
    """Scores a single incident by id, updates its risk_score in the DB,
    and returns the full report (incident + blast radius + risk score)."""
    conn = get_connection()
    row = conn.execute(
        """SELECT i.*, u.privilege_level, u.name AS user_name, u.role, u.department
           FROM INCIDENTS i JOIN USERS u ON i.entity_id = u.id
           WHERE i.id = ?""", (incident_id,)
    ).fetchone()

    if not row:
        conn.close()
        raise ValueError(f"No incident found with id {incident_id}")

    incident = dict(row)
    blast_report = calculate_blast_radius(incident["entity_id"], graph=graph)
    risk = calculate_risk_score(
        incident["incident_type"], incident["risk_level"], incident["privilege_level"], blast_report
    )

    conn.execute(
        "UPDATE INCIDENTS SET risk_score = ?, risk_level = ? WHERE id = ?",
        (risk["score"], risk["status"], incident_id),
    )
    conn.commit()
    conn.close()

    return {"incident": incident, "blast_radius": blast_report, "risk": risk}


def prioritize_all_open_incidents():
    """Scores every OPEN incident and returns them sorted highest-risk first.
    This is the ranked list a SOC analyst would triage from."""
    conn = get_connection()
    open_ids = [r["id"] for r in conn.execute("SELECT id FROM INCIDENTS WHERE status = 'OPEN'").fetchall()]
    conn.close()

    graph = build_graph()  # build once, reuse for every incident (faster than rebuilding per call)
    results = [score_incident(iid, graph=graph) for iid in open_ids]
    results.sort(key=lambda r: r["risk"]["score"], reverse=True)
    return results


def print_priority_list(results):
    print(f"{'#':<4}{'Score':<7}{'Status':<10}{'Entity':<20}{'Incident':<28}{'Reachable':<10}")
    print("-" * 85)
    for r in results:
        inc = r["incident"]
        print(f"{inc['id']:<4}{r['risk']['score']:<7}{r['risk']['status']:<10}"
              f"{inc['user_name']:<20}{inc['incident_type']:<28}{r['blast_radius']['reachable_count']:<10}")


if __name__ == "__main__":
    from incident_engine import simulate_incident, clear_incidents

    print("=== Resetting and generating fresh demo incidents ===")
    clear_incidents()
    simulate_incident(privilege_level="admin", incident_type="Impossible Travel Login")
    simulate_incident(privilege_level="elevated", incident_type="Unusual Privilege Change")
    simulate_incident(privilege_level="standard", incident_type="Unexpected Access Pattern")
    simulate_incident(privilege_level="admin", incident_type="Abnormal API Activity")

    print("\n=== Scoring & Prioritizing All Open Incidents ===")
    ranked = prioritize_all_open_incidents()
    print_priority_list(ranked)

    print(f"\n=== Score breakdown for top incident ===")
    top = ranked[0]
    print(f"Entity: {top['incident']['user_name']} | Score: {top['risk']['score']}/100 ({top['risk']['status']})")
    for factor, val in top["risk"]["breakdown"].items():
        print(f"  {factor}: {val}")