"""Tests for question preprocessing, abbreviation expansion, and embedding hashing."""

from __future__ import annotations

import hashlib

import pytest

from app.services.embedding_engine import EmbeddingEngine, _normalize_whitespace
from tests.conftest import make_security_context


class TestNormalizeWhitespace:
    def test_collapses_multiple_spaces(self):
        assert _normalize_whitespace("hello   world") == "hello world"

    def test_strips_leading_trailing(self):
        assert _normalize_whitespace("  hello  ") == "hello"

    def test_collapses_tabs_newlines(self):
        assert _normalize_whitespace("hello\t\nworld") == "hello world"

    def test_empty_string(self):
        assert _normalize_whitespace("") == ""


class TestAbbreviationExpansion:

    @pytest.fixture
    def engine(self, test_settings, mock_embedding_client, mock_cache):
        return EmbeddingEngine(
            settings=test_settings,
            embedding_client=mock_embedding_client,
            cache=mock_cache,
        )

    def test_bp_expansion(self, engine):
        result = engine._expand_abbreviations("Show BP readings for patient")
        assert "blood pressure" in result
        assert "BP" in result  # Original preserved

    def test_mrn_expansion(self, engine):
        result = engine._expand_abbreviations("Find patient by MRN")
        assert "medical record number" in result
        assert "MRN" in result

    def test_dob_expansion(self, engine):
        result = engine._expand_abbreviations("Get DOB for all patients")
        assert "date of birth" in result

    def test_icd_expansion(self, engine):
        result = engine._expand_abbreviations("List ICD codes")
        assert "ICD-10" in result or "diagnosis code" in result

    def test_cpt_expansion(self, engine):
        result = engine._expand_abbreviations("CPT billing codes")
        assert "procedure code" in result

    def test_icu_expansion(self, engine):
        result = engine._expand_abbreviations("ICU admissions")
        assert "intensive care unit" in result

    def test_er_expansion(self, engine):
        result = engine._expand_abbreviations("ER visits today")
        assert "emergency" in result

    def test_cbc_expansion(self, engine):
        result = engine._expand_abbreviations("CBC results")
        assert "complete blood count" in result

    def test_a1c_expansion(self, engine):
        result = engine._expand_abbreviations("A1C levels above 7")
        assert "hemoglobin" in result or "glycated" in result

    def test_multiple_abbreviations(self, engine):
        result = engine._expand_abbreviations("Show BP and CBC for ICU patients")
        assert "blood pressure" in result
        assert "complete blood count" in result
        assert "intensive care unit" in result

    def test_unknown_words_unchanged(self, engine):
        result = engine._expand_abbreviations("Show all active patients")
        assert result == "Show all active patients"

    def test_dea_expansion(self, engine):
        result = engine._expand_abbreviations("DEA number for provider")
        assert "Drug Enforcement" in result

    def test_preserves_original(self, engine):
        """Verify abbreviation expansion is additive, not destructive."""
        result = engine._expand_abbreviations("MRN lookup")
        assert "MRN" in result  # Original kept
        assert "medical record number" in result  # Expansion added


class TestPreprocessing:

    @pytest.fixture
    def engine(self, test_settings, mock_embedding_client, mock_cache):
        return EmbeddingEngine(
            settings=test_settings,
            embedding_client=mock_embedding_client,
            cache=mock_cache,
        )

    def test_appends_department_and_role(self, engine, test_settings):
        ctx = make_security_context(test_settings, department="cardiology", roles=["doctor"])
        result = engine.preprocess("Show patient vitals", ctx)
        assert "department:cardiology" in result
        assert "role:doctor" in result

    def test_normalizes_whitespace(self, engine, test_settings):
        ctx = make_security_context(test_settings)
        result = engine.preprocess("  Show   patient   vitals  ", ctx)
        assert "  " not in result.split("[")[0]  # No double spaces before context

    def test_expands_abbreviations_in_preprocessing(self, engine, test_settings):
        ctx = make_security_context(test_settings)
        result = engine.preprocess("Show BP for MRN 12345", ctx)
        assert "blood pressure" in result
        assert "medical record number" in result


class TestCacheKeyGeneration:

    @pytest.fixture
    def engine(self, test_settings, mock_embedding_client, mock_cache):
        return EmbeddingEngine(
            settings=test_settings,
            embedding_client=mock_embedding_client,
            cache=mock_cache,
        )

    def test_deterministic_hashing(self, engine):
        key1 = engine.compute_cache_key("Show BP readings")
        key2 = engine.compute_cache_key("Show BP readings")
        assert key1 == key2

    def test_different_questions_different_keys(self, engine):
        key1 = engine.compute_cache_key("Show BP readings")
        key2 = engine.compute_cache_key("Show CBC results")
        assert key1 != key2

    def test_key_is_sha256_hex(self, engine):
        key = engine.compute_cache_key("test question")
        assert len(key) == 64  # SHA-256 hex digest length
        assert all(c in "0123456789abcdef" for c in key)
