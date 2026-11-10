"""Combine the cleaned clinic samples (Lab 3) and the TCGA feature table (Lab 4)
into one analytic table.

The two cohorts share no identifier: the clinic records are synthetic
(S0001..S0060) and the TCGA rows are patient barcodes, so a key-based join is
impossible (an inner join returns 0 rows, an outer join just pads). The
correct combination is a *harmonised stack*: both tables are mapped onto one
shared schema and concatenated with a `cohort` column, so downstream code can
summarise either cohort or both with the same column names.

Shared schema (one row per record):
    cohort            lab3_clinic | tcga_luad
    record_id         sample_id | patient_id
    sex               M / F / U / NA   (TCGA female/male recoded)
    site              clinic enrollment site | TCGA tissue source site
    age_years         clinic: age at the reference date from dob;
                      TCGA: age_at_diagnosis
    stage             NA for the clinic
    glucose_mgdl      NA for TCGA
    tmb_nonsynonymous NA for the clinic
    <GENE>_count      NA for the clinic (five genes)
    n_qc_flags        clinic: number of raised cleaning flags; TCGA: 0

Usage:
    python scripts/merge_tables.py --samples S --features F --output OUT \
        --reference-date YYYY-MM-DD
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

GENES = ["TP53", "KRAS", "EGFR", "STK11", "KEAP1"]
QC_FLAGS = ["dob_century_assumed", "dob_order_ambiguous", "glucose_starred", "glucose_unit_suspect"]
COLUMNS = (
    ["cohort", "record_id", "sex", "site", "age_years", "stage", "glucose_mgdl",
     "tmb_nonsynonymous"] + [f"{g}_count" for g in GENES] + ["n_qc_flags"]
)
SEX_MAP = {"female": "F", "male": "M", "M": "M", "F": "F", "U": "U"}


def harmonise_clinic(samples: pd.DataFrame, reference_date: str) -> pd.DataFrame:
    """Map the Lab 3 cleaned samples onto the shared schema."""
    ref = pd.Timestamp(reference_date)
    dob = pd.to_datetime(samples["dob"], errors="coerce")
    age = ((ref - dob).dt.days / 365.25).round(1)
    out = pd.DataFrame({
        "cohort": "lab3_clinic",
        "record_id": samples["sample_id"],
        "sex": samples["sex"].map(SEX_MAP),
        "site": samples["site"],
        "age_years": age,
        "stage": pd.NA,
        "glucose_mgdl": pd.to_numeric(samples["glucose_mgdl"], errors="coerce"),
        "tmb_nonsynonymous": pd.NA,
        "n_qc_flags": samples[QC_FLAGS].astype(bool).sum(axis=1),
    })
    for g in GENES:
        out[f"{g}_count"] = pd.NA
    return out[COLUMNS]


def harmonise_tcga(features: pd.DataFrame) -> pd.DataFrame:
    """Map the Lab 4 feature table onto the shared schema."""
    out = pd.DataFrame({
        "cohort": "tcga_luad",
        "record_id": features["patient_id"],
        "sex": features["sex"].map(SEX_MAP),
        "site": features["tissue_source_site"],
        "age_years": features["age_at_diagnosis"],
        "stage": features["stage"],
        "glucose_mgdl": pd.NA,
        "tmb_nonsynonymous": features["tmb_nonsynonymous"],
        "n_qc_flags": 0,
    })
    for g in GENES:
        out[f"{g}_count"] = features[f"{g}_count"]
    return out[COLUMNS]


def main() -> None:
    ap = argparse.ArgumentParser(description="harmonise and stack the two cohorts")
    ap.add_argument("--samples", required=True, type=Path, help="cleaned clinic samples TSV")
    ap.add_argument("--features", required=True, type=Path, help="TCGA feature table TSV")
    ap.add_argument("--output", required=True, type=Path, help="combined TSV to write")
    ap.add_argument("--reference-date", default="2026-08-08",
                    help="date the clinic ages are computed at (data generation date)")
    args = ap.parse_args()

    samples = pd.read_csv(args.samples, sep="\t", dtype={"sample_id": str, "sex": str},
                          keep_default_na=False, na_values=[""])
    features = pd.read_csv(args.features, sep="\t", na_values=["NA"])

    clinic = harmonise_clinic(samples, args.reference_date)
    tcga = harmonise_tcga(features)
    combined = pd.concat([clinic, tcga], ignore_index=True)

    # Row-count checks: nothing lost, nothing duplicated (Lab 4 habit).
    assert len(combined) == len(samples) + len(features), (len(combined), len(samples), len(features))
    assert combined["record_id"].is_unique, "record ids collide across cohorts"
    assert set(combined["cohort"]) == {"lab3_clinic", "tcga_luad"}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.output, sep="\t", index=False, na_rep="NA")
    print(f"{len(samples)} clinic + {len(features)} TCGA -> {len(combined)} rows x "
          f"{combined.shape[1]} cols -> {args.output}")
    print(combined["cohort"].value_counts().to_string())


if __name__ == "__main__":
    main()
