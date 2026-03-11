"""Compliance Report Generator.

Generates structured JSON reports. In production these are rendered to PDF/CSV.

Reports:
  - daily_summary: Total queries, denial rate, BTG activations, top tables
  - weekly_security: Validation blocks, injection attempts, anomaly trends
  - monthly_compliance: Minimum necessary score, role-based access review
  - btg_justification: Full BTG audit for a user/time range
  - breach_investigation: Pipeline replay for a specific time range / user
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

import structlog

from app.models.api import ComplianceReport, TimeRange
from app.models.enums import ReportType
from app.services import audit_store, alert_manager
from app.models.enums import EventSeverity

logger = structlog.get_logger(__name__)


def _minimum_necessary_score(
    events: list[Any],
    total_columns: int = 10,
    total_rows: int = 10000,
) -> dict[str, float]:
    """Compute HIPAA minimum necessary compliance score.

    Score = 0.4 * column_efficiency + 0.3 * row_efficiency + 0.3 * denial_rate
    Lower is better. < 0.3 = excellent, 0.3–0.6 = acceptable, > 0.6 = needs review.
    """
    total_queries = len(events)
    if total_queries == 0:
        return {"score": 0.0, "column_efficiency": 0.0,
                "row_efficiency": 0.0, "denial_rate": 0.0}

    total_cols_requested = sum(
        len(e.payload.get("columns", [])) for e in events
    )
    total_rows_returned = sum(
        e.payload.get("rows_returned", 0) for e in events
    )
    blocked_queries = sum(
        1 for e in events if e.event_type == "VALIDATION_BLOCK"
    )

    col_efficiency = min(total_cols_requested / (total_queries * total_columns), 1.0)
    row_efficiency = min(total_rows_returned / (total_queries * total_rows), 1.0)
    denial_rate = blocked_queries / total_queries

    score = 0.4 * col_efficiency + 0.3 * row_efficiency + 0.3 * denial_rate
    return {
        "score": round(score, 3),
        "column_efficiency": round(col_efficiency, 3),
        "row_efficiency": round(row_efficiency, 3),
        "denial_rate": round(denial_rate, 3),
        "compliance_level": (
            "excellent" if score < 0.3 else
            "acceptable" if score < 0.6 else
            "needs_review"
        ),
    }


def generate(
    report_type: ReportType,
    time_range: TimeRange | None = None,
    filters: dict[str, Any] | None = None,
) -> ComplianceReport:
    """Generate a compliance report. Returns structured JSON data."""
    filters = filters or {}
    from_time = time_range.from_time if time_range else None
    to_time = time_range.to_time if time_range else None

    if report_type == ReportType.DAILY_SUMMARY:
        data = _daily_summary(from_time, to_time)
    elif report_type == ReportType.WEEKLY_SECURITY:
        data = _weekly_security(from_time, to_time)
    elif report_type == ReportType.MONTHLY_COMPLIANCE:
        data = _monthly_compliance(from_time, to_time)
    elif report_type == ReportType.BTG_JUSTIFICATION:
        user_id = filters.get("user_id")
        data = _btg_justification(from_time, to_time, user_id)
    elif report_type == ReportType.BREACH_INVESTIGATION:
        request_id = filters.get("request_id")
        user_id = filters.get("user_id")
        data = _breach_investigation(from_time, to_time, request_id, user_id)
    else:
        data = {"error": f"Unknown report type: {report_type}"}

    report = ComplianceReport(
        report_type=report_type,
        time_range_from=from_time,
        time_range_to=to_time,
        data=data,
    )
    logger.info("report_generated",
                report_type=report_type,
                report_id=report.report_id)
    return report


def _daily_summary(from_time: datetime | None, to_time: datetime | None) -> dict:
    events, total = audit_store.query(from_time=from_time, to_time=to_time, limit=10000)

    user_counts: Counter = Counter(e.user_id for e in events)
    event_type_counts: Counter = Counter(e.event_type for e in events)
    layer_counts: Counter = Counter(e.source_layer for e in events)
    btg_activations = sum(1 for e in events if e.event_type == "BTG_ACTIVATION")
    blocks = sum(1 for e in events if e.event_type == "VALIDATION_BLOCK")
    sanitization = sum(1 for e in events if e.event_type == "SANITIZATION_APPLIED")

    top_tables: Counter = Counter()
    for e in events:
        for tbl in e.payload.get("tables_accessed", []):
            top_tables[tbl] += 1

    open_alerts = alert_manager.get_alerts(status=None, limit=1000)
    alert_counts = Counter(a.severity for a in open_alerts)

    return {
        "total_events": total,
        "unique_users": len(user_counts),
        "top_users": dict(user_counts.most_common(10)),
        "events_by_layer": dict(layer_counts),
        "events_by_type": dict(event_type_counts),
        "btg_activations": btg_activations,
        "validation_blocks": blocks,
        "sanitization_events": sanitization,
        "denial_rate": round(blocks / max(total, 1), 3),
        "top_tables_accessed": dict(top_tables.most_common(10)),
        "anomaly_alerts": {
            "INFO": alert_counts.get(EventSeverity.INFO, 0),
            "WARNING": alert_counts.get(EventSeverity.WARNING, 0),
            "HIGH": alert_counts.get(EventSeverity.HIGH, 0),
            "CRITICAL": alert_counts.get(EventSeverity.CRITICAL, 0),
        },
    }


def _weekly_security(from_time: datetime | None, to_time: datetime | None) -> dict:
    events, total = audit_store.query(from_time=from_time, to_time=to_time, limit=50000)

    blocks_by_type: Counter = Counter()
    for e in events:
        if e.event_type == "VALIDATION_BLOCK":
            for v in e.payload.get("violations", []):
                blocks_by_type[v.get("code", "UNKNOWN")] += 1

    injection_attempts = [
        {"user_id": e.user_id, "timestamp": e.timestamp.isoformat(),
         "risk_score": e.payload.get("risk_score", 0)}
        for e in events if e.event_type == "INJECTION_ATTEMPT"
    ]

    btg_events = [e for e in events if e.event_type in ("BTG_ACTIVATION", "BTG_EXPIRED")]
    circuit_breaker_events = [e for e in events if e.event_type == "CIRCUIT_BREAKER_CHANGE"]

    sanitization_by_column: Counter = Counter()
    for e in events:
        if e.event_type == "SANITIZATION_APPLIED":
            col = e.payload.get("column", "unknown")
            sanitization_by_column[col] += 1

    all_alerts = alert_manager.get_alerts(limit=1000)
    alerts_by_type: Counter = Counter(a.anomaly_type for a in all_alerts)
    alerts_by_severity: Counter = Counter(a.severity for a in all_alerts)

    return {
        "total_events": total,
        "validation_blocks_by_type": dict(blocks_by_type),
        "injection_attempts": len(injection_attempts),
        "injection_details": injection_attempts[:20],
        "btg_activations": len([e for e in btg_events if e.event_type == "BTG_ACTIVATION"]),
        "circuit_breaker_changes": len(circuit_breaker_events),
        "sanitization_by_column": dict(sanitization_by_column.most_common(20)),
        "anomaly_alerts_by_type": {k: v for k, v in alerts_by_type.items()},
        "anomaly_alerts_by_severity": {k: v for k, v in alerts_by_severity.items()},
    }


def _monthly_compliance(from_time: datetime | None, to_time: datetime | None) -> dict:
    events, total = audit_store.query(from_time=from_time, to_time=to_time, limit=100000)

    # Per-role stats
    role_stats: dict[str, dict] = defaultdict(
        lambda: {"queries": 0, "blocks": 0, "btg": 0, "sanitization": 0}
    )
    for e in events:
        role = e.payload.get("role", "unknown")
        role_stats[role]["queries"] += 1
        if e.event_type == "VALIDATION_BLOCK":
            role_stats[role]["blocks"] += 1
        if e.event_type == "BTG_ACTIVATION":
            role_stats[role]["btg"] += 1
        if e.event_type == "SANITIZATION_APPLIED":
            role_stats[role]["sanitization"] += 1

    mn_score = _minimum_necessary_score(events)

    return {
        "total_events": total,
        "minimum_necessary_compliance": mn_score,
        "role_based_access": {
            role: {
                **stats,
                "denial_rate": round(
                    stats["blocks"] / max(stats["queries"], 1), 3
                ),
            }
            for role, stats in role_stats.items()
        },
        "hipaa_requirements_addressed": [
            "§164.312(b) — Audit Controls",
            "§164.312(c) — Integrity Controls",
            "§164.312(d) — Authentication",
            "§164.308(a)(1)(ii)(D) — Information System Activity Review",
            "§164.308(a)(5)(ii)(C) — Login Monitoring",
            "§164.502(b) — Minimum Necessary Standard",
            "§164.308(a)(6)(ii) — Response and Reporting",
            "§164.530(j) — Record Retention",
        ],
    }


def _btg_justification(
    from_time: datetime | None,
    to_time: datetime | None,
    user_id: str | None,
) -> dict:
    events, _ = audit_store.query(
        from_time=from_time,
        to_time=to_time,
        user_id=user_id,
        event_types=["BTG_ACTIVATION", "BTG_EXPIRED", "EXECUTION_COMPLETE"],
        limit=10000,
    )

    activations = []
    for e in events:
        if e.event_type == "BTG_ACTIVATION":
            activations.append({
                "user_id": e.user_id,
                "timestamp": e.timestamp.isoformat(),
                "justification": e.payload.get("justification_text", ""),
                "emergency_type": e.payload.get("emergency_type", ""),
                "expected_duration": e.payload.get("expected_duration", ""),
                "patient_ids": e.payload.get("patient_ids", []),
            })

    executions_during_btg = [
        {
            "timestamp": e.timestamp.isoformat(),
            "user_id": e.user_id,
            "rows_returned": e.payload.get("rows_returned", 0),
            "database": e.payload.get("database", ""),
        }
        for e in events
        if e.event_type == "EXECUTION_COMPLETE" and e.btg_active
    ]

    return {
        "btg_activations": activations,
        "btg_activation_count": len(activations),
        "executions_during_btg": executions_during_btg,
        "total_rows_accessed_during_btg": sum(
            x["rows_returned"] for x in executions_during_btg
        ),
        "review_status": "PENDING_HIPAA_OFFICER_REVIEW",
    }


def _breach_investigation(
    from_time: datetime | None,
    to_time: datetime | None,
    request_id: str | None,
    user_id: str | None,
) -> dict:
    """Full pipeline replay for forensic investigation."""
    if request_id:
        events = audit_store.get_by_request_id(request_id)
    else:
        events, _ = audit_store.query(
            from_time=from_time,
            to_time=to_time,
            user_id=user_id,
            limit=10000,
        )

    timeline = [
        {
            "timestamp": e.timestamp.isoformat(),
            "source_layer": e.source_layer,
            "event_type": e.event_type,
            "event_id": e.event_id,
            "request_id": e.request_id,
            "user_id": e.user_id,
            "severity": e.severity,
            "btg_active": e.btg_active,
            "integrity_verified": e.integrity_verified,
            "payload_summary": {
                k: v for k, v in e.payload.items()
                if k not in ("sql", "prompt", "raw_input")  # Exclude potentially sensitive
            },
        }
        for e in events
    ]

    # Group by request_id for cross-layer correlation
    by_request: dict[str, list] = defaultdict(list)
    for t in timeline:
        by_request[t["request_id"]].append(t)

    return {
        "investigation_scope": {
            "request_id": request_id,
            "user_id": user_id,
            "from_time": from_time.isoformat() if from_time else None,
            "to_time": to_time.isoformat() if to_time else None,
        },
        "total_events": len(timeline),
        "pipeline_chains": len(by_request),
        "timeline": timeline,
        "cross_layer_chains": {
            rid: sorted(evts, key=lambda x: x["timestamp"])
            for rid, evts in list(by_request.items())[:50]  # Cap at 50 chains
        },
    }
