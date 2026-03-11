"""Tests for the Secure Prompt Assembler."""

import pytest
from app.models.enums import SQLDialect
from app.services.prompt_assembler import assemble_prompt


class TestPromptAssembly:
    def test_all_four_sections_present(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="How many patients were admitted to my unit this month?",
            envelope=physician_envelope,
            schema=simple_schema,
            dialect=SQLDialect.POSTGRESQL,
        )
        assert "=== MANDATORY RULES ===" in result.user_message
        assert "=== AVAILABLE SCHEMA ===" in result.user_message
        assert "=== USER QUESTION ===" in result.user_message
        assert result.system_prompt  # System prompt exists

    def test_policy_rules_included_verbatim(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="Show my patients",
            envelope=physician_envelope,
            schema=simple_schema,
        )
        # NL rules from envelope must appear verbatim
        for rule in physician_envelope.global_nl_rules:
            assert rule in result.user_message
        for tp in physician_envelope.table_permissions:
            for rule in tp.nl_rules:
                assert rule in result.user_message

    def test_allowed_tables_appear_in_schema(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="Show patients",
            envelope=physician_envelope,
            schema=simple_schema,
        )
        assert "encounters" in result.user_message
        assert "patients" in result.user_message

    def test_question_appears_last(self, physician_envelope, simple_schema):
        question = "How many ICU patients today?"
        result = assemble_prompt(
            sanitized_question=question,
            envelope=physician_envelope,
            schema=simple_schema,
        )
        user_msg = result.user_message
        # Question section must come after schema section
        schema_pos = user_msg.find("=== AVAILABLE SCHEMA ===")
        question_pos = user_msg.find("=== USER QUESTION ===")
        assert schema_pos < question_pos

    def test_rules_before_schema(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="Show patients",
            envelope=physician_envelope,
            schema=simple_schema,
        )
        user_msg = result.user_message
        rules_pos = user_msg.find("=== MANDATORY RULES ===")
        schema_pos = user_msg.find("=== AVAILABLE SCHEMA ===")
        assert rules_pos < schema_pos

    def test_tables_included_count(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="Show patients",
            envelope=physician_envelope,
            schema=simple_schema,
        )
        assert result.tables_included == 2  # encounters + patients

    def test_rules_count_matches(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="Show patients",
            envelope=physician_envelope,
            schema=simple_schema,
        )
        expected_rules = len(physician_envelope.all_nl_rules)
        assert result.rules_count == expected_rules

    def test_postgresql_dialect_hint(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="Show patients",
            envelope=physician_envelope,
            schema=simple_schema,
            dialect=SQLDialect.POSTGRESQL,
        )
        assert "PostgreSQL" in result.system_prompt or "LIMIT" in result.system_prompt

    def test_tsql_dialect_hint(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="Show patients",
            envelope=physician_envelope,
            schema=simple_schema,
            dialect=SQLDialect.TSQL,
        )
        assert "T-SQL" in result.system_prompt or "TOP" in result.system_prompt

    def test_masked_column_annotation(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="Show patient names",
            envelope=physician_envelope,
            schema=simple_schema,
        )
        # Masking annotation should appear for full_name
        assert "MASKED" in result.user_message

    def test_row_filter_annotation(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="Show encounters",
            envelope=physician_envelope,
            schema=simple_schema,
        )
        assert "REQUIRED" in result.user_message

    def test_token_breakdown_populated(self, physician_envelope, simple_schema):
        result = assemble_prompt(
            sanitized_question="Show patients",
            envelope=physician_envelope,
            schema=simple_schema,
        )
        assert "system" in result.token_breakdown
        assert "rules" in result.token_breakdown
        assert "schema" in result.token_breakdown
        assert "question" in result.token_breakdown
        assert all(v > 0 for v in result.token_breakdown.values())

    def test_empty_envelope_no_rules(self, simple_schema):
        from app.models.api import PermissionEnvelope
        empty_envelope = PermissionEnvelope(table_permissions=[], global_nl_rules=[])
        result = assemble_prompt(
            sanitized_question="Show data",
            envelope=empty_envelope,
            schema=simple_schema,
        )
        # No rules section if no rules
        assert result.rules_count == 0


class TestBillingPrompt:
    def test_billing_schema_visible(self, billing_envelope, simple_schema):
        from app.models.api import FilteredSchema, FilteredTable, SchemaColumn
        billing_schema = FilteredSchema(tables=[
            FilteredTable(
                table_id="claims",
                table_name="claims",
                domain="Billing",
                nl_description="Insurance claims",
                relevance_score=0.94,
                columns=[
                    SchemaColumn(name="claim_id", data_type="UUID"),
                    SchemaColumn(name="mrn", data_type="VARCHAR"),
                    SchemaColumn(name="total_amount", data_type="DECIMAL"),
                    SchemaColumn(name="service_date", data_type="DATE"),
                ],
            ),
        ])
        result = assemble_prompt(
            sanitized_question="Show total claims by insurance",
            envelope=billing_envelope,
            schema=billing_schema,
        )
        assert "claims" in result.user_message
        assert "Do not include clinical_notes" in result.user_message
