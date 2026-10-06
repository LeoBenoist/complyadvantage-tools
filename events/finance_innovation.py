import requests
import pandas as pd


def fetch_and_flatten_data():
    url = "https://www.finance-innovation.com/api/0e4d0ddf-9f5a-f111-8fcb-6045bd954326/person/query"

    headers = {
        "accept": "*/*",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,fr;q=0.7",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "origin": "https://www.finance-innovation.com",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "sec-ch-ua": '"Google Chrome";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    }

    cookies = {
        "hasConsentFor0e4d0ddf-9f5a-f111-8fcb-6045bd954326": "state#accepted|consent#2026-09-14T08:45:20.550Z",
        "id.financeinnovation": "CfDJ8Hp9naXR8jRLglmRsVDney-Ei37-25qr8cYJ7ExkHqJiN4uVjx2M-7UXAQylh1YWPtsht5LBLlO1QGfgrnxYv6HmDaGvvyZm4WLkR_-b7f4mBpBSFKbgqQdWGyCvjp8CdNgIDPnvpPlk1-7-at1kh9beLHjtgQqjM8osEO1DUuoSmJZPM05tFqECSiun9KpdjDfHUmCHSG9FySTturHE5w46EluxgtWmAiEDfNvI8Zt1h3qoUJbNxlMoWLkrgvlC5i1ZASzeHz2GFX9XgeOJf4LE-v-nNod5Qw1JBG1JTeMiKYClJSQ69QWleM36JZVDrM1Vi4P5g1N_v0rX8PK40MHyXncQzgVZwTfWlvHgvzBdP96pkvXUeCy09cpDmWuuSxs53TYR8MwzRoJXsEZH53giXbxIv-vs23JmbGBNvkwqnXC20bHCCZB3eCJaA_GTUyb3KrB6oIWJ3QSE5LM42sQJnoZHC7qGJy3gOLSptUwfNnD4M3X0GyTPU5IpeGl_1zbfc4RI_b6WFxUe--TRWFPO_tMZ6Epq41jdUP864-CxytP-2nkoSyaO6Ifss3BmbNE6j-7w8UdRimTftJHHCcsMhnRBG9RTwdLNi772LeOJIZly-1TNO4iCj3anbsm1UQ2y_UxODO_u-6bV6xz2iSCNODYij88XAzedLkadg3LbAKIRmKebXA7hcDEB7LPB3PLIsfp2bcE14RkReQxRR1MSgmNoUvJxVygT4glFxCQlIBsu1Gdrh8dlZTiM4XfblaCxWj-h_RlbirelVNZbedrV-ht0H9sSNbwxwE0wr-9o1Si21PB4gsFzWPewK_l1Eu4tf6gK23VIvv4-yMIdOPSDKqb2Jtc74-zAQCM63dg5N0y-SRfdcj9GPItnLRG2ZubwJvomrD9t3VHGATOvZCaMylplxz3xvYICu2J0euV1GcY9fPbjGmLRP1_z6bYbcwvqRonFujZqScAO-CQYVr9R0tC2BqrYXWbegwN-Cj9GyL36IfbMjUyUm0pwuRf3pYY9kQ4cHn2AkMjZFmEO8M3zHYWrrIDh0N-d-t0umJGjMl09ZTNeAf9_-nWgU99NQIbob7dbTgkjXxQ9lrKsc8fxGckYnFefs3CUTwg-WBYlhE_7K26dZGNRNFVx2q0BaH_27TXutFkSLp-bOpsPNc2rI4pecxowPwA23-8Mu65W_eSIuGy6rHaInpBhLoYf-09-cmtcg9wgjGnteFBeh9L46l9A-7vZjtOK8l9bS1yUx9IVotxXXfEJk4rTyaog8WB4VX1o3XDi_y4DPfbExEblzTa0LVxS80S1ooZir3wx5dFaIXFMwlVARrpvJwREwDypwU1at1MfHU9kwfkoFOVOzjcpHpH7w6ECrkJTfh11IyE9DWmCn7509MEs9GR1kbOI6NK0BcoeT8vNmrcfcdJvxA3LHBK-WnXh1ojo5Z_RwgAglK21hqPKG9L9P12TptK_tWulaF7qpgUgKnv6OCjGJr1-2XKbOSvNaETZLWedihkn-El8KcDH2_K-6SxqzBBWIyLE01apD-myNcu_FdftZ80VswsfSLrClqFs6KVA-ez1jYSnoarVPCaKXGo8OGhjpJ7isA1X4gmKjxlmE2Q",
    }

    page_size = 50
    page_index = 0
    all_results = []

    while True:
        payload = {
            "page": {"index": page_index, "size": page_size},
            "selects": {"$all": True},
            "filters": {
                "$and": [
                    {"allowNetworking": {"$equal": True}},
                    {"isRegistered": {"$equal": True}},
                ]
            },
            "allowSelf": True,
            "orders": [{"desc": False, "value": {"lastname": {}}}],
        }

        print(f"Fetching page {page_index + 1}...")
        response = requests.post(url, headers=headers, cookies=cookies, json=payload)

        if response.status_code != 200:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            print(response.text)
            break

        data = response.json()
        current_results = data.get("data", [])

        if not current_results:
            print("No more results.")
            break

        all_results.extend(current_results)
        print(f"  Got {len(current_results)} records (total so far: {len(all_results)})")

        if len(current_results) < page_size:
            break

        page_index += 1

    print(f"\nFinished fetching. Total records retrieved: {len(all_results)}")

    if not all_results:
        print("No data found to export.")
        return

    df = pd.json_normalize(all_results)

    for col in df.columns:
        df[col] = df[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)

    output_filename = "finance_innovation.xlsx"
    df.to_excel(output_filename, index=False)

    print(f"Data successfully saved to {output_filename}")


if __name__ == "__main__":
    fetch_and_flatten_data()