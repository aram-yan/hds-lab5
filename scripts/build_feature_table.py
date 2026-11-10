"""Query cohort.db into a one-row-per-patient feature table (Lab 4 logic, reused
in the Lab 5 workflow).

SQL does the querying and joining (sql/queries.sql); pandas does the reshape
from long (patient, gene, count) to wide (one column per gene). Row counts
are checked at every step and written to <out>/query_row_counts.md.

Usage:
    python scripts/build_feature_table.py --db PATH --out DIR
Called by the `query_features` rule in the Snakefile. Both paths come from the
workflow; the SQL file is the one declared as a rule input.
"""
import argparse
import re
import sqlite3
from pathlib import Path

import pandas as pd

DEFAULT_DB = Path("data/raw/cohort.db")
DEFAULT_SQL = Path(__file__).resolve().parent.parent / "sql" / "queries.sql"
GENES = ["TP53", "KRAS", "EGFR", "STK11", "KEAP1"]
N_PATIENTS_EXPECTED = 566
NA_CODE = "NA"  # how missing clinical values are written in the TSV


def load_queries(path):
    """Split queries.sql into {name: sql} using the '-- name:' marker lines."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^-- name: (\w+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--sql", type=Path, default=DEFAULT_SQL, help="queries.sql")
    ap.add_argument("--out", type=Path, default=Path("results/features"))
    args = ap.parse_args()
    if not args.db.exists():
        raise SystemExit(f"database not found: {args.db} (pass --db)")
    args.out.mkdir(parents=True, exist_ok=True)

    q = load_queries(args.sql)
    con = sqlite3.connect(args.db)
    counts = []  # (query, expected, actual, note)

    # Patient count before any join: the number every later step must preserve.
    n_before = pd.read_sql(q["check_patient_count"], con).iloc[0, 0]
    assert n_before == N_PATIENTS_EXPECTED, n_before
    counts.append(("patients table (before joins)", N_PATIENTS_EXPECTED, n_before, "baseline"))

    # Query 1: per patient x gene protein-altering counts (long format).
    long = pd.read_sql(q["q1_gene_counts"], con)
    exp1 = N_PATIENTS_EXPECTED * len(GENES)
    counts.append(("q1_gene_counts", exp1, len(long),
                   "566 patients x 5 genes; zero rows kept by LEFT JOIN with filters in ON"))
    assert len(long) == exp1, len(long)
    assert long.groupby("patient_id").size().eq(len(GENES)).all()

    # Query 2: patients per site per stage (NULL stage kept).
    site_stage = pd.read_sql(q["q2_site_by_stage"], con)
    n_null_stage_rows = site_stage["stage"].isna().sum()
    counts.append(("q2_site_by_stage", "unknown a priori (occurring site x stage combos)",
                   len(site_stage),
                   f"n_patients sums to {site_stage['n_patients'].sum()}; "
                   f"{n_null_stage_rows} rows have NULL stage"))
    assert site_stage["n_patients"].sum() == N_PATIENTS_EXPECTED
    assert n_null_stage_rows > 0, "NULL-stage patients were dropped"
    site_stage.to_csv(args.out / "patients_by_site_stage.tsv", sep="\t", index=False, na_rep=NA_CODE)

    # Query 3: one clinical row per patient.
    clinical = pd.read_sql(q["q3_clinical"], con)
    counts.append(("q3_clinical", N_PATIENTS_EXPECTED, len(clinical), "one sample per patient"))
    assert len(clinical) == N_PATIENTS_EXPECTED
    assert clinical["patient_id"].is_unique

    # Reshape long -> wide in pandas (Task 3). Grain is already one row per
    # (patient, gene), so pivot needs no aggregation; a patient with several
    # mutations in one gene is already a single row with count > 1.
    wide = (long.pivot(index="patient_id", columns="gene_symbol", values="n_protein_altering")
                .reindex(columns=GENES)
                .astype(int))
    wide.columns = [f"{g}_count" for g in GENES]
    wide = wide.reset_index()
    assert len(wide) == N_PATIENTS_EXPECTED

    features = clinical.merge(wide, on="patient_id", how="left", validate="one_to_one")
    n_after = len(features)
    counts.append(("feature table (after joins + pivot)", N_PATIENTS_EXPECTED, n_after, "no patient lost"))
    assert n_after == N_PATIENTS_EXPECTED and features["patient_id"].is_unique
    assert features[[f"{g}_count" for g in GENES]].notna().all().all()

    # Age is stored as REAL (70.0); write it as a nullable integer.
    features["age_at_diagnosis"] = features["age_at_diagnosis"].astype("Int64")
    features = features.sort_values("patient_id").reset_index(drop=True)
    features.to_csv(args.out / "feature_table.tsv", sep="\t", index=False, na_rep=NA_CODE)

    # Task 5: data dictionary, generated here so it cannot drift from the table.
    gene_def = ("Number of protein-altering somatic mutations in {g} in the patient's tumor "
                "sample: all variant_classification values except Silent (Missense, Nonsense, "
                "Splice_Site, Frame_Shift_Del/Ins, In_Frame_Del/Ins, Nonstop, Translation_Start_Site). "
                "0 means the sample was sequenced and no qualifying mutation was called.")
    rows = [
        ("patient_id", "TCGA patient barcode; one row per patient", "", "patients", "never missing"),
        ("sex", "Patient sex as recorded by TCGA (female/male)", "", "patients",
         f"{NA_CODE} when not recorded"),
        ("age_at_diagnosis", "Age at initial pathologic diagnosis", "years", "patients",
         f"{NA_CODE} when not recorded"),
        ("stage", "AJCC pathologic tumor stage (IA, IB, IIA, IIB, IIIA, IIIB, IV; a few coded only I or II)",
         "", "patients", f"{NA_CODE} when not recorded"),
        ("tissue_source_site", "Institution that contributed the tumor sample", "", "samples",
         "never missing"),
        ("tmb_nonsynonymous", "Tumor mutation burden, nonsynonymous mutations per megabase, "
         "as computed by cBioPortal", "mutations/Mb", "samples", "never missing"),
    ] + [
        (f"{g}_count", gene_def.format(g=g), "count", "mutations (via samples)",
         "never missing; 0 = no qualifying mutation, not unknown")
        for g in GENES
    ]
    dictionary = pd.DataFrame(rows, columns=["column", "meaning", "units", "source_table", "missing_values"])
    assert list(dictionary["column"]) == list(features.columns), "dictionary and table columns differ"
    dictionary.to_csv(args.out / "data_dictionary.tsv", sep="\t", index=False)

    # Task 4 evidence: how many values are missing per column, after the joins.
    missing = (features.isna().sum().rename("n_missing")
               .rename_axis("column").reset_index())
    missing.to_csv(args.out / "missing_values_summary.tsv", sep="\t", index=False)

    # Row-count log (Task 2: expected vs actual).
    lines = ["| step | expected rows | actual rows | note |", "|---|---|---|---|"]
    lines += [f"| {s} | {e} | {a} | {n} |" for s, e, a, n in counts]
    (args.out / "query_row_counts.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"patients before joins: {n_before}; feature table rows: {n_after}")
    print("\n".join(lines))
    print("\nmissing values per column:")
    print(missing.to_string(index=False))
    print("\npatients with >=1 protein-altering mutation per gene:")
    print({g: int((features[f'{g}_count'] > 0).sum()) for g in GENES})
    print(f"\nwrote {args.out / 'feature_table.tsv'} ({features.shape[0]} rows x {features.shape[1]} cols)")


if __name__ == "__main__":
    main()
