import pandas as pd
from pathlib import Path


def find_duplicates(folder_path: str) -> None:
    folder = Path(folder_path)
    excel_files = list(folder.glob("*.xlsx")) + list(folder.glob("*.xls"))

    if not excel_files:
        print(f"No Excel files found in {folder_path}")
        return

    all_records = []

    for file in excel_files:
        try:
            df = pd.read_excel(file)
            if "transaction.external_identifier" not in df.columns:
                print(f"[SKIP] Column not found in: {file.name}")
                continue
            for value in df["transaction.external_identifier"].dropna():
                all_records.append({"file": file.name, "external_identifier": value})
        except Exception as e:
            print(f"[ERROR] Could not read {file.name}: {e}")

    if not all_records:
        print("No data found.")
        return

    combined = pd.DataFrame(all_records)
    duplicates = combined[combined.duplicated(subset="external_identifier", keep=False)]

    if duplicates.empty:
        print("No duplicates found.")
        return

    duplicates_sorted = duplicates.sort_values("external_identifier")
    print(f"Found {duplicates['external_identifier'].nunique()} duplicate external identifier(s):\n")
    print(duplicates_sorted.to_string(index=False))

    output_path = folder / "duplicate_external_ids.csv"
    duplicates_sorted.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python find_duplicate_external_ids.py <folder_path>")
        sys.exit(1)

    find_duplicates(sys.argv[1])
