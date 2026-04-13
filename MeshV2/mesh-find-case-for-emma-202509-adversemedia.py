import requests
import sys
import json
import time
import getpass
import pandas as pd

TOKEN_ENDPOINT = "/token"
CASES_ENDPOINT = "/cases"
WORKFLOWS_ENDPOINT = "/cases/workflows"
ACCOUNTS_ENDPOINT = "/users/me/accounts"
SET_ACCOUNT_ENDPOINT = "/accounts/me"
CUSTOMER_ENDPOINT = "/customers/{customer_identifier}"
ALERTS_ENDPOINT = "/cases/{case_identifier}/alerts"
RISKS_ENDPOINT = "/alerts/{alert_identifier}/risks"
DECISION_ENDPOINT = "/alerts/{alert_identifier}/risks/{risk_identifier}/decision"
NOTE_ENDPOINT = "/cases/{case_identifier}/notes"

BASE_URL = "https://api.mesh.complyadvantage.com/v2"
default_username = "leo.benoist@complyadvantage.com"
default_password = ""
default_realm = "complyadvantage-eu3"
default_account_name = ""

global_token = None

def authenticate(username, password, realm):
    global global_token
    payload = {"username": username, "password": password, "realm": realm}
    response = send_request("POST", TOKEN_ENDPOINT, json_payload=payload)
    global_token = response.get("access_token")
    print("Authentication successful.")

def send_request(method, endpoint, json_payload=None):
    url = BASE_URL + endpoint
    headers = {"accept": "application/json"}
    if global_token:
        headers["Authorization"] = f"Bearer {global_token}"

    response = requests.request(method, url, headers=headers, json=json_payload)

    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            return ''
    elif response.status_code == 429:
        print("Rate limit exceeded. Retrying in 10 seconds...")
        time.sleep(10)
        return send_request(method, endpoint, json_payload)
    else:
        print(f"Failed to {method} {endpoint}. Status Code: {response.status_code}")
        print("Response:", response.text)
        sys.exit(1)

def get_accounts(account_name):
    endpoint = f"{ACCOUNTS_ENDPOINT}?name_contains={account_name}&page_number=1&page_size=10"
    return send_request("GET", endpoint).get("accounts", [])

def set_account(account_identifier):
    payload = {"account_identifier": account_identifier}
    send_request("PUT", SET_ACCOUNT_ENDPOINT, json_payload=payload)
    print("Account set successfully.")

def verify_account():
    account_info = send_request("GET", SET_ACCOUNT_ENDPOINT)
    print("Current active account:", account_info.get("name"))
    return account_info

def get_customer_details(customer_identifier):
    endpoint = CUSTOMER_ENDPOINT.format(customer_identifier=customer_identifier)
    return send_request("GET", endpoint)

def get_case_workflows():
    return send_request("GET", WORKFLOWS_ENDPOINT)

def get_open_case_workflows_url_string():
    workflows = get_case_workflows()
    data = workflows['workflows']
    result = []
    for item in data:
        if item['case_type'] != 'PAYMENT_SCREENING' and item['case_type'] != 'TRANSACTION_MONITORING':
            for stage in item['stages']:
                if stage['stage_type'] != 'DECISION':
                    result.append(f"stage.identifier={stage['identifier']}")

    output_string = "&".join(result)
    return output_string


def get_alert_risks(alert_identifier):
    page_number, page_size, all_risks = 1, 100, []
    while True:
        endpoint = RISKS_ENDPOINT.format(alert_identifier=alert_identifier) + f"?page_number={page_number}&page_size={page_size}"
        risks = send_request("GET", endpoint).get("risks", [])
        if not risks:
            break
        for risk in risks:
            risk["alert_identifier"] = alert_identifier  # Append alert_identifier to each risk
            all_risks.append(risk)
        page_number += 1
        if len(risks) < page_size:
            break
    return all_risks


def get_all_cases():
    page_number, page_size, consolidated_cases = 1, 100, []
    while True:
        endpoint = f"{CASES_ENDPOINT}?page_number={page_number}&page_size={page_size}&{get_open_case_workflows_url_string()}" # TODO INFO Add &search=xx to test on one case only
        print(endpoint)
        cases = send_request("GET", endpoint).get("cases", [])
        if not cases:
            break
        for case in cases:
            consolidated_cases.append({
                "case": case,
            })
        page_number += 1
    return consolidated_cases

def get_input(prompt, default=None, is_password=False):
    response = getpass.getpass(f"{prompt} [{'*' * len(default) if default else ''}]: ") if is_password else input(f"{prompt} [{default}]: ")
    return response if response else default

def case_analyser(case_data):
    return extract_alert_data(case_data)

def extract_alert_data(data):
    results = []
    case = data.get('case', {})
    customer = data.get('case', {}).get('customer', {})
    case_identifier = data.get('case', {}).get('identifier')
    aml_types = json.dumps(case.get('risk_types'))

    results.append({
        'case_identifier': case_identifier,
        'customer_identifier': customer.get('external_identifier', []),
        'aml_types': aml_types,
        'mesh_url': 'https://mesh.complyadvantage.com/cases/'+case_identifier,
    })


    return results

def main():
    authenticate(default_username, default_password, default_realm)
    accounts = get_accounts(default_account_name)
    print(accounts)
    # set_account(accounts[0]["identifier"])
    verify_account()
    cases = get_all_cases()
    all_results = []
    for case in cases:
        result = case_analyser(case)
        if isinstance(result, list):
            all_results.extend(result)
    write_to_excel(all_results)

def write_to_excel(data, filename="results.xlsx"):
    """
    Writes a list of lists to an Excel file using pandas.

    Args:
        data: A list of lists to write to the Excel file.
        filename: The name of the Excel file to create (default: "results.xlsx").
    """
    try:
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False)
        print(f"Successfully wrote results to '{filename}'")
    except ImportError:
        print("Error: pandas library is not installed. Please install it using 'pip install pandas openpyxl'")
    except Exception as e:
        print(f"Error writing to Excel file: {e}")

if __name__ == "__main__":
    main()