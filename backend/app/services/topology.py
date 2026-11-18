"""
Service Dependency Topology & Blast Radius Engine (Module 8)
Models the synthetic Pine Labs payment architecture as a Directed Acyclic Graph (DAG)
using NetworkX and calculates Observed Impact vs Potential Blast Radius.
Includes cycle detection and resilience against malformed topological graphs.
"""
import networkx as nx
from typing import Dict, List, Set, Any
from app.schemas.incident import BlastRadiusResponse, BlastRadiusNode, BlastRadiusEdge

# Service Criticality Tiers
CRITICALITY_TIERS = {
    "payment-api": "TIER_1",
    "payment-orchestrator": "TIER_1",
    "order-db": "TIER_1",
    "bank-connector": "TIER_1",
    "message-queue": "TIER_2",
    "webhook-dispatcher": "TIER_2",
    "settlement-engine": "TIER_3",
    "customer-checkout": "CLIENT",
    "external-payment-partner": "EXTERNAL_DEPENDENCY",
    "merchant-endpoint": "EXTERNAL_DEPENDENCY",
    "core-banking-network": "EXTERNAL_DEPENDENCY"
}


def build_payment_topology() -> nx.DiGraph:
    """
    Constructs the standard Pine Labs payment lifecycle dependency DAG.
    Edges represent request flow: A -> B means A calls/depends on B.
    """
    G = nx.DiGraph()

    for svc, tier in CRITICALITY_TIERS.items():
        G.add_node(svc, tier=tier)

    dependencies = [
        ("customer-checkout", "payment-api", "HTTP_REST_ORDER"),
        ("payment-api", "payment-orchestrator", "GRPC_DISPATCH"),
        ("payment-orchestrator", "order-db", "POSTGRES_POOL"),
        ("payment-orchestrator", "message-queue", "ASYNC_EVENTS"),
        ("payment-orchestrator", "bank-connector", "INTERNAL_RPC"),
        ("bank-connector", "external-payment-partner", "ISO8583_REST_GATEWAY"),
        ("message-queue", "webhook-dispatcher", "QUEUE_CONSUMER"),
        ("webhook-dispatcher", "merchant-endpoint", "OUTBOUND_WEBHOOK_HTTP"),
        ("message-queue", "settlement-engine", "BATCH_QUEUE_CONSUMER"),
        ("settlement-engine", "core-banking-network", "RECON_UTR_BATCH")
    ]

    for src, dst, rel in dependencies:
        G.add_edge(src, dst, relationship=rel)

    return G


def get_synthetic_topology() -> nx.DiGraph:
    """Alias for build_payment_topology."""
    return build_payment_topology()


def get_service_dependencies(service_name: str) -> List[str]:
    """Returns direct downstream dependencies that service_name calls."""
    G = build_payment_topology()
    if service_name in G:
        return list(G.successors(service_name))
    return []


def compute_blast_radius(incident_id: str, events: List[Dict[str, Any]]) -> BlastRadiusResponse:
    """
    Calculates Observed Impact vs Potential Blast Radius with cycle-safe BFS traversal.
    """
    G = build_payment_topology()

    # 1. Count errors per service
    service_errors: Dict[str, int] = {}
    for evt in events:
        svc = evt.get("service", "unknown-service").lower()
        if evt.get("log_level") in ["WARN", "ERROR", "CRITICAL"] or evt.get("error_type"):
            service_errors[svc] = service_errors.get(svc, 0) + 1

    observed_services: Set[str] = {svc for svc, count in service_errors.items() if count > 0}

    # Ensure all observed services exist in G
    for svc in observed_services:
        if svc not in G:
            G.add_node(svc, tier="DYNAMIC_SERVICE")

    # 2. Cycle-safe traversal on reverse graph to find upstream callers exposed to downstream failure
    reverse_G = G.reverse()
    potential_exposed: Set[str] = set()

    for failed_svc in observed_services:
        if failed_svc in reverse_G:
            # Use bounded BFS to guard against any cyclic graphs
            visited = set()
            queue = [failed_svc]
            while queue:
                curr = queue.pop(0)
                if curr not in visited:
                    visited.add(curr)
                    for neighbor in reverse_G.successors(curr):
                        if neighbor not in observed_services:
                            potential_exposed.add(neighbor)
                        if neighbor not in visited and neighbor not in queue:
                            queue.append(neighbor)

    nodes: List[BlastRadiusNode] = []
    for node in G.nodes():
        if node in observed_services:
            status = "OBSERVED_IMPACT"
        elif node in potential_exposed:
            status = "POTENTIAL_BLAST_RADIUS"
        else:
            status = "NO_ERRORS_OBSERVED"

        nodes.append(BlastRadiusNode(
            service=node,
            status=status,
            depth=1 if status == "OBSERVED_IMPACT" else (2 if status == "POTENTIAL_BLAST_RADIUS" else 0),
            error_count=service_errors.get(node, 0)
        ))

    edges: List[BlastRadiusEdge] = []
    for u, v, data in G.edges(data=True):
        edges.append(BlastRadiusEdge(
            from_service=u,
            to_service=v,
            relationship=data.get("relationship", "DEPENDS_ON")
        ))

    exposed_list = sorted(list(potential_exposed))
    return BlastRadiusResponse(
        incident_id=incident_id,
        observed_services=sorted(list(observed_services)),
        exposed_upstream_services=exposed_list,
        exposed_downstream_services=exposed_list,
        nodes=nodes,
        edges=edges
    )
