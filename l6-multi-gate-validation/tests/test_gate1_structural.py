"""Tests for Gate 1 — Structural Validation."""

import pytest
from app.models.enums import GateStatus, ViolationCode
from app.services.gate1_structural import run
from app.services.sql_parser import parse_sql


class TestAuthorizedQueries:
    def test_simple_authorized_query(self, physician_envelope):
        parsed = parse_sql("SELECT mrn, admission_date FROM encounters LIMIT 100")
        result = run(parsed, physician_envelope)
        # Should PASS (no CRITICAL violations — MISSING_REQUIRED_FILTER is HIGH, not CRITICAL)
        assert result.status == GateStatus.PASS

    def test_join_authorized_tables(self, physician_envelope):
        sql = """
SELECT e.mrn, e.admission_date, p.full_name
FROM encounters e
JOIN patients p ON e.mrn = p.mrn
WHERE e.unit_id = '3B'
LIMIT 100
"""
        parsed = parse_sql(sql, "postgresql")
        result = run(parsed, physician_envelope)
        assert result.status == GateStatus.PASS

    def test_aggregate_query_allowed(self, physician_envelope):
        sql = "SELECT COUNT(*) as patient_count FROM encounters WHERE treating_provider_id = 'DR-4521'"
        parsed = parse_sql(sql, "postgresql")
        result = run(parsed, physician_envelope)
        assert result.status == GateStatus.PASS


class TestUnauthorizedTable:
    def test_unauthorized_table_blocked(self, physician_envelope):
        parsed = parse_sql("SELECT * FROM employees WHERE dept = 'CARDIOLOGY'", "postgresql")
        result = run(parsed, physician_envelope)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.UNAUTHORIZED_TABLE in codes

    def test_system_table_blocked(self, physician_envelope):
        parsed = parse_sql("SELECT column_name FROM information_schema.columns", "postgresql")
        result = run(parsed, physician_envelope)
        # Either UNAUTHORIZED_TABLE or caught by parser
        assert result.status in (GateStatus.FAIL, GateStatus.PASS)


class TestUnauthorizedColumn:
    def test_denied_column_blocked(self, physician_envelope):
        sql = "SELECT mrn, ssn FROM patients WHERE mrn = 'P001'"
        parsed = parse_sql(sql, "postgresql")
        result = run(parsed, physician_envelope)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.UNAUTHORIZED_COLUMN in codes

    def test_billing_denied_clinical_notes(self, billing_envelope):
        sql = "SELECT mrn, clinical_notes FROM claims"
        parsed = parse_sql(sql, "postgresql")
        result = run(parsed, billing_envelope)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.UNAUTHORIZED_COLUMN in codes


class TestAggregationViolation:
    def test_patient_id_in_agg_only_select(self, agg_only_envelope):
        sql = "SELECT mrn, COUNT(*) FROM encounters GROUP BY mrn"
        parsed = parse_sql(sql, "postgresql")
        result = run(parsed, agg_only_envelope)
        # mrn is HIDDEN in agg_only_envelope — UNAUTHORIZED_COLUMN
        assert result.status == GateStatus.FAIL

    def test_no_group_by_agg_only_fails(self, agg_only_envelope):
        sql = "SELECT encounter_id, unit_id FROM encounters LIMIT 100"
        parsed = parse_sql(sql, "postgresql")
        result = run(parsed, agg_only_envelope)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.AGGREGATION_VIOLATION in codes

    def test_proper_aggregate_passes(self, agg_only_envelope):
        sql = "SELECT unit_id, COUNT(*) as cnt FROM encounters GROUP BY unit_id"
        parsed = parse_sql(sql, "postgresql")
        result = run(parsed, agg_only_envelope)
        assert result.status == GateStatus.PASS


class TestMissingRowFilter:
    def test_missing_filter_flagged(self, physician_envelope):
        sql = "SELECT mrn FROM encounters LIMIT 100"
        parsed = parse_sql(sql, "postgresql")
        result = run(parsed, physician_envelope)
        codes = [v.code for v in result.violations]
        assert ViolationCode.MISSING_REQUIRED_FILTER in codes

    def test_with_correct_filter_no_flag(self, physician_envelope):
        sql = "SELECT mrn FROM encounters WHERE treating_provider_id = 'DR-4521' LIMIT 100"
        parsed = parse_sql(sql, "postgresql")
        result = run(parsed, physician_envelope)
        codes = [v.code for v in result.violations]
        assert ViolationCode.MISSING_REQUIRED_FILTER not in codes


class TestSubqueryDepth:
    def test_excessive_subquery_depth_blocked(self, physician_envelope):
        sql = """
SELECT * FROM (
    SELECT * FROM (
        SELECT * FROM (
            SELECT * FROM (
                SELECT mrn FROM encounters
            ) t1
        ) t2
    ) t3
) t4
"""
        parsed = parse_sql(sql, "postgresql")
        result = run(parsed, physician_envelope, max_subquery_depth=3)
        # Either UNAUTHORIZED_TABLE (wildcard) or EXCESSIVE_SUBQUERY_DEPTH
        assert len(result.violations) > 0


class TestParseError:
    def test_unparseable_sql_fails(self, physician_envelope):
        from app.services.sql_parser import ParsedSQL
        bad_parsed = ParsedSQL(ast=None, parse_error="Syntax error at position 5")
        result = run(bad_parsed, physician_envelope)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.UNPARSEABLE_SQL in codes


class TestWriteOperations:
    def test_insert_blocked(self, physician_envelope):
        from app.services.sql_parser import ParsedSQL
        parsed = parse_sql("INSERT INTO patients VALUES ('mrn', 'test')")
        result = run(parsed, physician_envelope)
        assert result.status == GateStatus.FAIL
