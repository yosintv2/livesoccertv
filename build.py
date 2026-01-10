import json, os, re, glob
from datetime import datetime, timedelta

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
DATE_FOLDER = "date/*.json"

def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

# 1. DATA MERGING & DE-DUPLICATION
all_matches = {}
for file_path in glob.glob(DATE_FOLDER):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for m in data:
                # Unique ID: combination of teams and kickoff time to prevent duplicates
                uid = f"{m['fixture']}-{m['kickoff']}"
                if uid not in all_matches:
                    all_matches[uid] = m
    except Exception as e:
        print(f"Skipping {file_path} due to error: {e}")

matches = list(all_matches.values())
matches.sort(key=lambda x: x['kickoff'])

# 2. DATE MENU LOGIC
today_dt = datetime.now()
date_menu = ""
for offset in [-1, 0, 1]:
    d = today_dt + timedelta(days=offset)
    label = ["Yesterday", "Today", "Tomorrow"][offset + 1]
    btn_style = "bg-[#00a0e9] text-white" if offset == 0 else "bg-slate-700 text-slate-300 hover:bg-slate-600"
    date_menu += f'<a href="/" class="px-4 py-2 rounded text-[11px] font-black uppercase tracking-tighter transition {btn_style}">{label} ({d.strftime("%b %d")})</a>'

# 3. LOAD ALL TEMPLATES
with open('home_template.html', 'r') as f: home_temp = f.read()
with open('match_template.html', 'r') as f: match_temp = f.read()
with open('channel_template.html', 'r') as f: chan_temp = f.read()

leagues_dict = {}
channels_dict = {}

# 4. GENERATE MATCH PAGES
for m in matches:
    dt = datetime.fromtimestamp(m['kickoff'])
    t_str, d_str = dt.strftime('%H:%M'), dt.strftime('%d %b %Y')
    league, venue = m.get('league', 'International'), m.get('venue', 'TBA Stadium')
    
    # Path: /match/team-a-vs-team-b/20260111/
    match_path = f"match/{slugify(m['fixture'])}/{dt.strftime('%Y%m%d')}"
    os.makedirs(match_path, exist_ok=True)

    rows_html, top_ch = "", []
    for c in m.get('tv_channels', []):
        pills = ""
        for ch in c['channels']:
            p_slug = slugify(ch)
            pills += f'<a href="/channel/{p_slug}/" class="pill">{ch}</a>'
            channels_dict.setdefault(ch, []).append(m)
            if ch not in top_ch: top_ch.append(ch)
        rows_html += f'<div class="row"><div class="c-name">{c["country"]}</div><div class="ch-list">{pills}</div></div>'

    # Match Page Replacement
    m_page = match_temp.replace("{{FIXTURE}}", m['fixture']).replace("{{LEAGUE}}", league) \
                      .replace("{{TIME}}", t_str).replace("{{DATE}}", d_str) \
                      .replace("{{VENUE}}", venue).replace("{{BROADCAST_ROWS}}", rows_html) \
                      .replace("{{TOP_CHANNELS}}", ", ".join(top_ch[:3])) \
                      .replace("{{TITLE}}", f"{m['fixture']} Live Stream - {league} TV Guide") \
                      .replace("{{CANONICAL}}", f"{DOMAIN}/{match_path}/")
    
    with open(f"{match_path}/index.html", "w") as f: f.write(m_page)
    leagues_dict.setdefault(league, []).append({"time": t_str, "fixture": m['fixture'], "url": f"/{match_path}/"})

# 5. GENERATE CHANNEL PAGES
for ch_name, ch_mats in channels_dict.items():
    c_slug = f"channel/{slugify(ch_name)}"
    os.makedirs(c_slug, exist_ok=True)
    c_list = "".join([f'<a href="{f"/match/{slugify(x["fixture"])}/{datetime.fromtimestamp(x["kickoff"]).strftime("%Y%m%d")}/"}" class="match-card"><div class="time-col">{datetime.fromtimestamp(x["kickoff"]).strftime("%H:%M")}</div><div><div class="font-bold">{x["fixture"]}</div><div class="text-[10px] uppercase text-slate-400">{x["league"]}</div></div></a>' for x in ch_mats])
    
    c_page = chan_temp.replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", c_list) \
                      .replace("{{TITLE}}", f"Watch Football on {ch_name} - Live Broadcast Schedule")
    with open(f"{c_slug}/index.html", "w") as f: f.write(c_page)

# 6. GENERATE HOME PAGE
h_listing = ""
for l_name, m_list in leagues_dict.items():
    h_listing += f'<div class="mb-6"><div class="league-title">{l_name}</div>'
    for match in m_list:
        h_listing += f'<a href="{match["url"]}" class="match-card"><div class="time-col">{match["time"]}</div><div class="font-bold">{match["fixture"]}</div></a>'
    h_listing += '</div>'

with open("index.html", "w") as f:
    f.write(home_temp.replace("{{MATCH_LISTING}}", h_listing).replace("{{DATE_MENU}}", date_menu))

print("Build Successful: Site generated at tv.cricfoot.net")
