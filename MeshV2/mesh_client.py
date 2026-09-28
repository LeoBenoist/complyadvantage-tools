import requests
import sys
import json
import time
import pandas as pd
import os
import hashlib
import calendar
from collections import deque
from datetime import datetime, date
from dotenv import load_dotenv
from get_token import get_guest_access_token

load_dotenv()

# --- API Endpoints ---
CASES_ENDPOINT = "/v2/cases"
WORKFLOWS_ENDPOINT = "/v2/cases/workflows"
CUSTOMER_ENDPOINT = "/v2/customers/{customer_identifier}"
ALERTS_ENDPOINT = "/v2/cases/{case_identifier}/alerts"
RISKS_ENDPOINT = "/v2/alerts/{alert_identifier}/risks"
RISK_ENDPOINT = "/v2/entity-screening/risks/{risk_identifier}"

# --- Module-level config ---
BASE_URL = f"https://api.{os.environ['REGION']}.mesh.complyadvantage.com"
search_key = os.getenv("SEARCH_KEY", "default")
global_token = get_guest_access_token()

# Rate tracking — sliding window of live request timestamps (last 60 s)
_request_timestamps: deque = deque()
_RATE_LIMIT_WARN = 200  # requests per minute

def get_cache_filename(method, endpoint, json_payload=None):
    path, _, query = endpoint.partition('?')
    path_part = path.replace('/', '_')
    if query:
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        base_filename = f"{method}_{path_part}_{query_hash}"
    else:
        base_filename = f"{method}_{path_part}"
    if json_payload:
        payload_str = json.dumps(json_payload, sort_keys=True)
        payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()
        base_filename += f"_{payload_hash}"
    return f"{base_filename}.json"


def send_request(method, endpoint, json_payload=None):
    """
    This function now acts as a wrapper. It first checks for a cached
    response. If found, it returns the cached data. If not, it makes a
    live API call and then saves the response to the cache.
    """
    # Create the cache directory if it doesn't exist
    cache_dir = './cache/'+search_key
    if not os.path.exists(cache_dir):
        print(f"Creating cache directory: '{cache_dir}'")
        os.makedirs(cache_dir)

    # Generate a unique filename for this specific request
    cache_filename = get_cache_filename(method, endpoint, json_payload)
    cache_filepath = os.path.join(cache_dir, cache_filename)

    # First, check if the response is already cached
    if os.path.exists(cache_filepath):
        print(f"CACHE HIT: Loading response for {method} {endpoint} from {cache_filepath}")
        with open(cache_filepath, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from cache file: {cache_filepath}. Making a live request.")
                # If the cached file is corrupted, we'll proceed to make a live request

    # Cache miss — make live request
    response_data = _send_live_request(method, endpoint, json_payload)

    if not response_data:
        raise RuntimeError(f"No cache available and live request returned no result for {method} {endpoint}")

    print(f"Caching response for {method} {endpoint} to {cache_filepath}")
    with open(cache_filepath, 'w') as f:
        json.dump(response_data, f, indent=4)

    return response_data

def _check_rate():
    while True:
        now = time.monotonic()
        while _request_timestamps and _request_timestamps[0] < now - 60:
            _request_timestamps.popleft()
        if len(_request_timestamps) < _RATE_LIMIT_WARN:
            break
        wait = 60 - (now - _request_timestamps[0])
        print(f"\033[33mWARNING: rate limit reached ({_RATE_LIMIT_WARN} req/min) — throttling for {wait:.1f}s\033[0m", flush=True)
        time.sleep(wait)
    _request_timestamps.append(time.monotonic())


def _send_live_request(method, endpoint, json_payload=None):
    _check_rate()
    url = BASE_URL + endpoint
    headers = {"accept": "application/json"}
    if global_token:
        headers["Authorization"] = f"Bearer {global_token}"

    try:
        response = requests.request(method, url, headers=headers, json=json_payload)

        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                return ''
        if response.status_code == 204:
                return ''
        elif response.status_code == 429:
            print("Rate limit exceeded. Retrying in 2 seconds...")
            time.sleep(2)
            return _send_live_request(method, endpoint, json_payload)
        elif response.status_code == 500:
            print("500 error. Retrying in 30 seconds...")
            time.sleep(30)
            return _send_live_request(method, endpoint, json_payload)
        else:
            print(f"Failed to {method} {endpoint}. Status Code: {response.status_code}")
            print("Response:", response.text)
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
        print("Retrying in 60 seconds...")
        time.sleep(60)
        return _send_live_request(method, endpoint, json_payload)


def get_customer_details(customer_identifier):
    endpoint = CUSTOMER_ENDPOINT.format(customer_identifier=customer_identifier)
    return send_request("GET", endpoint)


def get_case_workflows():
    return send_request("GET", WORKFLOWS_ENDPOINT)


def get_open_case_workflows_url_string():
    workflows = get_case_workflows()
    data = workflows.get('workflows', [])
    result = []
    for item in data:
        if item['case_type'] != 'PAYMENT_SCREENING' and item['case_type'] != 'TRANSACTION_MONITORING':
            for stage in item['stages']:
                if stage['stage_type'] != 'DECISION':
                    result.append(f"stage.identifier={stage['identifier']}")
    return "&".join(result)


def get_alert_risks(alert_identifier):
    page_number, page_size, all_risks = 1, 100, []
    while True:
        endpoint = RISKS_ENDPOINT.format(alert_identifier=alert_identifier) + f"?page_number={page_number}&page_size={page_size}"
        risks_response = send_request("GET", endpoint)
        risks = risks_response.get("risks", []) if risks_response else []
        if not risks:
            break
        for risk in risks:
            risk["alert_identifier"] = alert_identifier
            all_risks.append(risk)
        page_number += 1
        if len(risks) < page_size:
            break
    return all_risks


def get_case_alerts(case_identifier):
    endpoint = ALERTS_ENDPOINT.format(case_identifier=case_identifier)
    alerts_response = send_request("GET", endpoint)
    alerts = alerts_response.get("alerts", []) if alerts_response else []
    for alert in alerts:
        alert["risks"] = get_alert_risks(alert["identifier"])
    return alerts

def get_open_case_workflows_url_string():
    workflows = get_case_workflows()
    data = workflows.get('workflows', [])
    result = []
    for item in data:
        if item['case_type'] != 'PAYMENT_SCREENING' and item['case_type'] != 'TRANSACTION_MONITORING':
            for stage in item['stages']:
                if stage['stage_type'] != 'DECISION':
                    result.append(f"stage.identifier={stage['identifier']}")
    return "&".join(result)

def get_all_cases():
    consolidated_cases = []
    open_stages = get_open_case_workflows_url_string()
    page_size = 100

    now = datetime.utcnow()
    year, month = 2026, 8

    while (year, month) <= (now.year, now.month):
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        from_str = first_day.strftime("%Y-%m-%dT00:00:00.000Z")
        to_str = last_day.strftime("%Y-%m-%dT23:59:59.999Z")

        # if year == 2024:
        #     break

        page_number = 1
        print(f"Fetching cases for {year}-{month:02d}...")
        while True:
            endpoint = (
                f"{CASES_ENDPOINT}?page_number={page_number}&page_size={page_size}"
                f"&created_at_from={from_str}&created_at_to={to_str}"
                f"&sort=CREATED_AT&{open_stages}"
            )
            print(f"  Page {page_number}: {endpoint}")
            cases_response = send_request("GET", endpoint)
            cases = cases_response.get("cases", []) if cases_response else []
            if not cases:
                break
            for case in cases:
                if case.get("type") not in ("CUSTOMER_ONBOARDING", "CUSTOMER_MONITORING", "CUSTOMER_SCREENING"):
                    continue
                customer_identifier = case.get("customer", {}).get("identifier")
                customer_detail = get_customer_details(customer_identifier) if customer_identifier else {}
                consolidated_cases.append({
                    "case": case,
                    "alerts": get_case_alerts(case["identifier"]),
                    "customer_detail": customer_detail,
                })
            page_number += 1
            if len(cases) < page_size:
                break

        month += 1
        if month > 12:
            month = 1
            year += 1

    return consolidated_cases


# def get_input(prompt, default=None, is_password=False):
#     response = getpass.getpass(f"{prompt} [{'*' * len(default) if default else ''}]: ") if is_password else input(f"{prompt} [{default}]: ")
#     return response if response else default


def write_to_excel(data, filename):
    if not data:
        print("No data to write to Excel.")
        return
    try:
        df = pd.DataFrame(data)
        df.to_excel('./results/'+filename, index=False)
        print(f"Successfully wrote results to '{filename}'")
    except ImportError:
        print("Error: pandas library is not installed. Please install it using 'pip install pandas openpyxl'")
    except Exception as e:
        print(f"Error writing to Excel file: {e}")


def run_main(case_analyser_fn, output_filename):
    cases = get_all_cases()
    all_results = []
    for case in cases:
        result = case_analyser_fn(case)
        if isinstance(result, list):
            all_results.extend(result)
    write_to_excel(all_results, output_filename)
