import os
import time
import requests
import pandas as pd

API_KEY = "579b464db66ec23bdd0000019d62b14cdd144d3d5c624f54894d4782"  # <-- Put your API key inside these quotes!
RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
OUTPUT_CSV = "telangana_full_multiyear_data.csv"

url = "https:" + chr(47) + chr(47) + "api.data.gov.in" + chr(47) + "resource" + chr(47) + RESOURCE_ID

limit = 500
headers = {"User-Agent": "Mozilla/5.0"}

if os.path.exists(OUTPUT_CSV):
    offset = len(pd.read_csv(OUTPUT_CSV))
    print(f"Resuming from row {offset}...")
else:
    offset = 0
    print("Starting download...")

while True:
    params = {
        "api-key": API_KEY.strip(),
        "format": "json",
        "offset": offset,
        "limit": limit,
        "filters[state]": "Telangana"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        data = r.json()

        if "records" not in data:
            print("Server message:", data)
            break

        records = data["records"]
        if not records:
            print("Done! All Telangana rows downloaded.")
            break

        df = pd.DataFrame(records)
        df.to_csv(OUTPUT_CSV, mode="a", header=not os.path.exists(OUTPUT_CSV), index=False)

        offset += len(records)
        print(f"Saved {offset} rows...")
        time.sleep(0.3)

    except Exception as e:
        print("Error:", e)
        break
