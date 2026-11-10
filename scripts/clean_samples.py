"""Regex-based cleaning of messy_samples.csv (Lab 3 logic, reused in the Lab 5 workflow).

Usage: python scripts/clean_samples.py --input <messy_samples.csv> --output <samples_clean.tsv>
Called by the `clean_samples` rule in the Snakefile; input and output come
from the workflow, nothing is read from a hard-coded path.

Normalization decisions (documented per rubric):
- sample_id: 'S0001' / 's-0003' variants -> 'S0003' (upper, no punctuation).
- dob -> ISO YYYY-MM-DD. Four input formats: ISO, MM/DD/YYYY, DD-Mon-YYYY,
  and MM.DD.YY. Two-digit years use a study-anchored pivot: YY <= 26 ->
  20YY, else 19YY (a DOB cannot postdate the 2026 study). Flagged in
  dob_century_assumed. Numeric dates where both fields are <= 12 are
  month/day-order ambiguous under the assumed US order; flagged in
  dob_order_ambiguous.
- sex: {m,male}->M, {f,female}->F, {u,unknown}->U, blank stays missing.
  U (recorded as unknown) is deliberately distinct from missing (blank).
- enrollment_site: 'siteB', 'SITE-A', 'Site  C ', 'site_a' -> 'Site A/B/C'.
- glucose: trailing '*' stripped and flagged (glucose_starred). mmol/L
  converted to mg/dL (x18.0182, the standard glucose factor); original
  unit kept in glucose_unit_original.
- patient_name: title-cased ('J. SMITH' -> 'J. Smith').
"""
import argparse
import re
from pathlib import Path

import pandas as pd

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"])}
PIVOT = 26          # YY <= 26 -> 20YY (study year 2026), else 19YY
MMOL_TO_MGDL = 18.0182


def clean_sample_id(raw: str) -> str:
    m = re.fullmatch(r"[Ss]-?0*(\d+)", raw.strip())
    return f"S{int(m.group(1)):04d}" if m else raw.strip()


def clean_dob(raw: str):
    """Return (iso_date, century_assumed, order_ambiguous)."""
    s = raw.strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)           # ISO
    if m:
        return s, False, False
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)       # MM/DD/YYYY
    if m:
        mo, d, y = map(int, m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}", False, (mo <= 12 and d <= 12)
    m = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", s)   # DD-Mon-YYYY
    if m:
        d, mon, y = m.groups()
        return f"{int(y):04d}-{MONTHS[mon.lower()]:02d}-{int(d):02d}", False, False
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{2})", s)     # MM.DD.YY
    if m:
        mo, d, yy = map(int, m.groups())
        y = 2000 + yy if yy <= PIVOT else 1900 + yy
        return f"{y:04d}-{mo:02d}-{d:02d}", True, (mo <= 12 and d <= 12)
    return "", False, False                                    # unparsed


def clean_sex(raw: str) -> str:
    s = raw.strip().lower()
    return {"m": "M", "male": "M", "f": "F", "female": "F",
            "u": "U", "unknown": "U"}.get(s, "" if s == "" else s)


def clean_site(raw: str) -> str:
    m = re.search(r"(?i)site[\s_-]*([abc])", raw.strip())
    return f"Site {m.group(1).upper()}" if m else raw.strip()


MMOL_PLAUSIBLE_MAX = 30     # glucose above ~30 mmol/L is not survivable;
                            # a larger "mmol/L" value means the unit label
                            # is wrong, not the patient


def clean_glucose(value: str, unit: str):
    """Return (mgdl_value, unit_original, starred, unit_suspect)."""
    raw = value.strip()
    starred = raw.endswith("*")
    digits = re.sub(r"[^\d.]", "", raw)
    u = unit.strip()
    if digits == "":                               # "N/A" or blank
        return "", u, starred, False
    v = float(digits)
    if u.lower() == "mmol/l":
        if v > MMOL_PLAUSIBLE_MAX:
            # Value is mg/dL magnitude despite the label: converting would
            # produce an impossible result (e.g. 159.9 -> 2881 mg/dL).
            # Keep the number, flag the label as suspect.
            return round(v, 1), u, starred, True
        return round(v * MMOL_TO_MGDL, 1), u, starred, False
    return round(v, 1), u, starred, False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--input", required=True, type=Path, help="messy_samples.csv")
    ap.add_argument("--output", required=True, type=Path, help="cleaned TSV to write")
    args = ap.parse_args()
    df = pd.read_csv(args.input, dtype=str).fillna("")

    rows = []
    for _, r in df.iterrows():
        dob, century, ambiguous = clean_dob(r["dob"])
        glu, unit_orig, starred, suspect = clean_glucose(r["glucose_value"], r["glucose_unit"])
        rows.append({
            "sample_id": clean_sample_id(r["sample_id"]),
            "patient_name": r["patient_name"].strip().title(),
            "dob": dob,
            "dob_century_assumed": century,
            "dob_order_ambiguous": ambiguous,
            "sex": clean_sex(r["sex"]),
            "site": clean_site(r["enrollment_site"]),
            "glucose_mgdl": glu,
            "glucose_unit_original": unit_orig,
            "glucose_starred": starred,
            "glucose_unit_suspect": suspect,
            "notes": r["notes"].strip(),
        })
    out = pd.DataFrame(rows)

    out_path = args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, sep="\t", index=False)

    print(f"{len(out)} records cleaned -> {out_path}")
    print(f"  dates with assumed century : {int(out.dob_century_assumed.sum())}")
    print(f"  month/day-order ambiguous  : {int(out.dob_order_ambiguous.sum())}")
    print(f"  starred glucose values     : {int(out.glucose_starred.sum())}")
    print(f"  mmol/L-labeled rows        : {(out.glucose_unit_original.str.lower() == 'mmol/l').sum()}")
    print(f"  unit labels flagged suspect: {int(out.glucose_unit_suspect.sum())} (NOT converted)")
    print(f"  sex breakdown              : {out.sex.replace('', 'MISSING').value_counts().to_dict()}")
    print(f"  sites                      : {sorted(out.site.unique())}")


if __name__ == "__main__":
    main()
