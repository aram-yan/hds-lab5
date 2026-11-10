# Lab 5: four-stage analysis workflow (PUBH 6854).
#
#   messy_samples.csv --clean_samples--> samples_clean.tsv --+
#                                                            +--merge--> combined.tsv --report--> figure + summary
#   cohort.db + queries.sql --query_features--> feature_table.tsv --+
#
# Every rule declares every file it reads and writes; the scripts take all
# paths as arguments, so nothing depends on a file the workflow does not know
# about. Run `snakemake --cores 2` for everything, `snakemake -n` to preview.

configfile: "config.yaml"


rule all:
    input:
        "results/report/figure.png",
        "results/report/summary.md",


rule clean_samples:
    # Lab 3: regex cleaning of the messy clinic samples.
    input:
        config["messy_samples"],
    output:
        "results/samples_clean.tsv",
    log:
        "logs/clean_samples.log",
    shell:
        "python scripts/clean_samples.py --input {input} --output {output} > {log} 2>&1"


rule query_features:
    # Lab 4: SQL queries over cohort.db, pivoted to one row per patient.
    input:
        db=config["cohort_db"],
        sql="sql/queries.sql",
    output:
        table="results/features/feature_table.tsv",
        counts="results/features/query_row_counts.md",
        dictionary="results/features/data_dictionary.tsv",
        site_stage="results/features/patients_by_site_stage.tsv",
        missing="results/features/missing_values_summary.tsv",
    params:
        out_dir="results/features",
    log:
        "logs/query_features.log",
    shell:
        "python scripts/build_feature_table.py --db {input.db} --sql {input.sql} "
        "--out {params.out_dir} > {log} 2>&1"


rule merge_tables:
    # Harmonise both cohorts onto one schema and stack them (no shared key exists).
    input:
        samples=rules.clean_samples.output[0],
        features=rules.query_features.output.table,
    output:
        "results/combined.tsv",
    params:
        reference_date=config["reference_date"],
    log:
        "logs/merge_tables.log",
    shell:
        "python scripts/merge_tables.py --samples {input.samples} --features {input.features} "
        "--output {output} --reference-date {params.reference_date} > {log} 2>&1"


rule report:
    # Figure + Markdown summary computed from the combined table.
    input:
        rules.merge_tables.output[0],
    output:
        figure="results/report/figure.png",
        summary="results/report/summary.md",
    log:
        "logs/report.log",
    shell:
        "python scripts/make_report.py --input {input} --figure {output.figure} "
        "--summary {output.summary} > {log} 2>&1"
