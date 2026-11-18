"""
Evidence Graph Engine (Module 11)
Constructs a verifiable bipartite knowledge graph connecting:
Log Events -> Error Patterns -> Service Entities -> Hypotheses -> Recommendations
Enforces strict reference validation: rejects non-existent event ID citations.
"""
from typing import List, Dict, Any, Set
from app.schemas.incident import EvidenceGraphResponse, EvidenceGraphNode, EvidenceGraphEdge


def build_evidence_graph(
    incident_id: str,
    events: List[Dict[str, Any]],
    patterns: List[Dict[str, Any]],
    hypotheses: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]],
    severity_reasons: List[Any]
) -> EvidenceGraphResponse:
    """
    Assembles graph nodes and directed evidence edges.
    Guarantees that only genuine ingested event IDs are linked.
    """
    nodes: List[EvidenceGraphNode] = []
    edges: List[EvidenceGraphEdge] = []
    seen_node_ids: Set[str] = set()

    # Pre-index valid event IDs to reject hallucinated citations
    valid_event_map = {e.get("event_id"): e for e in events if e.get("event_id")}

    def add_node(node_id: str, label: str, node_type: str, metadata: Dict[str, Any] = None):
        if node_id not in seen_node_ids:
            seen_node_ids.add(node_id)
            nodes.append(EvidenceGraphNode(
                id=node_id,
                label=label,
                type=node_type,
                metadata=metadata or {}
            ))

    # 1. Hypotheses Nodes
    for hyp in hypotheses:
        h_id = hyp.get("hypothesis_code", "H-001")
        is_primary = hyp.get("is_primary", False)
        add_node(h_id, hyp.get("title", "Hypothesis"), "hypothesis", {
            "confidence": hyp.get("confidence", "MEDIUM"),
            "description": hyp.get("description", ""),
            "status": "PRIMARY_HYPOTHESIS" if is_primary else "ALTERNATIVE_HYPOTHESIS",
            "logical_truth": "UNVERIFIED_AI_HYPOTHESIS"  # Clearly marked until engineer review
        })

        # Connect supporting evidence / events ONLY if they truly exist in valid_event_map
        for evt_id in hyp.get("supporting_event_ids", []):
            if evt_id in valid_event_map:
                evt_data = valid_event_map[evt_id]
                add_node(evt_id, f"Event {evt_id}", "event", {
                    "service": evt_data.get("service"),
                    "is_verified_fact": True
                })
                edges.append(EvidenceGraphEdge(
                    source=evt_id,
                    target=h_id,
                    label="SUPPORTS_HYPOTHESIS"
                ))

    # 2. Recommendations Nodes
    for idx, rec in enumerate(recommendations, start=1):
        r_id = f"REC-{idx:02d}"
        add_node(r_id, rec.get("action", f"Action {idx}")[:40] + "...", "recommendation", {
            "priority": rec.get("priority", idx),
            "rationale": rec.get("rationale", ""),
            "runbook": rec.get("associated_runbook_id")
        })
        if hypotheses:
            primary_h = hypotheses[0].get("hypothesis_code", "H-001")
            edges.append(EvidenceGraphEdge(
                source=primary_h,
                target=r_id,
                label="MITIGATES"
            ))

    # 3. Severity Rule Nodes
    for idx, reason in enumerate(severity_reasons, start=1):
        rule_name = getattr(reason, "rule", None) or (reason.get("rule", f"RULE_{idx}") if isinstance(reason, dict) else f"RULE_{idx}")
        rule_node_id = f"RULE-{rule_name}"
        desc = getattr(reason, "description", None) or (reason.get("description", "") if isinstance(reason, dict) else "")
        add_node(rule_node_id, rule_name, "rule", {"description": desc})

        evt_ids = getattr(reason, "supporting_event_ids", None) or (reason.get("supporting_event_ids", []) if isinstance(reason, dict) else [])
        for e_id in evt_ids:
            if e_id in valid_event_map:
                add_node(e_id, f"Event {e_id}", "event", {"is_verified_fact": True})
                edges.append(EvidenceGraphEdge(
                    source=e_id,
                    target=rule_node_id,
                    label="TRIGGERS_POLICY"
                ))

    # 4. Pattern Nodes
    for p in patterns[:5]:
        p_id = f"PAT-{p['fingerprint']}"
        add_node(p_id, f"Pattern ({p['occurrence_count']}x): {p['service']}", "pattern", {
            "service": p["service"],
            "count": p["occurrence_count"],
            "template": p["pattern_template"]
        })
        for sample_id in p.get("sample_event_ids", [])[:3]:
            if sample_id in valid_event_map:
                add_node(sample_id, f"Event {sample_id}", "event", {"is_verified_fact": True})
                edges.append(EvidenceGraphEdge(
                    source=sample_id,
                    target=p_id,
                    label="CLUSTERS_INTO"
                ))

    return EvidenceGraphResponse(
        incident_id=incident_id,
        nodes=nodes,
        edges=edges
    )
