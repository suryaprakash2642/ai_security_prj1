# Apollo Hospitals - Product Test QA Guide Results

**Date**: 2026-03-15 17:01:22  
**Result**: 44/50 (88%)  
**Total Time**: 1291s  
**Pipeline**: L1 -> L3 -> L4 (real envelope) -> L5 -> L6 -> L7  
**Database**: apollo_analytics (PostgreSQL)  

## User Summary

| User | Role | Pass | Total | % |
|------|------|------|-------|---|
| Dr. Rajesh Patel (Attending Physician, C | doctor | 8 | 10 | 80% |
| Anita Kumar (Registered Nurse, Cardiolog | nurse | 10 | 10 | 100% |
| Maria Fernandes (Billing Clerk) | billing | 7 | 10 | 70% |
| Vikram Joshi (IT Administrator) | it_admin | 10 | 10 | 100% |
| Priya Mehta (HR Manager) | hr | 9 | 10 | 90% |

---

## All Tests

| # | User | QID | Question | Min Rows | Result | Time | Outcome |
|---|------|-----|----------|----------|--------|------|---------|
| 1 | doctor | Q01 | How many total inpatient encounters were reco | 1 | PASS | 51.9s | 1 rows |
| 2 | doctor | Q02 | What is the average length of stay for cardia | 1 | PASS | 22.5s | 1 rows |
| 3 | doctor | Q03 | Which departments at FAC-001 had a readmissio | 0 | PASS | 23.6s | 24 rows |
| 4 | doctor | Q04 | Show the mortality rate trend for FAC-001 ove | 1 | PASS | 24.2s | 120 rows |
| 5 | doctor | Q05 | What are all Patient_Safety quality metrics c | 0 | PASS | 23.7s | 27 rows |
| 6 | doctor | Q06 | Compare bed occupancy between Cardiology and  | 1 | PASS | 23.8s | 39 rows |
| 7 | doctor | Q07 | Show total revenue per encounter type for Car | 1 | FAIL | 26.8s | 0 rows |
| 8 | doctor | Q08 | What is the disease burden by age group for c | 1 | PASS | 22.5s | 6 rows |
| 9 | doctor | Q09 | List all active research cohorts in the Cardi | 1 | FAIL | 26.0s | 0 rows |
| 10 | doctor | Q10 | Show monthly encounter trend for Cardiology a | 1 | PASS | 22.5s | 5 rows |
| 11 | nurse | Q01 | What is the current bed occupancy rate at FAC | 0 | PASS | 27.7s | 1 rows |
| 12 | nurse | Q02 | Show total admissions vs discharges for Cardi | 0 | PASS | 24.4s | 0 rows |
| 13 | nurse | Q03 | What is the readmission count for FAC-001 Car | 0 | PASS | 23.8s | 1 rows |
| 14 | nurse | Q04 | Show average length of stay per department at | 0 | PASS | 22.7s | 0 rows |
| 15 | nurse | Q05 | List all Patient_Safety quality metrics for F | 0 | PASS | 22.7s | 0 rows |
| 16 | nurse | Q06 | Compare bed occupancy between FAC-001 and FAC | 0 | PASS | 16.8s | 0 rows (CANNOT_ANSWER) |
| 17 | nurse | Q07 | Show monthly encounter trend for Cardiology a | 1 | PASS | 22.4s | 5 rows |
| 18 | nurse | Q08 | What is the population health burden for the  | 1 | PASS | 23.3s | 40 rows |
| 19 | nurse | Q09 | How many total encounters were recorded at ea | 0 | PASS | 21.9s | 0 rows |
| 20 | nurse | Q10 | What quality metrics at FAC-001 are currently | 0 | PASS | 22.3s | 0 rows |
| 21 | billing | Q01 | What is the total revenue generated at FAC-00 | 0 | PASS | 37.6s | 1 rows |
| 22 | billing | Q02 | Show average revenue per encounter for each d | 1 | PASS | 24.0s | 16 rows |
| 23 | billing | Q03 | What is the total revenue trend for Apollo Ju | 1 | FAIL | 27.6s | 0 rows |
| 24 | billing | Q04 | Which Apollo facility has the highest total r | 1 | FAIL | 22.3s | 0 rows |
| 25 | billing | Q05 | Show revenue breakdown by encounter type at F | 1 | PASS | 26.4s | 3 rows |
| 26 | billing | Q06 | Compare average revenue per encounter for Car | 1 | PASS | 27.3s | 39 rows |
| 27 | billing | Q07 | What is the total revenue across all 8 Apollo | 1 | FAIL | 17.2s | DENIED at L5: CANNOT_ANSWER |
| 28 | billing | Q08 | Show monthly revenue vs encounter count for F | 1 | PASS | 24.9s | 12 rows |
| 29 | billing | Q09 | Which single department generates the highest | 1 | PASS | 25.7s | 1 rows |
| 30 | billing | Q10 | Show all quality metrics for FAC-001 this mon | 0 | PASS | 24.5s | 0 rows |
| 31 | it_admin | Q01 | How many total records exist across all 4 tab | 1 | PASS | 42.2s | 1 rows |
| 32 | it_admin | Q02 | What are the distinct facility IDs and names  | 1 | PASS | 25.9s | 1 rows |
| 33 | it_admin | Q03 | What is the date range of report_month in the | 1 | PASS | 22.7s | 1 rows |
| 34 | it_admin | Q04 | Show all encounter summary records inserted i | 0 | PASS | 28.7s | 0 rows |
| 35 | it_admin | Q05 | List all Critical quality metrics across all  | 0 | PASS | 25.2s | 0 rows |
| 36 | it_admin | Q06 | How many quality metrics are below target per | 0 | PASS | 24.8s | 0 rows |
| 37 | it_admin | Q07 | Show all active research cohorts with their p | 1 | PASS | 25.1s | 8 rows |
| 38 | it_admin | Q08 | What distinct department names exist in the e | 1 | PASS | 25.0s | 16 rows |
| 39 | it_admin | Q09 | How many research cohorts are there per depar | 1 | PASS | 21.6s | 8 rows |
| 40 | it_admin | Q10 | Show population health record count by facili | 1 | PASS | 26.2s | 4 rows |
| 41 | hr | Q01 | What is the total encounter count and readmis | 1 | FAIL | 33.4s | 0 rows |
| 42 | hr | Q02 | Show all Patient_Safety quality metrics acros | 1 | PASS | 23.0s | 60 rows |
| 43 | hr | Q03 | List all quality metrics above target for FAC | 0 | PASS | 22.2s | 0 rows |
| 44 | hr | Q04 | What is the population health breakdown by ag | 1 | PASS | 21.4s | 12 rows |
| 45 | hr | Q05 | Show disease category distribution for the 45 | 1 | PASS | 22.7s | 40 rows |
| 46 | hr | Q06 | What is the average treatment cost by disease | 0 | PASS | 22.1s | 10 rows |
| 47 | hr | Q07 | Show population health data for female patien | 1 | PASS | 25.7s | 120 rows |
| 48 | hr | Q08 | List all research cohorts with patient counts | 1 | PASS | 23.7s | 8 rows |
| 49 | hr | Q09 | What is the average length of stay by age gro | 1 | PASS | 24.2s | 6 rows |
| 50 | hr | Q10 | Show quality metrics with Below_Target or Cri | 0 | PASS | 25.7s | 46 rows |

---

## Dr. Rajesh Patel (Attending Physician, Cardiology)

### Q01: How many total inpatient encounters were recorded for Cardiology at FAC-001 this year?
**Status**: PASS (51.9s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT SUM(total_encounters) AS total_inpatient_encounters FROM encounter_summaries AS es WHERE facility_id = 'FAC-001' AND UPPER(es.encounter_type) = UPPER('INPATIENT') AND UPPER(es.department_name) LIKE UPPER('%CARDIO%') AND EXTRACT(YEAR FROM es.report_month) = EXTRACT(YEAR FROM CURRENT_DATE) LIMIT 1000
```
**Rows returned**: 1  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (1 of 1 rows):
| {'name': 'total_inpa |
| --- |
| None |

### Q02: What is the average length of stay for cardiac patients across all Apollo facilities?
**Status**: PASS (22.5s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT facility_id, facility_name, AVG(avg_length_of_stay) AS avg_length_of_stay FROM encounter_summaries WHERE facility_id = 'FAC-001' AND UPPER(department_name) LIKE '%CARDIO%' AND UPPER(encounter_type) = UPPER('INPATIENT') GROUP BY facility_id, facility_name ORDER BY avg_length_of_stay DESC LIMIT 10000
```
**Rows returned**: 1  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (1 of 1 rows):
| {'name': 'facility_i | {'name': 'facility_n | {'name': 'avg_length |
| --- | --- | --- |
| FAC-001 | Apollo Hospitals Jub | 6.9500000000000000 |

### Q03: Which departments at FAC-001 had a readmission rate above 5% last quarter?
**Status**: PASS (23.6s)  
**Expected tables**: encounter_summaries  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT department_id, department_name, readmission_rate FROM encounter_summaries WHERE facility_id = 'FAC-001' AND report_month >= DATE_TRUNC('QUARTER', CURRENT_DATE) - INTERVAL '3 MONTH' AND report_month < DATE_TRUNC('QUARTER', CURRENT_DATE) AND readmission_rate > 0.05 AND UPPER(encounter_type) = UPPER('INPATIENT') GROUP BY department_id, department_name, readmission_rate ORDER BY readmission_rate DESC LIMIT 10000
```
**Rows returned**: 24  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 24 rows):
| {'name': 'department | {'name': 'department | {'name': 'readmissio |
| --- | --- | --- |
| DEPT-PATH | Pathology | 11.80 |
| DEPT-ORTH | Orthopaedics | 11.11 |
| DEPT-CARD | Cardiology | 10.94 |
| DEPT-GAST | Gastroenterology | 10.32 |
| DEPT-GAST | Gastroenterology | 9.83 |

### Q04: Show the mortality rate trend for FAC-001 over the past 6 months
**Status**: PASS (24.2s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT report_month, mortality_rate FROM encounter_summaries WHERE facility_id = 'FAC-001' AND report_month >= (CURRENT_DATE - INTERVAL '6 MONTHS') ORDER BY report_month ASC LIMIT 1000
```
**Rows returned**: 120  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 120 rows):
| {'name': 'report_mon | {'name': 'mortality_ |
| --- | --- |
| 2025-10-01 | 0.000 |
| 2025-10-01 | 0.676 |
| 2025-10-01 | 2.098 |
| 2025-10-01 | 0.466 |
| 2025-10-01 | 0.000 |

### Q05: What are all Patient_Safety quality metrics currently below target at FAC-001?
**Status**: PASS (23.7s)  
**Expected tables**: quality_metrics  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT metric_id, metric_name, metric_category, metric_value, target_value, department_id, report_month, performance_status FROM quality_metrics WHERE facility_id = 'FAC-001' AND UPPER(metric_category) = UPPER('Patient_Safety') AND metric_value < target_value LIMIT 1000
```
**Rows returned**: 27  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 27 rows):
| {'name': 'metric_id' | {'name': 'metric_nam | {'name': 'metric_cat | {'name': 'metric_val | {'name': 'target_val | {'name': 'department | {'name': 'report_mon | {'name': 'performanc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| b623063c-3d1c-4d59-a | HAI Rate (Hospital A | Patient_Safety | 82.727 | 85.284 | None | 2025-01-01 | Above_Target |
| 02580dde-538e-4f97-9 | Surgical Site Infect | Patient_Safety | 1.956 | 8.685 | None | 2025-01-01 | Above_Target |
| ccda94ec-2784-4079-a | Hand Hygiene Complia | Patient_Safety | 27.360 | 36.863 | None | 2025-01-01 | Above_Target |
| bf2cd258-8f12-42e3-8 | HAI Rate (Hospital A | Patient_Safety | 34.081 | 36.231 | None | 2025-02-01 | Above_Target |
| 1df15303-b238-4edb-8 | Hand Hygiene Complia | Patient_Safety | 18.006 | 24.187 | None | 2025-02-01 | Above_Target |

### Q06: Compare bed occupancy between Cardiology and Emergency Medicine at FAC-001
**Status**: PASS (23.8s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT es.department_id, es.department_name, es.encounter_type, es.bed_occupancy_rate FROM encounter_summaries AS es WHERE es.facility_id = 'FAC-001' AND (UPPER(es.department_name) LIKE '%CARDIOLOGY%' OR UPPER(es.department_name) LIKE '%EMERGENCY MEDICINE%') ORDER BY es.department_name, es.encounter_type LIMIT 1000
```
**Rows returned**: 39  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 39 rows):
| {'name': 'department | {'name': 'department | {'name': 'encounter_ | {'name': 'bed_occupa |
| --- | --- | --- | --- |
| DEPT-CARD | Cardiology | EMERGENCY | 80.48 |
| DEPT-CARD | Cardiology | EMERGENCY | 86.61 |
| DEPT-CARD | Cardiology | EMERGENCY | 90.55 |
| DEPT-CARD | Cardiology | EMERGENCY | 86.61 |
| DEPT-CARD | Cardiology | EMERGENCY | 75.06 |

### Q07: Show total revenue per encounter type for Cardiology this year
**Status**: FAIL (26.8s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT encounter_type, SUM(total_revenue) AS total_revenue FROM encounter_summaries WHERE facility_id = 'FAC-001' AND UPPER(department_name) LIKE '%CARDIO%' AND report_month >= DATE_TRUNC('YEAR', CURRENT_DATE) GROUP BY encounter_type ORDER BY total_revenue DESC LIMIT 10000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q08: What is the disease burden by age group for cardiovascular conditions at FAC-001?
**Status**: PASS (22.5s)  
**Expected tables**: population_health  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT age_group, SUM(encounter_count) AS total_encounters, SUM(patient_count) AS total_patients FROM population_health WHERE facility_id = 'FAC-001' AND UPPER(disease_category) LIKE '%CARDIO%' GROUP BY age_group ORDER BY total_encounters DESC LIMIT 10000
```
**Rows returned**: 6  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 6 rows):
| {'name': 'age_group' | {'name': 'total_enco | {'name': 'total_pati |
| --- | --- | --- |
| 30-44 | 1369 | 700 |
| 75+ | 1273 | 797 |
| 0-14 | 1140 | 587 |
| 15-29 | 1118 | 536 |
| 45-59 | 840 | 504 |

### Q09: List all active research cohorts in the Cardiology department
**Status**: FAIL (26.0s)  
**Expected tables**: research_cohorts  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT cohort_id, cohort_name, created_at, department_id, enrollment_end, enrollment_start, exclusion_criteria, inclusion_criteria, irb_approval_number, patient_count, principal_investigator, status, study_id
FROM research_cohorts rc
WHERE UPPER(rc.status) = UPPER('active')
  AND UPPER(rc.department_id) LIKE '%CARDIO%'
LIMIT 1000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q10: Show monthly encounter trend for Cardiology at FAC-001 for full year 2025
**Status**: PASS (22.5s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT report_month, facility_id, facility_name, department_id, department_name, SUM(total_encounters) AS total_encounters FROM encounter_summaries WHERE facility_id = 'FAC-001' AND UPPER(department_name) LIKE '%CARDIO%' AND report_month >= '2025-01-01' AND report_month < '2026-01-01' GROUP BY report_month, facility_id, facility_name, department_id, department_name ORDER BY report_month ASC LIMIT 10000
```
**Rows returned**: 5  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 5 rows):
| {'name': 'report_mon | {'name': 'facility_i | {'name': 'facility_n | {'name': 'department | {'name': 'department | {'name': 'total_enco |
| --- | --- | --- | --- | --- | --- |
| 2025-01-01 | FAC-001 | Apollo Hospitals Jub | DEPT-CARD | Cardiology | 1100 |
| 2025-05-01 | FAC-001 | Apollo Hospitals Jub | DEPT-CARD | Cardiology | 895 |
| 2025-06-01 | FAC-001 | Apollo Hospitals Jub | DEPT-CARD | Cardiology | 455 |
| 2025-10-01 | FAC-001 | Apollo Hospitals Jub | DEPT-CARD | Cardiology | 958 |
| 2025-11-01 | FAC-001 | Apollo Hospitals Jub | DEPT-CARD | Cardiology | 1698 |

## Anita Kumar (Registered Nurse, Cardiology)

### Q01: What is the current bed occupancy rate at FAC-001 this month?
**Status**: PASS (27.7s)  
**Expected tables**: encounter_summaries  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT COALESCE(SUM(e.bed_occupancy_rate), 0) AS total_bed_occupancy_rate FROM encounter_summaries AS e WHERE e.facility_id = 'FAC-001' AND DATE_TRUNC('MONTH', e.report_month) = DATE_TRUNC('MONTH', CURRENT_DATE) LIMIT 1000
```
**Rows returned**: 1  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (1 of 1 rows):
| {'name': 'total_bed_ |
| --- |
| 0 |

### Q02: Show total admissions vs discharges for Cardiology last month
**Status**: PASS (24.4s)  
**Expected tables**: encounter_summaries  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT es.facility_id, es.facility_name, es.department_id, es.department_name, COALESCE(SUM(es.total_admissions), 0) AS total_admissions, COALESCE(SUM(es.total_discharges), 0) AS total_discharges, es.report_month FROM encounter_summaries AS es WHERE es.facility_id = 'FAC-001' AND UPPER(es.department_name) LIKE '%CARDIO%' AND es.report_month = DATE_TRUNC('MONTH', CURRENT_DATE) - INTERVAL '1 MONTH' AND UPPER(es.encounter_type) = UPPER('INPATIENT') GROUP BY es.facility_id, es.facility_name, es.department_id, es.department_name, es.report_month ORDER BY total_admissions DESC LIMIT 10000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q03: What is the readmission count for FAC-001 Cardiology in the last 30 days?
**Status**: PASS (23.8s)  
**Expected tables**: encounter_summaries  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT COALESCE(SUM(e.readmission_count), 0) AS total_readmission_count FROM encounter_summaries AS e WHERE e.facility_id = 'FAC-001' AND UPPER(e.department_name) LIKE '%CARDIO%' AND e.report_month >= DATE_TRUNC('MONTH', CURRENT_DATE) - INTERVAL '30 DAYS' AND UPPER(e.encounter_type) = UPPER('INPATIENT') LIMIT 1000
```
**Rows returned**: 1  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (1 of 1 rows):
| {'name': 'total_read |
| --- |
| 0 |

### Q04: Show average length of stay per department at FAC-001 this quarter
**Status**: PASS (22.7s)  
**Expected tables**: encounter_summaries  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT es.department_id, es.department_name, COALESCE(AVG(es.avg_length_of_stay), 0) AS avg_length_of_stay FROM encounter_summaries AS es WHERE es.facility_id = 'FAC-001' AND es.report_month >= DATE_TRUNC('QUARTER', CURRENT_DATE) AND es.report_month < DATE_TRUNC('QUARTER', CURRENT_DATE) + INTERVAL '3 MONTH' AND UPPER(es.encounter_type) = UPPER('INPATIENT') GROUP BY es.department_id, es.department_name ORDER BY avg_length_of_stay DESC LIMIT 10000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q05: List all Patient_Safety quality metrics for FAC-001 this month
**Status**: PASS (22.7s)  
**Expected tables**: quality_metrics  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT 
  qm.metric_id,
  qm.metric_name,
  qm.metric_category,
  qm.metric_value,
  qm.benchmark_value,
  qm.target_value,
  qm.performance_status,
  qm.department_id,
  qm.report_month
FROM quality_metrics qm
WHERE 
  qm.facility_id = 'FAC-001'
  AND UPPER(qm.metric_category) = UPPER('Patient_Safety')
  AND qm.report_month = DATE_TRUNC('month', CURRENT_DATE)
LIMIT 1000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q06: Compare bed occupancy between FAC-001 and FAC-002 this month
**Status**: PASS (16.8s)  
**Expected tables**: encounter_summaries  
**Min rows**: 0  

### Q07: Show monthly encounter trend for Cardiology at FAC-001 for 2025
**Status**: PASS (22.4s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT es.report_month, COALESCE(SUM(es.total_encounters), 0) AS total_encounters FROM encounter_summaries AS es WHERE es.facility_id = 'FAC-001' AND UPPER(es.department_name) LIKE '%CARDIO%' AND es.report_month >= CAST('2025-01-01' AS DATE) AND es.report_month < CAST('2026-01-01' AS DATE) GROUP BY es.report_month ORDER BY es.report_month ASC LIMIT 10000
```
**Rows returned**: 5  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 5 rows):
| {'name': 'report_mon | {'name': 'total_enco |
| --- | --- |
| 2025-01-01 | 1100 |
| 2025-05-01 | 895 |
| 2025-06-01 | 455 |
| 2025-10-01 | 958 |
| 2025-11-01 | 1698 |

### Q08: What is the population health burden for the 45-59 age group at FAC-001?
**Status**: PASS (23.3s)  
**Expected tables**: population_health  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT
  age_group,
  disease_category,
  icd_chapter,
  gender,
  report_quarter,
  encounter_count,
  patient_count,
  avg_cost,
  avg_los,
  complication_rate
FROM population_health
WHERE facility_id = 'FAC-001'
  AND age_group = '45-59'
LIMIT 1000
```
**Rows returned**: 40  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 40 rows):
| {'name': 'age_group' | {'name': 'disease_ca | {'name': 'icd_chapte | {'name': 'gender', ' | {'name': 'report_qua | {'name': 'encounter_ | {'name': 'patient_co | {'name': 'avg_cost', |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 45-59 | Obstetric | None | Male | 2025-01-01 | 110 | 76 | 21229.00 |
| 45-59 | Respiratory | None | Male | 2025-01-01 | 103 | 70 | 465698.00 |
| 45-59 | Oncology | None | Male | 2025-01-01 | 546 | 278 | 101178.00 |
| 45-59 | Cardiovascular | None | Male | 2025-01-01 | 378 | 174 | 182244.00 |
| 45-59 | GI | None | Male | 2025-01-01 | 427 | 221 | 100500.00 |

### Q09: How many total encounters were recorded at each Apollo facility last month?
**Status**: PASS (21.9s)  
**Expected tables**: encounter_summaries  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT es.facility_id, es.facility_name, COALESCE(SUM(es.total_encounters), 0) AS total_encounters_last_month FROM encounter_summaries AS es WHERE es.facility_id = 'FAC-001' AND es.report_month = DATE_TRUNC('MONTH', CURRENT_DATE) - INTERVAL '1 MONTH' GROUP BY es.facility_id, es.facility_name ORDER BY total_encounters_last_month DESC LIMIT 10000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q10: What quality metrics at FAC-001 are currently marked as Critical?
**Status**: PASS (22.3s)  
**Expected tables**: quality_metrics  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT 
  qm.metric_id,
  qm.metric_name,
  qm.metric_category,
  qm.performance_status,
  qm.metric_value,
  qm.target_value,
  qm.benchmark_value,
  qm.report_month,
  qm.department_id
FROM quality_metrics qm
WHERE qm.facility_id = 'FAC-001'
  AND UPPER(qm.performance_status) = UPPER('Critical')
LIMIT 1000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

## Maria Fernandes (Billing Clerk)

### Q01: What is the total revenue generated at FAC-001 for the current month?
**Status**: PASS (37.6s)  
**Expected tables**: encounter_summaries  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT COALESCE(SUM(es.total_revenue), 0) AS total_revenue FROM encounter_summaries AS es WHERE es.facility_id = 'FAC-001' AND DATE_TRUNC('MONTH', es.report_month) = DATE_TRUNC('MONTH', CURRENT_DATE) LIMIT 1000
```
**Rows returned**: 1  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (1 of 1 rows):
| {'name': 'total_reve |
| --- |
| 0 |

### Q02: Show average revenue per encounter for each department at FAC-001
**Status**: PASS (24.0s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT es.department_id, es.department_name, es.facility_id, es.facility_name, AVG(es.avg_revenue_per_encounter) AS avg_revenue_per_encounter FROM encounter_summaries AS es WHERE es.facility_id = 'FAC-001' GROUP BY es.department_id, es.department_name, es.facility_id, es.facility_name ORDER BY avg_revenue_per_encounter DESC LIMIT 10000
```
**Rows returned**: 16  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 16 rows):
| {'name': 'department | {'name': 'department | {'name': 'facility_i | {'name': 'facility_n | {'name': 'avg_revenu |
| --- | --- | --- | --- | --- |
| DEPT-GENSURG | General Surgery | FAC-001 | Apollo Hospitals Jub | 128519.XXXX XXXX 333 |
| DEPT-NEUR | Neurology | FAC-001 | Apollo Hospitals Jub | 92402.XXXX XXXX 3333 |
| DEPT-PATH | Pathology | FAC-001 | Apollo Hospitals Jub | 77551.XXXX XXXX 2222 |
| DEPT-TRAN | Transplant Surgery | FAC-001 | Apollo Hospitals Jub | 76197.XXXX XXXX 9259 |
| DEPT-ENDO | Endocrinology | FAC-001 | Apollo Hospitals Jub | 69202.XXXX XXXX 6667 |

### Q03: What is the total revenue trend for Apollo Jubilee Hills over the last 6 months?
**Status**: FAIL (27.6s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT DATE_TRUNC('MONTH', es.report_month) AS month, COALESCE(SUM(es.total_revenue), 0) AS total_revenue FROM encounter_summaries AS es WHERE es.facility_id = 'FAC-001' AND UPPER(es.facility_name) = UPPER('Apollo Jubilee Hills') AND es.report_month >= DATE_TRUNC('MONTH', CURRENT_DATE) - INTERVAL '5 MONTHS' GROUP BY month ORDER BY month ASC LIMIT 10000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q04: Which Apollo facility has the highest total revenue this quarter?
**Status**: FAIL (22.3s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT
  es.facility_id,
  es.facility_name,
  SUM(es.total_revenue) AS total_revenue
FROM
  encounter_summaries es
WHERE
  es.facility_id = 'FAC-001'
  AND es.report_month >= DATE_TRUNC('quarter', CURRENT_DATE)
  AND es.report_month < DATE_TRUNC('quarter', CURRENT_DATE) + INTERVAL '3 months'
GROUP BY
  es.facility_id,
  es.facility_name
ORDER BY
  total_revenue DESC
LIMIT 1
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q05: Show revenue breakdown by encounter type at FAC-001
**Status**: PASS (26.4s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT es.encounter_type, SUM(es.total_revenue) AS total_revenue, COUNT(*) AS num_records FROM encounter_summaries AS es WHERE es.facility_id = 'FAC-001' GROUP BY es.encounter_type ORDER BY total_revenue DESC LIMIT 10000
```
**Rows returned**: 3  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (3 of 3 rows):
| {'name': 'encounter_ | {'name': 'total_reve | {'name': 'num_record |
| --- | --- | --- |
| OUTPATIENT | 940279077.00 | 112 |
| EMERGENCY | 888348714.00 | 113 |
| INPATIENT | 840202782.00 | 112 |

### Q06: Compare average revenue per encounter for Cardiology vs Oncology across all facilities
**Status**: PASS (27.3s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT
  es.facility_id,
  es.facility_name,
  es.department_name,
  es.avg_revenue_per_encounter
FROM
  encounter_summaries es
WHERE
  es.facility_id = 'FAC-001'
  AND (
    UPPER(es.department_name) LIKE '%CARDIO%'
    OR UPPER(es.department_name) LIKE '%ONCO%'
  )
LIMIT 1000
```
**Rows returned**: 39  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 39 rows):
| {'name': 'facility_i | {'name': 'facility_n | {'name': 'department | {'name': 'avg_revenu |
| --- | --- | --- | --- |
| FAC-001 | Apollo Hospitals Jub | Cardiology | 4874.00 |
| FAC-001 | Apollo Hospitals Jub | Cardiology | 10107.00 |
| FAC-001 | Apollo Hospitals Jub | Cardiology | 50168.00 |
| FAC-001 | Apollo Hospitals Jub | Oncology | 38017.00 |
| FAC-001 | Apollo Hospitals Jub | Oncology | 17475.00 |

### Q07: What is the total revenue across all 8 Apollo facilities this year?
**Status**: FAIL (17.2s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Error detail**: Only data for facility_id = 'FAC-001' is available in the schema; cannot aggregate across all 8 Apollo facilities.  

### Q08: Show monthly revenue vs encounter count for FAC-001 in 2025
**Status**: PASS (24.9s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT DATE_TRUNC('MONTH', e.report_month) AS month, COALESCE(SUM(e.total_revenue), 0) AS total_revenue, COALESCE(SUM(e.total_encounters), 0) AS total_encounters FROM encounter_summaries AS e WHERE e.facility_id = 'FAC-001' AND e.report_month >= '2025-01-01' AND e.report_month < '2026-01-01' GROUP BY DATE_TRUNC('MONTH', e.report_month) ORDER BY month LIMIT 10000
```
**Rows returned**: 12  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 12 rows):
| {'name': 'month', 't | {'name': 'total_reve | {'name': 'total_enco |
| --- | --- | --- |
| 2025-01-01 00:00:00+ | 205522437.00 | 5933 |
| 2025-02-01 00:00:00+ | 148637461.00 | 5881 |
| 2025-03-01 00:00:00+ | 181314733.00 | 7465 |
| 2025-04-01 00:00:00+ | 198174114.00 | 6877 |
| 2025-05-01 00:00:00+ | 222467550.00 | 4749 |

### Q09: Which single department generates the highest average revenue per encounter at FAC-001?
**Status**: PASS (25.7s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT es.department_id, es.department_name, AVG(es.avg_revenue_per_encounter) AS avg_revenue_per_encounter
FROM encounter_summaries es
WHERE es.facility_id = 'FAC-001'
GROUP BY es.department_id, es.department_name
ORDER BY avg_revenue_per_encounter DESC
LIMIT 1
```
**Rows returned**: 1  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (1 of 1 rows):
| {'name': 'department | {'name': 'department | {'name': 'avg_revenu |
| --- | --- | --- |
| DEPT-GENSURG | General Surgery | 128519.XXXX XXXX 333 |

### Q10: Show all quality metrics for FAC-001 this month across all categories
**Status**: PASS (24.5s)  
**Expected tables**: quality_metrics  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT metric_id, metric_name, metric_category, department_id, facility_id, report_month, metric_value, target_value, benchmark_value, numerator, denominator, performance_status FROM quality_metrics WHERE facility_id = 'FAC-001' AND report_month = DATE_TRUNC('MONTH', CURRENT_DATE) LIMIT 1000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

## Vikram Joshi (IT Administrator)

### Q01: How many total records exist across all 4 tables in the analytics database?
**Status**: PASS (42.2s)  
**Expected tables**: encounter_summaries, quality_metrics, population_health, research_cohorts  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT (SELECT COUNT(*) FROM encounter_summaries WHERE facility_id = 'FAC-001') + (SELECT COUNT(*) FROM quality_metrics WHERE facility_id = 'FAC-001') + (SELECT COUNT(*) FROM population_health WHERE facility_id = 'FAC-001') + (SELECT COUNT(*) FROM research_cohorts) AS total_records LIMIT 1000
```
**Rows returned**: 1  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (1 of 1 rows):
| {'name': 'total_reco |
| --- |
| 753 |

### Q02: What are the distinct facility IDs and names in the analytics database?
**Status**: PASS (25.9s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT DISTINCT es.facility_id, es.facility_name
FROM encounter_summaries es
WHERE es.facility_id = 'FAC-001'
LIMIT 1000
```
**Rows returned**: 1  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (1 of 1 rows):
| {'name': 'facility_i | {'name': 'facility_n |
| --- | --- |
| FAC-001 | Apollo Hospitals Jub |

### Q03: What is the date range of report_month in the encounter_summaries table?
**Status**: PASS (22.7s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT MIN(report_month) AS min_report_month, MAX(report_month) AS max_report_month FROM encounter_summaries WHERE facility_id = 'FAC-001' LIMIT 1000
```
**Rows returned**: 1  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (1 of 1 rows):
| {'name': 'min_report | {'name': 'max_report |
| --- | --- |
| 2025-01-01 | 2025-12-01 |

### Q04: Show all encounter summary records inserted in the last 7 days ordered by total encounters
**Status**: PASS (28.7s)  
**Expected tables**: encounter_summaries  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT 
  es.summary_id,
  es.facility_id,
  es.facility_name,
  es.department_id,
  es.department_name,
  es.encounter_type,
  es.report_month,
  es.total_encounters,
  es.total_admissions,
  es.total_discharges,
  es.avg_length_of_stay,
  es.bed_occupancy_rate,
  es.mortality_count,
  es.mortality_rate,
  es.readmission_count,
  es.readmission_rate,
  es.total_revenue,
  es.avg_revenue_per_encounter
FROM encounter_summaries es
WHERE es.facility_id = 'FAC-001'
  AND es.created_at >= NOW() - INTERVAL '7 days'
ORDER BY es.total_encounters DESC
LIMIT 1000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q05: List all Critical quality metrics across all facilities
**Status**: PASS (25.2s)  
**Expected tables**: quality_metrics  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT qm.metric_id, qm.metric_name, qm.metric_category, qm.department_id, qm.benchmark_value, qm.target_value, qm.metric_value, qm.performance_status, qm.report_month, qm.facility_id FROM quality_metrics AS qm WHERE qm.facility_id = 'FAC-001' AND UPPER(qm.metric_category) = UPPER('CRITICAL') LIMIT 1000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q06: How many quality metrics are below target per facility this month?
**Status**: PASS (24.8s)  
**Expected tables**: quality_metrics  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT q.facility_id, COUNT(q.metric_id) AS below_target_metric_count FROM quality_metrics AS q WHERE q.facility_id = 'FAC-001' AND q.report_month = DATE_TRUNC('MONTH', CURRENT_DATE) AND q.metric_value < q.target_value GROUP BY q.facility_id ORDER BY below_target_metric_count DESC LIMIT 10000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q07: Show all active research cohorts with their patient counts
**Status**: PASS (25.1s)  
**Expected tables**: research_cohorts  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT rc.cohort_id, rc.cohort_name, rc.patient_count
FROM research_cohorts rc
WHERE UPPER(rc.status) = UPPER('active')
LIMIT 1000
```
**Rows returned**: 8  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 8 rows):
| {'name': 'cohort_id' | {'name': 'cohort_nam | {'name': 'patient_co |
| --- | --- | --- |
| 21588a47-2369-4281-8 | Outcomes of TAVI in  | 461 |
| 7566ee4f-10db-4e62-a | Immunotherapy Respon | 483 |
| 761b207d-180d-4ea6-b | Deep Brain Stimulati | 181 |
| 8cc0077a-c095-47c4-a | Long-term Outcomes o | 171 |
| 48c3494f-52fd-4b97-8 | Diabetes Reversal Th | 114 |

### Q08: What distinct department names exist in the encounter_summaries table?
**Status**: PASS (25.0s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT DISTINCT es.department_name
FROM encounter_summaries es
WHERE es.facility_id = 'FAC-001'
LIMIT 1000
```
**Rows returned**: 16  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 16 rows):
| {'name': 'department |
| --- |
| Orthopaedics |
| Cardiology |
| Gastroenterology |
| Oncology |
| Emergency Medicine |

### Q09: How many research cohorts are there per department?
**Status**: PASS (21.6s)  
**Expected tables**: research_cohorts  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT r.department_id, COUNT(r.cohort_id) AS cohort_count FROM research_cohorts AS r GROUP BY r.department_id ORDER BY cohort_count DESC LIMIT 10000
```
**Rows returned**: 8  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 8 rows):
| {'name': 'department | {'name': 'cohort_cou |
| --- | --- |
| DEPT-NEUR | 1 |
| DEPT-PULM | 1 |
| DEPT-CARD | 1 |
| DEPT-NEPH | 1 |
| DEPT-ONCO | 1 |

### Q10: Show population health record count by facility and quarter
**Status**: PASS (26.2s)  
**Expected tables**: population_health  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT p.facility_id, COUNT(p.record_id) AS record_count, p.report_quarter FROM population_health AS p WHERE p.facility_id = 'FAC-001' GROUP BY p.facility_id, p.report_quarter ORDER BY record_count DESC LIMIT 10000
```
**Rows returned**: 4  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (4 of 4 rows):
| {'name': 'facility_i | {'name': 'record_cou | {'name': 'report_qua |
| --- | --- | --- |
| FAC-001 | 60 | 2025-10-01 |
| FAC-001 | 60 | 2025-07-01 |
| FAC-001 | 60 | 2025-04-01 |
| FAC-001 | 60 | 2025-01-01 |

## Priya Mehta (HR Manager)

### Q01: What is the total encounter count and readmission rate for FAC-001 this year?
**Status**: FAIL (33.4s)  
**Expected tables**: encounter_summaries  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT es.facility_id, es.facility_name, SUM(es.total_encounters) AS total_encounter_count, AVG(es.readmission_rate) AS avg_readmission_rate FROM encounter_summaries AS es WHERE es.facility_id = 'FAC-001' AND es.report_month >= DATE_TRUNC('YEAR', CURRENT_DATE) AND es.report_month < DATE_TRUNC('YEAR', CURRENT_DATE) + INTERVAL '1 YEAR' GROUP BY es.facility_id, es.facility_name ORDER BY total_encounter_count DESC LIMIT 10000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q02: Show all Patient_Safety quality metrics across all facilities
**Status**: PASS (23.0s)  
**Expected tables**: quality_metrics  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT 
  qm.metric_id,
  qm.metric_name,
  qm.metric_category,
  qm.department_id,
  qm.facility_id,
  qm.benchmark_value,
  qm.target_value,
  qm.metric_value,
  qm.numerator,
  qm.denominator,
  qm.performance_status,
  qm.report_month
FROM quality_metrics qm
WHERE qm.facility_id = 'FAC-001'
  AND UPPER(qm.metric_category) = UPPER('Patient_Safety')
LIMIT 1000
```
**Rows returned**: 60  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 60 rows):
| {'name': 'metric_id' | {'name': 'metric_nam | {'name': 'metric_cat | {'name': 'department | {'name': 'facility_i | {'name': 'benchmark_ | {'name': 'target_val | {'name': 'metric_val |
| --- | --- | --- | --- | --- | --- | --- | --- |
| b623063c-3d1c-4d59-a | HAI Rate (Hospital A | Patient_Safety | None | FAC-001 | 68.410 | 85.284 | 82.727 |
| 02580dde-538e-4f97-9 | Surgical Site Infect | Patient_Safety | None | FAC-001 | 16.849 | 8.685 | 1.956 |
| 71e7a919-9f3c-4b06-8 | Falls per 1000 Patie | Patient_Safety | None | FAC-001 | 12.017 | 25.179 | 26.471 |
| f976298b-9731-4d4c-a | Medication Error Rat | Patient_Safety | None | FAC-001 | 63.994 | 47.079 | 56.876 |
| ccda94ec-2784-4079-a | Hand Hygiene Complia | Patient_Safety | None | FAC-001 | 16.414 | 36.863 | 27.360 |

### Q03: List all quality metrics above target for FAC-001 this month
**Status**: PASS (22.2s)  
**Expected tables**: quality_metrics  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT q.metric_id, q.metric_name, q.metric_category, q.department_id, q.facility_id, q.metric_value, q.target_value, q.benchmark_value, q.performance_status, q.report_month FROM quality_metrics AS q WHERE q.facility_id = 'FAC-001' AND q.metric_value > q.target_value AND q.report_month = DATE_TRUNC('MONTH', CURRENT_DATE) LIMIT 1000
```
**Rows returned**: 0  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

### Q04: What is the population health breakdown by age group and gender at FAC-001?
**Status**: PASS (21.4s)  
**Expected tables**: population_health  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT ph.age_group, ph.gender, SUM(ph.patient_count) AS total_patients, SUM(ph.encounter_count) AS total_encounters, AVG(ph.avg_cost) AS avg_cost, AVG(ph.avg_los) AS avg_length_of_stay, AVG(ph.complication_rate) AS avg_complication_rate FROM population_health AS ph WHERE ph.facility_id = 'FAC-001' GROUP BY ph.age_group, ph.gender ORDER BY total_patients DESC LIMIT 10000
```
**Rows returned**: 12  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 12 rows):
| {'name': 'age_group' | {'name': 'gender', ' | {'name': 'total_pati | {'name': 'total_enco | {'name': 'avg_cost', | {'name': 'avg_length | {'name': 'avg_compli |
| --- | --- | --- | --- | --- | --- | --- |
| 0-14 | Female | 3598 | 6124 | 273738.XXXX XXXX 000 | 6.8150000000000000 | 0.090750000000000000 |
| 30-44 | Male | 3430 | 6001 | 231633.XXXX XXXX 000 | 8.0000000000000000 | 0.074350000000000000 |
| 75+ | Male | 3355 | 6562 | 207838.XXXX XXXX 000 | 7.1950000000000000 | 0.079500000000000000 |
| 45-59 | Female | 3201 | 5755 | 247943.XXXX XXXX 000 | 9.1200000000000000 | 0.068800000000000000 |
| 45-59 | Male | 3164 | 5374 | 248797.XXXX XXXX 000 | 9.1650000000000000 | 0.081750000000000000 |

### Q05: Show disease category distribution for the 45-59 age group across all facilities
**Status**: PASS (22.7s)  
**Expected tables**: population_health  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT
  ph.disease_category,
  ph.encounter_count,
  ph.patient_count,
  ph.complication_rate,
  ph.avg_cost,
  ph.avg_los
FROM population_health ph
WHERE ph.facility_id = 'FAC-001'
  AND UPPER(ph.age_group) = UPPER('45-59')
LIMIT 1000
```
**Rows returned**: 40  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 40 rows):
| {'name': 'disease_ca | {'name': 'encounter_ | {'name': 'patient_co | {'name': 'complicati | {'name': 'avg_cost', | {'name': 'avg_los',  |
| --- | --- | --- | --- | --- | --- |
| Obstetric | 110 | 76 | 0.129 | 21229.00 | 6.0 |
| Respiratory | 103 | 70 | 0.140 | 465698.00 | 8.3 |
| Oncology | 546 | 278 | 0.071 | 101178.00 | 6.2 |
| Cardiovascular | 378 | 174 | 0.091 | 182244.00 | 10.3 |
| GI | 427 | 221 | 0.041 | 100500.00 | 7.6 |

### Q06: What is the average treatment cost by disease category at FAC-001 this quarter?
**Status**: PASS (22.1s)  
**Expected tables**: population_health  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT ph.disease_category, AVG(ph.avg_cost) AS avg_treatment_cost FROM population_health AS ph WHERE ph.facility_id = 'FAC-001' GROUP BY ph.disease_category ORDER BY avg_treatment_cost DESC LIMIT 10000
```
**Rows returned**: 10  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 10 rows):
| {'name': 'disease_ca | {'name': 'avg_treatm |
| --- | --- |
| Cardiovascular | 324805.XXXX XXXX 173 |
| Musculoskeletal | 293351.XXXX XXXX 333 |
| Obstetric | 271857.XXXX XXXX 629 |
| Infectious | 269091.XXXX XXXX 666 |
| Endocrine | 257857.XXXX XXXX 000 |

### Q07: Show population health data for female patients across all age groups at FAC-001
**Status**: PASS (25.7s)  
**Expected tables**: population_health  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT
  ph.age_group,
  ph.disease_category,
  ph.icd_chapter,
  ph.patient_count,
  ph.encounter_count,
  ph.avg_cost,
  ph.avg_los,
  ph.complication_rate,
  ph.report_quarter
FROM population_health ph
WHERE ph.facility_id = 'FAC-001'
  AND UPPER(ph.gender) = UPPER('female')
LIMIT 1000
```
**Rows returned**: 120  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 120 rows):
| {'name': 'age_group' | {'name': 'disease_ca | {'name': 'icd_chapte | {'name': 'patient_co | {'name': 'encounter_ | {'name': 'avg_cost', | {'name': 'avg_los',  | {'name': 'complicati |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0-14 | Renal | None | 278 | 458 | 134467.00 | 1.9 | 0.133 |
| 0-14 | Cardiovascular | None | 111 | 231 | 471076.00 | 6.7 | 0.111 |
| 0-14 | Musculoskeletal | None | 180 | 440 | 23330.00 | 11.5 | 0.083 |
| 0-14 | Obstetric | None | 53 | 70 | 411570.00 | 10.9 | 0.042 |
| 0-14 | Infectious | None | 238 | 336 | 423746.00 | 14.1 | 0.124 |

### Q08: List all research cohorts with patient counts and enrollment date ranges
**Status**: PASS (23.7s)  
**Expected tables**: research_cohorts  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT
  cohort_id,
  cohort_name,
  patient_count,
  enrollment_start,
  enrollment_end
FROM research_cohorts
LIMIT 1000
```
**Rows returned**: 8  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 8 rows):
| {'name': 'cohort_id' | {'name': 'cohort_nam | {'name': 'patient_co | {'name': 'enrollment | {'name': 'enrollment |
| --- | --- | --- | --- | --- |
| 21588a47-2369-4281-8 | Outcomes of TAVI in  | 461 | 2024-04-01 | 2026-06-30 |
| 7566ee4f-10db-4e62-a | Immunotherapy Respon | 483 | 2024-02-01 | 2026-09-30 |
| 761b207d-180d-4ea6-b | Deep Brain Stimulati | 181 | 2024-06-01 | 2026-09-30 |
| 8cc0077a-c095-47c4-a | Long-term Outcomes o | 171 | 2024-01-01 | 2026-06-30 |
| 48c3494f-52fd-4b97-8 | Diabetes Reversal Th | 114 | 2024-02-01 | 2026-12-30 |

### Q09: What is the average length of stay by age group at FAC-001?
**Status**: PASS (24.2s)  
**Expected tables**: population_health  
**Min rows**: 1  

**Generated SQL**:
```sql
SELECT age_group, AVG(avg_los) AS avg_length_of_stay FROM population_health WHERE facility_id = 'FAC-001' GROUP BY age_group ORDER BY avg_length_of_stay DESC LIMIT 10000
```
**Rows returned**: 6  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 6 rows):
| {'name': 'age_group' | {'name': 'avg_length |
| --- | --- |
| 45-59 | 9.1425000000000000 |
| 15-29 | 8.3900000000000000 |
| 60-74 | 8.0250000000000000 |
| 75+ | 7.6875000000000000 |
| 30-44 | 7.6325000000000000 |

### Q10: Show quality metrics with Below_Target or Critical status across all departments and facilities
**Status**: PASS (25.7s)  
**Expected tables**: quality_metrics  
**Min rows**: 0  

**Generated SQL**:
```sql
SELECT 
  qm.metric_id,
  qm.metric_name,
  qm.metric_category,
  qm.department_id,
  qm.facility_id,
  qm.benchmark_value,
  qm.target_value,
  qm.metric_value,
  qm.performance_status,
  qm.report_month
FROM quality_metrics qm
WHERE qm.facility_id = 'FAC-001'
  AND (UPPER(qm.performance_status) = UPPER('Below_Target') OR UPPER(qm.performance_status) = UPPER('Critical'))
LIMIT 1000
```
**Rows returned**: 46  
**Target DB**: apollo_analytics | **Dialect**: postgresql  

**Sample data** (5 of 46 rows):
| {'name': 'metric_id' | {'name': 'metric_nam | {'name': 'metric_cat | {'name': 'department | {'name': 'facility_i | {'name': 'benchmark_ | {'name': 'target_val | {'name': 'metric_val |
| --- | --- | --- | --- | --- | --- | --- | --- |
| f976298b-9731-4d4c-a | Medication Error Rat | Patient_Safety | None | FAC-001 | 63.994 | 47.079 | 56.876 |
| 5ddc1fe9-f09e-46dd-9 | Average Time to Surg | Process | None | FAC-001 | 14.821 | 11.411 | 18.620 |
| 2a303c86-058c-48b5-b | ED Wait Time (minute | Process | None | FAC-001 | 9.031 | 9.493 | 17.327 |
| 36722a50-6ea9-4e2b-b | Discharge Instructio | Process | None | FAC-001 | 15.694 | 7.670 | 16.528 |
| 8711f256-d35f-4662-9 | Surgical Site Infect | Patient_Safety | None | FAC-001 | 15.363 | 10.247 | 18.030 |

---

## Failed Tests Summary

- **doctor/Q07**: Show total revenue per encounter type for Cardiology this ye -> 0 rows
- **doctor/Q09**: List all active research cohorts in the Cardiology departmen -> 0 rows
- **billing/Q03**: What is the total revenue trend for Apollo Jubilee Hills ove -> 0 rows
- **billing/Q04**: Which Apollo facility has the highest total revenue this qua -> 0 rows
- **billing/Q07**: What is the total revenue across all 8 Apollo facilities thi -> DENIED at L5: CANNOT_ANSWER
  - Detail: Only data for facility_id = 'FAC-001' is available in the schema; cannot aggregate across all 8 Apollo facilities.
- **hr/Q01**: What is the total encounter count and readmission rate for F -> 0 rows
