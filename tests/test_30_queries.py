#!/usr/bin/env python3
"""
30-Query Role-Based Access Test Suite — Apollo Hospitals Zero Trust Pipeline
Tests L1 → L3 (with L2 + L4) for 5 users, 30 queries each = 150 total.

Check types:
  not_denied       → at least 1 table returned
  has_table X      → table X appears in filtered_schema
  no_table  X      → table X does NOT appear (cross-domain protection)
  table_has_hidden X → table X has hidden_column_count >= 1 (PHI masking)
"""

import hmac, hashlib, time, requests, sys
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
L1        = "http://localhost:8001"
L3        = "http://localhost:8300"
L3_SECRET = "dev-secret-change-in-production-min-32-chars-xx"

USERS = {
    "dr_patel": {
        "oid": "oid-dr-patel-4521", "name": "Dr. Rajesh Patel",
        "email": "rajesh.patel@apollohospitals.com",
        "roles": ["ATTENDING_PHYSICIAN"], "groups": ["physicians-cardiology"],
        "role_label": "ATTENDING_PHYSICIAN", "clearance": 4,
    },
    "anita_kumar": {
        "oid": "oid-nurse-kumar-2847", "name": "Anita Kumar",
        "email": "anita.kumar@apollohospitals.com",
        "roles": ["REGISTERED_NURSE"], "groups": ["nursing-cardiology"],
        "role_label": "REGISTERED_NURSE", "clearance": 2,
    },
    "maria_fernandes": {
        "oid": "oid-bill-maria-5521", "name": "Maria Fernandes",
        "email": "maria.fernandes@apollohospitals.com",
        "roles": ["billing_staff"], "groups": ["billing-team"],
        "role_label": "BILLING_STAFF", "clearance": 2,
    },
    "vikram_joshi": {
        "oid": "oid-it-admin-7801", "name": "Vikram Joshi",
        "email": "vikram.joshi@apollohospitals.com",
        "roles": ["admin"], "groups": ["it-team"],
        "role_label": "ADMIN", "clearance": 2,
    },
    "priya_mehta": {
        "oid": "oid-hr-priya-7701", "name": "Priya Mehta",
        "email": "priya.mehta@apollohospitals.com",
        "roles": ["hr_staff"], "groups": ["hr-team"],
        "role_label": "HR_STAFF", "clearance": 3,
    },
}

# ── 30 Queries per Role ───────────────────────────────────────────────────────
# Format: (description, nl_query, [checks...])
# Queries are grouped: Domain Access (✓) | PHI Masking (🔒) | Cross-Domain Deny (✗)

TEST_CASES = {

    # ══════════════════════════════════════════════════════════════════════════
    # DR. RAJESH PATEL — ATTENDING_PHYSICIAN — Clearance 4
    # Domain: Full clinical access (diagnoses, admissions, prescriptions,
    #         lab_results, lab_orders, vital_signs, nursing_assessments,
    #         allergies, immunizations, procedures, therapy_notes, etc.)
    # ══════════════════════════════════════════════════════════════════════════
    "dr_patel": [
        # ── Clinical Domain Access (20 queries) ──────────────────────────────
        (
            "✓ 01 Patient diagnoses in cardiology",
            "Show all current diagnoses for patients in the cardiology department",
            [("has_table", "diagnoses"), ("not_denied", None)],
        ),
        (
            "✓ 02 Patient admissions in ward",
            "Show active patient admissions in the cardiology ward",
            [("has_table", "admissions"), ("not_denied", None)],
        ),
        (
            "✓ 03 Lab results for patient",
            "Get lab results for patient admitted this morning",
            [("has_table", "lab_results"), ("not_denied", None)],
        ),
        (
            "✓ 04 Prescriptions issued today",
            "List all prescriptions I issued to patients today",
            [("has_table", "prescriptions"), ("not_denied", None)],
        ),
        (
            "✓ 05 Patient vital signs",
            "Get vital signs recorded for ICU patients in the last shift",
            [("has_table", "vital_signs"), ("not_denied", None)],
        ),
        (
            "✓ 06 Nursing assessments for my patients",
            "Show nursing assessments completed for my patients today",
            [("has_table", "nursing_assessments"), ("not_denied", None)],
        ),
        (
            "✓ 07 Patient allergies on record",
            "Get documented allergies for cardiology patients in ward 3A",
            [("has_table", "allergies"), ("not_denied", None)],
        ),
        (
            "✓ 08 Immunization records",
            "Show immunization records for patients admitted this week",
            [("has_table", "immunizations"), ("not_denied", None)],
        ),
        (
            "✓ 09 Pending lab orders",
            "List all lab orders pending results for my patients",
            [("has_table", "lab_orders"), ("not_denied", None)],
        ),
        (
            "✓ 10 Scheduled procedures",
            "Show surgical procedures scheduled for cardiology patients",
            [("has_table", "procedures"), ("not_denied", None)],
        ),
        (
            "✓ 11 Therapy session notes",
            "Get therapy notes for post-operative cardiac patients",
            [("has_table", "therapy_notes"), ("not_denied", None)],
        ),
        (
            "✓ 12 Operating room schedule",
            "Show operating room schedule for cardiac surgery this week",
            [("has_table", "operating_room_schedules"), ("not_denied", None)],
        ),
        (
            "✓ 13 Discharge diagnoses",
            "Get diagnoses for patients scheduled for discharge today",
            [("has_table", "diagnoses"), ("not_denied", None)],
        ),
        (
            "✓ 14 Abnormal lab results",
            "Show lab results marked as abnormal requiring physician review",
            [("has_table", "lab_results"), ("not_denied", None)],
        ),
        (
            "✓ 15 Drug prescriptions for review",
            "List prescriptions requiring physician approval for renewal",
            [("has_table", "prescriptions"), ("not_denied", None)],
        ),
        (
            "✓ 16 Patient vital monitoring",
            "Get blood pressure and heart rate readings for ICU patients",
            [("has_table", "vital_signs"), ("not_denied", None)],
        ),
        (
            "✓ 17 Patients with multiple diagnoses",
            "Show patients with multiple active diagnoses in cardiology",
            [("has_table", "diagnoses"), ("not_denied", None)],
        ),
        (
            "✓ 18 Medication allergies",
            "Get medication allergies documented for patients requiring anesthesia",
            [("has_table", "allergies"), ("not_denied", None)],
        ),
        (
            "✓ 19 Post-op nursing assessment",
            "Show nursing assessments for post-operative patients in recovery",
            [("has_table", "nursing_assessments"), ("not_denied", None)],
        ),
        (
            "✓ 20 Patients admitted this week",
            "List all patient admissions in cardiology department this week",
            [("has_table", "admissions"), ("not_denied", None)],
        ),
        # ── PHI Masking (5 queries) ───────────────────────────────────────────
        (
            "🔒 21 HIV status hidden in lab results",
            "Get all lab results including HIV test status for admitted patients",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")],
        ),
        (
            "🔒 22 Sensitive lab values accessible with hidden PHI",
            "Show complete lab result panel for patient workup including all viral markers",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")],
        ),
        (
            "🔒 23 Lab results with infectious disease markers",
            "Get infectious disease screening lab results for admitted patients",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")],
        ),
        (
            "🔒 24 Comprehensive patient labs with sensitive markers",
            "Show full diagnostic lab results for patients in cardiology",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")],
        ),
        (
            "🔒 25 Lab panel including viral load tests",
            "Get viral marker test results from lab for all admitted patients",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")],
        ),
        # ── Cross-Domain Denial (5 queries) ───────────────────────────────────
        (
            "✗ 26 DENY: Billing claims denied",
            "Show insurance billing claims submitted for cardiology procedures",
            [("no_table", "claims"), ("no_table", "revenue_analytics")],
        ),
        (
            "✗ 27 DENY: HR attendance denied",
            "Get attendance records for medical staff in cardiology department",
            [("no_table", "attendance"), ("no_table", "leave_records")],
        ),
        (
            "✗ 28 DENY: Payroll and benefits denied",
            "Show salary and benefits information for cardiology physicians",
            [("no_table", "benefits"), ("no_table", "accounts_receivable")],
        ),
        (
            "✗ 29 DENY: Vendor contracts denied",
            "Get vendor contracts for medical equipment procurement",
            [("no_table", "vendor_master"), ("no_table", "cost_centers")],
        ),
        (
            "✗ 30 DENY: Financial analytics denied",
            "Show revenue analytics and department KPIs for hospital",
            [("no_table", "revenue_analytics"), ("no_table", "department_kpis")],
        ),
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # ANITA KUMAR — REGISTERED_NURSE — Clearance 2
    # Domain: Clinical nursing access (same clinical tables as physician)
    # ══════════════════════════════════════════════════════════════════════════
    "anita_kumar": [
        # ── Clinical Nursing Domain Access (20 queries) ───────────────────────
        (
            "✓ 01 Nursing assessments this shift",
            "Show nursing assessments completed in ward B during my shift",
            [("has_table", "nursing_assessments"), ("not_denied", None)],
        ),
        (
            "✓ 02 Patient vital signs monitoring",
            "Get vital signs recorded for all patients in ward B today",
            [("has_table", "vital_signs"), ("not_denied", None)],
        ),
        (
            "✓ 03 Medication prescriptions to administer",
            "Show prescriptions scheduled for administration during this shift",
            [("has_table", "prescriptions"), ("not_denied", None)],
        ),
        (
            "✓ 04 Patient admissions requiring nursing care",
            "Get all active patient admissions in my assigned nursing ward",
            [("has_table", "admissions"), ("not_denied", None)],
        ),
        (
            "✓ 05 Allergy alerts for patients",
            "Show documented allergies for patients I am caring for today",
            [("has_table", "allergies"), ("not_denied", None)],
        ),
        (
            "✓ 06 Lab orders to facilitate",
            "List lab orders that nursing staff need to collect samples for",
            [("has_table", "lab_orders"), ("not_denied", None)],
        ),
        (
            "✓ 07 Patient immunization status",
            "Get immunization records for patients requiring vaccination today",
            [("has_table", "immunizations"), ("not_denied", None)],
        ),
        (
            "✓ 08 Diagnoses requiring special nursing care",
            "Show patient diagnoses requiring isolation or special nursing protocols",
            [("has_table", "diagnoses"), ("not_denied", None)],
        ),
        (
            "✓ 09 Therapy care plans",
            "Get therapy notes and care plans for rehabilitation patients",
            [("has_table", "therapy_notes"), ("not_denied", None)],
        ),
        (
            "✓ 10 Procedures requiring nursing assistance",
            "List all bedside procedures that require nursing staff assistance today",
            [("has_table", "procedures"), ("not_denied", None)],
        ),
        (
            "✓ 11 Blood pressure monitoring",
            "Show blood pressure readings for hypertensive patients in ward",
            [("has_table", "vital_signs"), ("not_denied", None)],
        ),
        (
            "✓ 12 Patient nursing care documentation",
            "Get nursing care documentation completed for my patients today",
            [("has_table", "nursing_assessments"), ("not_denied", None)],
        ),
        (
            "✓ 13 Medication allergy checks",
            "Show medication allergy alerts for patients receiving new prescriptions",
            [("has_table", "allergies"), ("not_denied", None)],
        ),
        (
            "✓ 14 Lab result notification",
            "Get lab results that have come back for patients in my ward",
            [("has_table", "lab_results"), ("not_denied", None)],
        ),
        (
            "✓ 15 Post-operative patient monitoring",
            "Show vital signs for post-operative patients requiring close monitoring",
            [("has_table", "vital_signs"), ("not_denied", None)],
        ),
        (
            "✓ 16 Patient care plans",
            "Get nursing assessments and care plans for patients admitted yesterday",
            [("has_table", "nursing_assessments"), ("not_denied", None)],
        ),
        (
            "✓ 17 Antibiotic prescription tracking",
            "List antibiotic prescriptions for patients in isolation ward",
            [("has_table", "prescriptions"), ("not_denied", None)],
        ),
        (
            "✓ 18 Immunization follow-up",
            "Show patients requiring follow-up immunizations before discharge",
            [("has_table", "immunizations"), ("not_denied", None)],
        ),
        (
            "✓ 19 Patient diagnoses for nursing protocols",
            "Get diagnoses for patients needing specific nursing protocols applied",
            [("has_table", "diagnoses"), ("not_denied", None)],
        ),
        (
            "✓ 20 Ward patient admissions",
            "Show all current patient admissions in nursing ward with status",
            [("has_table", "admissions"), ("not_denied", None)],
        ),
        # ── PHI Masking (5 queries) ───────────────────────────────────────────
        (
            "🔒 21 Lab results with HIV status hidden",
            "Show all patient lab results including complete test panel values",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")],
        ),
        (
            "🔒 22 Infectious disease lab markers hidden",
            "Get lab results for infectious disease screening of admitted patients",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")],
        ),
        (
            "🔒 23 Full lab panel for patients",
            "Show complete diagnostic lab results for patients in my ward",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")],
        ),
        (
            "🔒 24 Sensitive viral test results hidden",
            "Get viral load and infectious marker test results for patients",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")],
        ),
        (
            "🔒 25 All lab result values for patients",
            "Show all laboratory test values for patients receiving antiviral treatment",
            [("has_table", "lab_results"), ("table_has_hidden", "lab_results")],
        ),
        # ── Cross-Domain Denial (5 queries) ───────────────────────────────────
        (
            "✗ 26 DENY: Billing claims denied",
            "Get billing claims for nursing procedures performed this shift",
            [("no_table", "claims"), ("no_table", "revenue_analytics")],
        ),
        (
            "✗ 27 DENY: Insurance data denied",
            "Show insurance reimbursement data for nursing services provided",
            [("no_table", "claims"), ("no_table", "accounts_receivable")],
        ),
        (
            "✗ 28 DENY: HR attendance denied",
            "Get attendance records for nursing staff in my department",
            [("no_table", "attendance"), ("no_table", "leave_records")],
        ),
        (
            "✗ 29 DENY: Employee benefits denied",
            "Show benefits and salary information for nursing staff",
            [("no_table", "benefits"), ("no_table", "positions")],
        ),
        (
            "✗ 30 DENY: Financial and IT data denied",
            "Show department budget KPIs and vendor contracts for nursing",
            [("no_table", "department_kpis"), ("no_table", "vendor_master")],
        ),
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # MARIA FERNANDES — BILLING_STAFF — Clearance 2
    # Domain: Billing only (claims, revenue_analytics, accounts_receivable)
    # ══════════════════════════════════════════════════════════════════════════
    "maria_fernandes": [
        # ── Billing Domain Access (20 queries) ────────────────────────────────
        (
            "✓ 01 Pending insurance claims",
            "Show all pending insurance claims submitted this month",
            [("has_table", "claims"), ("not_denied", None)],
        ),
        (
            "✓ 02 Revenue analytics by department",
            "Get revenue breakdown by department for billing analysis",
            [("has_table", "revenue_analytics"), ("not_denied", None)],
        ),
        (
            "✓ 03 Outstanding accounts receivable",
            "List outstanding accounts receivable older than 30 days",
            [("has_table", "accounts_receivable"), ("not_denied", None)],
        ),
        (
            "✓ 04 Rejected claims for resubmission",
            "Show rejected insurance claims that need to be resubmitted",
            [("has_table", "claims"), ("not_denied", None)],
        ),
        (
            "✓ 05 Claims by insurance provider",
            "Get all claims submitted to insurance companies this week",
            [("has_table", "claims"), ("not_denied", None)],
        ),
        (
            "✓ 06 Revenue by service type",
            "Show revenue analytics broken down by hospital service type",
            [("has_table", "revenue_analytics"), ("not_denied", None)],
        ),
        (
            "✓ 07 Overdue accounts receivable",
            "List accounts receivable overdue by more than 60 days",
            [("has_table", "accounts_receivable"), ("not_denied", None)],
        ),
        (
            "✓ 08 Claim approval status",
            "Get approval status for insurance claims submitted recently",
            [("has_table", "claims"), ("not_denied", None)],
        ),
        (
            "✓ 09 Monthly billing summary",
            "Show total billing value for all claims submitted this month",
            [("has_table", "claims"), ("not_denied", None)],
        ),
        (
            "✓ 10 Accounts receivable payments",
            "Get payment history for accounts receivable settlements",
            [("has_table", "accounts_receivable"), ("not_denied", None)],
        ),
        (
            "✓ 11 Claims with errors",
            "List insurance claims with submission errors requiring correction",
            [("has_table", "claims"), ("not_denied", None)],
        ),
        (
            "✓ 12 Insurance reimbursement received",
            "Show revenue from insurance reimbursements received this quarter",
            [("has_table", "revenue_analytics"), ("not_denied", None)],
        ),
        (
            "✓ 13 Billing records for inpatient",
            "Get billing records for inpatient procedures billed to insurance",
            [("has_table", "claims"), ("not_denied", None)],
        ),
        (
            "✓ 14 Revenue performance metrics",
            "Show revenue performance and collection efficiency metrics",
            [("has_table", "revenue_analytics"), ("not_denied", None)],
        ),
        (
            "✓ 15 Outstanding patient balances",
            "List patient accounts with outstanding balances in receivables",
            [("has_table", "accounts_receivable"), ("not_denied", None)],
        ),
        (
            "✓ 16 Claim submission history",
            "Get history of claims submitted to all insurance companies",
            [("has_table", "claims"), ("not_denied", None)],
        ),
        (
            "✓ 17 Revenue collection rates",
            "Show revenue collection rates by payer and service category",
            [("has_table", "revenue_analytics"), ("not_denied", None)],
        ),
        (
            "✓ 18 Unpaid claims follow-up",
            "List unpaid claims requiring follow-up with insurance providers",
            [("has_table", "claims"), ("not_denied", None)],
        ),
        (
            "✓ 19 Accounts receivable aging",
            "Show accounts receivable aging report for collections team",
            [("has_table", "accounts_receivable"), ("not_denied", None)],
        ),
        (
            "✓ 20 Billing department revenue",
            "Get total revenue and billing activity for hospital departments",
            [("has_table", "revenue_analytics"), ("not_denied", None)],
        ),
        # ── Cross-Domain Denial: Clinical (5 queries) ─────────────────────────
        (
            "✗ 21 DENY: Patient diagnoses denied",
            "Show patient diagnoses for billing code verification purposes",
            [("no_table", "diagnoses"), ("no_table", "admissions")],
        ),
        (
            "✗ 22 DENY: Lab results denied",
            "Get patient lab results for billing audit and charge capture",
            [("no_table", "lab_results"), ("no_table", "lab_orders")],
        ),
        (
            "✗ 23 DENY: Medical records denied",
            "Show patient medical records and clinical notes for billing review",
            [("no_table", "nursing_assessments"), ("no_table", "prescriptions")],
        ),
        (
            "✗ 24 DENY: Patient vitals denied",
            "Get patient vital signs data for billing documentation",
            [("no_table", "vital_signs"), ("no_table", "procedures")],
        ),
        (
            "✗ 25 DENY: Admission records denied",
            "Show patient admission details for inpatient billing verification",
            [("no_table", "admissions"), ("no_table", "diagnoses")],
        ),
        # ── Cross-Domain Denial: HR and IT (5 queries) ────────────────────────
        (
            "✗ 26 DENY: HR attendance denied",
            "Get employee attendance records for billing staff scheduling",
            [("no_table", "attendance"), ("no_table", "leave_records")],
        ),
        (
            "✗ 27 DENY: Employee benefits denied",
            "Show staff salary and benefits information for payroll billing",
            [("no_table", "benefits"), ("no_table", "positions")],
        ),
        (
            "✗ 28 DENY: Vendor master denied",
            "Get vendor contract information for billing department",
            [("no_table", "vendor_master"), ("no_table", "cost_centers")],
        ),
        (
            "✗ 29 DENY: Department KPIs denied",
            "Show department performance KPIs for billing benchmarking",
            [("no_table", "department_kpis")],
        ),
        (
            "✗ 30 DENY: Training records denied",
            "Get employee training records for billing staff compliance",
            [("no_table", "training_records"), ("no_table", "departments")],
        ),
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # VIKRAM JOSHI — ADMIN (IT) — Clearance 2
    # Domain: IT/Analytics only (department_kpis, cost_centers, vendor_master)
    # Hard DENY: clinical data (no access at all, no fallback)
    # ══════════════════════════════════════════════════════════════════════════
    "vikram_joshi": [
        # ── IT/Analytics Domain Access (15 queries) ───────────────────────────
        (
            "✓ 01 Department KPIs overview",
            "Show department performance KPIs for all hospital departments",
            [("has_table", "department_kpis"), ("not_denied", None)],
        ),
        (
            "✓ 02 Cost center budgets",
            "Get cost center budget allocations for current fiscal period",
            [("has_table", "cost_centers"), ("not_denied", None)],
        ),
        (
            "✓ 03 Active vendor contracts",
            "List all active vendor contracts and their expiry dates",
            [("has_table", "vendor_master"), ("not_denied", None)],
        ),
        (
            "✓ 04 Department operational metrics",
            "Show operational performance metrics for hospital departments",
            [("has_table", "department_kpis"), ("not_denied", None)],
        ),
        (
            "✓ 05 Cost center spending",
            "Get spending analysis for all cost centers in the hospital",
            [("has_table", "cost_centers"), ("not_denied", None)],
        ),
        (
            "✓ 06 IT vendor master list",
            "List vendors supplying IT infrastructure and software systems",
            [("has_table", "vendor_master"), ("not_denied", None)],
        ),
        (
            "✓ 07 Department efficiency metrics",
            "Show department efficiency KPIs for administrative review",
            [("has_table", "department_kpis"), ("not_denied", None)],
        ),
        (
            "✓ 08 Budget utilization by cost center",
            "Get budget utilization report for all cost centers",
            [("has_table", "cost_centers"), ("not_denied", None)],
        ),
        (
            "✓ 09 Vendor contract expiry",
            "Show vendor contracts expiring within the next quarter",
            [("has_table", "vendor_master"), ("not_denied", None)],
        ),
        (
            "✓ 10 KPI dashboard for administration",
            "Get performance KPI dashboard data for hospital administration",
            [("has_table", "department_kpis"), ("not_denied", None)],
        ),
        (
            "✓ 11 Cost center variance",
            "Show cost centers with budget variance above threshold",
            [("has_table", "cost_centers"), ("not_denied", None)],
        ),
        (
            "✓ 12 Active procurement vendors",
            "List procurement vendors with active service agreements",
            [("has_table", "vendor_master"), ("not_denied", None)],
        ),
        (
            "✓ 13 Department performance benchmarks",
            "Show department KPI benchmarks for operational review",
            [("has_table", "department_kpis"), ("not_denied", None)],
        ),
        (
            "✓ 14 Cost allocation summary",
            "Get department cost allocation summary for budget planning",
            [("has_table", "cost_centers"), ("not_denied", None)],
        ),
        (
            "✓ 15 Vendor master records",
            "Show vendor master list with active supplier and service contracts",
            [("has_table", "vendor_master"), ("not_denied", None)],
        ),
        # ── HARD DENY: Clinical Data (10 queries) ─────────────────────────────
        (
            "✗ 16 HARD DENY: Patient records denied",
            "Show patient records and admissions for system audit",
            [("no_table", "admissions"), ("no_table", "diagnoses"),
             ("no_table", "lab_results"), ("no_table", "prescriptions")],
        ),
        (
            "✗ 17 HARD DENY: Lab data denied",
            "Get patient lab results and lab orders for database testing",
            [("no_table", "lab_results"), ("no_table", "lab_orders")],
        ),
        (
            "✗ 18 HARD DENY: Nursing data denied",
            "Show nursing assessments and vital signs for system verification",
            [("no_table", "nursing_assessments"), ("no_table", "vital_signs")],
        ),
        (
            "✗ 19 HARD DENY: Prescriptions denied",
            "Get prescription records and medication orders for system audit",
            [("no_table", "prescriptions"), ("no_table", "allergies")],
        ),
        (
            "✗ 20 HARD DENY: Procedures denied",
            "Show surgical procedures and therapy notes for system testing",
            [("no_table", "procedures"), ("no_table", "therapy_notes")],
        ),
        (
            "✗ 21 HARD DENY: Clinical encounters denied",
            "Get patient encounters and clinical notes for IT audit",
            [("no_table", "admissions"), ("no_table", "diagnoses")],
        ),
        (
            "✗ 22 HARD DENY: Immunization records denied",
            "Show patient immunization records for system data check",
            [("no_table", "immunizations"), ("no_table", "allergies")],
        ),
        (
            "✗ 23 HARD DENY: OR schedule denied",
            "Get operating room schedule data for system capacity planning",
            [("no_table", "operating_room_schedules"), ("no_table", "procedures")],
        ),
        # ── Cross-Domain Denial: Billing and HR (7 queries) ───────────────────
        (
            "✗ 24 DENY: Billing claims denied",
            "Show insurance claims submitted for IT department billing audit",
            [("no_table", "claims"), ("no_table", "revenue_analytics")],
        ),
        (
            "✗ 25 DENY: Accounts receivable denied",
            "Get accounts receivable data for hospital financial IT audit",
            [("no_table", "accounts_receivable")],
        ),
        (
            "✗ 26 DENY: HR attendance denied",
            "Show employee attendance records for IT workforce planning",
            [("no_table", "attendance"), ("no_table", "leave_records")],
        ),
        (
            "✗ 27 DENY: Employee benefits denied",
            "Get employee benefits and salary data for IT system testing",
            [("no_table", "benefits"), ("no_table", "positions")],
        ),
        (
            "✗ 28 DENY: Training records denied",
            "Show employee training records for IT system verification",
            [("no_table", "training_records")],
        ),
        (
            "✗ 29 DENY: HR leave records denied",
            "Get staff leave applications and approval records for IT review",
            [("no_table", "leave_records"), ("no_table", "attendance")],
        ),
        (
            "✗ 30 DENY: Revenue analytics denied",
            "Show hospital revenue analytics for IT financial system audit",
            [("no_table", "revenue_analytics"), ("no_table", "claims")],
        ),
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # PRIYA MEHTA — HR_STAFF — Clearance 3
    # Domain: HR only (attendance, leave_records, benefits, departments,
    #                   positions, training_records)
    # ══════════════════════════════════════════════════════════════════════════
    "priya_mehta": [
        # ── HR Domain Access (20 queries) ─────────────────────────────────────
        (
            "✓ 01 Employee attendance report",
            "Show attendance records for all hospital staff this month",
            [("has_table", "attendance"), ("not_denied", None)],
        ),
        (
            "✓ 02 Leave applications pending",
            "Get leave applications pending approval from all departments",
            [("has_table", "leave_records"), ("not_denied", None)],
        ),
        (
            "✓ 03 Employee benefits enrollment",
            "List employee benefits enrollment status for all staff",
            [("has_table", "benefits"), ("not_denied", None)],
        ),
        (
            "✓ 04 Department structure",
            "Show department hierarchy and reporting structure",
            [("has_table", "departments"), ("not_denied", None)],
        ),
        (
            "✓ 05 Mandatory training completion",
            "Get training completion records for mandatory compliance programs",
            [("has_table", "training_records"), ("not_denied", None)],
        ),
        (
            "✓ 06 Employee positions by department",
            "Show employee positions and job titles in each department",
            [("has_table", "positions"), ("not_denied", None)],
        ),
        (
            "✓ 07 Pending leave requests",
            "List all employees with pending leave requests for this week",
            [("has_table", "leave_records"), ("not_denied", None)],
        ),
        (
            "✓ 08 Attendance compliance",
            "Get attendance compliance report for all hospital departments",
            [("has_table", "attendance"), ("not_denied", None)],
        ),
        (
            "✓ 09 Benefits renewal due",
            "List employees whose benefits enrollment requires renewal",
            [("has_table", "benefits"), ("not_denied", None)],
        ),
        (
            "✓ 10 Department headcount",
            "Show headcount and staff distribution across departments",
            [("has_table", "departments"), ("not_denied", None)],
        ),
        (
            "✓ 11 Training programs scheduled",
            "Get training programs scheduled for staff this quarter",
            [("has_table", "training_records"), ("not_denied", None)],
        ),
        (
            "✓ 12 Employee leave balances",
            "Show leave balance for all employees by department",
            [("has_table", "leave_records"), ("not_denied", None)],
        ),
        (
            "✓ 13 Open positions in hospital",
            "List all open positions available in each hospital department",
            [("has_table", "positions"), ("not_denied", None)],
        ),
        (
            "✓ 14 Absenteeism report",
            "Get absenteeism report showing attendance gaps for departments",
            [("has_table", "attendance"), ("not_denied", None)],
        ),
        (
            "✓ 15 Training compliance for nursing",
            "Show training completion status for nursing staff compliance",
            [("has_table", "training_records"), ("not_denied", None)],
        ),
        (
            "✓ 16 Staff in each department",
            "Get employee information for each department in the hospital",
            [("has_table", "departments"), ("not_denied", None)],
        ),
        (
            "✓ 17 Leave utilization patterns",
            "Show leave utilization patterns for all staff categories",
            [("has_table", "leave_records"), ("not_denied", None)],
        ),
        (
            "✓ 18 New employee onboarding",
            "List new employee positions added in last month onboarding",
            [("has_table", "positions"), ("not_denied", None)],
        ),
        (
            "✓ 19 Upcoming training deadlines",
            "Show employees with training deadlines in the next 30 days",
            [("has_table", "training_records"), ("not_denied", None)],
        ),
        (
            "✓ 20 Benefits by employee category",
            "Get benefits utilization by employee grade and category",
            [("has_table", "benefits"), ("not_denied", None)],
        ),
        # ── Cross-Domain Denial: Clinical (5 queries) ─────────────────────────
        (
            "✗ 21 DENY: Patient records denied",
            "Show patient medical records for HR wellness program planning",
            [("no_table", "admissions"), ("no_table", "diagnoses")],
        ),
        (
            "✗ 22 DENY: Lab results denied",
            "Get patient lab results for employee health screening program",
            [("no_table", "lab_results"), ("no_table", "vital_signs")],
        ),
        (
            "✗ 23 DENY: Prescriptions denied",
            "Show patient prescriptions for HR occupational health review",
            [("no_table", "prescriptions"), ("no_table", "nursing_assessments")],
        ),
        (
            "✗ 24 DENY: Clinical procedures denied",
            "Get surgical procedure records for HR staff performance review",
            [("no_table", "procedures"), ("no_table", "allergies")],
        ),
        (
            "✗ 25 DENY: Nursing data denied",
            "Show nursing assessment data for HR staff evaluation program",
            [("no_table", "nursing_assessments"), ("no_table", "immunizations")],
        ),
        # ── Cross-Domain Denial: Billing and IT (5 queries) ───────────────────
        (
            "✗ 26 DENY: Billing claims denied",
            "Get billing claims data for HR department cost analysis",
            [("no_table", "claims"), ("no_table", "revenue_analytics")],
        ),
        (
            "✗ 27 DENY: Insurance revenue denied",
            "Show insurance revenue analytics for HR budgeting purposes",
            [("no_table", "revenue_analytics"), ("no_table", "accounts_receivable")],
        ),
        (
            "✗ 28 DENY: Vendor contracts denied",
            "Get vendor contract information for HR procurement review",
            [("no_table", "vendor_master"), ("no_table", "cost_centers")],
        ),
        (
            "✗ 29 DENY: Department KPIs denied",
            "Show department performance KPIs for HR assessment metrics",
            [("no_table", "department_kpis")],
        ),
        (
            "✗ 30 DENY: Accounts receivable denied",
            "Get accounts receivable data for HR salary reconciliation",
            [("no_table", "accounts_receivable"), ("no_table", "claims")],
        ),
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_token_and_context(user_key: str):
    u = USERS[user_key]
    r = requests.post(f"{L1}/mock/token",
        params={"oid": u["oid"], "name": u["name"], "email": u["email"], "include_mfa": "true"},
        json={"roles": u["roles"], "groups": u["groups"]}, timeout=5)
    r.raise_for_status()
    jwt_token = r.json()["token"]

    r2 = requests.post(f"{L1}/identity/resolve",
        headers={"Authorization": f"Bearer {jwt_token}"}, timeout=5)
    r2.raise_for_status()
    resolve = r2.json()
    ctx_id = resolve["context_token_id"]

    r3 = requests.get(f"{L1}/identity/verify/{ctx_id}",
        headers={"Authorization": f"Bearer {jwt_token}"}, timeout=5)
    r3.raise_for_status()
    full = r3.json()

    expiry_ts = int(datetime.fromisoformat(full["expires_at"].replace("Z", "+00:00")).timestamp())
    sc = {
        "user_id":           full["identity"]["oid"],
        "effective_roles":   full["authorization"]["effective_roles"],
        "department":        full["org_context"]["department"],
        "clearance_level":   full["authorization"]["clearance_level"],
        "session_id":        full["request_metadata"]["session_id"],
        "context_signature": resolve["context_signature"],
        "facility_id":       full["org_context"]["facility_ids"][0] if full["org_context"].get("facility_ids") else "FAC-001",
    }
    return jwt_token, sc, expiry_ts


def make_service_token():
    svc_id = "test-service"; role = "pipeline_reader"; issued = str(int(time.time()))
    payload = f"{svc_id}|{role}|{issued}"
    sig = hmac.new(L3_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def query_l3(user_key: str, nl_query: str):
    try:
        _, sc, expiry_ts = get_token_and_context(user_key)
    except Exception as e:
        return {"error": f"L1 auth failed: {e}", "_http_status": 0}

    payload = {
        "question": nl_query,
        "security_context": {
            "user_id":           sc["user_id"],
            "effective_roles":   sc["effective_roles"],
            "department":        sc["department"],
            "clearance_level":   sc["clearance_level"],
            "session_id":        sc["session_id"],
            "context_signature": sc["context_signature"],
            "context_expiry":    expiry_ts,
            "facility_id":       sc.get("facility_id", "FAC-001"),
        },
        "request_id": f"test30-{user_key}-{int(time.time())}",
    }
    try:
        r = requests.post(f"{L3}/api/v1/retrieval/resolve",
            json=payload, headers={"Authorization": f"Bearer {make_service_token()}"}, timeout=90)
        result = r.json()
        result["_http_status"] = r.status_code
        return result
    except Exception as e:
        return {"error": str(e), "_http_status": 0}


def extract_tables(resp: dict) -> list[str]:
    inner = resp.get("data", resp)
    if isinstance(inner, dict):
        inner = inner.get("data", inner)
    schema = inner.get("filtered_schema", [])
    if isinstance(schema, list):
        return [t.get("table_name", "") for t in schema]
    return []


def hidden_count_for(resp: dict, table_name: str) -> int:
    inner = resp.get("data", resp)
    if isinstance(inner, dict):
        inner = inner.get("data", inner)
    for t in (inner.get("filtered_schema", []) or []):
        if table_name in t.get("table_name", ""):
            return t.get("hidden_column_count", 0) or 0
    return 0


# ── Runner ────────────────────────────────────────────────────────────────────

def run():
    grand_total = grand_pass = grand_fail = 0
    user_summaries = []
    all_failures = []

    print("\n" + "═" * 76)
    print("  APOLLO HOSPITALS — 30-QUERY ROLE-BASED ACCESS TEST SUITE (150 TOTAL)")
    print("═" * 76)

    for user_key, cases in TEST_CASES.items():
        u = USERS[user_key]
        u_pass = u_fail = 0
        print(f"\n{'─' * 76}")
        print(f"  {u['name']}  |  {u['role_label']}  |  Clearance {u['clearance']}")
        print(f"{'─' * 76}")

        for desc, query, checks in cases:
            grand_total += 1
            resp    = query_l3(user_key, query)
            tables  = extract_tables(resp)
            http_st = resp.get("_http_status", 0)
            err_c   = resp.get("error_code")
            has_err = err_c in ("NO_RELEVANT_TABLES", "RESTRICTED_DATA_REQUEST")

            results = []
            for ctype, cval in checks:
                if ctype == "has_table":
                    ok = any(cval in t for t in tables)
                    msg = f"has_table({cval}) got {tables}"
                elif ctype == "no_table":
                    ok = not any(cval in t for t in tables)
                    msg = f"no_table({cval}) got {tables}"
                elif ctype == "table_has_hidden":
                    cnt = hidden_count_for(resp, cval)
                    ok  = cnt >= 1
                    msg = f"table_has_hidden({cval}) count={cnt}"
                elif ctype == "not_denied":
                    ok  = bool(tables) and not has_err
                    msg = f"not_denied: http={http_st} err={err_c} tables={tables}"
                elif ctype == "denied":
                    ok  = has_err or http_st in (403, 404) or not tables
                    msg = f"denied: http={http_st} err={err_c}"
                else:
                    ok = False; msg = f"unknown check: {ctype}"
                results.append((ctype, cval, ok, msg))

            passed = all(r[2] for r in results)
            if passed:
                grand_pass += 1; u_pass += 1
                tbl_str = ", ".join(tables) if tables else "∅ (none)"
                print(f"  ✅ {desc}")
                print(f"       tables=[{tbl_str}]")
            else:
                grand_fail += 1; u_fail += 1
                print(f"  ❌ {desc}")
                for ctype, cval, ok, msg in results:
                    if not ok:
                        print(f"       ⚠  FAIL: {msg}")
                all_failures.append((u["name"], desc, results, tables))

        u_total = u_pass + u_fail
        user_summaries.append((u["name"], u["role_label"], u_pass, u_total))
        print(f"\n  → User result: {u_pass}/{u_total} passed")

    # ── Final Summary ─────────────────────────────────────────────────────────
    print(f"\n{'═' * 76}")
    print("  FINAL RESULTS")
    print(f"{'═' * 76}")
    for name, role, p, t in user_summaries:
        bar = "█" * p + "░" * (t - p)
        print(f"  {name:<22} [{bar}] {p:2}/{t}")
    print(f"{'─' * 76}")
    print(f"  TOTAL: {grand_pass}/{grand_total} passed  |  {grand_fail} failed")
    print(f"{'═' * 76}\n")

    if all_failures:
        print("FAILED TESTS DETAIL:")
        for name, desc, results, tables in all_failures:
            print(f"\n  [{name}] {desc}")
            print(f"    tables={tables}")
            for ctype, cval, ok, msg in results:
                if not ok:
                    print(f"    ✗ {msg}")

    return grand_pass, grand_total


if __name__ == "__main__":
    p, t = run()
    sys.exit(0 if p == t else 1)
