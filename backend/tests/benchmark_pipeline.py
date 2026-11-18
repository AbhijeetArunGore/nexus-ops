"""
NEXUS Ops Performance & Scalability Benchmark
Measures parsing, redaction, fingerprinting, and severity evaluation throughput
across progressive log scales: 100 lines, 1,000 lines, and 10,000 lines.
"""
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.normalizer import normalize_log_stream
from app.services.fingerprinting import cluster_error_patterns
from app.services.severity_engine import evaluate_severity
from app.services.correlation import correlate_events


def generate_synthetic_logs(count: int) -> str:
    """Generates synthetic multi-service payment logs for benchmarking."""
    lines = []
    services = ["payment-api", "payment-orchestrator", "bank-connector", "order-db", "webhook-dispatcher"]
    for i in range(1, count + 1):
        svc = services[i % len(services)]
        status = 200 if i % 10 != 0 else (504 if i % 20 == 0 else 500)
        lvl = "INFO" if status == 200 else "ERROR"
        line = (
            f"2026-11-18T10:{(i//60)%60:02d}:{(i%60):02d}.000Z [{svc}] {lvl} "
            f"Request processed txn_id=SYN-TXN-{i:06d} http_status={status} "
            f"User 4111222233334444 with cvv: 123 bearer token=eyJhbGciOiJIUzI1Ni.sec{i} "
            f"duration_ms={15.5 + (i % 200)}"
        )
        lines.append(line)
    return "\n".join(lines)


def run_benchmark():
    print("=" * 65)
    print("  NEXUS Ops Deterministic Pipeline Throughput Benchmark")
    print("=" * 65)

    scales = [100, 1000, 10000]
    results = []

    for count in scales:
        print(f"\n[Benchmarking {count:,} Log Lines]...")
        raw_logs = generate_synthetic_logs(count)
        payload_bytes = len(raw_logs.encode("utf-8"))

        start_time = time.perf_counter()

        # Step 1: Normalization & Redaction
        t0 = time.perf_counter()
        events = normalize_log_stream(raw_logs)
        t_norm = time.perf_counter() - t0

        # Step 2: Fingerprinting
        t0 = time.perf_counter()
        patterns = cluster_error_patterns(events)
        t_fp = time.perf_counter() - t0

        # Step 3: Correlation
        t0 = time.perf_counter()
        correlated = correlate_events(events)
        t_corr = time.perf_counter() - t0

        # Step 4: Severity Decision
        t0 = time.perf_counter()
        severity = evaluate_severity(events, patterns, correlated)
        t_sev = time.perf_counter() - t0

        total_time = time.perf_counter() - start_time
        throughput = count / total_time

        print(f"  -> Total Time: {total_time * 1000:.2f} ms ({throughput:,.1f} lines/sec)")
        print(f"     - Normalization & Redaction: {t_norm * 1000:.2f} ms")
        print(f"     - Token Fingerprinting:      {t_fp * 1000:.2f} ms")
        print(f"     - Alert Correlation:         {t_corr * 1000:.2f} ms")
        print(f"     - Deterministic Severity:    {t_sev * 1000:.2f} ms")
        print(f"  -> Evaluated Severity: {severity.severity} (Score: {severity.score})")

        results.append({
            "lines": count,
            "bytes": payload_bytes,
            "time_ms": total_time * 1000,
            "throughput_lines_sec": throughput,
            "severity": severity.severity
        })

    return results


if __name__ == "__main__":
    run_benchmark()
