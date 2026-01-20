import asyncio
import json
import os
from datetime import datetime, timedelta
from curl_cffi.requests import AsyncSession

# ================= CONFIG =================

DATA_DIR = "data"
SPORT = "football"

ENDPOINTS = {
    "h2h": "h2h",
    "lineups": "lineups",
    "statistics": "statistics",
    "odds": "provider/1/winning-odds",
    "form": "pregame-form",
}

DAYS_RANGE = range(-3, 4)  # last 3 days + today + next 3 days
BATCH_SIZE = 5
SLEEP = 1

# =========================================


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def extract_goals(incidents_json, match_id):
    home_goals, away_goals = [], []

    for inc in incidents_json.get("incidents", []):
        if inc.get("incidentType") != "goal":
            continue

        player = inc.get("player", {}).get("name", "Unknown")
        minute = f"{inc.get('time', '')}'"
        is_home = inc.get("isHome")

        goal = {"name": player, "time": minute}

        if is_home:
            home_goals.append(goal)
        else:
            away_goals.append(goal)

    return {
        "match_id": match_id,
        "home_score": len(home_goals),
        "away_score": len(away_goals),
        "home_scorers": home_goals,
        "away_scorers": away_goals,
    }


async def fetch_json(session, url):
    try:
        r = await session.get(url, impersonate="chrome120", timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("[ERROR]", url, e)
    return None


async def fetch_match_ids(session, target_date):
    date_str = target_date.strftime("%Y-%m-%d")
    url = f"https://www.sofascore.com/api/v1/sport/{SPORT}/scheduled-events/{date_str}"

    data = await fetch_json(session, url)
    if not data:
        return []

    return [e["id"] for e in data.get("events", [])]


async def process_match(session, match_id, date_key):
    # ---------- NORMAL ENDPOINTS ----------
    for key, path in ENDPOINTS.items():
        url = f"https://api.sofascore.com/api/v1/event/{match_id}/{path}"
        data = await fetch_json(session, url)
        if not data:
            continue

        folder = os.path.join(DATA_DIR, key)
        ensure_dir(folder)
        file = os.path.join(folder, f"{date_key}.json")

        store = {}
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8") as f:
                store = json.load(f)

        store[str(match_id)] = data

        with open(file, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)

    # ---------- INCIDENTS (GOALS ONLY) ----------
    inc_url = f"https://api.sofascore.com/api/v1/event/{match_id}/incidents"
    inc_data = await fetch_json(session, inc_url)
    if not inc_data:
        return

    goals_data = extract_goals(inc_data, match_id)

    folder = os.path.join(DATA_DIR, "incidents")
    ensure_dir(folder)
    file = os.path.join(folder, f"{date_key}.json")

    store = {}
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            store = json.load(f)

    store[str(match_id)] = goals_data

    with open(file, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


async def process_day(session, offset):
    day = datetime.utcnow() + timedelta(days=offset)
    date_key = day.strftime("%Y%m%d")

    print(f"[INFO] Processing {date_key}")

    match_ids = await fetch_match_ids(session, day)

    if not match_ids:
        print(f"[INFO] {date_key} → No matches found")
        return

    for i in range(0, len(match_ids), BATCH_SIZE):
        batch = match_ids[i:i + BATCH_SIZE]
        await asyncio.gather(*[
            process_match(session, mid, date_key)
            for mid in batch
        ])
        await asyncio.sleep(SLEEP)


async def main():
    async with AsyncSession() as session:
        ensure_dir(DATA_DIR)

        for offset in DAYS_RANGE:
            await process_day(session, offset)


if __name__ == "__main__":
    asyncio.run(main())
