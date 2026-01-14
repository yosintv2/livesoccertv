import json, os, requests, time, glob
from datetime import datetime, timedelta

# Configuration for all 5 endpoints
ENDPOINTS = {
    "h2h": "h2h",
    "lineups": "lineups",
    "statistics": "statistics", # Added statistics
    "odds": "provider/1/winning-odds",
    "form": "pregame-form"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_and_save():
    # Get range for today and next 3 days
    today = datetime.now()
    target_dates = [(today + timedelta(days=i)).strftime('%Y%m%d') for i in range(4)]

    for date_str in target_dates:
        date_file = f"date/{date_str}.json"
        if not os.path.exists(date_file): continue
            
        with open(date_file, "r", encoding='utf-8') as f:
            matches = json.load(f)

        for m in matches:
            mid = m.get('match_id')
            if not mid: continue
            
            for folder, path in ENDPOINTS.items():
                os.makedirs(f"data/{folder}", exist_ok=True)
                target_file = f"data/{folder}/{date_str}.json"
                
                # Load existing data file for that date
                day_data = {}
                if os.path.exists(target_file):
                    with open(target_file, "r", encoding='utf-8') as rf:
                        try: day_data = json.load(rf)
                        except: day_data = {}
                
                # Skip if match data is already stored
                if str(mid) in day_data: continue

                try:
                    url = f"https://api.sofascore.com/api/v1/event/{mid}/{path}"
                    res = requests.get(url, headers=HEADERS, timeout=10)
                    
                    if res.status_code == 200:
                        day_data[str(mid)] = res.json()
                        with open(target_file, "w", encoding='utf-8') as wf:
                            json.dump(day_data, wf)
                        print(f"Saved {folder} for {mid}")
                    time.sleep(0.5) # Anti-block delay
                except Exception as e:
                    print(f"Error fetching {mid}: {e}")

if __name__ == "__main__":
    fetch_and_save()
