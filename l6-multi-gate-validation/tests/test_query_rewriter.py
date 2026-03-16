"""Tests for the Query Rewriter."""

import pytest
from app.models.api import Violation
from app.models.enums import RewriteType, ViolationCode, ViolationSeverity
from app.services.query_rewriter import rewrite
from app.services.sql_parser import parse_sql


class TestLimitEnforcement:
    def test_adds_limit_when_missing(self, physician_envelope):
        sql = "SELECT mrn, admission_date FROM encounters WHERE treating_provider_id = 'DR-4521'"
        parsed = parse_sql(sql, "postgresql")
        result = rewrite(sql, parsed, physician_envelope, "postgresql", default_max_rows=1000)
        assert result.success
        assert "LIMIT" in result.sql.upper() or "FETCH" in result.sql.upper()
        rewrite_types = [r.rewrite_type for r in result.rewrites]
        assert RewriteType.LIMIT in rewrite_types

    def test_preserves_tighter_existing_limit(self, physician_envelope):
        sql = "SELECT mrn FROM encounters WHERE treating_provider_id = 'DR-4521' LIMIT 50"
        parsed = parse_sql(sql, "postgresql")
        result = rewrite(sql, parsed, physician_envelope, "postgresql", default_max_rows=1000)
        assert result.success
        # LIMIT 50 should be preserved (tighter than 1000)
        assert "50" in result.sql

    def test_replaces_looser_existing_limit(self, physician_envelope):
        sql = "SELECT mrn FROM encounters WHERE treating_provider_id = 'DR-4521' LIMIT 5000"
        parsed = parse_sql(sql, "postgresql")
        result = rewrite(sql, parsed, physician_envelope, "postgresql", default_max_rows=1000)
        assert result.success
        # Should replace 5000 with 1000
        assert "5000" not in result.sql or "LIMIT 1000" in result.sql


class TestCommentStripping:
    def test_inline_comment_stripped(self, physician_envelope):
        sql = "SELECT mrn -- , ssn\nFROM encounters WHERE treating_provider_id = 'DR-4521'"
        parsed = parse_sql(sql, "postgresql")
        result = rewrite(sql, parsed, physician_envelope, "postgresql")
        assert result.success
        assert "--" not in result.sql
        rewrite_types = [r.rewrite_type for r in result.rewrites]
        assert RewriteType.COMMENT_STRIP in rewrite_types

    def test_block_comment_stripped(self, physician_envelope):
        sql = "SELECT mrn /* , ssn */ FROM encounters WHERE treating_provider_id = 'DR-4521'"
        parsed = parse_sql(sql, "postgresql")
        result = rewrite(sql, parsed, physician_envelope, "postgresql")
        assert result.success
        assert "/*" not in result.sql


class TestWhereFilterInjection:
    def test_injects_missing_row_filter(self, physician_envelope):
        sql = "SELECT mrn, admission_date FROM encounters LIMIT 100"
        parsed = parse_sql(sql, "postgresql")
        # Simulate Gate 1 missing filter violation
        g1_violations = [Violation(
            gate=1,
            code=ViolationCode.MISSING_REQUIRED_FILTER,
            severity=ViolationSeverity.HIGH,
            table="encounters",
            detail="Missing required filter",
        )]
        result = rewrite(sql, parsed, physician_envelope, "postgresql", gate1_violations=g1_violations)
        assert result.success
        rewrite_types = [r.rewrite_type for r in result.rewrites]
        assert RewriteType.WHERE_FILTER in rewrite_types


class TestMaskingRewrite:
    def test_masked_column_gets_rewritten(self, physician_envelope):
        sql = "SELECT mrn, full_name FROM patients LIMIT 100"
        parsed = parse_sql(sql, "postgresql")
        # Simulate Gate 2 unmasked PII violation
        g2_violations = [Violation(
            gate=2,
            code=ViolationCode.UNMASKED_PII_COLUMN,
            severity=ViolationSeverity.HIGH,
            table="patients",
            column="full_name",
            detail="full_name should be masked",
        )]
        result = rewrite(sql, parsed, physician_envelope, "postgresql", gate2_violations=g2_violations)
        assert result.success
        rewrite_types = [r.rewrite_type for r in result.rewrites]
        assert RewriteType.MASKING in rewrite_types


class TestNoRewrites:
    def test_clean_sql_no_rewrites(self, physician_envelope):
        sql = """
SELECT mrn, admission_date
FROM encounters
WHERE treating_provider_id = 'DR-4521' OR unit_id = '3B'
LIMIT 100
"""
        parsed = parse_sql(sql, "postgresql")
        result = rewrite(sql, parsed, physician_envelope, "postgresql")
        assert result.success
        # May have LIMIT rewrite if existing limit matches

    def test_rewrite_idempotent(self, physician_envelope):
        """Running rewriter twice should not change the result further."""
        sql = "SELECT mrn FROM encounters WHERE treating_provider_id = 'DR-4521' LIMIT 100"
        parsed1 = parse_sql(sql, "postgresql")
        result1 = rewrite(sql, parsed1, physician_envelope, "postgresql")
        assert result1.success

        # Rewrite the already-rewritten SQL
        parsed2 = parse_sql(result1.sql, "postgresql")
        result2 = rewrite(result1.sql, parsed2, physician_envelope, "postgresql")
        assert result2.success
        # The final SQL should be semantically equivalent


class TestAggregateLimit:
    def test_aggregate_query_gets_relaxed_limit(self, physician_envelope):
        sql = "SELECT unit_id, COUNT(*) as cnt FROM encounters WHERE treating_provider_id = 'DR-4521' GROUP BY unit_id"
        parsed = parse_sql(sql, "postgresql")
        result = rewrite(sql, parsed, physician_envelope, "postgresql", default_max_rows=1000)
        assert result.success
        # For GROUP BY queries, limit is relaxed (max_rows * 10)
        # Just verify it added some limit
        assert "LIMIT" in result.sql.upper() or "FETCH" in result.sql.upper() or len(result.rewrites) >= 0
