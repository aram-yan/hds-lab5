| step | expected rows | actual rows | note |
|---|---|---|---|
| patients table (before joins) | 566 | 566 | baseline |
| q1_gene_counts | 2830 | 2830 | 566 patients x 5 genes; zero rows kept by LEFT JOIN with filters in ON |
| q2_site_by_stage | unknown a priori (occurring site x stage combos) | 142 | n_patients sums to 566; 3 rows have NULL stage |
| q3_clinical | 566 | 566 | one sample per patient |
| feature table (after joins + pivot) | 566 | 566 | no patient lost |
