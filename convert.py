#!/usr/bin/env python3
import argparse
import csv
import sys
from typing import Optional

import numpy as np
import pandas as pd

import os
from datetime import datetime


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Convert eksport.csv-style files to YNAB CSV using pandas"
    )
    p.add_argument(
        "-i",
        "--input",
        default="~/Downloads/eksport.csv",
        help="Path to input eksport CSV",
    )
    p.add_argument(
        "-o",
        "--output",
        default="~/Downloads/ynab_data_{date}.csv",
        help="Path to output YNAB CSV (supports {date} placeholder as YYYYMMDD)",
    )
    return p.parse_args()


def resolve_paths(
    input_path: str, output_path: Optional[str]
) -> tuple[str, Optional[str]]:
    in_path = os.path.expanduser(input_path) if input_path else None
    out_path = output_path or "~/Downloads/ynab_data_{date}.csv"
    today = datetime.today().strftime("%Y%m%d")
    out_path = out_path.replace("{date}", today)
    out_path = os.path.expanduser(out_path)
    return in_path, out_path


def detect_amount_column(df: pd.DataFrame) -> int:
    # Pick the rightmost column that contains digits and no letters
    for col in reversed(df.columns.tolist()):
        s = df[col].fillna("").astype(str).str.strip()
        if (
            s.str.contains(r"\d", regex=True).any()
            and not s.str.contains(r"[A-Za-z]", regex=True).any()
        ):
            return col
    # Fallback to the third column if present
    return 2 if 2 in df.columns else df.columns[-1]


def to_number(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str)
    s = s.str.replace("\xa0", "", regex=False).str.replace(" ", "", regex=False)
    s = s.str.replace(r"[^0-9,.-]", "", regex=True)
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def format_number(series: pd.Series) -> pd.Series:
    def _fmt(x: Optional[float]) -> str:
        if pd.isna(x) or x == 0:
            return ""
        # Use comma as thousands separator and dot as decimal separator
        return f"{float(x):,.2f}"

    return series.map(_fmt)


def convert(input_path: str) -> pd.DataFrame:
    df = pd.read_csv(
        input_path,
        sep=";",
        header=None,
        dtype=str,
        encoding="utf-8-sig",
        engine="python",
    )

    # Replace NaNs with empty strings, then cleanup stray bullet chars
    df = df.where(pd.notna(df), "")
    df = df.apply(lambda col: col.astype(str).str.replace("\u2022", "", regex=False))

    amount_col = detect_amount_column(df)
    amounts = to_number(df[amount_col])

    outflow = amounts.where(amounts < 0, np.nan).abs()
    inflow = amounts.where(amounts > 0, np.nan)

    out = pd.DataFrame(
        {
            "Date": df.get(0, "").astype(str).str.strip(),
            "Payee": df.get(1, "").astype(str).str.strip(),
            "Memo": "",
            "Outflow": format_number(outflow),
            "Inflow": format_number(inflow),
        }
    )

    # Drop rows without date or payee
    out = out[(out["Date"] != "") & (out["Payee"] != "")]
    return out


def write_output(df: pd.DataFrame, output_path: Optional[str]) -> None:
    if output_path:
        df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL, encoding="utf-8")
    else:
        df.to_csv(sys.stdout, index=False, quoting=csv.QUOTE_ALL)


def main() -> int:
    args = parse_args()
    in_path, out_path = resolve_paths(args.input, args.output)
    out_df = convert(in_path)
    write_output(out_df, out_path)
    print(f"Successfully converted {in_path} into {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
