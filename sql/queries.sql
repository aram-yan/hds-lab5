-- Lab 4 queries against cohort.db (TCGA LUAD PanCancer Atlas, via cBioPortal).
-- Each query is delimited by a "-- name: <id>" line so src/build_feature_table.py
-- can load them by name; they can also be pasted into the sqlite3 shell as-is.
--
-- Grain reminders (checked in src/explore_schema.py, not assumed):
--   patients  : one row per patient            (566)
--   samples   : one row per tumor sample       (566; exactly one per patient)
--   mutations : one row per somatic mutation   (200,789)
--   genes     : one row per gene symbol        (17,756)


-- name: q1_gene_counts
-- Task 2, query 1. Grain: one row per (patient, gene) for the five target genes.
-- Protein-altering = every variant_classification except 'Silent'.
-- Patients and genes come from a CROSS JOIN so that every patient gets a row
-- for every gene, with COUNT(...) = 0 where no qualifying mutation exists.
-- Both filters on the optional side live in ON, not WHERE (Week 8, habit 2):
-- moving them to WHERE would silently drop every zero row.
-- Expected rows: 566 patients x 5 genes = 2,830.
WITH target_genes(gene_symbol) AS (
    VALUES ('TP53'), ('KRAS'), ('EGFR'), ('STK11'), ('KEAP1')
)
SELECT
    p.patient_id,
    g.gene_symbol,
    COUNT(m.mutation_id) AS n_protein_altering
FROM patients p
CROSS JOIN target_genes g
LEFT JOIN samples   s ON s.patient_id = p.patient_id
LEFT JOIN mutations m ON m.sample_id = s.sample_id
                     AND m.gene_symbol = g.gene_symbol
                     AND m.variant_classification <> 'Silent'
GROUP BY p.patient_id, g.gene_symbol
ORDER BY p.patient_id, g.gene_symbol;


-- name: q2_site_by_stage
-- Task 2, query 2. Grain: one row per (tissue source site, stage) combination
-- that actually occurs. Each patient is counted once (COUNT DISTINCT guards
-- against any future patient with more than one sample). Stage is not
-- filtered, so patients with NULL stage appear as their own rows per site
-- instead of vanishing. Expected rows: not knowable in advance (it is the
-- number of occurring combinations, at most 34 sites x 10 stage values); the
-- checkable expectation is that n_patients sums to 566 and NULL-stage rows
-- are present.
SELECT
    s.tissue_source_site,
    p.stage,
    COUNT(DISTINCT p.patient_id) AS n_patients
FROM patients p
LEFT JOIN samples s ON s.patient_id = p.patient_id
GROUP BY s.tissue_source_site, p.stage
ORDER BY s.tissue_source_site, p.stage;


-- name: q3_clinical
-- Task 3 input. Grain: one row per patient, with the sample-level columns
-- attached. LEFT JOIN so a patient without a sample would still be kept
-- (there are none, but the query should not depend on that).
-- Expected rows: 566.
SELECT
    p.patient_id,
    p.sex,
    p.age_at_diagnosis,
    p.stage,
    s.tissue_source_site,
    s.tmb_nonsynonymous
FROM patients p
LEFT JOIN samples s ON s.patient_id = p.patient_id
ORDER BY p.patient_id;


-- name: check_patient_count
-- Used before and after the joins so the reader can see nobody was lost.
SELECT COUNT(*) AS n_patients FROM patients;
