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

DATA_DIR = "data"
BATCH_SIZE = 5
SLEEP_BETWEEN_BATCHES = 1

# =========================================


async def fetch_sofa_endpoint(session, match_id, key, path):
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/{path}"
    try:
        res = await session.get(
            url,
            impersonate="chrome120",
            timeout=10
        )
        if res.status_code == 200:
            return key, res.json()
    except Exception as e:
        print(f"[ERROR] {key} | Match {match_id}: {e}")
    return key, None


def process_incidents(data):
    incidents = data.get("incidents", [])

    home_score = 0
    away_score = 0
    home_scorers = []
    away_scorers = []

    for i in incidents:
        if i.get("incidentType") == "goal":
            minute = f"{i.get('time', '')}'"
            name = i.get("player", {}).get("name", "Unknown")

            home_score = i.get("homeScore", home_score)
            away_score = i.get("awayScore", away_score)

            if i.get("isHome"):
                home_scorers.append([name, minute])
            else:
                away_scorers.append([name, minute])

    return {
        "home_score": home_score,
        "away_score": away_score,
        "home_scorers": home_scorers,
        "away_scorers": away_scorers
    }


async def process_match(session, match_id, day_data):
    tasks = [
        fetch_sofa_endpoint(session, match_id, key, path)
        for key, path in ENDPOINTS.items()
    ]

    results = await asyncio.gather(*tasks)

    match_data = {"match_id": match_id}

    for key, data in results:
        if not data:
            continue
        if key == "incidents":
            match_data["incidents"] = process_incidents(data)
        else:
            match_data[key] = data

    day_data[str(match_id)] = match_data


async def main():
    async with AsyncSession() as session:
        # ⬅️ LAST 3 DAYS | TODAY | NEXT 3 DAYS ➡️
        target_dates = [
            (datetime.now() + timedelta(days=i)).strftime("%Y%m%d")
            for i in range(-3, 4)
        ]

        for date_str in target_dates:
            file_path = os.path.join(DATA_DIR, f"{date_str}.json")

            # Ensure data folder exists
            os.makedirs(DATA_DIR, exist_ok=True)

            # Load match list
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        content = json.load(f)
                    except:
                        content = []
            else:
                content = []

            # Normalize to match list
            if isinstance(content, dict):
                # Already processed → extract match IDs
                matches = [{"match_id": int(mid)} for mid in content.keys()]
            else:
                matches = content

            if not matches:
                print(f"[INFO] {date_str} → No matches found")
                continue

            print(f"[UPDATE] {date_str} → {len(matches)} matches")

            day_data = {}

            for i in range(0, len(matches), BATCH_SIZE):
                batch = matches[i:i + BATCH_SIZE]

                await asyncio.gather(*[
                    process_match(session, m["match_id"], day_data)
                    for m in batch if "match_id" in m
                ])

                await asyncio.sleep(SLEEP_BETWEEN_BATCHES)

            with open(file_path, "w", encoding="utf-8") as wf:
                json.dump(day_data, wf, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
