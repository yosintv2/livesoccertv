import json, os, re, glob
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
NOW = datetime.now(timezone.utc)
TODAY_DATE = NOW.date()

# Friday to Thursday Logic
days_since_friday = (TODAY_DATE.weekday() - 4) % 7
START_WEEK = TODAY_DATE - timedelta(days=days_since_friday)

TOP_LEAGUE_IDS = [7, 35, 23, 17]

# YOUR SPECIFIC AD UNIT
AD_CODE = '''
<div class="ad-container py-4 bg-slate-50 border-b border-slate-200">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-5525538810839147"
         data-ad-slot="4345862479"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
'''

def slugify(t): 
    return re.sub(r'[^a-z0-9]+', '-', str(t).lower()).strip('-')

# --- 1. LOAD TEMPLATES ---
templates = {}
for name in ['home', 'match', 'channel']:
    try:
        with open(f'{name}_template.html', 'r', encoding='utf-8') as f:
            templates[name] = f.read()
    except FileNotFoundError:
        print(f"CRITICAL ERROR: {name}_template.html not found.")

# --- 2. LOAD DATA ---
all_matches = []
seen_match_ids = set()
for f in glob.glob("date/*.json"):
    with open(f, 'r', encoding='utf-8') as j:
        try:
            data = json.load(j)
            for m in data:
                mid = m.get('match_id')
                if mid and mid not in seen_match_ids:
                    all_matches.append(m)
                    seen_match_ids.add(mid)
        except: continue

channels_data = {}
sitemap_urls = [DOMAIN + "/"]

# --- 3. GENERATE DAILY PAGES ---
for i in range(7):
    day = START_WEEK + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    
    if fname != "index.html":
        sitemap_urls.append(f"{DOMAIN}/{fname}")

    # Build Dynamic Menu
    current_page_menu = ""
    for j in range(7):
        m_day = START_WEEK + timedelta(days=j)
        m_fname = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        active_class = "active" if m_day == day else ""
        current_page_menu += f'<a href="{DOMAIN}/{m_fname}" class="date-btn {active_class}"><div>{m_day.strftime("%a")}</div><b>{m_day.strftime("%b %d")}</b></a>'

    # Filter matches using UTC to ensure correct day grouping (Fixes Jan 11/12 issue)
    day_matches = []
    for m in all_matches:
        m_dt = datetime.fromtimestamp(int(m['kickoff']), timezone.utc)
        if m_dt.date() == day:
            day_matches.append(m)

    day_matches.sort(key=lambda x: (x.get('league_id') not in TOP_LEAGUE_IDS, x.get('league', ''), x['kickoff']))

    listing_html, last_league = "", ""
    for m in day_matches:
        league = m.get('league', 'Other Football')
        
        if league != last_league:
            if last_league != "":
                listing_html += AD_CODE
            listing_html += f'<div class="league-header">{league}</div>'
            last_league = league
        
        m_dt = datetime.fromtimestamp(int(m['kickoff']), timezone.utc)
        m_slug = slugify(m['fixture'])
        m_date_folder = m_dt.strftime('%Y%m%d')
        m_url = f"{DOMAIN}/match/{m_slug}/{m_date_folder}/"
        sitemap_urls.append(m_url)
        
        # DISPLAY FULL DATE AND TIME IN LISTING
        listing_html += f'''
        <a href="{m_url}" class="match-row flex items-center p-4 bg-white group">
            <div class="time-box" style="min-width: 100px; display: flex; flex-direction: column; justify-content: center; text-align: center; border-right: 1px solid #edf2f7;">
                <div class="text-[10px] uppercase text-slate-400 font-bold local-date" data-unix="{m['kickoff']}">{m_dt.strftime('%d %b')}</div>
                <div class="font-bold text-blue-600 text-sm local-time" data-unix="{m['kickoff']}">{m_dt.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1 px-4">
                <span class="text-slate-800 font-semibold text-sm md:text-base">{m['fixture']}</span>
            </div>
        </a>'''

        # --- 4. GENERATE MATCH PAGES ---
        m_path = f"match/{m_slug}/{m_date_folder}"
        os.makedirs(m_path, exist_ok=True)
        venue_name = m.get('venue', 'To Be Announced')
        
        rows = ""
        for c in m.get('tv_channels', []):
            pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="mx-1 text-blue-600 underline text-xs">{ch}</a>' for ch in c['channels']])
            for ch in c['channels']:
                if ch not in channels_data: channels_data[ch] = []
                if m not in channels_data[ch]: channels_data[ch].append(m)
            rows += f'<div class="flex justify-between p-4 border-b"><b>{c["country"]}</b><div>{pills}</div></div>'

        with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
            m_html = templates['match'].replace("{{FIXTURE}}", m['fixture'])
            m_html = m_html.replace("{{TIME}}", str(m['kickoff']))
            m_html = m_html.replace("{{VENUE}}", venue_name)
            m_html = m_html.replace("{{DOMAIN}}", DOMAIN)
            m_html = m_html.replace("{{BROADCAST_ROWS}}", rows)
            m_html = m_html.replace("{{LEAGUE}}", league)
            m_html = m_html.replace("{{DATE}}", m_dt.strftime('%d %b %Y'))
            mf.write(m_html)

    # WRITE DAILY FILE
    with open(fname, "w", encoding='utf-8') as df:
        output = templates['home'].replace("{{MATCH_LISTING}}", listing_html)
        output = output.replace("{{WEEKLY_MENU}}", current_page_menu)
        output = output.replace("{{DOMAIN}}", DOMAIN)
        output = output.replace("{{SELECTED_DATE}}", day.strftime("%A, %b %d, %Y"))
        # PAGE TITLE FIX
        output = output.replace("{{PAGE_TITLE}}", f"SocccerTV Live Streaming TV Channels For {day.strftime('%A, %b %d, %Y')} - CricFootTV")
        df.write(output)

# --- 5. CHANNEL PAGES ---
for ch_name, ms in channels_data.items():
    c_slug = slugify(ch_name)
    c_dir = f"channel/{c_slug}"
    os.makedirs(c_dir, exist_ok=True)
    c_listing = ""
    for x in ms:
        x_dt = datetime.fromtimestamp(x['kickoff'], timezone.utc)
        c_listing += f'''
        <a href="{DOMAIN}/match/{slugify(x['fixture'])}/{x_dt.strftime('%Y%m%d')}/" class="match-row flex items-center p-4 bg-white">
            <div class="time-box" style="min-width: 100px; text-align: center;">
                <div class="text-[10px] text-slate-400 font-bold local-date" data-unix="{x['kickoff']}">{x_dt.strftime('%d %b')}</div>
                <div class="local-time font-bold text-blue-600" data-unix="{x['kickoff']}">{x_dt.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1 px-4">
                <span class="text-sm font-semibold">{x['fixture']}</span>
            </div>
        </a>'''
    with open(f"{c_dir}/index.html", "w", encoding='utf-8') as cf:
        cf.write(templates['channel'].replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", c_listing).replace("{{DOMAIN}}", DOMAIN))

# --- 6. SITEMAP ---
sitemap_content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in sitemap_urls:
    sitemap_content += f'<url><loc>{url}</loc><lastmod>{NOW.strftime("%Y-%m-%d")}</lastmod></url>'
sitemap_content += '</urlset>'
with open("sitemap.xml", "w", encoding='utf-8') as sm:
    sm.write(sitemap_content)

print(f"Build Successful. Created sitemap with {len(sitemap_urls)} URLs.")
