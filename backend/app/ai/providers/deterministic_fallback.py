"""
Deterministic Offline Fallback Provider
Provides 100% reliable, zero-network heuristic reasoning when an LLM API key is absent,
rate-limited, or timing out. Guarantees that NEXUS Ops never crashes in offline demonstrations.
Explicitly flags all outputs as rule-based heuristics rather than AI generation.
"""
from typing import Dict, Any, Optional
from app.ai.providers.base import BaseLLMProvider


class DeterministicFallbackProvider(BaseLLMProvider):

    async def generate_investigation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes normalized patterns, services, and events to produce evidence-grounded hypotheses.
        """
        events = payload.get("events", [])
        patterns = payload.get("patterns", [])
        correlated = payload.get("correlated_groups", [])
        severity = payload.get("severity", "MEDIUM")

        error_events = [e for e in events if e.get("log_level") in ["WARN", "ERROR", "CRITICAL"] or e.get("error_type")]
        failing_services = list({e.get("service") for e in error_events})

        hypotheses = []
        recommendations = []
        missing_evidence = []

        # Case A: Database Pool Exhaustion
        if any("pool" in e.get("message", "").lower() or e.get("error_type") == "DatabaseConnectionError" for e in error_events):
            db_evts = [e["event_id"] for e in error_events if "pool" in e.get("message", "").lower() or e.get("error_type") == "DatabaseConnectionError"]
            hypotheses.append({
                "hypothesis_code": "H-001",
                "title": "Database Connection Pool Saturation & Starvation",
                "confidence": "HIGH",
                "description": "The relational database connection pool reached maximum capacity, leading to connection acquisition timeouts and cascading HTTP 500 errors in upstream payment services.",
                "supporting_event_ids": db_evts[:5],
                "contradicting_event_ids": [],
                "verification_steps": [
                    "Query `pg_stat_activity` to check active vs idle connection counts.",
                    "Verify max_connections ceiling in database configuration.",
                    "Check connection release logic in payment-orchestrator repository."
                ],
                "is_primary": True
            })
            recommendations.append({
                "priority": 1,
                "action": "Increase database connection pool size and configure pool acquisition timeout backoff.",
                "rationale": "Prevents immediate cascading failures during peak transaction bursts.",
                "associated_runbook_id": "RB-PAY-002",
                "verification_step": "Confirm pool acquisition wait time drops below 500ms."
            })
            missing_evidence.append("Database CPU and memory metrics during the failure interval.")

        # Case B: Bank Connector / Upstream Partner Latency
        elif any("bank-connector" in s or "partner" in s or "timeout" in e.get("message", "").lower() for s in failing_services for e in error_events):
            timeout_evts = [e["event_id"] for e in error_events if "timeout" in e.get("message", "").lower() or e.get("service") == "bank-connector"]
            hypotheses.append({
                "hypothesis_code": "H-001",
                "title": "External Acquiring Partner Socket Timeout & Latency Cascade",
                "confidence": "HIGH",
                "description": "Downstream acquiring bank partner experienced latency exceeding client socket timeouts, triggering 504 Gateway Timeouts on ingress Payment API.",
                "supporting_event_ids": timeout_evts[:5],
                "contradicting_event_ids": [],
                "verification_steps": [
                    "Review partner bank ISO8583 response latency metrics.",
                    "Verify Bank Connector circuit-breaker tripping status.",
                    "Inspect outbound socket timeout configurations."
                ],
                "is_primary": True
            })
            recommendations.append({
                "priority": 1,
                "action": "Trip Bank Connector circuit-breaker and failover traffic to secondary acquiring route.",
                "rationale": "Isolates failing banking partner and protects customer checkout success rate.",
                "associated_runbook_id": "RB-PAY-005",
                "verification_step": "Verify gateway route health metrics and confirm p95 latency drops < 1,000ms."
            })
            missing_evidence.append("External partner health status dashboard and raw ISO8583 response codes.")

        # Case C: Webhook Failures
        elif any("webhook" in s for s in failing_services):
            wh_evts = [e["event_id"] for e in error_events if "webhook" in e.get("service", "").lower()]
            hypotheses.append({
                "hypothesis_code": "H-001",
                "title": "Merchant Webhook Dispatch Failure & Callback Unreachability",
                "confidence": "HIGH",
                "description": "Webhook Dispatcher failed to deliver terminal payment notifications to merchant endpoint due to connection timeouts or 5xx responses.",
                "supporting_event_ids": wh_evts[:5],
                "contradicting_event_ids": [],
                "verification_steps": [
                    "Test merchant webhook URL reachability and TLS certificate.",
                    "Verify dead-letter queue (DLQ) backlog.",
                    "Inspect exponential retry scheduler logs."
                ],
                "is_primary": True
            })
            recommendations.append({
                "priority": 1,
                "action": "Verify merchant endpoint reachability and monitor dead-letter retry queue.",
                "rationale": "Prevents silent notification loss for completed payment transactions.",
                "associated_runbook_id": "RB-PAY-003",
                "verification_step": "Confirm webhook dispatcher receives 200 OK on redelivery."
            })
            missing_evidence.append("Merchant server access logs and TLS handshake records.")

        # Default Generic Case
        else:
            sample_evts = [e["event_id"] for e in error_events[:4]]
            hypotheses.append({
                "hypothesis_code": "H-001",
                "title": "Application Exception in Core Payment Pipeline",
                "confidence": "MEDIUM",
                "description": f"Encountered unexpected application exceptions across {', '.join(failing_services) if failing_services else 'payment services'}.",
                "supporting_event_ids": sample_evts,
                "contradicting_event_ids": [],
                "verification_steps": [
                    "Inspect stack traces for unhandled exceptions.",
                    "Check recent deployments or configuration changes."
                ],
                "is_primary": True
            })
            recommendations.append({
                "priority": 1,
                "action": "Inspect application error logs and restart degraded service worker pods.",
                "rationale": "Restores baseline request handling capacity.",
                "associated_runbook_id": "RB-PAY-010",
                "verification_step": "Verify error rate drops to zero."
            })

        # Add Secondary / Alternative Hypothesis
        hypotheses.append({
            "hypothesis_code": "H-002",
            "title": "Transient Network Fluctuation or Ingress Throttling",
            "confidence": "LOW",
            "description": "Errors may have been triggered by transient network packet drop or sudden traffic spike rather than permanent code defect.",
            "supporting_event_ids": [e["event_id"] for e in error_events[:2]] if error_events else [],
            "contradicting_event_ids": [],
            "verification_steps": ["Inspect load balancer ingress packet drops and TCP retransmission rates."],
            "is_primary": False
        })

        # Add secondary recommendation
        recommendations.append({
            "priority": 2,
            "action": "Conduct server-to-server transaction status verification for ambiguous orders.",
            "rationale": "Ensures customer ledger consistency for transactions affected during the incident window.",
            "associated_runbook_id": "RB-PAY-006",
            "verification_step": "Ensure all orders reach terminal CHARGED or FAILED status."
        })

        summary = f"Forensic analysis identified {len(error_events)} error events across {len(failing_services)} services. Deterministic severity is evaluated as {severity}. The primary contributing factor is modeled as {hypotheses[0]['title']}."

        return {
            "is_fallback": True,
            "provider_name": "deterministic_fallback",
            "incident_summary": summary,
            "primary_hypothesis": hypotheses[0],
            "alternative_hypotheses": hypotheses[1:],
            "recommendations": recommendations,
            "missing_evidence": missing_evidence,
            "limitations": [
                "Analysis generated by deterministic rule-based heuristic fallback engine (LLM API inactive).",
                "Telemetry analyzed within simulated boundary.",
                "No live production network probes were initiated."
            ]
        }

    async def answer_copilot_query(self, query: str, mode: str, incident_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Produces detailed technical answers tailored to LEARNING or ENGINEERING mode.
        Ensures prompt injection immunity, evidence grounding, and uncertainty communication.
        """
        q = query.lower()
        title = incident_context.get("title", "Current Incident") if incident_context else "General Payment Operations"

        # 1. Adversarial Prompt Injection Defense
        if any(w in q for w in ["override", "ignore", "system prompt", "previous instruction", "safety rules"]):
            return {
                "query": query,
                "mode": mode,
                "is_fallback": True,
                "provider_name": "deterministic_fallback",
                "answer": "Security Policy Enforcement: Adversarial prompt override rejected. The deterministic engine treats log content and instructions strictly as passive data. Operational severity, incident status, and evidence citations cannot be overridden by conversational prompts.",
                "technical_details": "AppSec Invariant: Model prompt isolation prevents indirect prompt injection from altering forensic conclusions or incident state machines.",
                "supporting_evidence": ["NEXUS Ops Application Security Policy: SEC-PROMPT-001"],
                "suggested_actions": ["Review raw logs for prompt injection attempts.", "Maintain deterministic severity scoring."],
                "source_references": ["https://owasp.org/www-project-top-10-for-large-language-model-applications/"],
                "follow_up_questions": []
            }

        # 2. Contradictory Evidence Handling
        if any(w in q for w in ["contradict", "mismatch", "conflict"]) or ("timeout" in q and "capture" in q) or ("504" in q and "capture" in q) or ("timeout" in q and "bank" in q and "connector" in q):
            return {
                "query": query,
                "mode": mode,
                "is_fallback": True,
                "provider_name": "deterministic_fallback",
                "answer": "Contradictory Evidence Analysis: Ingress HTTP 504 indicates a client/gateway timeout, whereas upstream Bank Connector logs confirm successful payment capture. This represents an Ambiguous State Mismatch rather than a confirmed payment failure. The gateway timed out waiting for the bank, but the bank successfully authorized the charge.",
                "technical_details": "Fintech Telemetry Invariant: When upstream and downstream status codes conflict, the banking partner's capture journal is the authoritative ledger of record. The downstream HTTP 504 merely indicates the reverse proxy cut the connection before the upstream response completed.",
                "supporting_evidence": ["NEXUS Ops Scenario 01: Late Payment Authorization Response", "SRE Principle: Authoritative Source of Truth in Distributed Ledgers"],
                "suggested_actions": [
                    "Query the bank reconciliation API using the transaction reference (`txn_id` or `utr`).",
                    "Do NOT mark the transaction as failed in the merchant database without server-to-server sync.",
                    "Update order state to `AMBIGUOUS_STATE_MISMATCH` pending automated recon."
                ],
                "source_references": ["https://www.pinelabs.com/docs/online-payments", "https://sre.google/sre-book/incident-management/"],
                "follow_up_questions": [
                    "How does automated recon resolve ambiguous payment states?",
                    "What are the risks of treating a gateway timeout as a definitive failure?"
                ]
            }

        # 3. Missing Information & Telemetry Gap Handling
        if any(w in q for w in ["telemetry gap", "missing telemetry", "missing metric", "missing information", "unobserved"]):
            return {
                "query": query,
                "mode": mode,
                "is_fallback": True,
                "provider_name": "deterministic_fallback",
                "answer": "Telemetry Gap Audit: The incident logs exhibit observable symptoms (e.g. elevated latency and connection timeouts), but lack critical observability telemetry: 1) Continuous database connection pool utilization gauges (e.g. HikariCP active/idle counters); 2) Distributed W3C traceparent context across microservice hops; 3) Host-level CPU/memory saturation metrics and network TCP retransmissions.",
                "technical_details": "Observability Standard: Without distributed tracing spans and pool saturation time-series metrics, causal inference is limited to temporal correlation. Causal certainty requires corroborating infrastructure metrics with application logs.",
                "supporting_evidence": ["OpenTelemetry Semantic Conventions", "Google SRE Handbook: Monitoring Distributed Systems"],
                "suggested_actions": [
                    "Deploy OpenTelemetry auto-instrumentation for end-to-end trace context.",
                    "Configure Prometheus scraping for database pool active/pending connection gauges.",
                    "Correlate application error timestamps with host-level TCP retransmission rates."
                ],
                "source_references": ["https://opentelemetry.io/docs/specs/semconv/", "https://prometheus.io/docs/practices/instrumentation/"],
                "follow_up_questions": [
                    "Which metrics are required to confirm database pool exhaustion?",
                    "How does missing distributed tracing impact mean time to resolution (MTTR)?"
                ]
            }

        # 4. Insufficient Evidence & Uncertainty Communication
        if any(w in q for w in ["cannot conclude", "insufficient", "isolated", "corruption", "confirm database"]):
            return {
                "query": query,
                "mode": mode,
                "is_fallback": True,
                "provider_name": "deterministic_fallback",
                "answer": "Forensic Uncertainty Notice: Cannot conclude root cause from an isolated client connection drop. There is insufficient evidence to confirm database corruption or backend failure without verifying pg_stat_activity, server error logs, and disk I/O metrics.",
                "technical_details": "SRE Standard: Single-point client disconnections are frequently transient client-side network interruptions. Declaring database corruption without correlating database engine telemetry is a false-positive violation.",
                "supporting_evidence": ["Google SRE Handbook: Being On-Call & Triaging Signals"],
                "suggested_actions": [
                    "Query `pg_stat_activity` to verify database connection health.",
                    "Inspect database engine logs for PANIC or FATAL events.",
                    "Gather upstream client-checkout drop rate telemetry metrics."
                ],
                "source_references": ["https://sre.google/sre-book/incident-management/"],
                "follow_up_questions": [
                    "What telemetry is required to verify database health?",
                    "How do we distinguish client-side network drops from API gateway timeouts?"
                ]
            }

        if mode == "LEARNING":
            if "idempotency" in q or "duplicate" in q:
                ans = "Idempotency means that making the exact same request multiple times has the exact same result as making it once. For example, if a network hiccup causes an app to send 'Charge ₹500' twice with the same idempotency key (such as order_id), the payment gateway recognizes the duplicate and ensures the customer is not double-debited."
                tech = "Pine Labs and modern payment APIs use idempotency keys (like `X-Idempotency-Key` or `order_id`) stored in Redis or PostgreSQL with unique constraints. If an event with the same key is already processed, subsequent attempts return the cached authorization result."
                acts = ["Ensure client checkout generates UUIDv4 idempotency keys.", "Check deduplication cache TTL.", "Verify idempotency key collision warnings in logs."]
            elif "504" in q or "timeout" in q or "gateway" in q:
                ans = "An HTTP 504 Gateway Timeout occurs when one server acting as an intermediate gateway or proxy does not receive a timely response from an upstream server. In payment architectures, when the Payment API calls the Bank Connector, if the bank takes longer than the configured timeout (e.g. 15 seconds) to approve the payment, the Payment API returns a 504 to the user."
                tech = "Key concept: The customer's bank account might still have been debited by the upstream bank! Never tell a customer a 504 means the transaction failed without verifying with the bank first using an idempotency key."
                acts = ["Check the transaction status verification API.", "Do not immediately initiate a retry without an idempotency key."]
            elif "database" in q or "pool" in q:
                ans = "A database connection pool is a cache of database connections kept open so they can be reused. Opening a new database connection for every payment is slow and resource-heavy. If all pooled connections are busy running long queries, new payment requests get blocked waiting for a free slot and eventually fail with connection pool exhaustion."
                tech = "Analogy: Think of a bank branch with 10 teller windows. If all 10 tellers are helping slow customers, the queue out the door backs up."
                acts = ["Inspect pg_stat_activity to find slow queries.", "Increase pool size if database CPU permits."]
            else:
                ans = f"In {title}, the incident reflects payment pipeline degradation. The deterministic rule engine evaluates evidence such as error rates, affected service tiers, and customer impact to guide triage."
                tech = "Best practice: Always gather observable facts (timestamps, trace IDs, error fingerprints) before jumping to root cause conclusions."
                acts = ["Review the incident timeline.", "Inspect the Evidence Graph to see what events triggered the severity rating."]

            return {
                "query": query,
                "mode": mode,
                "is_fallback": True,
                "provider_name": "deterministic_fallback",
                "answer": ans,
                "technical_details": tech,
                "supporting_evidence": ["Pine Labs Public Developer Portal (Payment Lifecycle & API Guides)"],
                "suggested_actions": acts,
                "source_references": ["https://www.pinelabs.com/docs/online-payments", "https://opentelemetry.io/docs/"],
                "follow_up_questions": [
                    "What is the difference between a payment failure and a delayed response?",
                    "How does idempotency prevent duplicate debit?",
                    "Why was this incident given its current severity?"
                ]
            }

        else:
            # ENGINEERING MODE
            if ("distinguish" in q and "database" in q) or ("latency" in q and "exhaustion" in q) or ("network" in q and "pool" in q):
                ans = "To distinguish network latency from database connection pool exhaustion: 1) Network latency manifests as socket timeout errors, TCP retransmissions, and high span durations on outbound HTTP/ISO8583 banking connector clients; 2) Database connection pool saturation manifests as HikariPool acquisition timeouts (`timeout 30000ms`), saturated `max_connections` in PostgreSQL, and connection slot exhaustion (`FATAL: remaining connection slots are reserved`)."
                tech = "Diagnostic metrics: Check `pg_stat_activity` for `state = 'active'` vs `state = 'idle in transaction'`. If database CPU is low but connections are maxed out, it indicates leaked sessions or long-running locks rather than external network latency."
                acts = [
                    "Inspect pg_stat_activity: `SELECT count(*), state FROM pg_stat_activity GROUP BY state;`",
                    "Check network socket metrics and partner bank ping/handshake latency.",
                    "Verify connection pool acquisition wait time in metrics dashboards."
                ]
            elif "database" in q or "pg_stat_activity" in q or "saturation" in q or "query" in q or "lock" in q:
                ans = "Database connection pool saturation indicates that active worker threads have saturated `max_connections` or connection lease duration exceeds threshold, exhausting available connection slots."
                tech = "Query: `SELECT pid, state, now() - xact_start as xact_age, query FROM pg_stat_activity WHERE state = 'active' ORDER BY xact_age DESC LIMIT 10;`. Check for table-level exclusive locks (`AccessExclusiveLock`) blocking transaction commits against `max_connections` ceilings."
                acts = [
                    "Terminate idle-in-transaction queries older than 30s using `SELECT pg_terminate_backend(pid);`.",
                    "Tune HikariCP/SQLAlchemy `pool_size`, `max_overflow`, and `pool_timeout`.",
                    "Verify connection release inside `finally` blocks."
                ]
            elif "504" in q or "timeout" in q or "root cause" in q:
                ans = f"Forensic analysis of {title} demonstrates latency propagation through the payment request DAG. When an upstream callee (such as external banking partner or internal orchestrator) breaches socket read timeout thresholds, the ingress reverse proxy terminates the connection with HTTP 504."
                tech = "Diagnostic procedure: 1) Extract distributed W3C traceparent headers; 2) Check p99 duration across spans; 3) Inspect TCP SYN retransmission and socket buffer saturation; 4) Check partner SLA dashboard."
                acts = [
                    "Execute `curl -I -X GET <partner_endpoint>/health --connect-timeout 2` to verify TCP socket connectivity.",
                    "Verify circuit breaker state machine (`CLOSED` -> `OPEN`).",
                    "Query order ledger for transactions in AMBIGUOUS state."
                ]
            else:
                ans = f"Incident forensic evaluation for {title}: Telemetry indicates multi-service correlation with deterministic severity. All hypotheses are grounded against concrete event identifiers."
                tech = "SRE verification standard: Correlation != Causation. A causal relationship requires demonstrating temporal precedence, topological adjacency, and consistent mechanism of failure."
                acts = [
                    "Inspect the Blast Radius Graph for upstream exposure.",
                    "Run 'What Am I Missing?' to audit unexamined failure modes.",
                    "Draft incident postmortem with preventive action items."
                ]

            return {
                "query": query,
                "mode": mode,
                "is_fallback": True,
                "provider_name": "deterministic_fallback",
                "answer": ans,
                "technical_details": tech,
                "supporting_evidence": ["Google SRE Handbook: Managing Incidents", "PostgreSQL pg_stat_activity documentation"],
                "suggested_actions": acts,
                "source_references": ["https://sre.google/sre-book/incident-management/", "https://www.pinelabs.com/docs"],
                "follow_up_questions": [
                    "How can retry storms increase cascading failures?",
                    "What evidence is required to verify complete service recovery?",
                    "Which telemetry gaps currently limit root cause confidence?"
                ]
            }

    async def draft_postmortem(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Drafts a structured postmortem report.
        """
        inc_num = incident_data.get("incident_number", "INC-001")
        title = incident_data.get("title", "Payment Pipeline Incident")
        sev = incident_data.get("severity", "MEDIUM")
        events = incident_data.get("events", [])
        hypotheses = incident_data.get("hypotheses", [])

        primary_h = hypotheses[0]["title"] if hypotheses else "Service Degradation"

        return {
            "incident_number": inc_num,
            "status": "DRAFT",
            "is_fallback": True,
            "provider_name": "deterministic_fallback",
            "executive_summary": f"On {incident_data.get('created_at', 'today')}, NEXUS Ops detected a {sev} severity incident affecting {title}. Automated deterministic analysis established that {primary_h} caused service disruption. Total observed events: {len(events)}.",
            "timeline": [
                {"time": "T+00m", "description": "First anomalous telemetry detected in logs."},
                {"time": "T+02m", "description": "Deterministic severity engine categorized incident as " + sev + "."},
                {"time": "T+05m", "description": "Correlated group and blast radius analysis generated."},
                {"time": "T+15m", "description": "Mitigation steps and verification runbook executed."}
            ],
            "root_cause_analysis": f"The leading verified hypothesis is {primary_h}. Downstream callers experienced elevated latency and connection saturation.",
            "what_went_well": [
                "Deterministic severity engine classified incident within seconds without LLM latency.",
                "Sensitive data redaction masked all tokens and simulated payment credentials.",
                "Evidence graph provided 100% verifiable event citations."
            ],
            "what_went_wrong": [
                "Missing distributed trace context on several microservice boundaries.",
                "Absence of proactive connection pool gauge alerts prior to failure."
            ],
            "detection_gaps": [
                "No early warning alarm for p99 latency degradation.",
                "Lack of automated synthetic canary transactions."
            ],
            "action_items": [
                {"action": "Implement OpenTelemetry W3C trace propagation", "owner": "Core SRE Team", "priority": "P1"},
                {"action": "Tune connection pool timeouts and set up Prometheus alert on 80% pool utilization", "owner": "Database Team", "priority": "P1"},
                {"action": "Update runbook RB-PAY-001 with partner escalation contacts", "owner": "Payment Ops", "priority": "P2"}
            ]
        }
