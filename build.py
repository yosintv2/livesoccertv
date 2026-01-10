import json, os, re, glob, time
from datetime import datetime, timedelta

# --- AUTOMATIC CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
TODAY = datetime.now().date() # Automatically gets today's date
TOMORROW = TODAY + timedelta(days=1)
YESTERDAY = TODAY - timedelta(days=1)

def slugify(t): 
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

# 1. LOAD DATA
all_matches = {}
json_files = glob.glob("date/*.json")

if not json_files:
    print("❌ ERROR: No JSON files found in 'date/' folder.")
    exit()

for file_path in json_files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for m in json.load(f):
                uid = f"{m['fixture']}-{m['kickoff']}"
                if uid not in all_matches: all_matches[uid] = m
    except: pass

# 2. LOAD TEMPLATES
with open('home_template.html', 'r') as f: home_temp = f.read()
with open('match_template.html', 'r') as f: match_temp = f.read()
with open('channel_template.html', 'r') as f: chan_temp = f.read()

channels_data = {}
matches_by_date = {YESTERDAY: [], TODAY: [], TOMORROW: []}
sitemap_urls = [DOMAIN + "/", DOMAIN + "/yesterday.html", DOMAIN + "/tomorrow.html", DOMAIN + "/live.html"]

# 3. MATCH & CHANNEL GENERATION
for m in all_matches.values():
    m_dt = datetime.fromtimestamp(m['kickoff'])
    m_date = m_dt.date()
    
    if m_date in matches_by_date:
        matches_by_date[m_date].append(m)
        slug = slugify(m['fixture'])
        date_folder = m_dt.strftime('%Y%m%d')
        
        match_rel_path = f"match/{slug}/{date_folder}"
        os.makedirs(match_rel_path, exist_ok=True)
        sitemap_urls.append(f"{DOMAIN}/{match_rel_path}/")

        rows, top_ch = "", []
        for c in m.get('tv_channels', []):
            pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="pill">{ch}</a>' for ch in c['channels']])
            rows += f'<div class="row"><div class="c-name">{c["country"]}</div><div class="ch-list">{pills}</div></div>'
            for ch in c['channels']:
                channels_data.setdefault(ch, []).append(m)
                top_ch.append(ch)

        m_html = match_temp.replace("{{FIXTURE}}", m['fixture']).replace("{{TIME}}", m_dt.strftime('%H:%M')) \
                           .replace("{{DATE}}", m_dt.strftime('%d %b %Y')).replace("{{BROADCAST_ROWS}}", rows) \
                           .replace("{{LEAGUE}}", m.get('league', 'Football')).replace("{{DOMAIN}}", DOMAIN)
        with open(f"{match_rel_path}/index.html", "w") as f: f.write(m_html)

# 4. HOME PAGE GENERATION
files = [("index.html", TODAY), ("tomorrow.html", TOMORROW), ("yesterday.html", YESTERDAY)]
for filename, target_date in files:
    menu = ""
    for f_name, f_date in files:
        style = "bg-[#00a0e9] text-white" if f_date == target_date else "bg-slate-800 text-slate-400"
        # Navigation links are now clickable
        menu += f'<a href="{DOMAIN}/{f_name}" class="flex-1 text-center py-2 rounded text-[10px] font-black uppercase {style}">{f_date.strftime("%b %d")}</a>'

    listing = ""
    for mx in sorted(matches_by_date[target_date], key=lambda x: x['kickoff']):
        t_str = datetime.fromtimestamp(mx['kickoff']).strftime('%H:%M')
        m_url = f"{DOMAIN}/match/{slugify(mx['fixture'])}/{datetime.fromtimestamp(mx['kickoff']).strftime('%Y%m%d')}/"
        listing += f'<a href="{m_url}" class="match-card"><div class="time-col">{t_str}</div><div class="font-bold">{mx["fixture"]}</div></a>'

    with open(filename, "w") as f:
        f.write(home_temp.replace("{{MATCH_LISTING}}", listing).replace("{{DATE_MENU}}", menu).replace("{{DOMAIN}}", DOMAIN))

# 5. GENERATE SITEMAP.XML
sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in sitemap_urls:
    sitemap_xml += f'<url><loc>{url}</loc><lastmod>{TODAY.strftime("%Y-%m-%d")}</lastmod><changefreq>daily</changefreq></url>'
sitemap_xml += '</urlset>'
with open("sitemap.xml", "w") as f: f.write(sitemap_xml)

print(f"✅ Build Finished! Today is {TODAY}. Sitemap created.")
