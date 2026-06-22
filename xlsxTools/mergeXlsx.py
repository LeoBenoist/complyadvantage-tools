#!/usr/bin/env python3
"""
Merge all .xlsx files in a folder into one (or several) output spreadsheet(s).

Behaviour:
  - Reads every .xlsx file in the input folder.
  - Builds a unified set of columns: headers shared across files appear once,
    unique headers from individual files are kept. No duplicated columns.
  - Sorts all rows chronologically by the `transaction.occurred_at.timestamp`
    column (ISO 8601, e.g. 2026-04-30T21:46:58.000000Z).
  - Optionally splits the merged output into multiple files of X rows each.

Usage:
  python merge_xlsx.py INPUT_DIR [-o OUTPUT.xlsx] [--split N]
                       [--timestamp-col COL] [--sheet SHEET] [--recursive]

Examples:
  python merge_xlsx.py ./data
  python merge_xlsx.py ./data -o merged.xlsx
  python merge_xlsx.py ./data -o merged.xlsx --split 50000
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

TIMESTAMP_COL = "transaction.occurred_at.timestamp"


def find_xlsx_files(input_dir: Path, recursive: bool) -> list[Path]:
    pattern = "**/*.xlsx" if recursive else "*.xlsx"
    files = [
        p
        for p in sorted(input_dir.glob(pattern))
        if not p.name.startswith("~$")  # skip Excel temp/lock files
    ]
    return files


def read_all(files: list[Path], sheet) -> tuple[pd.DataFrame, list[str]]:
    """Read every file, preserving column order of first appearance across files."""
    frames = []
    ordered_cols: list[str] = []
    seen = set()

    for f in files:
        try:
            df = pd.read_excel(f, sheet_name=sheet, dtype=object)
        except Exception as e:
            print(f"  ! Skipping {f.name}: {e}", file=sys.stderr)
            continue
        df["__source_file__"] = f.name
        frames.append(df)
        for col in df.columns:
            if col not in seen:
                seen.add(col)
                ordered_cols.append(col)
        print(f"  + {f.name}: {len(df)} rows, {len(df.columns) - 1} columns")

    if not frames:
        raise SystemExit("No readable .xlsx files found.")

    # Union of all columns; missing columns become NaN automatically on concat.
    merged = pd.concat(frames, ignore_index=True, sort=False)
    # Reorder to first-appearance order (keeps __source_file__ last).
    cols = [c for c in ordered_cols if c != "__source_file__"] + ["__source_file__"]
    merged = merged.reindex(columns=cols)
    return merged, cols


def sort_chronologically(df: pd.DataFrame, ts_col: str) -> pd.DataFrame:
    if ts_col not in df.columns:
        print(
            f"  ! Timestamp column '{ts_col}' not found — output left unsorted.",
            file=sys.stderr,
        )
        return df
    parsed = pd.to_datetime(df[ts_col], format="ISO8601", utc=True, errors="coerce")
    n_bad = parsed.isna().sum()
    if n_bad:
        print(
            f"  ! {n_bad} row(s) had an unparseable timestamp — sorted to the end.",
            file=sys.stderr,
        )
    df = df.assign(__ts__=parsed).sort_values(
        "__ts__", kind="stable", na_position="last"
    )
    return df.drop(columns="__ts__").reset_index(drop=True)


def write_output(df: pd.DataFrame, out_path: Path, split: int | None) -> list[Path]:
    written = []
    if not split or split <= 0 or len(df) <= split:
        df.to_excel(out_path, index=False)
        written.append(out_path)
        return written

    total_parts = (len(df) + split - 1) // split
    width = len(str(total_parts))
    for i in range(total_parts):
        chunk = df.iloc[i * split : (i + 1) * split]
        part_path = out_path.with_name(
            f"{out_path.stem}_part{i + 1:0{width}d}{out_path.suffix}"
        )
        chunk.to_excel(part_path, index=False)
        written.append(part_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge all .xlsx files in a folder, dedupe headers, sort by timestamp."
    )
    parser.add_argument("input_dir", type=Path, help="Folder containing .xlsx files")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .xlsx path (default: <input_dir>/merged.xlsx)",
    )
    parser.add_argument(
        "--split",
        type=int,
        default=None,
        metavar="N",
        help="Split output into multiple files of N rows each",
    )
    parser.add_argument(
        "--timestamp-col",
        default=TIMESTAMP_COL,
        help=f"Column used for chronological sort (default: {TIMESTAMP_COL})",
    )
    parser.add_argument(
        "--sheet",
        default=0,
        help="Sheet name or index to read from each file (default: first sheet)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search subfolders for .xlsx files too",
    )
    parser.add_argument(
        "--keep-source-col",
        action="store_true",
        help="Keep a __source_file__ column recording each row's origin file",
    )
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        raise SystemExit(f"Not a directory: {args.input_dir}")

    output = args.output or (args.input_dir / "merged.xlsx")
    output.parent.mkdir(parents=True, exist_ok=True)

    files = find_xlsx_files(args.input_dir, args.recursive)
    # Avoid re-ingesting the output file if it lives in the input dir.
    files = [f for f in files if f.resolve() != output.resolve()]
    if not files:
        raise SystemExit(f"No .xlsx files found in {args.input_dir}")

    print(f"Found {len(files)} file(s):")
    merged, _ = read_all(files, args.sheet)
    merged = sort_chronologically(merged, args.timestamp_col)

    if not args.keep_source_col and "__source_file__" in merged.columns:
        merged = merged.drop(columns="__source_file__")

    written = write_output(merged, output, args.split)

    print(
        f"\nMerged {len(merged)} rows × {len(merged.columns)} columns "
        f"into {len(written)} file(s):"
    )
    for p in written:
        print(f"  -> {p}")


if __name__ == "__main__":
    main()