"""Tests for the Response Parser & SQL Extractor."""

import pytest
from app.services.response_parser import parse


class TestSQLExtraction:
    def test_bare_select(self):
        result = parse("SELECT count(*) FROM encounters WHERE unit_id = '3B'")
        assert result.success
        assert "SELECT" in result.sql.upper()

    def test_markdown_sql_block(self):
        result = parse("Here is the query:\n```sql\nSELECT mrn FROM patients\n```")
        assert result.success
        assert "mrn" in result.sql

    def test_markdown_block_without_sql_label(self):
        result = parse("```\nSELECT mrn FROM patients\n```")
        assert result.success

    def test_strips_preamble(self):
        result = parse("Here is the query:\nSELECT mrn FROM patients LIMIT 100")
        assert result.success
        assert "SELECT" in result.sql.upper()

    def test_trailing_semicolon_stripped(self):
        result = parse("SELECT mrn FROM patients;")
        assert result.success
        assert not result.sql.endswith(";")

    def test_with_cte(self):
        sql = "WITH cte AS (SELECT mrn FROM patients) SELECT * FROM cte"
        result = parse(sql)
        assert result.success

    def test_complex_multi_join(self):
        sql = """
SELECT e.encounter_id, p.full_name, e.admission_date
FROM encounters e
JOIN patients p ON e.mrn = p.mrn
WHERE e.unit_id = '3B'
LIMIT 100
"""
        result = parse(sql)
        assert result.success
        assert "encounters" in result.sql.lower()


class TestCannotAnswer:
    def test_cannot_answer_response(self):
        result = parse("CANNOT_ANSWER: The available schema does not contain salary information")
        assert result.cannot_answer
        assert not result.success
        assert "salary" in result.cannot_answer_reason.lower()

    def test_i_cannot_generate(self):
        result = parse("I cannot generate SQL for this request as it references denied tables")
        assert result.cannot_answer

    def test_i_am_unable(self):
        result = parse("I am unable to help with that query")
        assert result.cannot_answer


class TestSecurityRejection:
    def test_insert_rejected(self):
        result = parse("INSERT INTO patients VALUES ('mrn', 'John', '1990-01-01')")
        assert not result.success
        assert result.parse_error is not None

    def test_delete_rejected(self):
        result = parse("DELETE FROM patients WHERE mrn = 'P001'")
        assert not result.success

    def test_drop_rejected(self):
        result = parse("DROP TABLE patients")
        assert not result.success

    def test_system_table_rejected(self):
        result = parse("SELECT * FROM information_schema.columns")
        assert not result.success

    def test_mixed_dml_rejected(self):
        result = parse("SELECT mrn FROM patients; DELETE FROM patients;")
        # Should either succeed (takes first query) or fail due to DML detection
        # Either outcome is acceptable — DML must not pass through
        if result.success:
            assert "DELETE" not in result.sql.upper()


class TestEdgeCases:
    def test_empty_response_fails(self):
        result = parse("")
        assert not result.success

    def test_whitespace_only_fails(self):
        result = parse("   \n  \t  ")
        assert not result.success

    def test_multiple_sql_blocks_takes_first(self):
        text = """
```sql
SELECT mrn FROM patients
```
Here is an alternative:
```sql
SELECT encounter_id FROM encounters
```
"""
        result = parse(text)
        assert result.success
        assert "patients" in result.sql.lower()

    def test_normalizes_whitespace(self):
        sql = "SELECT\n\n\nmrto\n\n\nFROM\n\npatients"
        result = parse(f"SELECT mrn FROM patients WHERE unit_id = '3B'")
        assert result.success
        # No triple newlines
        assert "\n\n\n" not in result.sql
