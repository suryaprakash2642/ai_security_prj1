"""Tests for Result Sanitizer — PII detection and runtime masking."""

import pytest
from app.models.api import ColumnMetadata
from app.models.enums import PIIType
from app.services.result_sanitizer import sanitize


def _cols(*names: str) -> list[ColumnMetadata]:
    return [ColumnMetadata(name=n, type="VARCHAR") for n in names]


class TestCleanData:
    def test_clean_rows_unchanged(self):
        rows = [["MRN-001", "J. Patel", "2026-01-15"]]
        cols = _cols("mrn", "full_name", "admission_date")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 0
        assert out[0][0] == "MRN-001"

    def test_empty_rows(self):
        out, result = sanitize([], _cols("mrn"))
        assert result.pii_detected == 0
        assert out == []

    def test_numeric_column_skipped(self):
        rows = [["123-45-6789"]]  # Would be SSN if string column
        cols = [ColumnMetadata(name="amount", type="INTEGER")]
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 0

    def test_none_value_skipped(self):
        rows = [[None, "normal_value"]]
        cols = _cols("col1", "col2")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 0


class TestSSNDetection:
    def test_ssn_in_notes_column_masked(self):
        rows = [["Patient SSN is 123-45-6789 per records"]]
        cols = _cols("clinical_notes")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 1
        assert "123-45-6789" not in out[0][0]
        assert "6789" in out[0][0]  # Last 4 preserved

    def test_ssn_format_masked(self):
        rows = [["SSN: 987-65-4321"]]
        cols = _cols("notes")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 1
        event = result.events[0]
        assert event.pii_type == PIIType.SSN

    def test_multiple_ssns_in_row(self):
        # Only first match per cell per pattern is replaced (re.search, not findall)
        rows = [["SSN1: 123-45-6789 and SSN2: 987-65-4321"]]
        cols = _cols("notes")
        out, result = sanitize(rows, cols)
        assert result.pii_detected >= 1


class TestAadhaarDetection:
    def test_aadhaar_masked(self):
        rows = [["Aadhaar: 1234 5678 9012"]]
        cols = _cols("patient_notes")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 1
        assert "9012" in out[0][0]  # Last 4 preserved

    def test_aadhaar_without_spaces(self):
        rows = [["Aadhaar 123456789012"]]
        cols = _cols("notes")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 1


class TestEmailDetection:
    def test_email_masked(self):
        rows = [["Contact: doctor@apollohospitals.com for follow-up"]]
        cols = _cols("notes")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 1
        assert "doctor@apollohospitals.com" not in out[0][0]
        assert "apollohospitals.com" in out[0][0]  # Domain preserved

    def test_email_first_char_preserved(self):
        rows = [["Email: john@example.com"]]
        cols = _cols("contact_info")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 1
        assert out[0][0].startswith("Email: j")


class TestPhoneDetection:
    def test_phone_10digit_masked(self):
        rows = [["Call 9876543210 for appointment"]]
        cols = _cols("notes")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 1
        assert "3210" in out[0][0]  # Last 4 preserved

    def test_phone_excluded_for_mrn_column(self):
        # MRN columns should not flag phone numbers (false positive prevention)
        rows = [["MRN-9876543210"]]
        cols = _cols("mrn")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 0

    def test_phone_excluded_for_encounter_id(self):
        rows = [["ENC-9876543210"]]
        cols = _cols("encounter_id")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 0


class TestMultiColumnRow:
    def test_pii_in_one_column_others_untouched(self):
        rows = [["MRN-001", "SSN: 111-22-3333", "INPATIENT"]]
        cols = _cols("mrn", "notes", "encounter_type")
        out, result = sanitize(rows, cols)
        assert result.pii_detected == 1
        assert out[0][0] == "MRN-001"  # Untouched
        assert "111-22-3333" not in out[0][1]  # Masked
        assert out[0][2] == "INPATIENT"  # Untouched

    def test_multiple_rows_multiple_pii(self):
        rows = [
            ["note with 123-45-6789", "clean"],
            ["another SSN: 987-65-4321", "also clean"],
        ]
        cols = _cols("notes", "status")
        out, result = sanitize(rows, cols)
        assert result.rows_scanned == 2
        assert result.pii_detected == 2


class TestSanitizationReport:
    def test_report_tracks_column_and_row(self):
        rows = [["clean row"], ["SSN found: 123-45-6789"]]
        cols = _cols("notes")
        _, result = sanitize(rows, cols)
        assert result.pii_detected == 1
        event = result.events[0]
        assert event.row_index == 1
        assert event.column == "notes"
