#!/usr/bin/env python3
"""
Close all open TRANSACTION_MONITORING cases.

Usage:
    python close_tm_cases.py --base-url https://your-api.example.com --token YOUR_API_TOKEN [options]

Options:
    --base-url      API base URL (required)
    --token         Bearer token (required)
    --verdict       'false_positive' or 'true_positive' (default: false_positive)
    --note          Note to attach to the transition (default: 'Closed by script')
    --dry-run       Print what would be done without making changes
    --realm         Realm header value (optional, set if your API requires X-Realm)
"""

import argparse
import sys
import time
import requests

END_STATE_MAP = {
    "false_positive": "POSITIVE_END_STATE",
    "true_positive": "NEGATIVE_END_STATE",
}


def make_session(base_url: str, token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    s.base_url = base_url.rstrip("/")
    return s


def get(session: requests.Session, path: str, params: dict = None) -> dict:
    url = session.base_url + path
    r = session.get(url, params=params)
    r.raise_for_status()
    return r.json()


def post(session: requests.Session, path: str, body: dict) -> dict:
    url = session.base_url + path
    r = session.post(url, json=body)
    r.raise_for_status()
    return r.json()


def fetch_workflows(session: requests.Session) -> list[dict]:
    data = get(session, "/v2/cases/workflows", {"page_size": 100})
    return data.get("workflows", [])


def get_tm_decision_stage(workflows: list[dict]) -> str:
    """Return the first DECISION stage identifier for TRANSACTION_MONITORING workflow."""
    for wf in workflows:
        if wf.get("case_type") != "TRANSACTION_MONITORING":
            continue
        for stage in wf.get("stages", []):
            if stage.get("stage_type") == "DECISION":
                return stage["identifier"]
    return None


def fetch_open_tm_cases(session: requests.Session, open_stage_ids: list[str]) -> list[dict]:
    """Page through all open TM cases."""
    cases = []
    page = 1
    page_size = 100
    while True:
        params = {
            "page_number": page,
            "page_size": page_size,
            "case_type": "TRANSACTION_MONITORING",
        }
        if open_stage_ids:
            # The API accepts repeated query params; requests handles list values
            params["stage.identifier"] = open_stage_ids
        data = get(session, "/v2/cases", params)
        batch = data.get("cases", [])
        cases.extend(batch)
        total = data.get("total_count", 0)
        if len(cases) >= total or len(batch) == 0:
            break
        page += 1
    return cases


def fetch_open_stage_ids(workflows: list[dict], case_type: str) -> list[str]:
    """Return stage identifiers that are NOT decision stages (i.e. open stages) for a given case type."""
    ids = []
    for wf in workflows:
        if wf.get("case_type") != case_type:
            continue
        for stage in wf.get("stages", []):
            if not stage.get("decision_type"):
                ids.append(stage["identifier"])
    return sorted(ids)


def close_case(
    session: requests.Session,
    case: dict,
    decision_state: str,
    stage_id: str,
    note: str,
    dry_run: bool,
) -> None:
    case_id = case["identifier"]
    customer = case.get("customer", {}) or {}
    label = customer.get("name") or case_id

    print(f"  Processing case: {label} ({case_id})")

    if dry_run:
        print(f"    [dry-run] Would close case with stage={stage_id}, verdict={decision_state}")
        return

    # 1. Fetch alerts
    alerts_data = get(session, f"/v2/cases/{case_id}/alerts", {"page_size": 200})
    alerts = alerts_data.get("alerts", [])

    open_alerts = [
        a for a in alerts
        if a.get("state") not in ("POSITIVE_END_STATE", "NEGATIVE_END_STATE")
    ]
    print(f"    Found {len(open_alerts)} open alert(s) out of {len(alerts)}")

    # 2. Transition each open alert
    for alert in open_alerts:
        alert_id = alert["identifier"]
        print(decision_state)
        post(session, f"/v2/alerts/{alert_id}/transition", {"state": decision_state})
        print(f"    Transitioned alert {alert_id} → {decision_state}")
    # 3. Small delay before transitioning the case (mirrors the UI behaviour)
    time.sleep(1)

    # 4. Transition case to end-state stage
    post(
        session,
        f"/v2/cases/{case_id}/transition",
        {"stage_identifier": stage_id, "note": note},
    )
    print(f"    Case transitioned to stage {stage_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Close all open TRANSACTION_MONITORING cases")
    url = "https://api.mesh.complyadvantage.com"
    token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjdqUUpidUZmdjk0TnFXN0gwWWdhRyJ9.eyJhcHBfbWV0YWRhdGEiOnsiYWNjb3VudF9pZGVudGlmaWVyIjoiMDE5ZWFiODUtZWNlNi03MDU5LWFlZTUtNTlkZTZlYWEyNmI2IiwiY2xpZW50X2lkZW50aWZpZXIiOiIwMTk3NjQwNS00Y2QwLTdlMmEtYTY4OS04ZTk1YTUxNWZhMWMiLCJjbHVzdGVyIjoiZ2tlLXByb2QtZXczLWNsdXN0ZXItMCIsImd1ZXN0X2FjY2VzcyI6eyJyZXN0b3JlX3ZhbHVlcyI6eyJhY2NvdW50X2lkZW50aWZpZXIiOiIwMTkxZmFkZC1hMjllLTdiM2ItYWQ5Mi0zZDExMDhhZmMwYjgiLCJjbGllbnRfaWRlbnRpZmllciI6IjAxOGYyZTgyLTFmZmMtN2UxMS1hNWI5LThhMWQwMzQzYTQxOSIsInBlcm1pc3Npb25zIjoiNDAwMDAwMDAwNDAwMDAwMGM3ZmZmNDAwZjgifSwic2Vzc2lvbl9lbmRfdGltZSI6IjIwMjYtMDYtMjJUMTQ6MzU6MTEuNjM2Mjc5WiIsInNlc3Npb25faWRlbnRpZmllciI6IjAxOWVlZjhhLWNkMTQtNzc2NC05YTI1LTRhN2Q5ZTk4YWYyMSJ9LCJwZXJtaXNzaW9ucyI6ImFmZTdlZmZkZGRkYmZmZmVmZjI4MDBkZmUwMmEiLCJ1c2VyX2lkZW50aWZpZXIiOiIwMTk2OTE0Yy01ODBkLTc3NzAtOTQ2OS03YWEzMGZmM2ZkYzEifSwidXNlcl9tZXRhZGF0YSI6eyJsb2NhbGUiOiJmci1DQSIsInNzb19vbmx5Ijp0cnVlfSwiaXNzIjoiaHR0cHM6Ly9jYS1wbGF0Zm9ybS1wcm9kLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJvaWRjfHNzby1jb21wbHlhZHZhbnRhZ2UtZXUzfDExMzUxMDI2NjY3MjExNDYzMjEyMCIsImF1ZCI6WyJodHRwczovL3BsYXRmb3JtLWFwaS5jb21wbHlhZHZhbnRhZ2UuY29tIiwiaHR0cHM6Ly9jYS1wbGF0Zm9ybS1wcm9kLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3ODIxMzc0MTEsImV4cCI6MTc4MjIyMzgxMSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsIm9yZ19pZCI6Im9yZ181eU81U29qQTU3T05CWnRUIiwib3JnX25hbWUiOiJjb21wbHlhZHZhbnRhZ2UtZXUzIiwiYXpwIjoiZHdId1owbEMza2hZV0dMaEJOcU9aN2ZMcG1pelFpbloifQ.Zs1MBNd4xjaHlz6eHnhbQHt5pIthwZCCVlfmsc5gUAZT84lV8JNb0qyDK_JHZMzc2CKLMtEiZn2RKkxaL0zNtG-5af4EtnF57GtL05xhNjpjKAQlwhmrNVSsbhdy7W9s9GgBO7wtFQVgOuQHFWHjDdBi07Js_XY2jtplku_wjojsa9EL5LupHLz3nulJmDWgau786sCQp3cvvUm60Y5alhja6MKtqx23454mW8WKKKG_CDUVH6be6kG_-vnrftjCmzAzAxY2zswz-aExlvY9jpEcJ4DAIjSAsWwCPlA4zODlxScyayyTMrb_F9CtEW6CaS-QI2_U1YoBElpCLIDfZQ"
    parser.add_argument(
        "--verdict",
        choices=["false_positive", "true_positive"],
        default="false_positive",
        help="Alert verdict to apply (default: false_positive)",
    )
    parser.add_argument("--note", default="Closed by script", help="Transition note")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview actions without making changes"
    )
    args = parser.parse_args()

    decision_state = END_STATE_MAP[args.verdict]

    session = make_session(url, token)

    print("Fetching workflows...")
    workflows = fetch_workflows(session)
    if not workflows:
        print("No workflows found. Exiting.")
        sys.exit(1)

    stage_id = get_tm_decision_stage(workflows)
    if not stage_id:
        print("ERROR: No DECISION stage found for TRANSACTION_MONITORING workflow.")
        sys.exit(1)
    print(f"Using end-state stage: {stage_id}")

    open_stage_ids = fetch_open_stage_ids(workflows, "TRANSACTION_MONITORING")
    print(f"Open stage IDs for TM: {open_stage_ids}")

    print("Fetching open TRANSACTION_MONITORING cases...")
    cases = fetch_open_tm_cases(session, open_stage_ids)
    print(f"Found {len(cases)} open case(s)")

    if not cases:
        print("Nothing to do.")
        return

    if args.dry_run:
        print("\n[DRY RUN] The following cases would be closed:")

    failed = 0
    for i, case in enumerate(cases, 1):
        print(f"\n[{i}/{len(cases)}]", end=" ")
        try:
            close_case(session, case, decision_state, stage_id, args.note, args.dry_run)
        except requests.HTTPError as e:
            print(f"    ERROR: {e} — {e.response.text if e.response else ''}")
            failed += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            failed += 1

    print(f"\nDone. {len(cases) - failed}/{len(cases)} case(s) closed successfully.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
