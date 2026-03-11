"""Tests for intent classification — all 7 intents and domain hint extraction."""

from __future__ import annotations

import pytest

from app.models.enums import DomainHint, QueryIntent
from app.services.intent_classifier import IntentClassifier


@pytest.fixture
def classifier():
    return IntentClassifier()


class TestIntentClassification:

    def test_data_lookup_basic(self, classifier):
        result = classifier.classify("Show me all patient records")
        assert result.intent == QueryIntent.DATA_LOOKUP

    def test_data_lookup_find(self, classifier):
        result = classifier.classify("Find patients with diabetes")
        assert result.intent == QueryIntent.DATA_LOOKUP

    def test_aggregation_count(self, classifier):
        result = classifier.classify("How many patients were admitted this month?")
        assert result.intent == QueryIntent.AGGREGATION

    def test_aggregation_average(self, classifier):
        result = classifier.classify("What is the average length of stay?")
        assert result.intent == QueryIntent.AGGREGATION

    def test_aggregation_total(self, classifier):
        result = classifier.classify("Total revenue by department")
        assert result.intent == QueryIntent.AGGREGATION

    def test_aggregation_group_by(self, classifier):
        result = classifier.classify("Breakdown of charges per insurance payer")
        assert result.intent == QueryIntent.AGGREGATION

    def test_comparison_vs(self, classifier):
        result = classifier.classify("Compare ER visits vs ICU admissions")
        assert result.intent == QueryIntent.COMPARISON

    def test_comparison_ranking(self, classifier):
        result = classifier.classify("Top 10 providers by patient volume")
        assert result.intent in (QueryIntent.COMPARISON, QueryIntent.AGGREGATION)

    def test_trend_over_time(self, classifier):
        result = classifier.classify("Show admission trends over the last 12 months")
        assert result.intent == QueryIntent.TREND

    def test_trend_monthly(self, classifier):
        result = classifier.classify("Monthly readmission rates for 2024")
        assert result.intent == QueryIntent.TREND

    def test_trend_year_over_year(self, classifier):
        result = classifier.classify("Year over year growth in outpatient visits")
        assert result.intent == QueryIntent.TREND

    def test_join_query_explicit(self, classifier):
        result = classifier.classify("Join patients with their encounters and diagnoses")
        assert result.intent == QueryIntent.JOIN_QUERY

    def test_join_query_relationship(self, classifier):
        result = classifier.classify("Show patients along with their lab results")
        assert result.intent == QueryIntent.JOIN_QUERY

    def test_join_query_across(self, classifier):
        result = classifier.classify("Link patient data across clinical and billing systems")
        assert result.intent == QueryIntent.JOIN_QUERY

    def test_existence_check(self, classifier):
        result = classifier.classify("Is there any data for patient MRN 12345?")
        assert result.intent == QueryIntent.EXISTENCE_CHECK

    def test_existence_check_verify(self, classifier):
        result = classifier.classify("Check if we have lab results for this patient")
        assert result.intent == QueryIntent.EXISTENCE_CHECK

    def test_definition_what_is(self, classifier):
        result = classifier.classify("What is stored in the encounters table?")
        assert result.intent == QueryIntent.DEFINITION

    def test_definition_schema(self, classifier):
        result = classifier.classify("Describe the schema for patient records")
        assert result.intent == QueryIntent.DEFINITION

    def test_confidence_is_bounded(self, classifier):
        result = classifier.classify("Show all patients with diabetes")
        assert 0.0 <= result.confidence <= 1.0

    def test_matched_keywords_populated(self, classifier):
        result = classifier.classify("How many patients in the ICU?")
        assert len(result.matched_keywords) > 0

    def test_default_to_data_lookup(self, classifier):
        """Ambiguous questions default to DATA_LOOKUP."""
        result = classifier.classify("patients")
        assert result.intent == QueryIntent.DATA_LOOKUP

    def test_no_fallback_used(self, classifier):
        """Rule-based classifier should not use fallback."""
        result = classifier.classify("Show all patients")
        assert result.used_fallback is False


class TestDomainHintExtraction:

    def test_clinical_domain(self, classifier):
        result = classifier.classify("Show patient diagnosis records")
        assert DomainHint.CLINICAL in result.domain_hints

    def test_billing_domain(self, classifier):
        result = classifier.classify("Show billing claims and payments")
        assert DomainHint.BILLING in result.domain_hints

    def test_pharmacy_domain(self, classifier):
        result = classifier.classify("List all prescribed medications")
        assert DomainHint.PHARMACY in result.domain_hints

    def test_laboratory_domain(self, classifier):
        result = classifier.classify("Show lab test results for CBC")
        assert DomainHint.LABORATORY in result.domain_hints

    def test_hr_domain(self, classifier):
        result = classifier.classify("Employee payroll and salary data")
        assert DomainHint.HR in result.domain_hints

    def test_scheduling_domain(self, classifier):
        result = classifier.classify("Show appointment schedule for today")
        assert DomainHint.SCHEDULING in result.domain_hints

    def test_multiple_domains(self, classifier):
        result = classifier.classify("Show patient lab results and billing claims")
        hints = result.domain_hints
        assert len(hints) >= 2

    def test_max_three_domain_hints(self, classifier):
        """Domain hints capped at 3."""
        result = classifier.classify(
            "patient medication lab appointment billing employee"
        )
        assert len(result.domain_hints) <= 3
