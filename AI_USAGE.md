# AI usage

**Model:** Claude (Claude Fable 5.1, Anthropic) via Claude Code. Date:
2026-11-09.

**What it did:** working from the lab's four-stage description and my Lab 3
and Lab 4 repositories, the AI drafted the `Snakefile` and `config.yaml`
(the lab says workflow syntax is a normal place to use AI help), the two new
scripts (`scripts/merge_tables.py`, `scripts/make_report.py`), the changes
that make my Lab 3 and Lab 4 scripts take every path as an argument, and the
first draft of the README. The regex cleaning logic, the SQL queries and the
feature-table code are my own from Labs 3 and 4 (`aram-yan/hds-lab3`,
`aram-yan/hds-lab4`) and were not rewritten.

## How the AI-written workflow was checked

The lab's own criteria were used as the checks, and the console output of
each is kept in `evidence/`:

1. **Clean full run.** `rm -rf results logs .snakemake && snakemake --cores 2`
   completes 5 of 5 steps in about 10 s (`evidence/clean_run.txt`). The
   row counts in the logs match the earlier labs: 60 cleaned samples, 566
   patients, 2,830 gene-count rows, 626 combined records.
2. **Partial re-run on an input change.** After appending one record to
   `data/raw/messy_samples.csv`, the dry run lists `clean_samples`,
   `merge_tables` and `report` only; `query_features` is not re-run, and
   the real run confirms it, 4 of 4 steps (`evidence/partial_rerun.txt`).
3. **Partial re-run on a parameter change.** `--config
   reference_date=2026-09-01` re-runs `merge_tables` and `report` only,
   because the date is a declared `params:` of `merge_tables`
   (`evidence/params_rerun.txt`).
4. **No hidden dependencies.** Each script was grepped for `read_csv`,
   `read_sql`, `open(`, `connect(` and hard-coded `Path(...)` literals;
   every file read or written arrives through a command-line argument that
   the Snakefile fills from `input:`/`output:`/`params:`. The one hidden
   dependency found was in my Lab 4 script, which located `sql/queries.sql`
   relative to its own file; it now takes `--sql`, and the SQL file is a
   declared input of `query_features`, so editing a query re-runs the rule.
5. **DAG shape.** `snakemake --dag` and `--rulegraph` (`evidence/dag.txt`)
   show `clean_samples` and `query_features` as independent parents of
   `merge_tables`, with `report` last.

## Design decision: stack, not join

The AI proposed a harmonised stack instead of a key-based merge, on the
grounds that the clinic samples (`S0001`..`S0060`, synthetic) and the TCGA
barcodes share no identifier. That claim was checked rather than taken on
trust: the two id sets overlap on 0 values and an inner join returns 0 rows
(`evidence/no_shared_key.txt`). The script asserts that the stacked row
count equals the sum of the inputs and that record ids are unique.

## Things changed from the AI draft

- The draft `.gitignore` ignored `results/`; the lab asks for the combined
  table and report to be in the repo, so `results/` is committed and only
  `data/`, `logs/` and `.snakemake/` are ignored.
- Downstream rules reference `rules.<name>.output` instead of repeating
  the output path strings, so a renamed output cannot silently break the
  chain.
- `matplotlib.use("Agg")` was added to the report script so the rule runs
  without a display; checked by running the rule from a plain terminal.
- Every rule writes a per-rule log under `logs/`, so a failing script
  leaves its own output behind, not only Snakemake's traceback.

All final files were reviewed by me and I take responsibility for them.
