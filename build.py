import json, os, re
from datetime import datetime

DOMAIN = "https://tv.cricfoot.net" # Change this!

# Load templates
with open('matches.json', 'r') as f: matches = json.load(f)
with open('home_template.html', 'r') as f: home_temp = f.read()
with open('match_template.html', 'r') as f: match_temp = f.read()

def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

channel_map = {}
leagues = {}

# 1. Create Match Pages
for m in matches:
    dt = datetime.fromtimestamp(m['kickoff'])
    time_str = dt.strftime('%H:%M')
    date_str = dt.strftime('%d %b %Y')
    slug = f"match/{slugify(m['fixture'])}/{dt.strftime('%d-%b-%Y').lower()}"
    os.makedirs(slug, exist_ok=True)

    rows = ""
    top_ch = []
    for c in m['tv_channels']:
        btns = "".join([f'<a href="/channel/{slugify(ch)}/" class="channel-btn">{ch}</a>' for ch in c['channels']])
        rows += f'<div class="country-cell">{c["country"]}</div><div class="channel-cell">{btns}</div>'
        top_ch.extend(c['channels'][:2])
        for ch in c['channels']: channel_map.setdefault(ch, []).append(m)

    # Inject Match Data
    content = match_temp.replace("{{FIXTURE}}", m['fixture']).replace("{{LEAGUE}}", m['league']) \
                        .replace("{{TIME}}", time_str).replace("{{DATE}}", date_str) \
                        .replace("{{BROADCAST_ROWS}}", rows).replace("{{TOP_CHANNELS}}", ", ".join(top_ch[:3])) \
                        .replace("{{TITLE}}", f"{m['fixture']} TV Channels - Live Broadcast Guide")
    
    with open(f"{slug}/index.html", "w") as f: f.write(content)
    leagues.setdefault(m['league'], []).append({"time": time_str, "fixture": m['fixture'], "url": f"/{slug}/"})

# 2. Create Home Page
listing = ""
for league, m_list in leagues.items():
    listing += f'<div class="league-card"><div class="league-header">{league}</div>'
    for match in m_list:
        listing += f'<a href="{match["url"]}" class="match-row"><span class="match-time">{match["time"]}</span><span class="match-fixture">{match["fixture"]}</span></a>'
    listing += '</div>'

with open("index.html", "w") as f: f.write(home_temp.replace("{{MATCH_LISTING}}", listing))

# 3. Create Channel Pages (Modern Grid)
for ch, ch_matches in channel_map.items():
    path = f"channel/{slugify(ch)}"
    os.makedirs(path, exist_ok=True)
    ch_list = "".join([f'<div class="p-4 bg-[#1e293b] rounded-lg border border-white/5"><p class="text-sky-400 font-bold">{datetime.fromtimestamp(x["kickoff"]).strftime("%H:%M")}</p><p class="font-bold">{x["fixture"]}</p></div>' for x in ch_matches])
    
    # Simple Modern Channel Page Template
    ch_html = home_temp.replace("{{MATCH_LISTING}}", f'<h1 class="text-3xl font-black mb-8">Matches on {ch}</h1><div class="grid grid-cols-1 md:grid-cols-2 gap-4">{ch_list}</div>')
    with open(f"{path}/index.html", "w") as f: f.write(ch_html)

print("Site built successfully.")
