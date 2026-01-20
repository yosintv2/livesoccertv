import asyncio
import json
import os
from datetime import datetime, timedelta
from curl_cffi.requests import AsyncSession

# ================= CONFIG =================

ENDPOINTS = {
    "h2h": "h2h",
    "lineups": "lineups",
    "statistics": "statistics",
    "odds": "provider/1/winning-odds",
    "form": "pregame-form",
    "incidents": "incidents"
}

DATE_DIR = "date"
DATA_DIR = "data"
BATCH_SIZE = 5
SLEEP_BETWEEN_BATCHES = 1

# =========================================


async def fetch_sofa_endpoint(session, match_id, endpoint_key, path):
    """Fetch a single SofaScore endpoint for one match."""
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/{path}"
    try:
        res = await session.get(
            url,
            impersonate="chrome120",
            timeout=10
        )
        if res.status_code == 200:
            return endpoint_key, res.json()
    except Exception as e:
        print(f"[ERROR] {endpoint_key} | Match {match_id}: {e}")
    return endpoint_key, None


async def process_match(session, match_id, date_str):
    """Fetch all endpoints for one match and save them."""
    tasks = [
        fetch_sofa_endpoint(session, match_id, key, path)
        for key, path in ENDPOINTS.items()
    ]

    results = await asyncio.gather(*tasks)

    for folder, data in results:
        if not data:
            continue

        folder_path = os.path.join(DATA_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)

        target_file = os.path.join(folder_path, f"{date_str}.json")

        day_data = {}
        if os.path.exists(target_file):
            try:
                with open(target_file, "r", encoding="utf-8") as rf:
                    day_data = json.load(rf)
            except:
                day_data = {}

        day_data[str(match_id)] = data

        with open(target_file, "w", encoding="utf-8") as wf:
            json.dump(day_data, wf, indent=2)


async def main():
    async with AsyncSession() as session:
        target_dates = [
            (datetime.now() + timedelta(days=i)).strftime("%Y%m%d")
            for i in range(4)
        ]

        for date_str in target_dates:
            date_file = os.path.join(DATE_DIR, f"{date_str}.json")

            if not os.path.exists(date_file):
                print(f"[SKIP] No matches for {date_str}")
                continue

            with open(date_file, "r", encoding="utf-8") as f:
                matches = json.load(f)

            print(f"[INFO] {date_str} → {len(matches)} matches")

            for i in range(0, len(matches), BATCH_SIZE):
                batch = matches[i:i + BATCH_SIZE]

                await asyncio.gather(*[
                    process_match(session, m["match_id"], date_str)
                    for m in batch if "match_id" in m
                ])

                await asyncio.sleep(SLEEP_BETWEEN_BATCHES)


if __name__ == "__main__":
    asyncio.run(main())
