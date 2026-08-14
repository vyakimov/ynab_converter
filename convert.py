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
        "input_file",
        nargs="?",
        help="Path to input eksport CSV (may also be given with -i)",
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
        help="Path to output YNAB CSV (supports {date} placeholder as YYYYMMDD). "
        "Defaults to ynab_data_{date}.csv next to the input file",
    )
    args = p.parse_args()
    # The positional form wins when both are given
    if args.input_file:
        args.input = args.input_file
    return args


def resolve_paths(
    input_path: str, output_path: Optional[str]
) -> tuple[str, Optional[str]]:
    in_path = os.path.expanduser(input_path) if input_path else None
    if output_path:
        out_path = output_path
    else:
        # Default to writing alongside the input file
        folder = os.path.dirname(os.path.abspath(in_path)) if in_path else "."
        out_path = os.path.join(folder, "ynab_data_{date}.csv")
    today = datetime.today().strftime("%Y%m%d")
    out_path = out_path.replace("{date}", today)
    out_path = os.path.expanduser(out_path)
    return in_path, out_path


# Matches common date layouts, e.g. 11-08-2026, 2026/08/11, 11.08.26
DATE_PATTERN = r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$"


def numeric_columns(df: pd.DataFrame) -> dict:
    """Return {column: parsed values} for every column that holds numbers."""
    found = {}
    for col in df.columns:
        raw = df[col].fillna("").astype(str).str.strip()
        non_empty = raw[raw != ""]
        if non_empty.empty:
            continue
        parsed = to_number(df[col])
        # A date column parses to NaN, so it never qualifies here
        if parsed[non_empty.index].notna().mean() >= 0.8:
            found[col] = parsed
    return found


def is_running_balance(balance: pd.Series, amount: pd.Series) -> bool:
    """True if `balance` is a running total whose steps are `amount`.

    Handles both row orders: newest-first (balance minus the row below) and
    oldest-first (balance minus the row above).
    """
    for shift in (-1, 1):
        steps = balance - balance.shift(shift)
        usable = steps.notna() & amount.notna()
        if usable.sum() < 2:
            continue
        if ((steps[usable] - amount[usable]).abs() <= 0.01).mean() >= 0.9:
            return True
    return False


def detect_amount_column(df: pd.DataFrame):
    """Find the transaction amount column.

    Banks may add extra numeric columns (most commonly a running account
    balance), so instead of relying on position we discard any column that
    behaves like a running total of another one, then prefer a column that
    actually contains negative values.
    """
    candidates = numeric_columns(df)
    if not candidates:
        # Fallback to the third column if present
        return 2 if 2 in df.columns else df.columns[-1]

    remaining = [
        col
        for col, values in candidates.items()
        if not any(
            is_running_balance(values, other)
            for name, other in candidates.items()
            if name != col
        )
    ]
    if not remaining:
        remaining = list(candidates)
    if len(remaining) == 1:
        return remaining[0]

    # Transaction amounts include spending; balances and reference numbers
    # rarely do. Leftmost wins any remaining tie.
    with_negatives = [col for col in remaining if (candidates[col] < 0).any()]
    return (with_negatives or remaining)[0]


def detect_date_column(df: pd.DataFrame, exclude: set):
    for col in df.columns:
        if col in exclude:
            continue
        raw = df[col].fillna("").astype(str).str.strip()
        non_empty = raw[raw != ""]
        if not non_empty.empty and non_empty.str.match(DATE_PATTERN).mean() >= 0.8:
            return col
    return df.columns[0]


def detect_payee_column(df: pd.DataFrame, exclude: set):
    """Pick the wordiest remaining column - descriptions beat currency codes."""
    best, best_length = None, 0
    for col in df.columns:
        if col in exclude:
            continue
        length = df[col].fillna("").astype(str).str.strip().str.len().mean()
        if length > best_length:
            best, best_length = col, length
    if best is not None:
        return best
    return 1 if 1 in df.columns else df.columns[-1]


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

    # Replace NaNs with empty strings, then cleanup stray bullet and BOM chars
    df = df.where(pd.notna(df), "")
    df = df.apply(
        lambda col: col.astype(str).str.replace(r"[\u2022\ufeff]", "", regex=True)
    )

    amount_col = detect_amount_column(df)
    amounts = to_number(df[amount_col])

    date_col = detect_date_column(df, exclude={amount_col})
    payee_col = detect_payee_column(df, exclude={amount_col, date_col})

    outflow = amounts.where(amounts < 0, np.nan).abs()
    inflow = amounts.where(amounts > 0, np.nan)

    out = pd.DataFrame(
        {
            "Date": df[date_col].astype(str).str.strip(),
            "Payee": df[payee_col].astype(str).str.strip(),
            "Memo": "",
            "Outflow": format_number(outflow),
            "Inflow": format_number(inflow),
        }
    )

    # Drop rows without date or payee, plus anything with no usable amount
    # (a header row, for instance)
    out = out[(out["Date"] != "") & (out["Payee"] != "") & amounts.notna()]
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
