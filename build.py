import json, os, re, glob
from datetime import datetime, timedelta

# --- CONFIG ---
DOMAIN = "https://tv.cricfoot.net"
NOW = datetime.now()
TODAY_DATE = NOW.date()

# Find Monday of this week
START_WEEK = TODAY_DATE - timedelta(days=TODAY_DATE.weekday())

def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

# 1. LOAD DATA
all_matches = {}
for f_path in glob.glob("date/*.json"):
    try:
        with open(f_path, 'r', encoding='utf-8') as f:
            for m in json.load(f):
                uid = f"{m['fixture']}-{m['kickoff']}"
                if uid not in all_matches: all_matches[uid] = m
    except: pass

with open('home_template.html', 'r') as f: home_temp = f.read()
with open('match_template.html', 'r') as f: match_temp = f.read()
with open('channel_template.html', 'r') as f: chan_temp = f.read()

# 2. GENERATE WEEKLY MENU
menu_html = ""
for i in range(7):
    day_dt = START_WEEK + timedelta(days=i)
    fname = "index.html" if day_dt == TODAY_DATE else f"day-{day_dt.strftime('%Y%m%d')}.html"
    active = "border-b-4 border-[#00a0e9] text-white" if day_dt == TODAY_DATE else "text-slate-400"
    
    menu_html += f'''
    <a href="{DOMAIN}/{fname}" class="flex-1 min-w-[100px] text-center py-4 px-2 hover:bg-slate-800 transition {active}">
        <div class="text-[10px] uppercase font-bold">{day_dt.strftime('%A')}</div>
        <div class="text-sm font-black">{day_dt.strftime('%b %d')}</div>
    </a>'''

# 3. GENERATE ALL DAYS
for i in range(7):
    current_gen_date = START_WEEK + timedelta(days=i)
    filename = "index.html" if current_gen_date == TODAY_DATE else f"day-{current_gen_date.strftime('%Y%m%d')}.html"
    
    # Group matches by league
    grouped = {}
    day_matches = [m for m in all_matches.values() if datetime.fromtimestamp(m['kickoff']).date() == current_gen_date]
    day_matches.sort(key=lambda x: x['kickoff'])
    
    for m in day_matches:
        league = m.get('league', 'World Football')
        grouped.setdefault(league, []).append(m)

    # Build HTML List
    listing_html = ""
    for league, matches in grouped.items():
        listing_html += f'<div class="league-header">{league}</div>'
        for mx in matches:
            t = datetime.fromtimestamp(mx['kickoff']).strftime('%H:%M')
            url = f"{DOMAIN}/match/{slugify(mx['fixture'])}/{datetime.fromtimestamp(mx['kickoff']).strftime('%Y%m%d')}/"
            listing_html += f'''
            <a href="{url}" class="match-row">
                <div class="match-time">{t}</div>
                <div class="match-info">{mx['fixture']}</div>
            </a>'''

    if not day_matches:
        listing_html = '<div class="p-20 text-center font-bold text-slate-400">NO MATCHES SCHEDULED FOR THIS DATE</div>'

    page_title = f"Live Soccer TV Guide - {current_gen_date.strftime('%A, %b %d')}"
    final_page = home_temp.replace("{{MATCH_LISTING}}", listing_html)\
                          .replace("{{WEEKLY_MENU}}", menu_html)\
                          .replace("{{PAGE_TITLE}}", page_title)\
                          .replace("{{DOMAIN}}", DOMAIN)
    
    with open(filename, "w") as f: f.write(final_page)

print(f"✅ Full Week Generated starting from Monday {START_WEEK}")
