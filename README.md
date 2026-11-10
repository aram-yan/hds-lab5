# hds-lab5

Lab 5: Scalable Analysis Workflow (PUBH 6854). A four-stage Snakemake
pipeline that chains my Lab 3 cleaning and Lab 4 database queries into one
combined analytic table and a summary report. AI use in
[AI_USAGE.md](AI_USAGE.md).

```
data/raw/messy_samples.csv ──clean_samples──> results/samples_clean.tsv ──┐
                                                                          ├─merge_tables─> results/combined.tsv ─report─> results/report/{figure.png, summary.md}
data/raw/cohort.db + sql/queries.sql ──query_features──> results/features/feature_table.tsv ──┘
```

| Rule | Reuses | Script | Declared inputs | Declared outputs |
|---|---|---|---|---|
| `clean_samples` | Lab 3 regex cleaning | `scripts/clean_samples.py` | `messy_samples.csv` | `results/samples_clean.tsv` |
| `query_features` | Lab 4 SQL + pandas pivot | `scripts/build_feature_table.py` | `cohort.db`, `sql/queries.sql` | `results/features/feature_table.tsv` (+ row-count log, data dictionary, site x stage, missing summary) |
| `merge_tables` | new | `scripts/merge_tables.py` | the two tables above | `results/combined.tsv` |
| `report` | new | `scripts/make_report.py` | `results/combined.tsv` | `results/report/figure.png`, `results/report/summary.md` |

Every script takes all its paths as arguments. No rule reads or writes a
file it does not declare, so Snakemake's dependency graph is the real one.
`snakemake --dag` output is in `evidence/dag.txt`.

## Getting started

Requires conda. The raw inputs are not committed (course rule; `cohort.db`
is 16 MB). They are the unchanged course files:

```bash
git clone https://github.com/aram-yan/hds-lab5.git
cd hds-lab5
conda env create -f environment.yml
conda activate hds-lab5

# raw inputs: copy from a clone of https://github.com/gwcbi/applied-computing-HDS
cp ../applied-computing-HDS/data/raw/lab3-messy-data/messy_samples.csv data/raw/
cp ../applied-computing-HDS/data/raw/lab4-cbioportal-luad/cohort.db   data/raw/
```

(Or edit the two paths in `config.yaml` to point at the course clone directly.)

## Running it

```bash
snakemake -n                 # dry run: lists the 4 jobs + `all`
snakemake --cores 2          # full run (about 10 s)
```

**Clean run from scratch** (what the grader should see; output kept in
`evidence/clean_run.txt`):

```bash
rm -rf results logs .snakemake
snakemake --cores 2
```

**Partial re-run** (`evidence/partial_rerun.txt`): change one upstream
input and only the rules downstream of it run.

```bash
# add one record to the clinic input (the TCGA side is untouched)
printf 'S0061,Z. Test,1990-01-01,F,Site A,100.0,mg/dL,\n' >> data/raw/messy_samples.csv
snakemake -n                 # shows clean_samples, merge_tables, report: NOT query_features
snakemake --cores 2
# restore the original input and the committed outputs
cp ../applied-computing-HDS/data/raw/lab3-messy-data/messy_samples.csv data/raw/
snakemake --cores 2
```

A second kind of partial re-run: changing `reference_date` in `config.yaml`
re-runs only `merge_tables` and `report`, because Snakemake 9 treats changed
`params` as a re-run trigger.

## Outputs (committed)

| File | What it is |
|---|---|
| `results/samples_clean.tsv` | 60 clinic samples, Lab 3 cleaning with its QC flag columns |
| `results/features/feature_table.tsv` | 566 TCGA LUAD patients x 11 columns, Lab 4 feature table |
| `results/features/query_row_counts.md` | expected vs actual row count per query step |
| `results/combined.tsv` | **the combined analytic table**: 626 records on one shared schema |
| `results/report/summary.md` | text summary computed from `combined.tsv` |
| `results/report/figure.png` | three-panel figure (clinic glucose by site; TCGA TMB by stage; mutated-gene shares) |
| `evidence/clean_run.txt` | console output of the full run from a clean state (5 of 5 steps) |
| `evidence/partial_rerun.txt` | dry run and real run after appending one clinic record: `clean_samples`, `merge_tables`, `report` run, `query_features` does not |
| `evidence/params_rerun.txt` | dry run after changing `reference_date`: only `merge_tables` and `report` |
| `evidence/no_shared_key.txt` | the check behind the merge design: 0 shared ids, inner join = 0 rows |
| `evidence/dag.txt` | `snakemake --dag` and `--rulegraph` output (Graphviz dot text) |

## How the two tables are merged

The cohorts share no identifier: the clinic records are synthetic
(`S0001`..`S0060`) and the TCGA rows are patient barcodes. A key-based join
is therefore impossible (an inner join returns 0 rows), so `merge_tables`
builds a *harmonised stack*: both tables are mapped onto one schema
(`cohort, record_id, sex, site, age_years, stage, glucose_mgdl,
tmb_nonsynonymous, <GENE>_count x5, n_qc_flags`) and concatenated with a
`cohort` column. Sex is recoded to one vocabulary (`female/male` to `F/M`),
clinic age is computed from the cleaned date of birth at the data-generation
date (`reference_date` in `config.yaml`), and columns that only one cohort
has are `NA` for the other. The script asserts that the row count is the sum
of the inputs and that record ids are unique.

## Comments for instructor

The Lab 3 and Lab 4 scripts are my own from those repos
(`aram-yan/hds-lab3`, `aram-yan/hds-lab4`), changed only to take input and
output paths as arguments instead of hard-coded locations, so that the
workflow owns every path.
