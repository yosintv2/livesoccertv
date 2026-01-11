import json, os, re, glob
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
LOCAL_OFFSET = timezone(timedelta(hours=5)) 

NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date()

# Friday to Thursday Logic
days_since_friday = (TODAY_DATE.weekday() - 4) % 7
START_WEEK = TODAY_DATE - timedelta(days=days_since_friday)

TOP_LEAGUE_IDS = [7, 35, 23, 17]

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
    if fname != "index.html": sitemap_urls.append(f"{DOMAIN}/{fname}")

    # IMPROVED: Responsive Date Menu with flex-nowrap and overflow-x-auto
    current_page_menu = '<div class="flex overflow-x-auto pb-2 gap-2 no-scrollbar md:justify-center">'
    for j in range(7):
        m_day = START_WEEK + timedelta(days=j)
        m_fname = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        active_class = "border-blue-600 bg-blue-50 text-blue-600" if m_day == day else "border-gray-200 text-gray-500"
        current_page_menu += f'''
        <a href="{DOMAIN}/{m_fname}" class="flex-none min-w-[70px] md:min-w-[100px] p-2 border-2 rounded-lg text-center transition-all {active_class}">
            <div class="text-[10px] uppercase font-bold">{m_day.strftime("%a")}</div>
            <div class="text-sm font-black">{m_day.strftime("%b %d")}</div>
        </a>'''
    current_page_menu += '</div>'

    day_matches = []
    for m in all_matches:
        m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        if m_dt_local.date() == day:
            day_matches.append(m)

    day_matches.sort(key=lambda x: (x.get('league_id') not in TOP_LEAGUE_IDS, x.get('league', 'Other Football'), x['kickoff']))

    listing_html, last_league = "", ""
    for m in day_matches:
        league = m.get('league', 'Other Football')
        if league != last_league:
            listing_html += f'<div class="bg-slate-100 p-2 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider border-y">{league}</div>'
            last_league = league
        
        m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        m_slug = slugify(m['fixture'])
        m_date_folder = m_dt_local.strftime('%Y%m%d')
        m_url = f"{DOMAIN}/match/{m_slug}/{m_date_folder}/"
        sitemap_urls.append(m_url)
        
        listing_html += f'''
        <a href="{m_url}" class="flex items-center p-4 bg-white border-b hover:bg-gray-50 transition-colors">
            <div class="w-20 md:w-24 text-center border-r border-gray-100 mr-4">
                <div class="text-[10px] text-gray-400 font-bold auto-date" data-unix="{m['kickoff']}">{m_dt_local.strftime('%d %b')}</div>
                <div class="text-base font-bold text-blue-600 auto-time" data-unix="{m['kickoff']}">{m_dt_local.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1 font-semibold text-gray-800 text-sm md:text-base">{m['fixture']}</div>
        </a>'''

        # --- 4. MATCH PAGES ---
        m_path = f"match/{m_slug}/{m_date_folder}"
        os.makedirs(m_path, exist_ok=True)
        venue_val = m.get('venue') or m.get('stadium') or "To Be Announced"
        
        # IMPROVED: Table-like structure for channels
        rows = ""
        for c in m.get('tv_channels', []):
            pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="inline-block bg-blue-50 text-blue-700 px-2 py-1 rounded text-[11px] font-bold m-0.5 hover:bg-blue-100 transition-colors">{ch}</a>' for ch in c['channels']])
            for ch in c['channels']:
                if ch not in channels_data: channels_data[ch] = []
                if not any(x['m']['match_id'] == m['match_id'] for x in channels_data[ch]):
                    channels_data[ch].append({'m': m, 'dt': m_dt_local, 'league': league})
            
            rows += f'''
            <div class="grid grid-cols-3 border-b items-center bg-white">
                <div class="col-span-1 p-3 text-sm font-bold text-gray-600 border-r bg-gray-50">{c["country"]}</div>
                <div class="col-span-2 p-3">{pills}</div>
            </div>'''

        with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
            m_html = templates['match'].replace("{{FIXTURE}}", m['fixture']).replace("{{DOMAIN}}", DOMAIN)
            m_html = m_html.replace("{{BROADCAST_ROWS}}", rows).replace("{{LEAGUE}}", league)
            plain_date, plain_time = m_dt_local.strftime("%d %b %Y"), m_dt_local.strftime("%H:%M")
            m_html = m_html.replace("{{DATE}}", plain_date).replace("{{TIME}}", plain_time)
            m_html = m_html.replace("{{LOCAL_DATE}}", f'<span class="auto-date" data-unix="{m["kickoff"]}">{plain_date}</span>')
            m_html = m_html.replace("{{LOCAL_TIME}}", f'<span class="auto-time" data-unix="{m["kickoff"]}">{plain_time}</span>')
            m_html = m_html.replace("{{UNIX}}", str(m['kickoff'])).replace("{{VENUE}}", venue_val) 
            mf.write(m_html)

    with open(fname, "w", encoding='utf-8') as df:
        output = templates['home'].replace("{{MATCH_LISTING}}", listing_html).replace("{{WEEKLY_MENU}}", current_page_menu)
        output = output.replace("{{DOMAIN}}", DOMAIN).replace("{{SELECTED_DATE}}", day.strftime("%A, %b %d, %Y"))
        output = output.replace("{{PAGE_TITLE}}", f"Soccer TV Channels For {day.strftime('%A, %b %d, %Y')}")
        df.write(output)

# --- 5. CHANNEL PAGES ---
for ch_name, matches in channels_data.items():
    c_slug = slugify(ch_name)
    c_dir = f"channel/{c_slug}"
    os.makedirs(c_dir, exist_ok=True)
    sitemap_urls.append(f"{DOMAIN}/{c_dir}/")
    c_listing = ""
    matches.sort(key=lambda x: x['m']['kickoff'])
    for item in matches:
        m, dt, m_league = item['m'], item['dt'], item['league']
        m_slug, m_date_folder = slugify(m['fixture']), dt.strftime('%Y%m%d')
        c_listing += f'''
        <a href="{DOMAIN}/match/{m_slug}/{m_date_folder}/" class="flex items-center p-4 bg-white border-b hover:bg-gray-50">
            <div class="w-20 md:w-24 text-center border-r border-gray-100 mr-4">
                <div class="text-[10px] text-gray-400 font-bold auto-date" data-unix="{m['kickoff']}">{dt.strftime('%d %b')}</div>
                <div class="text-base font-bold text-blue-600 auto-time" data-unix="{m['kickoff']}">{dt.strftime('%H:%M')}</div>
            </div>
            <div class="flex-1">
                <div class="font-semibold text-gray-800 text-sm md:text-base leading-tight">{m['fixture']}</div>
                <div class="text-[10px] text-blue-500 font-bold uppercase mt-1">{m_league}</div>
            </div>
        </a>'''

    with open(f"{c_dir}/index.html", "w", encoding='utf-8') as cf:
        c_html = templates['channel'].replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", c_listing)
        c_html = c_html.replace("{{DOMAIN}}", DOMAIN).replace("{{WEEKLY_MENU}}", current_page_menu)
        cf.write(c_html)

# --- 6. SITEMAP ---
sitemap_content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in list(set(sitemap_urls)):
    sitemap_content += f'<url><loc>{url}</loc><lastmod>{NOW.strftime("%Y-%m-%d")}</lastmod></url>'
sitemap_content += '</urlset>'
with open("sitemap.xml", "w", encoding='utf-8') as sm: sm.write(sitemap_content)
print(f"Success! {len(sitemap_urls)} URLs generated.")
