"""Summary report from the combined analytic table: one figure and a Markdown
text summary. Every number in the summary is computed here from the input.

Usage:
    python scripts/make_report.py --input combined.tsv --figure FIG.png --summary SUMMARY.md
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display needed inside the workflow
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

GENES = ["TP53", "KRAS", "EGFR", "STK11", "KEAP1"]


def make_figure(df: pd.DataFrame, path: Path) -> None:
    clinic = df[df["cohort"].eq("lab3_clinic")]
    tcga = df[df["cohort"].eq("tcga_luad")]

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))

    # Panel 1: clinic glucose by site
    sites = sorted(clinic["site"].dropna().unique())
    axes[0].boxplot([clinic.loc[clinic["site"].eq(s), "glucose_mgdl"].dropna() for s in sites],
                    tick_labels=sites)
    axes[0].set_title("Clinic cohort (Lab 3): glucose by site")
    axes[0].set_ylabel("glucose, mg/dL")

    # Panel 2: TCGA mutation burden by stage
    stage_order = [s for s in ["I", "IA", "IB", "II", "IIA", "IIB", "IIIA", "IIIB", "IV"]
                   if s in set(tcga["stage"].dropna())]
    axes[1].boxplot([tcga.loc[tcga["stage"].eq(s), "tmb_nonsynonymous"].dropna()
                     for s in stage_order], tick_labels=stage_order)
    axes[1].set_title("TCGA LUAD (Lab 4): TMB by stage")
    axes[1].set_ylabel("nonsynonymous mutations / Mb")
    axes[1].set_yscale("log")

    # Panel 3: share of TCGA patients with >= 1 protein-altering mutation per gene
    share = [(tcga[f"{g}_count"] > 0).mean() for g in GENES]
    axes[2].bar(GENES, share)
    axes[2].set_ylim(0, 1)
    axes[2].set_title("TCGA LUAD: patients with a mutation")
    axes[2].set_ylabel("share of 566 patients")

    fig.suptitle(f"Combined analytic table: {len(clinic)} clinic + {len(tcga)} TCGA records")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)


def write_summary(df: pd.DataFrame, figure: Path, path: Path) -> None:
    lines = ["# Summary report", "",
             f"Combined analytic table: {len(df)} records x {df.shape[1]} columns.", ""]

    lines += ["## Records per cohort", "", "| cohort | n | sex F | sex M | sex U | sex missing |",
              "|---|---|---|---|---|---|"]
    for cohort, g in df.groupby("cohort"):
        vc = g["sex"].value_counts(dropna=False)
        lines.append(f"| {cohort} | {len(g)} | {vc.get('F', 0)} | {vc.get('M', 0)} | "
                     f"{vc.get('U', 0)} | {int(g['sex'].isna().sum())} |")

    clinic = df[df["cohort"].eq("lab3_clinic")]
    tcga = df[df["cohort"].eq("tcga_luad")]
    lines += ["", "## Clinic cohort (Lab 3 cleaning)", ""]
    lines.append(f"- glucose available for {int(clinic['glucose_mgdl'].notna().sum())} of "
                 f"{len(clinic)} samples; median {clinic['glucose_mgdl'].median():.1f} mg/dL "
                 f"(IQR {clinic['glucose_mgdl'].quantile(0.25):.1f} to "
                 f"{clinic['glucose_mgdl'].quantile(0.75):.1f})")
    lines.append(f"- samples per site: " + ", ".join(
        f"{s} = {n}" for s, n in clinic["site"].value_counts().sort_index().items()))
    lines.append(f"- age at reference date: median {clinic['age_years'].median():.1f} years "
                 f"({int(clinic['age_years'].isna().sum())} unparseable dates)")
    lines.append(f"- records with at least one cleaning flag raised: "
                 f"{int((clinic['n_qc_flags'] > 0).sum())}")

    lines += ["", "## TCGA LUAD cohort (Lab 4 queries)", ""]
    lines.append(f"- {len(tcga)} patients; median age at diagnosis "
                 f"{tcga['age_years'].median():.0f} years ({int(tcga['age_years'].isna().sum())} missing)")
    lines.append(f"- median TMB {tcga['tmb_nonsynonymous'].median():.1f} nonsynonymous mutations/Mb")
    lines.append("- patients with >= 1 protein-altering mutation: " + ", ".join(
        f"{g} {int((tcga[f'{g}_count'] > 0).sum())}" for g in GENES))
    lines.append(f"- stage missing for {int(tcga['stage'].isna().sum())} patients")

    lines += ["", "## Missing values per column (whole table)", "",
              "| column | n missing |", "|---|---|"]
    lines += [f"| {c} | {int(n)} |" for c, n in df.isna().sum().items()]

    lines += ["", f"Figure: `{figure.as_posix()}`", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--figure", required=True, type=Path)
    ap.add_argument("--summary", required=True, type=Path)
    args = ap.parse_args()

    df = pd.read_csv(args.input, sep="\t", na_values=["NA"])
    make_figure(df, args.figure)
    write_summary(df, args.figure, args.summary)
    print(f"wrote {args.figure} and {args.summary} from {len(df)} records")


if __name__ == "__main__":
    main()
