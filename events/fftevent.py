import requests
import pandas as pd

def fetch_and_flatten_data():
    # Initial URL from your cURL command
    url = "https://api.crowdcomms.com/apps/fintechrev26/peoples/uncached-table/?search=&offset=0&limit=20"

    # Headers extracted from your cURL command
    headers = {
        'X-CC-APP-ENTRY-POINT': 'fintechrev26',
        'Authorization': 'Token eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmaW50ZWNocmV2MjYiLCJpYXQiOjE3NzQyODAxMzMuNTczNzc1NSwiZXhwIjoxNzc0MjgwNDMzLjU3Mzc5MiwidXNlciI6eyJpZCI6MjExNjAwNH0sImp0aSI6IkFSQ2VXeVJBTFBzUksza3EyczJjYXoiLCJwZXJzb24iOnsiaWQiOjk2MDI1NjIsImFwcCI6ImZpbnRlY2hyZXYyNiIsImdyb3VwcyI6WyItMjgzMDI4MjgyNDQ5OTk3NTgiXX19.UjhAgDRDFFl0JMpchIEJqUSdW8Xr-3tlk634ZKoXO6oDOlk621E6a2XoSYM9zAR1kEaklKLagScjlQXajugK-Q',
        'sec-ch-ua-platform': '"macOS"',
        'Referer': 'https://fintechrev26-880e2.apps.crowdcomms.com/fintechrev26/user/meetings',
        'Accept-Language': 'en',
        'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        'sec-ch-ua-mobile': '?0',
        'X-CC-Device-ID': '0edbc0bb-40fa-4751-94e6-c76d925e186b',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }

    all_results = []
    page_num = 1

    # Loop through pages as long as a 'next' URL is provided
    while url:
        print(f"Fetching page {page_num}...")
        response = requests.get(url, headers=headers)

        # Check if the request was successful
        if response.status_code != 200:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            print(response.text)
            break

        data = response.json()

        # Append the current page's results to our master list
        current_results = data.get('results', [])
        all_results.extend(current_results)

        # Get the URL for the next page (will be None if there are no more pages)
        url = data.get('next')
        page_num += 1

    print(f"\nFinished fetching. Total records retrieved: {len(all_results)}")

    if not all_results:
        print("No data found to export.")
        return

    # Flatten the JSON objects into a structured tabular format
    df = pd.json_normalize(all_results)

    # Excel doesn't support writing raw Python lists or dictionaries directly to cells.
    # We need to convert any lists (like 'device_ids' or 'user_tags') into strings.
    for col in df.columns:
        df[col] = df[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)

    # Dump the flattened DataFrame to an Excel file
    output_filename = 'fintechrev26_attendees.xlsx'
    df.to_excel(output_filename, index=False)

    print(f"Data successfully flattened and saved to {output_filename}")

if __name__ == "__main__":
    fetch_and_flatten_data()