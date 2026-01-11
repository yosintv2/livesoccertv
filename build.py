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

    # FIXED: Responsive Date Menu with horizontal scroll on mobile
    current_page_menu = '<div style="display: flex; overflow-x: auto; gap: 8px; padding: 10px 0; -webkit-overflow-scrolling: touch; scrollbar-width: none;">'
    for j in range(7):
        m_day = START_WEEK + timedelta(days=j)
        m_fname = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        # Logic for active state
        active_style = "background:#2563eb; color:#fff; border-color:#2563eb;" if m_day == day else "background:#fff; color:#64748b; border-color:#e2e8f0;"
        
        current_page_menu += f'''
        <a href="{DOMAIN}/{m_fname}" style="text-decoration:none; flex:0 0 auto; min-width:80px; padding:8px; border:1px solid; border-radius:8px; text-align:center; transition: all 0.2s; {active_style}">
            <div style="font-size:10px; text-transform:uppercase; font-weight:bold;">{m_day.strftime("%a")}</div>
            <div style="font-size:14px; font-weight:800;">{m_day.strftime("%b %d")}</div>
        </a>'''
    current_page_menu += '</div>'

    day_matches = []
    for m in all_matches:
        m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        if m_dt_local.date() == day:
            day_matches.append(m)

    # Sort: Top Leagues, then Name, then Time
    day_matches.sort(key=lambda x: (
        x.get('league_id') not in TOP_LEAGUE_IDS, 
        x.get('league', 'Other Football'), 
        x['kickoff']
    ))

    listing_html, last_league = "", ""
    for m in day_matches:
        league = m.get('league', 'Other Football')
        
        if league != last_league:
            listing_html += f'''<div style="background:#f8fafc; padding:10px 15px; font-size:12px; font-weight:bold; color:#64748b; text-transform:uppercase; border-bottom:1px solid #e2e8f0; border-top:1px solid #e2e8f0;">{league}</div>'''
            last_league = league
        
        m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        m_slug, m_date_folder = slugify(m['fixture']), m_dt_local.strftime('%Y%m%d')
        m_url = f"{DOMAIN}/match/{m_slug}/{m_date_folder}/"
        sitemap_urls.append(m_url)
        
        listing_html += f'''
        <a href="{m_url}" style="display:flex; align-items:center; padding:15px; background:#fff; border-bottom:1px solid #f1f5f9; text-decoration:none; color:inherit;">
            <div style="min-width:85px; text-align:center; border-right:1px solid #f1f5f9; margin-right:15px; padding-right:5px;">
                <div class="auto-date" data-unix="{m['kickoff']}" style="font-size:10px; color:#94a3b8; font-weight:bold;">{m_dt_local.strftime('%d %b')}</div>
                <div class="auto-time" data-unix="{m['kickoff']}" style="font-size:16px; color:#2563eb; font-weight:800;">{m_dt_local.strftime('%H:%M')}</div>
            </div>
            <div style="font-weight:600; font-size:15px; color:#1e293b; flex:1;">{m['fixture']}</div>
        </a>'''

        # --- 4. MATCH PAGES (BROADCAST TABLE) ---
        m_path = f"match/{m_slug}/{m_date_folder}"
        os.makedirs(m_path, exist_ok=True)
        venue_val = m.get('venue') or m.get('stadium') or "To Be Announced"
        
        rows = ""
        for c in m.get('tv_channels', []):
            # Format channel links as modern "pills" for better mobile tapping
            channel_pills = "".join([
                f'<a href="{DOMAIN}/channel/{slugify(ch)}/" style="display:inline-block; background:#eff6ff; color:#2563eb; padding:4px 10px; border-radius:6px; font-size:11px; font-weight:700; margin:3px; text-decoration:none; border:1px solid #dbeafe;">{ch}</a>' 
                for ch in c['channels']
            ])
            
            for ch in c['channels']:
                if ch not in channels_data: channels_data[ch] = []
                if not any(x['m']['match_id'] == m['match_id'] for x in channels_data[ch]):
                    channels_data[ch].append({'m': m, 'dt': m_dt_local, 'league': league})
            
            # Responsive Table Row: Country on left, Channels on right (wraps on mobile)
            rows += f'''
            <div style="display:flex; flex-wrap:wrap; border-bottom:1px solid #edf2f7; background:#fff;">
                <div style="flex:0 0 120px; background:#f8fafc; padding:12px; font-size:12px; font-weight:800; color:#475569; display:flex; align-items:center; border-right:1px solid #edf2f7; min-width:100px;">
                    {c["country"]}
                </div>
                <div style="flex:1; padding:10px; min-width:200px; display:flex; flex-wrap:wrap; align-items:center;">
                    {channel_pills}
                </div>
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

    # Home/Date Page output
    with open(fname, "w", encoding='utf-8') as df:
        output = templates['home'].replace("{{MATCH_LISTING}}", listing_html).replace("{{WEEKLY_MENU}}", current_page_menu)
        output = output.replace("{{DOMAIN}}", DOMAIN).replace("{{SELECTED_DATE}}", day.strftime("%A, %b %d, %Y"))
        output = output.replace("{{PAGE_TITLE}}", f"Soccer TV Channels For {day.strftime('%A, %b %d, %Y')}")
        df.write(output)

# --- 5. CHANNEL PAGES ---
for ch_name, matches in channels_data.items():
    c_dir = f"channel/{slugify(ch_name)}"
    os.makedirs(c_dir, exist_ok=True)
    sitemap_urls.append(f"{DOMAIN}/{c_dir}/")

    c_listing = ""
    matches.sort(key=lambda x: x['m']['kickoff'])
    
    for item in matches:
        m, dt, m_league = item['m'], item['dt'], item['league']
        m_slug, m_date_folder = slugify(m['fixture']), dt.strftime('%Y%m%d')
        
        c_listing += f'''
        <a href="{DOMAIN}/match/{m_slug}/{m_date_folder}/" style="display:flex; align-items:center; padding:15px; background:#fff; border-bottom:1px solid #f1f5f9; text-decoration:none; color:inherit;">
            <div style="min-width:85px; text-align:center; border-right:1px solid #f1f5f9; margin-right:15px;">
                <div class="auto-date" data-unix="{m['kickoff']}" style="font-size:10px; color:#94a3b8; font-weight:bold;">{dt.strftime('%d %b')}</div>
                <div class="auto-time" data-unix="{m['kickoff']}" style="font-size:16px; color:#2563eb; font-weight:800;">{dt.strftime('%H:%M')}</div>
            </div>
            <div style="flex:1;">
                <div style="font-weight:600; font-size:15px; color:#1e293b;">{m['fixture']}</div>
                <div style="font-size:10px; color:#94a3b8; text-transform:uppercase; font-weight:bold; margin-top:2px;">{m_league}</div>
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
