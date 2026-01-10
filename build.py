import json, os, re, glob
from datetime import datetime, timedelta

# --- CONFIG ---
DOMAIN = "https://tv.cricfoot.net"
DATE_FOLDER = "date/*.json" # Scans all files like 20260111.json

def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

# 1. LOAD & DE-DUPLICATE DATA
all_matches = {}
for file_path in glob.glob(DATE_FOLDER):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            for m in data:
                # Use matchId or a combination of fixture/time as a unique key
                uid = m.get('matchId') or f"{m['fixture']}-{m['kickoff']}"
                if uid not in all_matches:
                    all_matches[uid] = m
    except Exception as e:
        print(f"Error loading {file_path}: {e}")

matches = list(all_matches.values())
matches.sort(key=lambda x: x['kickoff']) # Sort by time

# 2. LOAD TEMPLATES
with open('home_template.html', 'r') as f: home_temp = f.read()
with open('match_template.html', 'r') as f: match_temp = f.read()
with open('channel_template.html', 'r') as f: chan_temp = f.read()

# 3. GENERATE DATE MENU (Yesterday, Today, Tomorrow)
today_dt = datetime.now()
date_menu = ""
for offset in [-1, 0, 1]:
    d = today_dt + timedelta(days=offset)
    label = ["Yesterday", "Today", "Tomorrow"][offset + 1]
    active = "bg-[#00a0e9]" if offset == 0 else "bg-slate-700 hover:bg-slate-600"
    date_menu += f'<a href="#" class="px-4 py-2 rounded text-xs font-bold text-white {active}">{label} ({d.strftime("%b %d")})</a>'

# 4. PROCESS MATCHES & CHANNELS
leagues_dict = {}
channels_dict = {}

for m in matches:
    dt = datetime.fromtimestamp(m['kickoff'])
    time_str, date_str = dt.strftime('%H:%M'), dt.strftime('%d %b %Y')
    league = m.get('league', 'International')
    venue = m.get('venue', 'TBA')
    
    match_slug = f"match/{slugify(m['fixture'])}/{dt.strftime('%Y%m%d')}"
    os.makedirs(match_slug, exist_ok=True)

    # Broadcast Rows & Channel Mapping
    rows_html, top_ch = "", []
    for c in m.get('tv_channels', []):
        pills = ""
        for ch in c['channels']:
            ch_slug = slugify(ch)
            pills += f'<a href="/channel/{ch_slug}/" class="pill">{ch}</a>'
            channels_dict.setdefault(ch, []).append(m)
            if ch not in top_ch: top_ch.append(ch)
        rows_html += f'<div class="row"><div class="c-name">{c["country"]}</div><div class="ch-list">{pills}</div></div>'

    # Build Match Page
    match_page = match_temp.replace("{{FIXTURE}}", m['fixture']).replace("{{LEAGUE}}", league) \
                          .replace("{{TIME}}", time_str).replace("{{DATE}}", date_str) \
                          .replace("{{VENUE}}", venue).replace("{{BROADCAST_ROWS}}", rows_html) \
                          .replace("{{TOP_CHANNELS}}", ", ".join(top_ch[:3])) \
                          .replace("{{TITLE}}", f"Watch {m['fixture']} Live - {league} TV Guide")
    
    with open(f"{match_slug}/index.html", "w") as f: f.write(match_page)
    leagues_dict.setdefault(league, []).append({"time": time_str, "fixture": m['fixture'], "url": f"/{match_slug}/"})

# 5. GENERATE HOME PAGE
home_listing = ""
for l_name, m_list in leagues_dict.items():
    home_listing += f'<div class="mb-6"><div class="league-title">{l_name}</div>'
    for match in m_list:
        home_listing += f'<a href="{match["url"]}" class="match-card"><div class="time-col">{match["time"]}</div><div class="font-bold">{match["fixture"]}</div></a>'
    home_listing += '</div>'

with open("index.html", "w") as f:
    f.write(home_temp.replace("{{MATCH_LISTING}}", home_listing).replace("{{DATE_MENU}}", date_menu))

# 6. GENERATE CHANNEL PAGES
for ch_name, ch_matches in channels_dict.items():
    ch_slug = f"channel/{slugify(ch_name)}"
    os.makedirs(ch_slug, exist_ok=True)
    m_html = "".join([f'<a href="#" class="match-card"><div class="time-col">{datetime.fromtimestamp(x["kickoff"]).strftime("%H:%M")}</div><div><div class="font-bold">{x["fixture"]}</div><div class="text-[10px] uppercase text-slate-400">{x["league"]}</div></div></a>' for x in ch_matches])
    
    final_chan = chan_temp.replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", m_html)
    with open(f"{ch_slug}/index.html", "w") as f: f.write(final_chan)

print("Build Successful - No duplicates found.")
