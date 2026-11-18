"""
Error Fingerprinting Engine (Module 4)
Strips transient variables (UUIDs, transaction IDs, IPs, numbers, hashes) to produce
normalized error pattern templates and SHA-256 fingerprint hashes.
"""
import re
import hashlib
from typing import List, Dict, Any
from datetime import datetime

# Patterns for token normalization
UUID_REGEX = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')
HEX_REGEX = re.compile(r'\b0x[0-9a-fA-F]+\b')
TXN_REGEX = re.compile(r'\b(?:SYN-)?TXN-[A-Za-z0-9\-_]+\b|\b(?:SYN-)?ORD-[A-Za-z0-9\-_]+\b')
IP_REGEX = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?\b')
TIMESTAMP_REGEX = re.compile(r'\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b')
DIGIT_REGEX = re.compile(r'\b\d+\b')


def extract_template(message: str) -> str:
    """
    Normalizes a message string into a canonical pattern template.
    """
    tmpl = message
    tmpl = TIMESTAMP_REGEX.sub("<TIMESTAMP>", tmpl)
    tmpl = UUID_REGEX.sub("<UUID>", tmpl)
    tmpl = TXN_REGEX.sub("<TXN_ID>", tmpl)
    tmpl = IP_REGEX.sub("<IP_ADDR>", tmpl)
    tmpl = HEX_REGEX.sub("<HEX>", tmpl)
    tmpl = DIGIT_REGEX.sub("<NUM>", tmpl)
    return tmpl.strip()


def compute_fingerprint(service: str, template: str) -> str:
    """
    Computes a deterministic SHA-256 hash for a service + template combination.
    """
    key = f"{service.lower()}:{template}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def cluster_error_patterns(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clusters events (primarily WARN, ERROR, CRITICAL) into normalized error patterns.
    """
    clusters: Dict[str, Dict[str, Any]] = {}

    for evt in events:
        level = evt.get("log_level", "INFO")
        # Include warning/error level events or any event with an explicit error_type
        if level in ["WARN", "ERROR", "CRITICAL"] or evt.get("error_type"):
            service = evt.get("service", "unknown-service")
            msg = evt.get("message", "")
            tmpl = extract_template(msg)
            fp = compute_fingerprint(service, tmpl)
            evt["fingerprint"] = fp  # attach fingerprint to event

            ts = evt.get("timestamp")

            if fp not in clusters:
                clusters[fp] = {
                    "fingerprint": fp,
                    "service": service,
                    "error_type": evt.get("error_type") or "ApplicationError",
                    "pattern_template": tmpl,
                    "occurrence_count": 1,
                    "first_seen": ts,
                    "last_seen": ts,
                    "sample_event_ids": [evt["event_id"]]
                }
            else:
                cluster = clusters[fp]
                cluster["occurrence_count"] += 1
                if ts:
                    if not cluster["first_seen"] or ts < cluster["first_seen"]:
                        cluster["first_seen"] = ts
                    if not cluster["last_seen"] or ts > cluster["last_seen"]:
                        cluster["last_seen"] = ts
                if len(cluster["sample_event_ids"]) < 5 and evt["event_id"] not in cluster["sample_event_ids"]:
                    cluster["sample_event_ids"].append(evt["event_id"])

    return list(clusters.values())
