import asyncio
import json
import os
from datetime import datetime, timedelta
from curl_cffi.requests import AsyncSession

SOURCE_NAME = "YoSinTV_Ultra_Engine"

async def get_channel_name(session, channel_id):
    """Fetches the actual name of a channel (e.g., 'Sky Sports') from its ID."""
    url = f"https://api.sofascore.com/api/v1/tv/channel/{channel_id}/schedule"
    try:
        res = await session.get(url, impersonate="chrome120", timeout=5)
        if res.status_code == 200:
            data = res.json()
            return data.get('channel', {}).get('name', 'Unknown Channel')
    except:
        pass
    return "Unknown Channel"

async def get_tv_data(session, match_id):
    """Fetches country-specific TV channels and resolves their names."""
    tv_url = f"https://api.sofascore.com/api/v1/tv/event/{match_id}/country-channels"
    broadcasters = []
    try:
        res = await session.get(tv_url, impersonate="chrome120", timeout=10)
        if res.status_code != 200: return []
        
        country_channels = res.json().get('countryChannels', {})
        
        for country_code, channel_ids in country_channels.items():
            channel_tasks = [get_channel_name(session, cid) for cid in channel_ids]
            names = await asyncio.gather(*channel_tasks)
            
            clean_names = list(set([n for n in names if n != "Unknown Channel"]))
            
            broadcasters.append({
                "country": country_code,
                "channels": clean_names if clean_names else ["TBA"]
            })
            
        return sorted(broadcasters, key=lambda x: x['country'])
    except:
        return []

async def fetch_match_details(session, match_id):
    """Fetches full fixture meta-data and TV listings."""
    event_url = f"https://api.sofascore.com/api/v1/event/{match_id}"
    try:
        res = await session.get(event_url, impersonate="chrome120", timeout=10)
        if res.status_code != 200: return None
        
        ev = res.json().get('event', {})
        tv_info = await get_tv_data(session, match_id)
        
        return {
            "match_id": ev.get('id'),
            "kickoff": ev.get('startTimestamp'),
            "fixture": f"{ev['homeTeam']['name']} vs {ev['awayTeam']['name']}",
            "league_id": ev.get('tournament', {}).get('uniqueTournament', {}).get('id', 0),
            "league": ev.get('tournament', {}).get('name', 'Unknown'),
            "venue": ev.get('venue', {}).get('name', 'TBA'),
            "tv_channels": tv_info
        }
    except:
        return None

async def process_day(session, days_offset):
    """Handles the scraping for a single future day."""
    target_date = datetime.now() + timedelta(days=days_offset)
    date_query = target_date.strftime('%Y-%m-%d')
    file_name = target_date.strftime('%Y%m%d') + ".json"
    
    schedule_url = f"https://www.sofascore.com/api/v1/sport/football/scheduled-events/{date_query}"
    
    print(f"--- Processing Day +{days_offset} ({date_query}) ---")
    resp = await session.get(schedule_url, impersonate="chrome120", timeout=30)
    
    if resp.status_code != 200:
        print(f"Failed to fetch schedule for {date_query}")
        return

    events = resp.json().get('events', [])
    if not events:
        print(f"No events found for {date_query}")
        return

    print(f"Found {len(events)} fixtures. Resolving TV data...")

    # Process match details in parallel
    tasks = [fetch_match_details(session, event['id']) for event in events]
    results = await asyncio.gather(*tasks)
    
    final_data = [r for r in results if r is not None]

    save_path = os.path.join("date", file_name)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=4)
    
    print(f"DONE: Generated {save_path}")

async def main():
    if not os.path.exists('date'): os.makedirs('date')

    async with AsyncSession() as session:
        # Loop through Tomorrow (1), Day After (2), and 3 Days Later (3)
        for offset in [1, 2, 3]:
            await process_day(session, offset)
            # 1 second delay between days to prevent IP flagging
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
