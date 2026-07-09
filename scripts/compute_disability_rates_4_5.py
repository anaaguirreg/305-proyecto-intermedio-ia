"""
compute_disability_rates_4_5.py — compute disability rates for sub_acto_4_5.

Reads:
  data/agregados_forense/ds4_interseccional.parquet  (VIF forensic, DS4)
  data/agregados_seforense/ds3_interseccional.parquet (Sexual forensic, DS3)

Disability field: dimension_discapacidad (categorical)
  Values: CON_CONDICION_DISCAPACIDAD | SIN_DISCAPACIDAD

Note: the interseccional parquets are PRE-AGGREGATED (not row-level).
Each row is a (ciclo_vital × dimension_etnia × dimension_discapacidad) cell
with n_casos count and pct_femenino. Disability counts are obtained by
summing n_casos per dimension_discapacidad category.

Sex breakdown is estimated from pct_femenino: female ≈ n_casos × pct_femenino/100.
Department breakdown is NOT available in interseccional (no departamento column).

Output: stdout only. Do not save JSON.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DS4_PATH = PROJECT_ROOT / "data" / "agregados_forense"  / "ds4_interseccional.parquet"
DS3_PATH = PROJECT_ROOT / "data" / "agregados_seforense" / "ds3_interseccional.parquet"

DISABILITY_COL = "dimension_discapacidad"
WITH_DISABILITY = "CON_CONDICION_DISCAPACIDAD"
WITHOUT_DISABILITY = "SIN_DISCAPACIDAD"

SEP = "=" * 60


def check_disability_field(df: pd.DataFrame, label: str) -> None:
    """Halt with diagnostic if disability field is missing or ambiguous."""
    candidates = [c for c in df.columns if "discap" in c.lower()]
    if DISABILITY_COL not in df.columns:
        print(f"HALT — {label}: expected '{DISABILITY_COL}' not found.")
        print(f"  Candidate columns: {candidates}")
        raise SystemExit(1)
    found_vals = set(df[DISABILITY_COL].unique())
    expected_vals = {WITH_DISABILITY, WITHOUT_DISABILITY}
    unexpected = found_vals - expected_vals
    if unexpected:
        print(f"HALT — {label}: unexpected values in '{DISABILITY_COL}': {unexpected}")
        raise SystemExit(1)


def compute_rates(df: pd.DataFrame, label: str) -> None:
    print(f"\n{SEP}")
    print(f"{label}")
    print(SEP)

    check_disability_field(df, label)

    total = df["n_casos"].sum()
    n_with = df.loc[df[DISABILITY_COL] == WITH_DISABILITY, "n_casos"].sum()
    n_without = df.loc[df[DISABILITY_COL] == WITHOUT_DISABILITY, "n_casos"].sum()
    pct_with = n_with / total * 100

    print(f"Total cases (n_casos sum): {total:,}")
    print(f"  CON_CONDICION_DISCAPACIDAD : {n_with:,}  ({pct_with:.2f}%)")
    print(f"  SIN_DISCAPACIDAD           : {n_without:,}  ({n_without/total*100:.2f}%)")

    # Sex estimate (pct_femenino is per row — weighted by n_casos)
    df_con = df[df[DISABILITY_COL] == WITH_DISABILITY].copy()
    if "pct_femenino" in df.columns and not df_con.empty:
        est_f = (df_con["n_casos"] * df_con["pct_femenino"] / 100).sum()
        est_m = n_with - est_f
        print(f"\nSex estimate (from pct_femenino, CON_CONDICION only):")
        print(f"  Estimated female: {est_f:.0f}  ({est_f/n_with*100:.1f}%)")
        print(f"  Estimated male  : {est_m:.0f}  ({est_m/n_with*100:.1f}%)")

    # Breakdown by ciclo_vital
    print(f"\nBy ciclo_vital (CON_CONDICION_DISCAPACIDAD / total in group):")
    cv_pivot = (
        df.groupby(["ciclo_vital", DISABILITY_COL])["n_casos"]
        .sum()
        .unstack(fill_value=0)
    )
    cv_pivot["total"] = cv_pivot.sum(axis=1)
    if WITH_DISABILITY in cv_pivot.columns:
        cv_pivot["pct_con"] = cv_pivot[WITH_DISABILITY] / cv_pivot["total"] * 100
        for cv, row in cv_pivot.iterrows():
            n_c = int(row.get(WITH_DISABILITY, 0))
            tot = int(row["total"])
            pct = row["pct_con"]
            print(f"  {cv:<30s}: {n_c:>4d}/{tot:>6d}  ({pct:.2f}%)")

    # Breakdown by etnia
    print(f"\nBy dimension_etnia (CON_CONDICION_DISCAPACIDAD / total in group):")
    et_pivot = (
        df.groupby(["dimension_etnia", DISABILITY_COL])["n_casos"]
        .sum()
        .unstack(fill_value=0)
    )
    et_pivot["total"] = et_pivot.sum(axis=1)
    if WITH_DISABILITY in et_pivot.columns:
        et_pivot["pct_con"] = et_pivot[WITH_DISABILITY] / et_pivot["total"] * 100
        for et, row in et_pivot.iterrows():
            n_c = int(row.get(WITH_DISABILITY, 0))
            tot = int(row["total"])
            pct = row["pct_con"]
            print(f"  {et:<30s}: {n_c:>4d}/{tot:>6d}  ({pct:.2f}%)")

    print(f"\nNote: department breakdown not available (interseccional table has no")
    print(f"      departamento column — the parquet is aggregated across departments).")


def main() -> None:
    print("compute_disability_rates_4_5.py")
    print("Source: ds4_interseccional.parquet (DS4/VIF forensic)")
    print("        ds3_interseccional.parquet (DS3/Sexual forensic)")
    print("Disability field: dimension_discapacidad (categorical)")

    ds4 = pd.read_parquet(DS4_PATH)
    ds3 = pd.read_parquet(DS3_PATH)

    compute_rates(ds4, "DS4 — VIF FORENSIC (Violencia intrafamiliar, Medicina Legal)")
    compute_rates(ds3, "DS3 — SEXUAL FORENSIC (Violencia sexual, Medicina Legal)")

    print(f"\n{SEP}")
    print("COMBINED SUMMARY")
    print(SEP)
    total_ds4 = ds4["n_casos"].sum()
    total_ds3 = ds3["n_casos"].sum()
    n_con_ds4 = ds4.loc[ds4[DISABILITY_COL] == WITH_DISABILITY, "n_casos"].sum()
    n_con_ds3 = ds3.loc[ds3[DISABILITY_COL] == WITH_DISABILITY, "n_casos"].sum()
    print(f"DS4 disability rate: {n_con_ds4}/{total_ds4} = {n_con_ds4/total_ds4*100:.2f}%")
    print(f"DS3 disability rate: {n_con_ds3}/{total_ds3} = {n_con_ds3/total_ds3*100:.2f}%")
    print()
    if n_con_ds4 / total_ds4 < 0.02 and n_con_ds3 / total_ds3 < 0.02:
        print("RECOMMENDATION TRIGGER: Both rates < 2% → Option A (stat card).")
    elif max(n_con_ds4/total_ds4, n_con_ds3/total_ds3) < 0.10:
        print("RECOMMENDATION TRIGGER: At least one rate 2–10% → Option B (stat + bar).")
    else:
        print("RECOMMENDATION TRIGGER: Rate ≥ 10% → Option C (sunburst/treemap).")


if __name__ == "__main__":
    main()
