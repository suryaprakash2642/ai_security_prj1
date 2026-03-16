# Apollo Hospitals — Demo Query Test Results

**Date**: 2026-03-15 16:39:28  
**Result**: 23/24 (96%)  
**Pipeline**: L1 -> L3 -> L4 (real envelope) -> L5 -> L6 -> L7  

---

## Summary

| # | Role | Question | Expected | Result | Outcome |
|---|------|----------|----------|--------|---------|
| 1 | doctor | Show total number of patients grouped by gender from th | >=0 rows | PASS | 2 rows |
| 2 | doctor | List the top 10 medications from prescriptions ordered  | >=0 rows | PASS | 10 rows |
| 3 | doctor | Show the total number of lab results grouped by test na | >=0 rows | PASS | 20 rows |
| 4 | doctor | List the 20 most recent encounters with patient details | >=0 rows | PASS | 20 rows |
| 5 | doctor | How many appointments are scheduled by department? | >=0 rows | PASS | 0 rows (CANNOT_ANSWER) |
| 6 | billing | Show all claims with total amount greater than 500000 | >=3 rows | PASS | 798 rows |
| 7 | billing | What is the total payment amount grouped by payment met | >=3 rows | PASS | 6 rows |
| 8 | billing | How many claims are there grouped by claim type and sta | >=3 rows | PASS | 15 rows |
| 9 | billing | List the top 10 insurance plans by number of claims | >=5 rows | PASS | 10 rows |
| 10 | billing | Show total billed amount by month for the last year | >=3 rows | PASS | 12 rows |
| 11 | hr | How many employees are there grouped by department_id? | >=3 rows | PASS | 25 rows |
| 12 | hr | How many employees are on leave right now? | >=0 rows | PASS | 1 rows |
| 13 | hr | Show the top 10 highest paid employees by gross salary | >=5 rows | PASS | 10 rows |
| 14 | revenue | Show total claim amount grouped by claim type from the  | >=2 rows | PASS | 3 rows |
| 15 | revenue | What is the total payment amount grouped by payment met | >=3 rows | PASS | 6 rows |
| 16 | revenue | List the top 10 payer contracts by discount percentage | >=2 rows | PASS | 10 rows |
| 17 | researcher | Show all quality metrics grouped by metric name | >=3 rows | PASS | 14 rows |
| 18 | researcher | Show population health data grouped by disease category | >=0 rows | PASS | 0 rows |
| 19 | researcher | List all research cohorts with their enrollment count | >=0 rows | PASS | 8 rows |
| 20 | billing | Show all patients admitted this month | DENY | FAIL | GOT 0 ROWS |
| 21 | doctor | Show the total payroll cost per department | DENY | PASS | DENIED |
| 22 | hr | Show all patients with abnormal lab results | DENY | PASS | DENIED |
| 23 | revenue | Show all employee leave records | DENY | PASS | DENIED |
| 24 | researcher | Show employee salary details from the payroll table | DENY | PASS | DENIED |

---

## Dr. Rajesh Patel (Attending Physician)

### Q1: Show total number of patients grouped by gender from the patients table
**Status**: PASS  
**Expected**: >= 0 rows  

**Generated SQL**:
```sql
SELECT UPPER(gender) AS gender, COUNT(*) AS total_patients
FROM patients
GROUP BY UPPER(gender)
LIMIT 1000
```
**Rows returned**: 2  
**Target DB**: apollohis | **Dialect**: mysql  

**Sample data** (2 of 2 rows):
| {'name': 'gender', ' | {'name': 'total_pati |
| --- | --- |
| FEMALE | 262 |
| MALE | 238 |

### Q2: List the top 10 medications from prescriptions ordered by frequency
**Status**: PASS  
**Expected**: >= 0 rows  

**Generated SQL**:
```sql
SELECT
  p.medication_name,
  COUNT(*) AS prescription_count
FROM
  prescriptions p
GROUP BY
  p.medication_name
ORDER BY
  prescription_count DESC
LIMIT 10
```
**Rows returned**: 10  
**Target DB**: apollohis | **Dialect**: mysql  

**Sample data** (5 of 10 rows):
| {'name': 'medication | {'name': 'prescripti |
| --- | --- |
| Sitagliptin 100mg | 115 |
| Omeprazole 20mg | 111 |
| Metformin 500mg | 111 |
| Atorvastatin 20mg | 109 |
| Enoxaparin 40mg | 107 |

### Q3: Show the total number of lab results grouped by test name
**Status**: PASS  
**Expected**: >= 0 rows  

**Generated SQL**:
```sql
SELECT lr.test_name, COUNT(*) AS total_lab_results
FROM lab_results lr
GROUP BY lr.test_name
ORDER BY total_lab_results DESC
LIMIT 1000
```
**Rows returned**: 20  
**Target DB**: apollohis | **Dialect**: mysql  

**Sample data** (5 of 20 rows):
| {'name': 'test_name' | {'name': 'total_lab_ |
| --- | --- |
| Comprehensive Metabo | 210 |
| Erythrocyte Sediment | 204 |
| Glycated Hemoglobin | 202 |
| B-type Natriuretic P | 191 |
| Renal Function Test | 191 |

### Q4: List the 20 most recent encounters with patient details
**Status**: PASS  
**Expected**: >= 0 rows  

**Generated SQL**:
```sql
SELECT 
  e.encounter_id,
  e.admission_date,
  e.discharge_date,
  e.encounter_type,
  e.status,
  e.department_id,
  e.unit_id,
  e.treating_provider_id,
  e.patient_id,
  p.full_name,
  p.gender,
  p.date_of_birth,
  p.phone_primary,
  p.email
FROM encounters e
JOIN patients p ON e.patient_id = p.patient_id
WHERE (e.treating_provider_id = 'DR-0001' OR e.unit_id = 'UNIT-1A-APJH')
  AND e.facility_id = 'FAC-001'
ORDER BY e.admission_date DESC
LIMIT 20
```
**Rows returned**: 20  
**Target DB**: apollohis | **Dialect**: mysql  

**Sample data** (5 of 20 rows):
| {'name': 'encounter_ | {'name': 'admission_ | {'name': 'discharge_ | {'name': 'encounter_ | {'name': 'status', ' | {'name': 'department | {'name': 'unit_id',  | {'name': 'treating_p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ENC-FA5661AE | 2026-01-23 22:10:00 | 2026-02-11 08:10:00 | DAY_SURGERY | DISCHARGED | DEPT-EMER-APJH | UNIT-1A-APJH | DR-0124 |
| ENC-DF24B869 | 2026-01-06 14:02:00 | 2026-01-08 01:02:00 | INPATIENT | DISCHARGED | DEPT-NEPH-APJH | UNIT-1A-APJH | DR-0085 |
| ENC-5F61919B | 2025-12-04 18:08:00 | 2025-12-24 21:08:00 | INPATIENT | DISCHARGED | DEPT-OBGY-APJH | UNIT-1A-APJH | DR-0080 |
| ENC-A913098D | 2025-11-30 16:30:00 | 2025-12-19 16:30:00 | OUTPATIENT | DISCHARGED | DEPT-PHAR-APJH | UNIT-1A-APJH | DR-0039 |
| ENC-994723BB | 2025-11-28 08:24:00 | None | EMERGENCY | ACTIVE | DEPT-PHAR-APJH | UNIT-1A-APJH | DR-0099 |

### Q5: How many appointments are scheduled by department?
**Status**: PASS  
**Expected**: >= 0 rows  

## Maria Fernandes (Billing Clerk)

### Q6: Show all claims with total amount greater than 500000
**Status**: PASS  
**Expected**: >= 3 rows  

**Generated SQL**:
```sql
SELECT 
  c.claim_id,
  c.claim_date,
  c.patient_id,
  c.encounter_id,
  c.total_amount,
  c.claim_status,
  c.claim_type,
  c.submitted_date,
  c.approved_amount,
  c.denied_amount,
  c.denial_reason,
  c.primary_dx_code,
  c.procedure_codes,
  c.insurance_plan_id,
  c.payer_id,
  c.adjudicated_date,
  c.payment_date,
  c.created_at
FROM claims c
WHERE c.total_amount > 500000
LIMIT 1000
```
**Rows returned**: 798  
**Target DB**: apollo_financial | **Dialect**: postgresql  

**Sample data** (5 of 798 rows):
| {'name': 'claim_id', | {'name': 'claim_date | {'name': 'patient_id | {'name': 'encounter_ | {'name': 'total_amou | {'name': 'claim_stat | {'name': 'claim_type | {'name': 'submitted_ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CLM-2AE8D200 | 2025-11-30 | PAT-B9F9340D | ENC-C795E56C | 721764.00 | APPROVED | Inpatient | 2025-11-30 |
| CLM-78940A9C | 2025-06-05 | PAT-979CCABA | ENC-53E5CC03 | 1217909.00 | APPROVED | Inpatient | 2025-06-05 |
| CLM-498CB042 | 2025-05-07 | PAT-715D5F1F | ENC-071B7547 | 1289448.00 | APPROVED | Emergency | 2025-05-07 |
| CLM-5856744B | 2026-01-17 | PAT-560CC997 | ENC-C6F798B3 | 682032.00 | IN_REVIEW | Outpatient | 2026-01-17 |
| CLM-76433E2F | 2025-03-06 | PAT-AB9D3B2F | ENC-7EA00EBA | 1257998.00 | APPROVED | Outpatient | 2025-03-06 |

### Q7: What is the total payment amount grouped by payment method?
**Status**: PASS  
**Expected**: >= 3 rows  

**Generated SQL**:
```sql
SELECT payment_method, COALESCE(SUM(payment_amount), 0) AS total_payment_amount FROM payments GROUP BY payment_method ORDER BY total_payment_amount DESC LIMIT 10000
```
**Rows returned**: 6  
**Target DB**: apollo_financial | **Dialect**: postgresql  

**Sample data** (5 of 6 rows):
| {'name': 'payment_me | {'name': 'total_paym |
| --- | --- |
| Cheque | 68430379.00 |
| UPI | 64829513.00 |
| Cash | 60829394.00 |
| Insurance_Transfer | 59888841.00 |
| Card | 55116896.00 |

### Q8: How many claims are there grouped by claim type and status?
**Status**: PASS  
**Expected**: >= 3 rows  

**Generated SQL**:
```sql
SELECT UPPER(c.claim_type) AS claim_type, UPPER(c.claim_status) AS claim_status, COUNT(*) AS claim_count FROM claims AS c GROUP BY UPPER(c.claim_type), UPPER(c.claim_status) ORDER BY claim_count DESC LIMIT 10000
```
**Rows returned**: 15  
**Target DB**: apollo_financial | **Dialect**: postgresql  

**Sample data** (5 of 15 rows):
| {'name': 'claim_type | {'name': 'claim_stat | {'name': 'claim_coun |
| --- | --- | --- |
| OUTPATIENT | APPROVED | 233 |
| INPATIENT | APPROVED | 214 |
| EMERGENCY | APPROVED | 200 |
| OUTPATIENT | SUBMITTED | 65 |
| OUTPATIENT | PARTIALLY_APPROVED | 63 |

### Q9: List the top 10 insurance plans by number of claims
**Status**: PASS  
**Expected**: >= 5 rows  

**Generated SQL**:
```sql
SELECT
  c.insurance_plan_id,
  COUNT(*) AS claim_count
FROM claims c
GROUP BY c.insurance_plan_id
ORDER BY claim_count DESC
LIMIT 10
```
**Rows returned**: 10  
**Target DB**: apollo_financial | **Dialect**: postgresql  

**Sample data** (5 of 10 rows):
| {'name': 'insurance_ | {'name': 'claim_coun |
| --- | --- |
| PLN-DCF51682 | 44 |
| PLN-97B57D51 | 43 |
| PLN-362DD11C | 42 |
| PLN-902184B0 | 42 |
| PLN-056C33FE | 40 |

### Q10: Show total billed amount by month for the last year
**Status**: PASS  
**Expected**: >= 3 rows  

**Generated SQL**:
```sql
SELECT DATE_TRUNC('MONTH', c.claim_date) AS month, COALESCE(SUM(c.total_amount), 0) AS total_billed_amount FROM claims AS c WHERE c.claim_date >= (CURRENT_DATE - INTERVAL '1 YEAR') GROUP BY DATE_TRUNC('MONTH', c.claim_date) ORDER BY month ASC LIMIT 10000
```
**Rows returned**: 12  
**Target DB**: apollo_financial | **Dialect**: postgresql  

**Sample data** (5 of 12 rows):
| {'name': 'month', 't | {'name': 'total_bill |
| --- | --- |
| 2025-03-01 00:00:00+ | 35043267.00 |
| 2025-04-01 00:00:00+ | 74878704.00 |
| 2025-05-01 00:00:00+ | 75571144.00 |
| 2025-06-01 00:00:00+ | 79683863.00 |
| 2025-07-01 00:00:00+ | 67353496.00 |

## Priya Mehta (HR Manager)

### Q11: How many employees are there grouped by department_id?
**Status**: PASS  
**Expected**: >= 3 rows  

**Generated SQL**:
```sql
SELECT e.department_id, COUNT(*) AS employee_count FROM employees AS e WHERE e.facility_id = 'FAC-001' GROUP BY e.department_id ORDER BY employee_count DESC LIMIT 10000
```
**Rows returned**: 25  
**Target DB**: apollohr | **Dialect**: mysql  

**Sample data** (5 of 25 rows):
| {'name': 'department | {'name': 'employee_c |
| --- | --- |
| DEPT-DERM | 9 |
| DEPT-ANES | 7 |
| DEPT-HR | 6 |
| DEPT-PULM | 6 |
| DEPT-EMER | 6 |

### Q12: How many employees are on leave right now?
**Status**: PASS  
**Expected**: >= 0 rows  

**Generated SQL**:
```sql
SELECT COUNT(*) AS employees_on_leave_now FROM leave_records AS lr WHERE lr.status = 'approved' AND CURDATE() BETWEEN lr.start_date AND lr.end_date LIMIT 1000
```
**Rows returned**: 1  
**Target DB**: apollohr | **Dialect**: mysql  

**Sample data** (1 of 1 rows):
| {'name': 'employees_ |
| --- |
| 0 |

### Q13: Show the top 10 highest paid employees by gross salary
**Status**: PASS  
**Expected**: >= 5 rows  

**Generated SQL**:
```sql
SELECT e.employee_id, e.full_name, p.gross_salary
FROM employees e
JOIN payroll p ON e.employee_id = p.employee_id
WHERE e.facility_id = 'FAC-001'
ORDER BY p.gross_salary DESC
LIMIT 10
```
**Rows returned**: 10  
**Target DB**: apollohr | **Dialect**: mysql  

**Sample data** (5 of 10 rows):
| {'name': 'employee_i | {'name': 'full_name' | {'name': 'gross_sala |
| --- | --- | --- |
| DR-0102 | Yogesh Gupta | 596242.00 |
| DR-0040 | Vandana Verma | 584411.00 |
| DR-0027 | Ritvik Menon | 582385.00 |
| DR-0062 | Swati Gandhi | 581194.00 |
| DR-0004 | Divya Agarwal | 579478.00 |

## James Thomas (Revenue Cycle Manager)

### Q14: Show total claim amount grouped by claim type from the claims table
**Status**: PASS  
**Expected**: >= 2 rows  

**Generated SQL**:
```sql
SELECT c.claim_type, SUM(c.total_amount) AS total_claim_amount FROM claims AS c GROUP BY c.claim_type ORDER BY total_claim_amount DESC LIMIT 10000
```
**Rows returned**: 3  
**Target DB**: apollo_financial | **Dialect**: postgresql  
**Aggregation-only tables in envelope**: apollo_financial.public.claims, apollo_financial.public.claim_line_items, apollo_financial.public.payments, apollo_financial.public.insurance_plans, apollo_financial.public.payer_contracts, apollo_analytics.public.encounter_summaries  
**Denied columns for apollo_financial.public.claims**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.claim_line_items**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.payments**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.insurance_plans**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.payer_contracts**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_analytics.public.encounter_summaries**: dob, full_name, mrn, patient_id, patient_mrn, ssn  

**Sample data** (3 of 3 rows):
| {'name': 'claim_type | {'name': 'total_clai |
| --- | --- |
| Outpatient | 340626137.00 |
| Inpatient | 293000384.00 |
| Emergency | 267546668.00 |

### Q15: What is the total payment amount grouped by payment method?
**Status**: PASS  
**Expected**: >= 3 rows  

**Generated SQL**:
```sql
SELECT payment_method, SUM(payment_amount) AS total_payment_amount FROM payments GROUP BY payment_method ORDER BY total_payment_amount DESC LIMIT 10000
```
**Rows returned**: 6  
**Target DB**: apollo_financial | **Dialect**: postgresql  
**Aggregation-only tables in envelope**: apollo_financial.public.insurance_plans, apollo_financial.public.payments, apollo_financial.public.claims, apollo_financial.public.payer_contracts, apollo_financial.public.claim_line_items, apollo_analytics.public.encounter_summaries, apollo_analytics.public.quality_metrics  
**Denied columns for apollo_financial.public.insurance_plans**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.payments**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.claims**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.payer_contracts**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.claim_line_items**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_analytics.public.encounter_summaries**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_analytics.public.quality_metrics**: dob, full_name, mrn, patient_id, patient_mrn, ssn  

**Sample data** (5 of 6 rows):
| {'name': 'payment_me | {'name': 'total_paym |
| --- | --- |
| Cheque | 68430379.00 |
| UPI | 64829513.00 |
| Cash | 60829394.00 |
| Insurance_Transfer | 59888841.00 |
| Card | 55116896.00 |

### Q16: List the top 10 payer contracts by discount percentage
**Status**: PASS  
**Expected**: >= 2 rows  

**Generated SQL**:
```sql
SELECT
  payer_name,
  contract_id,
  discount_percent,
  contract_type,
  is_active
FROM
  payer_contracts
GROUP BY
  payer_name,
  contract_id,
  discount_percent,
  contract_type,
  is_active
ORDER BY
  discount_percent DESC
LIMIT 10
```
**Rows returned**: 10  
**Target DB**: apollo_financial | **Dialect**: postgresql  
**Aggregation-only tables in envelope**: apollo_financial.public.payer_contracts, apollo_financial.public.insurance_plans, apollo_financial.public.claims, apollo_financial.public.payments, apollo_financial.public.claim_line_items, apollo_analytics.public.encounter_summaries  
**Denied columns for apollo_financial.public.payer_contracts**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.insurance_plans**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.claims**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.payments**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_financial.public.claim_line_items**: dob, full_name, mrn, patient_id, patient_mrn, ssn  
**Denied columns for apollo_analytics.public.encounter_summaries**: dob, full_name, mrn, patient_id, patient_mrn, ssn  

**Sample data** (5 of 10 rows):
| {'name': 'payer_name | {'name': 'contract_i | {'name': 'discount_p | {'name': 'contract_t | {'name': 'is_active' |
| --- | --- | --- | --- | --- |
| Religare Health Insu | CON-70F61E3A | 25.00 | Private | 1 |
| HDFC ERGO Health Ins | CON-0B310644 | 22.00 | Private | 1 |
| CGHS (Central Govt H | CON-C5F7E574 | 21.00 | Government | 1 |
| Apollo Munich Health | CON-3F74E88F | 21.00 | Private | 1 |
| ICICI Lombard Health | CON-CDF3D6A3 | 20.00 | Private | 1 |

## Dr. Anirban Das (Clinical Researcher)

### Q17: Show all quality metrics grouped by metric name
**Status**: PASS  
**Expected**: >= 3 rows  

**Generated SQL**:
```sql
SELECT qm.metric_name, COUNT(qm.metric_id) AS metric_count, AVG(qm.metric_value) AS avg_metric_value, AVG(qm.benchmark_value) AS avg_benchmark_value, AVG(qm.target_value) AS avg_target_value, SUM(qm.numerator) AS total_numerator, SUM(qm.denominator) AS total_denominator FROM quality_metrics AS qm WHERE qm.facility_id = 'FAC-005' GROUP BY qm.metric_name ORDER BY avg_metric_value DESC LIMIT 10000
```
**Rows returned**: 14  
**Target DB**: apollo_analytics | **Dialect**: postgresql  
**Aggregation-only tables in envelope**: apollo_analytics.public.encounter_summaries  
**Denied columns for apollo_analytics.public.encounter_summaries**: aadhaar_number, dob, full_name, mrn, ssn  

**Sample data** (5 of 14 rows):
| {'name': 'metric_nam | {'name': 'metric_cou | {'name': 'avg_metric | {'name': 'avg_benchm | {'name': 'avg_target | {'name': 'total_nume | {'name': 'total_deno |
| --- | --- | --- | --- | --- | --- | --- |
| Discharge Instructio | 12 | 44.8600833333333333 | 44.2758333333333333 | 49.1666666666666667 | 3838 | 11662 |
| ED Wait Time (minute | 12 | 42.8595000000000000 | 43.5546666666666667 | 44.7554166666666667 | 2829 | 9516 |
| Surgical Site Infect | 12 | 31.1994166666666667 | 32.6570833333333333 | 34.0055833333333333 | 2847 | 12090 |
| HAI Rate (Hospital A | 12 | 28.8033333333333333 | 29.1223333333333333 | 30.4413333333333333 | 3191 | 14502 |
| 30-Day Readmission R | 12 | 28.3052500000000000 | 28.2594166666666667 | 25.5862500000000000 | 3208 | 15915 |

### Q18: Show population health data grouped by disease category
**Status**: PASS  
**Expected**: >= 0 rows  

**Generated SQL**:
```sql
SELECT ph.disease_category, SUM(ph.encounter_count) AS total_encounters, SUM(ph.patient_count) AS total_patients, AVG(ph.avg_cost) AS avg_cost, AVG(ph.avg_los) AS avg_length_of_stay, AVG(ph.complication_rate) AS avg_complication_rate FROM population_health AS ph WHERE ph.facility_id = 'FAC-005' GROUP BY ph.disease_category ORDER BY total_encounters DESC LIMIT 10000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  
**Aggregation-only tables in envelope**: apollo_analytics.public.encounter_summaries  
**Denied columns for apollo_analytics.public.encounter_summaries**: aadhaar_number, dob, full_name, mrn, ssn  

### Q19: List all research cohorts with their enrollment count
**Status**: PASS  
**Expected**: >= 0 rows  

**Generated SQL**:
```sql
SELECT r.cohort_id, r.cohort_name, COALESCE(r.patient_count, 0) AS enrollment_count
FROM research_cohorts r
LIMIT 1000
```
**Rows returned**: 8  
**Target DB**: apollo_analytics | **Dialect**: postgresql  
**Aggregation-only tables in envelope**: apollo_analytics.public.encounter_summaries  
**Denied columns for apollo_analytics.public.encounter_summaries**: aadhaar_number, dob, full_name, mrn, ssn  

**Sample data** (5 of 8 rows):
| {'name': 'cohort_id' | {'name': 'cohort_nam | {'name': 'enrollment |
| --- | --- | --- |
| 21588a47-2369-4281-8 | Outcomes of TAVI in  | 461 |
| 7566ee4f-10db-4e62-a | Immunotherapy Respon | 483 |
| 761b207d-180d-4ea6-b | Deep Brain Stimulati | 181 |
| 8cc0077a-c095-47c4-a | Long-term Outcomes o | 171 |
| 48c3494f-52fd-4b97-8 | Diabetes Reversal Th | 114 |

## Maria Fernandes (Billing Clerk)

### Q20: Show all patients admitted this month
**Status**: FAIL  
**Expected**: DENY  
**Problem**: Query should have been denied but returned data  

**Generated SQL**:
```sql
SELECT department_id, department_name, facility_id, facility_name, report_month, total_admissions FROM encounter_summaries WHERE facility_id = 'FAC-001' AND UPPER(encounter_type) = UPPER('INPATIENT') AND DATE_TRUNC('MONTH', report_month) = DATE_TRUNC('MONTH', CURRENT_DATE) ORDER BY total_admissions DESC LIMIT 1000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

## Dr. Rajesh Patel (Attending Physician)

### Q21: Show the total payroll cost per department
**Status**: PASS  
**Expected**: DENY  
**Blocked at**: L5 — CANNOT_ANSWER  

## Priya Mehta (HR Manager)

### Q22: Show all patients with abnormal lab results
**Status**: PASS  
**Expected**: DENY  
**Blocked at**: L5 — CANNOT_ANSWER  

## James Thomas (Revenue Cycle Manager)

### Q23: Show all employee leave records
**Status**: PASS  
**Expected**: DENY  
**Blocked at**: L5 — CANNOT_ANSWER  

## Dr. Anirban Das (Clinical Researcher)

### Q24: Show employee salary details from the payroll table
**Status**: PASS  
**Expected**: DENY  
**Blocked at**: L5 — CANNOT_ANSWER  
