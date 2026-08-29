"""
IMPACT-X — Phase 6: Blast Radius & Attack Path Engine
The core intelligence of IMPACT-X. Takes a compromised identity (from an
incident) and calculates everything it can reach through the graph:
directly accessible assets, indirectly reachable assets, critical assets,
sensitive data, and affected business services.
"""

import os
from graph_engine import build_graph, get_direct_access, get_all_reachable, find_attack_path
from incident_engine import get_connection


def _is_critical_asset(node):
    """An asset counts as 'critical' if it's a database with high sensitivity,
    or a server/cloud_resource hosting one (kept simple for MVP: sensitivity-based)."""
    return node.get("data_sensitivity") == "high"


def calculate_blast_radius(entity_id, graph=None):
    """
    Given a compromised entity_id (usually a user), returns the full
    blast radius report:
      - directly_accessible: 1-hop nodes
      - all_reachable: every node reachable at any depth
      - critical_assets: high-sensitivity databases within reach
      - business_services_affected: business services within reach
      - blast_radius_level: LOW / MEDIUM / HIGH / CRITICAL
    """
    if graph is None:
        graph = build_graph()

    if entity_id not in graph:
        raise ValueError(f"Entity '{entity_id}' not found in graph")

    direct = get_direct_access(graph, entity_id)
    all_reachable = get_all_reachable(graph, entity_id)

    critical_assets = [n for n in all_reachable if _is_critical_asset(n)]
    sensitive_data = [n for n in all_reachable if n.get("data_sensitivity") in ("high", "medium")]
    business_services = [n for n in all_reachable if n.get("node_type") == "business_service"]

    # Attach an example attack path to each affected business service (for the UI)
    services_with_paths = []
    for svc in business_services:
        path = find_attack_path(graph, entity_id, svc["id"])
        services_with_paths.append({**svc, "attack_path": path})

    blast_level = _classify_blast_radius(len(all_reachable), len(critical_assets), len(business_services))

    return {
        "entity_id": entity_id,
        "directly_accessible": direct,
        "direct_count": len(direct),
        "all_reachable": all_reachable,
        "reachable_count": len(all_reachable),
        "critical_assets": critical_assets,
        "critical_count": len(critical_assets),
        "sensitive_data": sensitive_data,
        "sensitive_count": len(sensitive_data),
        "business_services_affected": services_with_paths,
        "business_services_count": len(business_services),
        "blast_radius_level": blast_level,
    }


def _classify_blast_radius(reachable_count, critical_count, service_count):
    """Simple threshold-based classification (Phase 7 will build a numeric
    score on top of this)."""
    if critical_count >= 2 or service_count >= 2 or reachable_count >= 15:
        return "CRITICAL"
    elif critical_count >= 1 or service_count >= 1 or reachable_count >= 8:
        return "HIGH"
    elif reachable_count >= 3:
        return "MEDIUM"
    else:
        return "LOW"


def analyze_incident(incident_id):
    """Looks up an incident by ID and returns its full blast radius report,
    combining the INCIDENTS row with the graph traversal."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM INCIDENTS WHERE id = ?", (incident_id,)).fetchone()
    conn.close()

    if not row:
        raise ValueError(f"No incident found with id {incident_id}")

    incident = dict(row)
    report = calculate_blast_radius(incident["entity_id"])
    return {"incident": incident, "blast_radius": report}


def print_report(report):
    """Pretty-prints a blast radius report for terminal/demo use."""
    print(f"\nENTITY: {report['entity_id']}")
    print(f"BLAST RADIUS: {report['blast_radius_level']}")
    print(f"Reachable Assets: {report['reachable_count']}")
    print(f"Critical Assets: {report['critical_count']}")
    print(f"Sensitive Data: {report['sensitive_count']}")
    print(f"Business Services: {report['business_services_count']}")

    if report["business_services_affected"]:
        print("\nAffected Business Services & Attack Paths:")
        for svc in report["business_services_affected"]:
            path_str = " -> ".join(svc["attack_path"]) if svc["attack_path"] else "N/A"
            print(f"  - {svc['label']} ({svc['criticality']}): {path_str}")


if __name__ == "__main__":
    from incident_engine import simulate_incident

    print("=== Simulating a HIGH-IMPACT incident for demo ===")
    incident = simulate_incident(privilege_level="admin")
    print(f"INCIDENT #{incident['incident_id']}: {incident['incident_type']} — {incident['entity_name']} "
          f"({incident['role']}, {incident['department']}, {incident['privilege_level']})")

    print("\n=== Calculating Blast Radius ===")
    result = analyze_incident(incident["incident_id"])
    print_report(result["blast_radius"])