import json, os, re, glob 
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
LOCAL_OFFSET = timezone(timedelta(hours=5)) 

NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date() 

# CENTER LOGIC: To make Today the 4th item, we start the menu 3 days ago
MENU_START_DATE = TODAY_DATE - timedelta(days=3)
# We calculate the end date of the menu as well
MENU_END_DATE = TODAY_DATE + timedelta(days=3)

TOP_LEAGUE_IDS = [17, 35, 23, 7, 8, 34, 679]

# Google Ads Code Block
ADS_CODE = '''
<div class="ad-container" style="margin: 20px 0; text-align: center;">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5525538810839147" crossorigin="anonymous"></script>
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-5525538810839147"
         data-ad-slot="4345862479"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
'''

MENU_CSS = '''
<style>
    .weekly-menu-container {
        display: flex;
        width: 100%;
        gap: 4px;
        padding: 10px 5px;
        box-sizing: border-box;
        justify-content: space-between;
    }
    .date-btn {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 8px 2px;
        text-decoration: none;
        border-radius: 6px;
        background: #fff;
        border: 1px solid #e2e8f0;
        min-width: 0; 
        transition: all 0.2s;
    }
    .date-btn div { font-size: 9px; text-transform: uppercase; color: #64748b; font-weight: bold; }
    .date-btn b { font-size: 10px; color: #1e293b; white-space: nowrap; }
    .date-btn.active { background: #2563eb; border-color: #2563eb; }
    .date-btn.active div, .date-btn.active b { color: #fff; }
    
    @media (max-width: 480px) {
        .date-btn b { font-size: 8px; }
        .date-btn div { font-size: 7px; }
        .weekly-menu-container { gap: 2px; padding: 5px 2px; }
    }
</style>
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

# --- 3. PRE-PROCESS ALL MATCHES (FOR MATCH PAGES & SITEMAP) ---
# We do this outside the 7-day loop so older/future matches are NOT skipped.
for m in all_matches:
    m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
    m_slug = slugify(m['fixture'])
    m_date_folder = m_dt_local.strftime('%Y%m%d')
    m_url = f"{DOMAIN}/match/{m_slug}/{m_date_folder}/"
    sitemap_urls.append(m_url)
    
    league = m.get('league', 'Other Football')
    
    # --- CHANNEL DATA POPULATION ---
    for c in m.get('tv_channels', []):
        for ch in c['channels']:
            if ch not in channels_data: channels_data[ch] = []
            # Keep history in channel pages if needed, or filter by time
            if int(m['kickoff']) > (NOW.timestamp() - 86400): # Show matches from last 24h onwards on channel pages
                if not any(x['m']['match_id'] == m['match_id'] for x in channels_data[ch]):
                    channels_data[ch].append({'m': m, 'dt': m_dt_local, 'league': league})

    # --- GENERATE INDIVIDUAL MATCH PAGE ---
    m_path = f"match/{m_slug}/{m_date_folder}"
    os.makedirs(m_path, exist_ok=True)
    venue_val = m.get('venue') or m.get('stadium') or "To Be Announced"
    
    rows = ""
    country_counter = 0
    for c in m.get('tv_channels', []):
        country_counter += 1
        channel_links = [f'<a href="{DOMAIN}/channel/{slugify(ch)}/" style="display: inline-block; background: #f1f5f9; color: #2563eb; padding: 2px 8px; border-radius: 4px; margin: 2px; text-decoration: none; font-weight: 600; border: 1px solid #e2e8f0;">{ch}</a>' for ch in c['channels']]
        pills = "".join(channel_links)
        
        rows += f'''
        <div style="display: flex; align-items: flex-start; padding: 12px; border-bottom: 1px solid #edf2f7; background: #fff;">
            <div style="flex: 0 0 100px; font-weight: 800; color: #475569; font-size: 13px; padding-top: 4px;">{c["country"]}</div>
            <div style="flex: 1; display: flex; flex-wrap: wrap; gap: 4px;">{pills}</div>
        </div>'''
        if country_counter % 10 == 0:
            rows += ADS_CODE

    with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
        m_html = templates['match'].replace("{{FIXTURE}}", m['fixture']).replace("{{DOMAIN}}", DOMAIN)
        m_html = m_html.replace("{{BROADCAST_ROWS}}", rows).replace("{{LEAGUE}}", league)
        m_html = m_html.replace("{{LOCAL_DATE}}", f'<span class="auto-date" data-unix="{m["kickoff"]}">{m_dt_local.strftime("%d %b %Y")}</span>')
        m_html = m_html.replace("{{LOCAL_TIME}}", f'<span class="auto-time" data-unix="{m["kickoff"]}">{m_dt_local.strftime("%H:%M")}</span>')
        m_html = m_html.replace("{{UNIX}}", str(m['kickoff'])).replace("{{VENUE}}", venue_val) 
        mf.write(m_html)

# --- 4. GENERATE DAILY LISTING PAGES (STILL 7 DAYS FOR MENU) ---
for i in range(7):
    day = MENU_START_DATE + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    if fname != "index.html": sitemap_urls.append(f"{DOMAIN}/{fname}")

    page_specific_menu = f'{MENU_CSS}<div class="weekly-menu-container">'
    for j in range(7):
        m_day = MENU_START_DATE + timedelta(days=j)
        m_fname = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        active_class = "active" if m_day == day else ""
        page_specific_menu += f'''
        <a href="{DOMAIN}/{m_fname}" class="date-btn {active_class}">
            <div>{m_day.strftime("%a")}</div>
            <b>{m_day.strftime("%b %d")}</b>
        </a>'''
    page_specific_menu += '</div>'

    day_matches = []
    for m in all_matches:
        m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        if m_dt_local.date() == day:
            day_matches.append(m)

    day_matches.sort(key=lambda x: (
        x.get('league_id') not in TOP_LEAGUE_IDS, 
        x.get('league', 'Other Football'), 
        x['kickoff']
    ))

    listing_html, last_league = "", ""
    league_counter = 0

    for m in day_matches:
        league = m.get('league', 'Other Football')
        if league != last_league:
            if last_league != "":
                league_counter += 1
                if league_counter % 3 == 0:
                    listing_html += ADS_CODE
            listing_html += f'<div class="league-header">{league}</div>'
            last_league = league
        
        m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        m_slug = slugify(m['fixture'])
        m_date_folder = m_dt_local.strftime('%Y%m%d')
        m_url = f"{DOMAIN}/match/{m_slug}/{m_date_folder}/"
        
        listing_html += f'''
        <a href="{m_url}" class="match-row flex items-center p-4 bg-white group border-b border-slate-100">
            <div class="time-box" style="min-width: 95px; text-align: center; border-right: 1px solid #edf2f7; margin-right: 10px;">
                <div class="text-[10px] uppercase text-slate-400 font-bold auto-date" data-unix="{m['kickoff']}">{m_dt_local.strftime('%d %b')}</div>
                <div class="font-bold text-blue-600 text-sm auto-time" data-unix="{m['kickoff']}">{m_dt_local.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1">
                <span class="text-slate-800 font-semibold text-sm md:text-base">{m['fixture']}</span>
            </div>
        </a>'''

    if listing_html != "": listing_html += ADS_CODE

    with open(fname, "w", encoding='utf-8') as df:
        output = templates['home'].replace("{{MATCH_LISTING}}", listing_html).replace("{{WEEKLY_MENU}}", page_specific_menu)
        output = output.replace("{{DOMAIN}}", DOMAIN).replace("{{SELECTED_DATE}}", day.strftime("%A, %b %d, %Y"))
        output = output.replace("{{PAGE_TITLE}}", f"TV Channels For {day.strftime('%A, %b %d, %Y')}")
        df.write(output)

# --- 5. CHANNEL PAGES ---
for ch_name, matches in channels_data.items():
    c_slug = slugify(ch_name)
    c_dir = f"channel/{c_slug}"
    os.makedirs(c_dir, exist_ok=True)
    sitemap_urls.append(f"{DOMAIN}/{c_dir}/")
    
    channel_menu = f'{MENU_CSS}<div class="weekly-menu-container">'
    for j in range(7):
        m_day = MENU_START_DATE + timedelta(days=j)
        m_fname = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        channel_menu += f'<a href="{DOMAIN}/{m_fname}" class="date-btn"><div>{m_day.strftime("%a")}</div><b>{m_day.strftime("%b %d")}</b></a>'
    channel_menu += '</div>'

    c_listing = ""
    matches.sort(key=lambda x: x['m']['kickoff'])
    for item in matches: 
        m, dt, m_league = item['m'], item['dt'], item['league']
        c_listing += f'''
        <a href="{DOMAIN}/match/{slugify(m['fixture'])}/{dt.strftime('%Y%m%d')}/" class="match-row flex items-center p-4 bg-white border-b border-slate-100 group">
            <div class="time-box" style="min-width: 95px; text-align: center; border-right: 1px solid #edf2f7; margin-right: 10px;">
                <div class="text-[10px] uppercase text-slate-400 font-bold auto-date" data-unix="{m['kickoff']}">{dt.strftime('%d %b')}</div>
                <div class="font-bold text-blue-600 text-sm auto-time" data-unix="{m['kickoff']}">{dt.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1">
                <span class="text-slate-800 font-semibold text-sm md:text-base">{m['fixture']}</span>
                <div class="text-[11px] text-blue-500 font-medium uppercase mt-0.5">{m_league}</div>
            </div>
        </a>'''
        
    with open(f"{c_dir}/index.html", "w", encoding='utf-8') as cf:
        cf.write(templates['channel'].replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", c_listing).replace("{{DOMAIN}}", DOMAIN).replace("{{WEEKLY_MENU}}", channel_menu))

# --- 6. SITEMAP ---
sitemap_content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in sorted(list(set(sitemap_urls))):
    sitemap_content += f'<url><loc>{url}</loc><lastmod>{NOW.strftime("%Y-%m-%d")}</lastmod></url>'
sitemap_content += '</urlset>'
with open("sitemap.xml", "w", encoding='utf-8') as sm: sm.write(sitemap_content)

print("Success! All matches from JSON generated and included in sitemap, regardless of menu dates.")
