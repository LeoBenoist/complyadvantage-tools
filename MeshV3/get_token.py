import os
import requests
from dotenv import load_dotenv


load_dotenv()


def get_url(r, path):
    return f"https://api.{r}.mesh.complyadvantage.com/{path}"

def get_guest_access_token():
    username = os.environ["EMAIL"]
    password = os.environ["PASSWORD"]
    region = os.environ["REGION"]
    realm = os.environ["ADMIN_REALM"]
    account = os.environ["ACCOUNT"]
    client = os.environ["CLIENT"]

    # Get a token in whatever account
    response = requests.post(
        get_url(region, "v2/token"),
        json={"username": username, "password": password, "realm": realm},
    )
    response.raise_for_status()
    JWT_TOKEN = response.json()['access_token']
    HEADERS = {'Authorization': f'Bearer {JWT_TOKEN}'}

    # Check if we're already on the right account
    response = requests.get(url=get_url(region, "v2/accounts/me"), headers=HEADERS)
    response.raise_for_status()
    me = response.json()
    if me.get('identifier') == account and me.get('client_identifier') == client:
        print(f"Already on the right account: {me['name']} ({me['identifier']})")
        return JWT_TOKEN

    # Get all my accounts to look for super
    response = requests.get(
        url=get_url(region, "v2/users/me/accounts?page_size=20"),
        headers=HEADERS,
    )
    response.raise_for_status()
    accounts = response.json()['accounts']

    for acc in accounts:
        if acc['name'] == 'super':
            response = requests.put(
                url=get_url(region, "v2/accounts/me"),
                json={"account_identifier": acc['identifier']},
                headers=HEADERS,
            )
            response.raise_for_status()
            break
    else:
        raise Exception(f"seems like you do not have access to super in {region}")

    # Now we're in super so we need another token
    response = requests.post(
        get_url(region, "v2/token"),
        json={"username": username, "password": password, "realm": realm},
    )
    response.raise_for_status()
    JWT_TOKEN = response.json()['access_token']
    HEADERS = {'Authorization': f'Bearer {JWT_TOKEN}'}

    # Look up the Admin role by name
    roles_response = requests.get(
        url=get_url(region, f"v2/iam/roles?account_identifier={account}&client_identifier={client}&page_number=1&page_size=1000"),
        headers=HEADERS,
    )
    roles_response.raise_for_status()
    roles = roles_response.json()['roles']
    admin_role = next((r for r in roles if r['name'] == 'Admin'), None)
    if not admin_role:
        raise Exception("Could not find role named 'Admin'")

    guest_access_params = {
        'account_identifier': account,
        'client_identifier': client,
        'role_identifiers': [admin_role['identifier']],
        'duration': 60 * 22,  # 3 hours
    }

    response = requests.post(
        url=get_url(region, "admin/v2/guest-access/enable"),
        headers=HEADERS,
        json=guest_access_params,
    )
    response.raise_for_status()

    # Get the guest access token
    response = requests.post(
        get_url(region, "v2/token"),
        json={"username": username, "password": password, "realm": realm},
    )
    response.raise_for_status()
    JWT_TOKEN = response.json()['access_token']
    HEADERS = {'Authorization': f'Bearer {JWT_TOKEN}'}

    # Verify we are on the right account
    response = requests.get(url=get_url(region, "v2/accounts/me"), headers=HEADERS)
    response.raise_for_status()
    me = response.json()
    if me['client_identifier'] != client:
        raise Exception(f"client_identifier mismatch: expected {client}, got {me['client_identifier']}")
    if me['identifier'] != account:
        raise Exception(f"account identifier mismatch: expected {account}, got {me['identifier']}")
    print(f"Account verified: {me['name']} ({me['identifier']})")

    return JWT_TOKEN


if __name__ == "__main__":
    token = get_guest_access_token()
    print(token)
