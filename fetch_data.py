import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from curl_cffi.requests import AsyncSession

# --- CONFIGURATION ---
ENDPOINTS = {
    "h2h": "h2h",
    "lineups": "lineups",
    "statistics": "statistics",
    "odds": "provider/1/winning-odds",
    "form": "pregame-form"
}

async def fetch_sofa_endpoint(session, mid, endpoint_key, path):
    """Fetches a specific SofaScore endpoint for a single match."""
    url = f"https://api.sofascore.com/api/v1/event/{mid}/{path}"
    try:
        # Using impersonate="chrome120" to bypass Cloudflare/Rate limits
        res = await session.get(url, impersonate="chrome120", timeout=10)
        if res.status_code == 200:
            return endpoint_key, res.json()
    except Exception as e:
        print(f"Error fetching {endpoint_key} for {mid}: {e}")
    return endpoint_key, None

async def process_match(session, mid, date_str):
    """Fetches all 5 data points for a single match and updates the day's JSON files."""
    tasks = [fetch_sofa_endpoint(session, mid, key, path) for key, path in ENDPOINTS.items()]
    results = await asyncio.gather(*tasks)

    for folder, data in results:
        if data:
            os.makedirs(f"data/{folder}", exist_ok=True)
            target_path = f"data/{folder}/{date_str}.json"
            
            # Load existing file to append new match data
            day_data = {}
            if os.path.exists(target_path):
                try:
                    with open(target_path, "r", encoding='utf-8') as rf:
                        day_data = json.load(rf)
                except: day_data = {}

            day_data[str(mid)] = data
            with open(target_path, "w", encoding='utf-8') as wf:
                json.dump(day_data, wf, indent=2)

async def main():
    async with AsyncSession() as session:
        # Today + 3 Days
        target_dates = [(datetime.now() + timedelta(days=i)).strftime('%Y%m%d') for i in range(4)]
        
        for date_str in target_dates:
            date_file = f"date/{date_str}.json"
            if not os.path.exists(date_file): 
                print(f"Skipping {date_str}, no match list found.")
                continue
                
            with open(date_file, "r", encoding='utf-8') as f:
                matches = json.load(f)

            print(f"--- Processing {len(matches)} matches for {date_str} ---")
            
            # Process matches in small batches to avoid triggering rate limits
            for i in range(0, len(matches), 5):
                batch = matches[i:i+5]
                match_tasks = [process_match(session, m['match_id'], date_str) for m in batch if 'match_id' in m]
                await asyncio.gather(*match_tasks)
                await asyncio.sleep(1) # Polite pause between batches

if __name__ == "__main__":
    asyncio.run(main())
