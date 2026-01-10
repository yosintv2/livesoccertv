import json, os, re
from datetime import datetime

# --- CONFIG ---
DOMAIN = "https://yourdomain.com"

with open('matches.json', 'r') as f: matches = json.load(f)
with open('home_template.html', 'r') as f: home_temp = f.read()
with open('match_template.html', 'r') as f: match_temp = f.read()

def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

leagues_listing = {}
channel_set = set()

# 1. PROCESS EACH MATCH
for m in matches:
    dt = datetime.fromtimestamp(m['kickoff'])
    time_str, date_str = dt.strftime('%H:%M'), dt.strftime('%d %b %Y')
    venue, league = m.get('venue', 'TBA'), m.get('league', 'Other')
    
    # Path: match/team-a-vs-team-b/11-jan-2026/index.html
    slug = f"match/{slugify(m['fixture'])}/{dt.strftime('%d-%b-%Y').lower()}"
    os.makedirs(slug, exist_ok=True)

    rows_html, top_ch = "", []
    for c in m.get('tv_channels', []):
        pills = ""
        for ch in c['channels']:
            pills += f'<a href="/channel/{slugify(ch)}/" class="pill">{ch}</a>'
            channel_set.add(ch)
            if ch not in top_ch: top_ch.append(ch)
        rows_html += f'<div class="row"><div class="c-name">{c["country"]}</div><div class="ch-list">{pills}</div></div>'

    # Inject into Match Template
    match_page = match_temp.replace("{{FIXTURE}}", m['fixture']).replace("{{LEAGUE}}", league) \
                          .replace("{{TIME}}", time_str).replace("{{DATE}}", date_str) \
                          .replace("{{VENUE}}", venue).replace("{{BROADCAST_ROWS}}", rows_html) \
                          .replace("{{TOP_CHANNELS}}", ", ".join(top_ch[:3])) \
                          .replace("{{TITLE}}", f"{m['fixture']} - TV Channels - {date_str}") \
                          .replace("{{SCHEMA}}", "") # Add Schema JSON here if needed

    with open(f"{slug}/index.html", "w") as f: f.write(match_page)
    leagues_listing.setdefault(league, []).append({"time": time_str, "fixture": m['fixture'], "url": f"/{slug}/"})

# 2. BUILD HOME LISTING
final_listing = ""
for l_name, m_list in leagues_listing.items():
    final_listing += f'<div class="mb-4"><div class="league-title">{l_name}</div>'
    for match in m_list:
        final_listing += f'<a href="{match["url"]}" class="match-card"><div class="w-16 font-bold text-[#00a0e9]">{match["time"]}</div><div class="font-bold">{match["fixture"]}</div></a>'
    final_listing += '</div>'

# 3. SAVE HOME
chan_pills = "".join([f'<span class="bg-gray-100 px-2 py-1 rounded text-[10px] font-bold">{c}</span>' for c in list(channel_set)[:10]])
with open("index.html", "w") as f:
    f.write(home_temp.replace("{{MATCH_LISTING}}", final_listing).replace("{{DATE_MENU}}", "").replace("{{CHANNEL_LIST}}", chan_pills))

print("Build Successful!")
