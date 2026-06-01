import time
import requests
import pandas as pd


def fetch_and_flatten_data():
    base_url = "https://api-prod.grip.events/1/container/9338/search/extension/125129"

    headers = {
        'accept': 'application/json',
        'accept-language': 'en-gb',
        'cache-control': 'No-Cache',
        'content-type': 'application/json',
        'login-source': 'web',
        'origin': 'https://matchmaking.grip.events',
        'pragma': 'No-Cache',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
        'x-authorization': '81054fbf-0097-4282-95da-1b97a9ccce40',
        'x-grip-version': 'Web/49.0.0',
    }

    all_results = []
    page_num = 1

    while True:
        params = {
            'order': 'asc',
            'sort': 'name',
            'page': page_num,
        }

        print(f"Fetching page {page_num}...")
        while True:
            response = requests.get(base_url, headers=headers, params=params)
            if response.status_code == 429:
                print("Rate limited (429). Waiting...")
                time.sleep(70)
                continue
            break

        if response.status_code != 200:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            print(response.text)
            break

        data = response.json()

        if not data.get('success'):
            print("API returned success=false")
            break

        current_results = data.get('data', [])
        if not current_results:
            print("No more results.")
            break

        all_results.extend(current_results)
        page_num += 1

    print(f"\nFinished fetching. Total records retrieved: {len(all_results)}")

    if not all_results:
        print("No data found to export.")
        return

    df = pd.json_normalize(all_results)

    for col in df.columns:
        df[col] = df[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)

    output_filename = 'money2020europe2026.xlsx'
    df.to_excel(output_filename, index=False)

    print(f"Data successfully flattened and saved to {output_filename}")


if __name__ == "__main__":
    fetch_and_flatten_data()
