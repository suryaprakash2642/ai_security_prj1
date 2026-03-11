"""L8 enumerations."""

from enum import Enum


class EventSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EventSourceLayer(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    L7 = "L7"
    L8 = "L8"  # Internal L8 events (integrity violations, etc.)


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AnomalyType(str, Enum):
    VOLUME = "VOLUME"
    TEMPORAL = "TEMPORAL"
    BEHAVIORAL = "BEHAVIORAL"
    SENSITIVITY_ESCALATION = "SENSITIVITY_ESCALATION"
    BTG_ABUSE = "BTG_ABUSE"
    VALIDATION_BLOCK_SPIKE = "VALIDATION_BLOCK_SPIKE"
    SANITIZATION_SPIKE = "SANITIZATION_SPIKE"
    INTEGRITY_VIOLATION = "INTEGRITY_VIOLATION"
    CROSS_LAYER = "CROSS_LAYER"


class ReportType(str, Enum):
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SECURITY = "weekly_security"
    MONTHLY_COMPLIANCE = "monthly_compliance"
    BTG_JUSTIFICATION = "btg_justification"
    BREACH_INVESTIGATION = "breach_investigation"
