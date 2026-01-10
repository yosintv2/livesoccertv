import json, os, re, glob, logging
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring

# --- CONFIG ---
DOMAIN = "https://tv.cricfoot.net"
INPUT_FOLDER = "date"
OUTPUT_FOLDER = "public"
PRIORITY_IDS = [23, 17] 

logging.basicConfig(level=logging.INFO, format='%(message)s')

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')

def run_build():
    # Ensure folders exist
    os.makedirs(INPUT_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # 1. LOAD TEMPLATES
    try:
        with open('home_template.html', 'r', encoding='utf-8') as f: home_t = f.read()
        with open('match_template.html', 'r', encoding='utf-8') as f: match_t = f.read()
        with open('channel_template.html', 'r', encoding='utf-8') as f: channel_t = f.read()
    except FileNotFoundError as e:
        logging.error(f"STOP: Template file missing! {e}")
        return

    # 2. LOAD DATA
    matches = []
    files = glob.glob(f"{INPUT_FOLDER}/*.json")
    for f_path in files:
        with open(f_path, 'r', encoding='utf-8') as f:
            matches.extend(json.load(f))

    # CRITICAL FIX: Create dummy data if empty so the page isn't blank
    if not matches:
        logging.warning("No JSON found in /date. Creating test match.")
        matches = [{
            "match_id": 1, "league_id": 23, "league": "Serie A", "kickoff": int(datetime.now().timestamp()),
            "fixture": "Test Match vs Sample Team", "venue": "Developer Stadium",
            "tv_channels": [{"country": "Global", "channels": ["CricFoot Sports"]}]
        }]

    # SORTING
    matches.sort(key=lambda x: (x.get('league_id') not in PRIORITY_IDS, x['kickoff']))

    # 3. GENERATE PAGES
    channels_db = {}
    sitemap_urls = [f"{DOMAIN}/"]
    
    # Process Matches
    for m in matches:
        m_dt = datetime.fromtimestamp(m['kickoff'])
        m_slug = slugify(m['fixture'])
        date_id = m_dt.strftime('%Y%m%d')
        m_dir = os.path.join(OUTPUT_FOLDER, "match", m_slug, date_id)
        os.makedirs(m_dir, exist_ok=True)

        rows = ""
        for item in m.get('tv_channels', []):
            pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="ch-pill">{ch}</a>' for ch in item['channels']])
            rows += f'<tr class="border-b"><td class="p-4 font-bold text-slate-600 text-sm">{item["country"]}</td><td class="p-4">{pills}</td></tr>'
            for ch in item['channels']: channels_db.setdefault(ch, []).append(m)

        m_html = match_t.replace("{{FIXTURE}}", m['fixture']).replace("{{TIME_UNIX}}", str(m['kickoff'])).replace("{{LEAGUE}}", m.get('league', 'Soccer')).replace("{{VENUE}}", m.get('venue', 'TBA')).replace("{{BROADCAST_ROWS}}", rows).replace("{{DOMAIN}}", DOMAIN)
        with open(os.path.join(m_dir, "index.html"), "w", encoding='utf-8') as f: f.write(m_html)
        sitemap_urls.append(f"{DOMAIN}/match/{m_slug}/{date_id}/")

    # Generate Home Page (Index)
    listing, last_league = "", ""
    for m in matches:
        if m['league'] != last_league:
            listing += f'<div class="league-header">{m["league"]}</div>'
            last_league = m['league']
        m_slug = slugify(m['fixture'])
        listing += f'<a href="{DOMAIN}/match/{m_slug}/{datetime.fromtimestamp(m["kickoff"]).strftime("%Y%m%d")}/" class="match-row"><div class="match-time" data-unix="{m["kickoff"]}"></div><div class="match-info">{m["fixture"]}</div></a>'

    final_h = home_t.replace("{{MATCH_LISTING}}", listing).replace("{{DOMAIN}}", DOMAIN).replace("{{PAGE_TITLE}}", "Live Football Guide").replace("{{WEEKLY_MENU}}", "")
    with open(os.path.join(OUTPUT_FOLDER, "index.html"), "w", encoding='utf-8') as f: f.write(final_h)

    logging.info(f"Build Finished! Open {OUTPUT_FOLDER}/index.html to see your site.")

if __name__ == "__main__":
    run_build()
