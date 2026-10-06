#!/usr/bin/env python3
"""
Set labels on customers from an Excel file.

The input Excel file must have two columns:
  - customer_id : UUID of the customer
  - label_id    : UUID of the label to assign

All label_ids for the same customer_id are collected and sent in a single
PUT request to /v2/customers/{customer_id}/labels.

Usage:
    python set_customer_labels.py <input.xlsx> [--dry-run]
"""

import argparse
import sys
import pandas as pd
import mesh_client


def set_customer_labels(customer_id: str, label_ids: list[str], dry_run: bool) -> None:
    endpoint = f"/v2/customers/{customer_id}/labels"
    if dry_run:
        print(f"  [dry-run] PUT {endpoint} -> {label_ids}")
        return
    mesh_client._send_live_request("PUT", endpoint, json_payload=label_ids)
    print(f"  Set {len(label_ids)} label(s) on customer {customer_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set labels on customers from an Excel file")
    parser.add_argument("input_file", help="Path to the Excel file (must have customer_id and label_id columns)")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without making API calls")
    args = parser.parse_args()

    # Load and validate the Excel file
    try:
        df = pd.read_excel(args.input_file)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        sys.exit(1)

    missing = [c for c in ("customer_id", "label_id") if c not in df.columns]
    if missing:
        print(f"Error: missing column(s) in Excel file: {', '.join(missing)}")
        sys.exit(1)

    df = df.dropna(subset=["customer_id", "label_id"])
    df["customer_id"] = df["customer_id"].astype(str).str.strip()
    df["label_id"] = df["label_id"].astype(str).str.strip()

    # Group label_ids by customer_id
    grouped = df.groupby("customer_id")["label_id"].apply(list).to_dict()
    print(f"Found {len(grouped)} unique customer(s) across {len(df)} row(s)")

    # Authenticate via mesh_client
    # mesh_client.authenticate(
    #     mesh_client.default_username,
    #     mesh_client.default_password,
    #     mesh_client.default_realm,
    # )
    # accounts = mesh_client.get_accounts(mesh_client.default_account_name)
    # if accounts:
    #     print(f"Found accounts: {[acc['name'] for acc in accounts]}")
    #     mesh_client.set_account(accounts[0]["identifier"])
    # else:
    #     print(f"No account found with the name '{mesh_client.default_account_name}'. Exiting.")
    #     sys.exit(1)
    #
    # mesh_client.verify_account()

    # Apply labels
    failed = 0
    for i, (customer_id, label_ids) in enumerate(grouped.items(), 1):
        print(f"\n[{i}/{len(grouped)}] Customer {customer_id} -> {label_ids}")
        try:
            set_customer_labels(customer_id, label_ids, args.dry_run)
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print(f"\nDone. {len(grouped) - failed}/{len(grouped)} customer(s) updated successfully.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()