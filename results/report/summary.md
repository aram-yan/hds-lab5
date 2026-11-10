# Summary report

Combined analytic table: 626 records x 14 columns.

## Records per cohort

| cohort | n | sex F | sex M | sex U | sex missing |
|---|---|---|---|---|---|
| lab3_clinic | 60 | 20 | 22 | 13 | 5 |
| tcga_luad | 566 | 275 | 239 | 0 | 52 |

## Clinic cohort (Lab 3 cleaning)

- glucose available for 60 of 60 samples; median 149.1 mg/dL (IQR 114.9 to 187.6)
- samples per site: Site A = 23, Site B = 20, Site C = 17
- age at reference date: median 39.6 years (0 unparseable dates)
- records with at least one cleaning flag raised: 29

## TCGA LUAD cohort (Lab 4 queries)

- 566 patients; median age at diagnosis 66 years (71 missing)
- median TMB 6.7 nonsynonymous mutations/Mb
- patients with >= 1 protein-altering mutation: TP53 287, KRAS 168, EGFR 69, STK11 74, KEAP1 102
- stage missing for 54 patients

## Missing values per column (whole table)

| column | n missing |
|---|---|
| cohort | 0 |
| record_id | 0 |
| sex | 57 |
| site | 0 |
| age_years | 71 |
| stage | 114 |
| glucose_mgdl | 566 |
| tmb_nonsynonymous | 60 |
| TP53_count | 60 |
| KRAS_count | 60 |
| EGFR_count | 60 |
| STK11_count | 60 |
| KEAP1_count | 60 |
| n_qc_flags | 0 |

Figure: `results/report/figure.png`
