import requests
import sys
import json
import time
import getpass
import pandas as pd
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

# --- API Endpoints ---
TOKEN_ENDPOINT = "/v2/token"
CASES_ENDPOINT = "/v2/cases"
WORKFLOWS_ENDPOINT = "/v2/cases/workflows"
ACCOUNTS_ENDPOINT = "/v2/users/me/accounts"
SET_ACCOUNT_ENDPOINT = "/v2/accounts/me"
CUSTOMER_ENDPOINT = "/v2/customers/{customer_identifier}"
ALERTS_ENDPOINT = "/v2/cases/{case_identifier}/alerts"
RISKS_ENDPOINT = "/v2/alerts/{alert_identifier}/risks?risk_type_version=ENTITY_SCREENING:3"
RISK_ENDPOINT = "/v2/entity-screening/risks/{risk_identifier}"

# --- Module-level config (override from each script) ---
BASE_URL = os.getenv("BASE_URL", "https://api.mesh.complyadvantage.com")
default_username = os.getenv("USERNAME", "xx@complyadvantage.com")
default_password = os.getenv("PASSWORD", "")
default_realm = os.getenv("REALM", "complyadvantage")
default_account_name = os.getenv("ACCOUNT_NAME", "Customer Account")
search_key = os.getenv("SEARCH_KEY", "default")
global_token = None

def get_cache_filename(method, endpoint, json_payload=None):
    base_filename = f"{method}_{endpoint.replace('/', '_').replace('?', '_').replace('=', '_').replace('&', '_')}"
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

def _send_live_request(method, endpoint, json_payload=None):
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


def authenticate(username, password, realm):
    global global_token
    payload = {"username": username, "password": password, "realm": realm}
    response = _send_live_request("POST", TOKEN_ENDPOINT, json_payload=payload)
    global_token = response.get("access_token")
    print("Authentication successful.")


def get_accounts(account_name):
    endpoint = f"{ACCOUNTS_ENDPOINT}?name_contains={account_name}&page_number=1&page_size=10"
    return _send_live_request("GET", endpoint).get("accounts", [])


def set_account(account_identifier):
    payload = {"account_identifier": account_identifier}
    _send_live_request("PUT", SET_ACCOUNT_ENDPOINT, json_payload=payload)
    print("Account set successfully.")


def verify_account():
    account_info = _send_live_request("GET", SET_ACCOUNT_ENDPOINT)
    print("Current active account:", account_info.get("name"))
    return account_info


def get_customer_details(customer_identifier):
    endpoint = CUSTOMER_ENDPOINT.format(customer_identifier=customer_identifier)
    return _send_live_request("GET", endpoint)


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
        endpoint = RISKS_ENDPOINT.format(alert_identifier=alert_identifier) + f"&page_number={page_number}&page_size={page_size}"
        risks_response = send_request("GET", endpoint)
        risks = risks_response.get("risks", []) if risks_response else []
        if not risks:
            break
        for risk in risks:
            risk["alert_identifier"] = alert_identifier
            risk_identifier = risk["identifier"]
            details_endpoint = RISK_ENDPOINT.format(risk_identifier=risk_identifier)
            risk["details"] = send_request("GET", details_endpoint)
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


def get_all_cases():
    page_number, page_size, consolidated_cases = 1, 100, []
    while True:
        endpoint = f"{CASES_ENDPOINT}?page_number={page_number}&page_size={page_size}&sort=-CREATED_AT&search={search_key}"
        print(f"Fetching cases: {endpoint}")
        cases_response = send_request("GET", endpoint)
        cases = cases_response.get("cases", []) if cases_response else []
        if not cases:
            break
        for case in cases:
            consolidated_cases.append({
                "case": case,
                "alerts": get_case_alerts(case["identifier"])
            })
        page_number += 1
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
    authenticate(default_username, default_password, default_realm)
    accounts = get_accounts(default_account_name)
    if accounts:
        print(f"Found accounts: {[acc['name'] for acc in accounts]}")
        set_account(accounts[0]["identifier"])
    else:
        print(f"No account found with the name '{default_account_name}'. Exiting.")
        sys.exit(1)

    verify_account()
    cases = get_all_cases()
    all_results = []
    for case in cases:
        result = case_analyser_fn(case)
        if isinstance(result, list):
            all_results.extend(result)
    write_to_excel(all_results, output_filename)
