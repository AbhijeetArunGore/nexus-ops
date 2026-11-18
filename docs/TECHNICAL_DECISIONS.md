# NEXUS Ops — Technical Decisions & Architecture Rationale

---

## 1. Modular Monolith vs Microservices

### Decision
Implement NEXUS Ops as a **Modular Monolith** using FastAPI and clean service boundaries rather than a distributed microservices architecture.

### Problem Solved
Avoids distributed systems overhead (network latency, distributed transaction coordination, multiple deployment manifests, independent service outages) while keeping ingestion, correlation, severity, and AI layers cleanly decoupled.

### Alternatives Considered
- **Microservices Architecture:** Ingestion Service, Severity Service, Correlation Service, AI Orchestrator Service separated across Docker containers with Kafka message bus.
- **Why Not Selected:** Massive operational complexity, deployment friction, and high latency for a single-node or developer workstation setup without providing measurable scalability benefits for this stage.

---

## 2. Deterministic Severity Engine vs LLM Severity Scoring

### Decision
Compute incident severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) using a **deterministic mathematical policy matrix** based on service criticality, error velocity, cascading depth, and customer impact.

### Problem Solved
Eliminates hallucinated, non-reproducible, and unpredictable severity classifications. Prevents prompt-injection attacks from downgrading an outage severity.

### Alternatives Considered
- **Direct LLM Prompting:** "Given these logs, return severity: CRITICAL, HIGH, MEDIUM, LOW."
- **Why Not Selected:** Non-deterministic, sensitive to phrasing, vulnerable to prompt injection, high latency (1-3s vs <1ms), and violates fintech SRE compliance audit standards.

---

## 3. Direct Gemini SDK / REST vs Heavy Agent Frameworks (LangChain / LangGraph)

### Decision
Use direct HTTP/REST and Google GenAI SDK integration with strict Pydantic v2 schemas and an offline deterministic fallback provider.

### Problem Solved
Eliminates dependency bloat, reduces inference latency, avoids hidden prompt injection vectors, and provides 100% reliable execution in offline or rate-limited environments.

### Alternatives Considered
- **LangChain / LangGraph:** Multi-agent autonomous debate frameworks.
- **Why Not Selected:** Adds 40+ heavyweight dependencies, introduces unpredictable agent loops, high token consumption, and debugging difficulty without solving any core domain problem that direct structured JSON output does not solve better.

---

## 4. NetworkX for Service DAG vs Graph Database (Neo4j)

### Decision
Model payment service dependencies and calculate blast radius using an in-memory directed graph with **NetworkX**.

### Problem Solved
Allows microsecond-level topological sorting and downstream caller traversal (`nx.descendants`) without requiring an external JVM-based database server.

### Alternatives Considered
- **Neo4j / Amazon Neptune:** Dedicated graph database.
- **Why Not Selected:** Requires running and maintaining a multi-gigabyte external daemon; unnecessary when the service architecture consists of 10-50 nodes with static dependency edges.

---

## 5. Dual Dialect SQLAlchemy (SQLite & PostgreSQL)

### Decision
Configure database models using SQLAlchemy ORM to support both SQLite (`sqlite:///./nexus_ops.db`) for instant local development and PostgreSQL in Docker.

### Problem Solved
Enables any developer or interviewer to clone the repository and run backend tests in 2 seconds with zero database setup, while offering full PostgreSQL production compatibility.
