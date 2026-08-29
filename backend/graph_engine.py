"""
IMPACT-X — Phase 4: Cyber Relationship Graph Engine
Builds a directed graph from the RELATIONSHIPS table using NetworkX.

Nodes: Users, Assets (applications/databases/servers/apis/cloud_resources), Business Services
Edges: HAS_ACCESS, CONNECTS_TO, DEPENDS_ON, HOSTS, SUPPORTS, OWNS

This graph is the foundation Phase 6 (Blast Radius Engine) traverses.
"""

import sqlite3
import os
import networkx as nx

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "impact_x.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_graph():
    """Reads all nodes and edges from the database and returns a populated
    networkx.DiGraph (directed graph — access/connections flow one way)."""
    conn = get_connection()
    cursor = conn.cursor()
    graph = nx.DiGraph()

    # --- Add nodes: USERS ---
    for row in cursor.execute("SELECT * FROM USERS"):
        graph.add_node(
            row["id"],
            label=row["name"],
            node_type="user",
            department=row["department"],
            role=row["role"],
            privilege_level=row["privilege_level"],
        )

    # --- Add nodes: ASSETS ---
    for row in cursor.execute("SELECT * FROM ASSETS"):
        graph.add_node(
            row["id"],
            label=row["name"],
            node_type=row["type"],  # application / database / server / api / cloud_resource
            owner_department=row["owner_department"],
            data_sensitivity=row["data_sensitivity"],
        )

    # --- Add nodes: BUSINESS_SERVICES ---
    for row in cursor.execute("SELECT * FROM BUSINESS_SERVICES"):
        graph.add_node(
            row["id"],
            label=row["name"],
            node_type="business_service",
            criticality=row["criticality"],
        )

    # --- Add edges: RELATIONSHIPS ---
    for row in cursor.execute("SELECT * FROM RELATIONSHIPS"):
        graph.add_edge(
            row["from_id"],
            row["to_id"],
            relationship_type=row["relationship_type"],
        )

    conn.close()
    return graph


def get_node_info(graph, node_id):
    """Returns the attribute dict for a single node, or None if not found."""
    if node_id not in graph:
        return None
    return {"id": node_id, **graph.nodes[node_id]}


def get_direct_access(graph, node_id):
    """Returns nodes directly reachable in ONE hop from node_id (its neighbors)."""
    if node_id not in graph:
        return []
    return [
        {"id": target, **graph.nodes[target], "via": graph.edges[node_id, target]["relationship_type"]}
        for target in graph.successors(node_id)
    ]


def get_all_reachable(graph, node_id):
    """Returns ALL nodes reachable from node_id, at any number of hops
    (this is the raw material for blast radius in Phase 6)."""
    if node_id not in graph:
        return []
    reachable_ids = nx.descendants(graph, node_id)  # all nodes reachable via directed edges
    return [{"id": rid, **graph.nodes[rid]} for rid in reachable_ids]


def find_attack_path(graph, source_id, target_id):
    """Returns the shortest path (list of node ids) from source to target,
    or None if no path exists."""
    try:
        return nx.shortest_path(graph, source=source_id, target=target_id)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def graph_summary(graph):
    """Quick stats about the graph — useful for sanity-checking and demo talking points."""
    node_type_counts = {}
    for _, attrs in graph.nodes(data=True):
        t = attrs.get("node_type", "unknown")
        node_type_counts[t] = node_type_counts.get(t, 0) + 1

    return {
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "nodes_by_type": node_type_counts,
    }


if __name__ == "__main__":
    g = build_graph()
    summary = graph_summary(g)

    print("=== IMPACT-X Graph Summary ===")
    print(f"Total nodes: {summary['total_nodes']}")
    print(f"Total edges: {summary['total_edges']}")
    print("Nodes by type:")
    for t, count in summary["nodes_by_type"].items():
        print(f"  {t}: {count}")

    # Demo: pick the first user in the graph and show what they can reach
    first_user = next((n for n, d in g.nodes(data=True) if d.get("node_type") == "user"), None)
    if first_user:
        info = get_node_info(g, first_user)
        print(f"\n=== Sample Traversal: {info['label']} ({first_user}) ===")
        direct = get_direct_access(g, first_user)
        print(f"Direct access ({len(direct)}):")
        for d in direct:
            print(f"  -> {d['label']} ({d['node_type']}) via {d['via']}")

        all_reachable = get_all_reachable(g, first_user)
        print(f"\nTotal reachable (all hops): {len(all_reachable)}")
        reachable_by_type = {}
        for r in all_reachable:
            t = r["node_type"]
            reachable_by_type[t] = reachable_by_type.get(t, 0) + 1
        for t, count in reachable_by_type.items():
            print(f"  {t}: {count}")