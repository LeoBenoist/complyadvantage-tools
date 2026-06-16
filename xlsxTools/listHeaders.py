"""
list_excel_headers.py
Lists headers that are NOT present in every Excel file in a folder (non-universal headers).

Usage:
    python list_excel_headers.py <folder_path>
    python list_excel_headers.py <folder_path> --output headers.csv
"""

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd


def get_headers(folder: Path) -> list[dict]:
    excel_extensions = {".xlsx", ".xlsm", ".xls", ".xlsb"}
    results = []

    files = sorted(f for f in folder.iterdir() if f.suffix.lower() in excel_extensions)

    if not files:
        print(f"No Excel files found in: {folder}")
        return results

    for file in files:
        try:
            sheets = pd.read_excel(file, sheet_name=None, nrows=0)
            for sheet_name, df in sheets.items():
                results.append({
                    "file": file.name,
                    "sheet": sheet_name,
                    "headers": set(df.columns),
                })
        except Exception as e:
            print(f"  [ERROR] {file.name}: {e}", file=sys.stderr)

    return results


def find_non_universal_headers(results: list[dict]) -> dict[str, list[str]]:
    """Return headers that are missing from at least one file, mapped to the files that have them."""
    all_headers: set[str] = set()
    for entry in results:
        all_headers |= entry["headers"]

    # A header is universal if every file/sheet entry contains it
    all_files = {entry["file"] for entry in results}
    header_files: dict[str, set[str]] = {h: set() for h in all_headers}
    for entry in results:
        for h in entry["headers"]:
            header_files[h].add(entry["file"])

    non_universal = {
        h: sorted(files)
        for h, files in header_files.items()
        if files != all_files
    }
    return non_universal


def print_results(results: list[dict], non_universal: dict[str, list[str]]) -> None:
    all_files = sorted({entry["file"] for entry in results})
    total_files = len(all_files)

    print(f"\nScanned {total_files} file(s), found {len(non_universal)} non-universal header(s).\n")

    if not non_universal:
        print("All headers are present in every file — no differences found.")
        return

    print(f"{'Header':<40} {'Present in':>10}  Files missing it")
    print("─" * 80)
    for header in sorted(non_universal):
        files_with = non_universal[header]
        files_without = sorted(set(all_files) - set(files_with))
        present = f"{len(files_with)}/{total_files}"
        missing_str = ", ".join(files_without)
        print(f"{str(header):<40} {present:>10}  (missing: {missing_str})")


def save_csv(results: list[dict], non_universal: dict[str, list[str]], output_path: Path) -> None:
    all_files = sorted({entry["file"] for entry in results})
    total_files = len(all_files)

    rows = []
    for header in sorted(non_universal):
        files_with = set(non_universal[header])
        files_without = sorted(set(all_files) - files_with)
        rows.append({
            "header": header,
            "present_in_count": len(files_with),
            "total_files": total_files,
            "files_with_header": ", ".join(sorted(files_with)),
            "files_missing_header": ", ".join(files_without),
        })

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "header", "present_in_count", "total_files",
            "files_with_header", "files_missing_header",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResults saved to: {output_path}  ({len(rows)} non-universal headers)")


def main():
    parser = argparse.ArgumentParser(
        description="List headers that are not present in every Excel file in a folder."
    )
    parser.add_argument("folder", help="Path to the folder containing Excel files")
    parser.add_argument("--output", "-o", help="Optional CSV file to save results", default=None)
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Error: '{folder}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning: {folder.resolve()}")
    results = get_headers(folder)

    if not results:
        return

    non_universal = find_non_universal_headers(results)
    print_results(results, non_universal)

    if args.output:
        save_csv(results, non_universal, output_path=Path(args.output))


if __name__ == "__main__":
    main()