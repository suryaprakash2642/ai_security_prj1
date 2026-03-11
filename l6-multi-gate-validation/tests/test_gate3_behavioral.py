"""Tests for Gate 3 — Behavioral Analysis."""

import pytest
from app.models.enums import GateStatus, ViolationCode
from app.services.gate3_behavioral import run
from app.services.sql_parser import parse_sql


class TestCleanSQL:
    def test_simple_select_passes(self):
        sql = "SELECT mrn, admission_date FROM encounters WHERE unit_id = '3B' LIMIT 100"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        critical = [v for v in result.violations if v.code in (
            ViolationCode.WRITE_OPERATION, ViolationCode.UNION_EXFILTRATION,
            ViolationCode.DYNAMIC_SQL, ViolationCode.SYSTEM_TABLE_ACCESS,
        )]
        assert len(critical) == 0

    def test_join_query_passes(self):
        sql = """
SELECT e.mrn, p.full_name FROM encounters e
JOIN patients p ON e.mrn = p.mrn
WHERE e.treating_provider_id = 'DR-4521'
LIMIT 100
"""
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.PASS

    def test_aggregate_query_passes(self):
        sql = "SELECT unit_id, COUNT(*) FROM encounters GROUP BY unit_id ORDER BY 2 DESC"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.PASS


class TestWriteOperations:
    def test_insert_blocked(self):
        sql = "INSERT INTO patients (mrn, full_name) VALUES ('P001', 'Test')"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.WRITE_OPERATION in codes

    def test_update_blocked(self):
        sql = "UPDATE patients SET full_name = 'Hacked' WHERE mrn = 'P001'"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL

    def test_delete_blocked(self):
        sql = "DELETE FROM patients WHERE mrn = 'P001'"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL

    def test_drop_blocked(self):
        sql = "DROP TABLE patients"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL

    def test_create_blocked(self):
        sql = "CREATE TABLE evil_table (id INT)"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL


class TestSystemTableAccess:
    def test_information_schema_blocked(self):
        sql = "SELECT column_name FROM information_schema.columns WHERE table_name = 'patients'"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.SYSTEM_TABLE_ACCESS in codes

    def test_pg_catalog_blocked(self):
        sql = "SELECT * FROM pg_catalog.pg_tables"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL

    def test_sys_tables_blocked(self):
        sql = "SELECT * FROM sys.tables"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL


class TestUnionExfiltration:
    def test_union_select_blocked(self):
        sql = "SELECT mrn FROM patients UNION SELECT username FROM sys.sql_logins"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.UNION_EXFILTRATION in codes

    def test_union_all_blocked(self):
        sql = "SELECT mrn FROM patients UNION ALL SELECT password FROM sys.users"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL


class TestDynamicSQL:
    def test_exec_blocked(self):
        result = run(parse_sql("SELECT 1"), "EXEC('SELECT * FROM patients')")
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.DYNAMIC_SQL in codes

    def test_sp_executesql_blocked(self):
        result = run(parse_sql("SELECT 1"),
                     "EXEC sp_executesql N'SELECT * FROM patients'")
        assert result.status == GateStatus.FAIL

    def test_execute_immediate_blocked(self):
        result = run(parse_sql("SELECT 1"),
                     "EXECUTE IMMEDIATE 'SELECT * FROM patients'")
        assert result.status == GateStatus.FAIL


class TestFileOperations:
    def test_into_outfile_blocked(self):
        sql = "SELECT * FROM patients INTO OUTFILE '/tmp/data.csv'"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.FILE_OPERATION in codes


class TestPrivilegeEscalation:
    def test_grant_blocked(self):
        sql = "GRANT ALL PRIVILEGES ON patients TO PUBLIC"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        assert result.status == GateStatus.FAIL
        codes = [v.code for v in result.violations]
        assert ViolationCode.PRIVILEGE_ESCALATION in codes


class TestCommentInjection:
    def test_sql_comment_flagged(self):
        sql = "SELECT mrn FROM patients -- WHERE ssn = 'secret'"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        codes = [v.code for v in result.violations]
        assert ViolationCode.COMMENT_INJECTION in codes

    def test_block_comment_flagged(self):
        sql = "SELECT /* ssn, */ mrn FROM patients"
        parsed = parse_sql(sql)
        result = run(parsed, sql)
        codes = [v.code for v in result.violations]
        assert ViolationCode.COMMENT_INJECTION in codes
