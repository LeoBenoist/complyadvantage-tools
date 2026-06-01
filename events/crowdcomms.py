import requests
import pandas as pd

def fetch_and_flatten_data():
    # Initial URL from your cURL command
    url = "https://api.crowdcomms.com/apps/fincrime4/modules/290823/people/peoples/table/?offset=0&limit=40&fields=last_name&fields=company&fields=title&fields=device_ids&fields=id&fields=job_title&fields=app_picture&fields=first_name&fields=pronouns&fields=tags&fields=user_tags&additive=true"

    # Headers extracted from your cURL command
    headers = {
        'X-CC-APP-ENTRY-POINT': 'fincrime4',
        'Authorization': 'Token eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmaW5jcmltZTQiLCJpYXQiOjE3NzYzNDM5NjAuNTg0NTE0OSwiZXhwIjoxNzc2MzQ0MjYwLjU4NDUyNSwidXNlciI6eyJpZCI6MjEzNDUxMX0sImp0aSI6IlZkVDZHVnRFSnA0VGVDRFZvQWlUQXQiLCJwZXJzb24iOnsiaWQiOjk4NDczMjAsImFwcCI6ImZpbmNyaW1lNCIsImdyb3VwcyI6WyItMjIxNzQ5NjExMjQ1MDU5MDE1MyJdfX0.Z5WkdsILbP4aMyTi-c_L2JMKHhV8ya9prWmCNNCaycx4WIm-8o8ZdFQqrsBmKt7MCFs7FLazZ-aLlveHnulDrA',
        'sec-ch-ua-platform': '"macOS"',
        'Referer': 'https://fincrime4-86c60.apps.crowdcomms.com/',
        'Accept-Language': 'en',
        'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        'sec-ch-ua-mobile': '?0',
        'X-CC-Device-ID': '7c32528c-dbbd-4725-92a0-b87d3235485a',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
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
    output_filename = 'crowdcomms.xlsx'
    df.to_excel(output_filename, index=False)

    print(f"Data successfully flattened and saved to {output_filename}")

if __name__ == "__main__":
    fetch_and_flatten_data()