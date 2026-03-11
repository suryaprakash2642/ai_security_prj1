"""Apollo Hospitals validation scenarios from the spec (Section 11).

Tests the 6 documented scenarios plus additional coverage.
"""

import pytest
from app.models.enums import GateStatus, ValidationDecision, ViolationCode
from app.services.gate1_structural import run as gate1
from app.services.gate3_behavioral import run as gate3
from app.services.sql_parser import parse_sql


class TestScenario1BillingClinicalColumnLeak:
    """Scenario 1: Billing Staff trying to access clinical_notes."""

    def test_clinical_notes_denied_to_billing(self, billing_envelope):
        sql = "SELECT mrn, clinical_notes FROM claims"
        parsed = parse_sql(sql)
        result = gate1(parsed, billing_envelope)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.UNAUTHORIZED_COLUMN in codes

    def test_billing_columns_allowed(self, billing_envelope):
        sql = "SELECT claim_id, mrn, total_amount FROM claims WHERE service_date > '2024-01-01'"
        parsed = parse_sql(sql)
        result = gate1(parsed, billing_envelope)
        assert result.status == GateStatus.PASS


class TestScenario3CrossDomainJoin:
    """Scenario 3: Cross-domain join attempt (Clinical + HR)."""

    def test_cross_domain_query_has_unauthorized_table(self, physician_envelope):
        sql = """
SELECT p.mrn, p.full_name, e.salary
FROM patients p
JOIN employees e ON p.mrn = e.employee_id
"""
        parsed = parse_sql(sql)
        result = gate1(parsed, physician_envelope)
        # employees is not in physician's envelope
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.UNAUTHORIZED_TABLE in codes


class TestScenario4UnionInjection:
    """Scenario 4: UNION-based SQL injection."""

    def test_union_system_table_blocked(self, physician_envelope):
        sql = "SELECT mrn, full_name FROM patients WHERE unit_id = '3B' UNION SELECT username, password FROM sys.sql_logins"
        parsed = parse_sql(sql)

        g1_result = gate1(parsed, physician_envelope)
        g3_result = gate3(parsed, sql)

        # Gate 1: sys.sql_logins unauthorized
        # Gate 3: UNION exfiltration + system table access
        assert g1_result.status == GateStatus.FAIL or g3_result.status == GateStatus.FAIL
        all_codes = [v.code for v in g1_result.violations + g3_result.violations]
        assert ViolationCode.UNION_EXFILTRATION in all_codes or ViolationCode.UNAUTHORIZED_TABLE in all_codes


class TestScenario5AggregationViolation:
    """Scenario 5: Revenue Cycle Manager — aggregation_only violation."""

    def test_patient_identifiers_in_agg_only_select(self, agg_only_envelope):
        sql = "SELECT mrn, full_name, SUM(total_amount) FROM encounters GROUP BY mrn, full_name"
        parsed = parse_sql(sql)
        result = gate1(parsed, agg_only_envelope)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        # mrn and full_name are HIDDEN in agg_only_envelope
        assert ViolationCode.UNAUTHORIZED_COLUMN in codes or ViolationCode.AGGREGATION_VIOLATION in codes


class TestScenario6MaskingRewrite:
    """Scenario 6: Masking rewrite for nurse accessing patient names."""

    def test_gate1_passes_for_masked_column(self, physician_envelope):
        # full_name is MASKED (not HIDDEN), so Gate 1 allows it
        sql = "SELECT mrn, full_name FROM patients WHERE unit_id = '3B' LIMIT 100"
        parsed = parse_sql(sql)
        result = gate1(parsed, physician_envelope)
        assert result.status == GateStatus.PASS  # Gate 1 passes; Gate 2 flags for rewriter

    def test_rewriter_applies_masking_expression(self, physician_envelope):
        from app.models.api import Violation
        from app.models.enums import ViolationSeverity
        from app.services.query_rewriter import rewrite

        sql = "SELECT mrn, full_name FROM patients WHERE unit_id = '3B' LIMIT 100"
        parsed = parse_sql(sql)
        g2_violations = [Violation(
            gate=2,
            code=ViolationCode.UNMASKED_PII_COLUMN,
            severity=ViolationSeverity.HIGH,
            table="patients",
            column="full_name",
            detail="Masking required",
        )]
        result = rewrite(sql, parsed, physician_envelope, gate2_violations=g2_violations)
        assert result.success
        assert any(r.column == "full_name" for r in result.rewrites)


class TestSSNAlwaysBlocked:
    """SSN is in denied_columns — must NEVER pass Gate 1."""

    def test_ssn_blocked_for_physician(self, physician_envelope):
        sql = "SELECT mrn, ssn FROM patients WHERE unit_id = '3B'"
        parsed = parse_sql(sql)
        result = gate1(parsed, physician_envelope)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.UNAUTHORIZED_COLUMN in codes

    def test_ssn_blocked_for_billing(self, billing_envelope):
        sql = "SELECT mrn, ssn FROM patients"
        parsed = parse_sql(sql)
        result = gate1(parsed, billing_envelope)
        assert result.status == GateStatus.FAIL


class TestFailSecure:
    """Every error path must result in BLOCKED."""

    def test_unparseable_sql_blocked(self, physician_envelope):
        from app.services.sql_parser import ParsedSQL
        bad = ParsedSQL(ast=None, parse_error="Invalid token at position 5")
        result = gate1(bad, physician_envelope)
        assert result.status == GateStatus.FAIL

    def test_write_op_blocked_in_gate3(self):
        for write_sql in [
            "INSERT INTO patients VALUES ('P001')",
            "UPDATE patients SET full_name = 'X'",
            "DELETE FROM patients",
            "DROP TABLE patients",
            "TRUNCATE TABLE patients",
        ]:
            parsed = parse_sql(write_sql)
            result = gate3(parsed, write_sql)
            codes = [v.code for v in result.violations]
            assert ViolationCode.WRITE_OPERATION in codes, f"Write op not detected for: {write_sql}"
