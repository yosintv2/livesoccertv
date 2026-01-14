import json, os, re, glob 
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
LOCAL_OFFSET = timezone(timedelta(hours=5)) 

NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date() 

# CENTER LOGIC: To make Today the 4th item, we start the menu 3 days ago
MENU_START_DATE = TODAY_DATE - timedelta(days=3)
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
    .weekly-menu-container { display: flex; width: 100%; gap: 4px; padding: 10px 5px; box-sizing: border-box; justify-content: space-between; overflow-x: auto; }
    .date-btn { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 8px 2px; text-decoration: none; border-radius: 6px; background: #fff; border: 1px solid #e2e8f0; min-width: 60px; transition: all 0.2s; }
    .date-btn div { font-size: 9px; text-transform: uppercase; color: #64748b; font-weight: bold; }
    .date-btn b { font-size: 10px; color: #1e293b; white-space: nowrap; }
    .date-btn.active { background: #2563eb; border-color: #2563eb; }
    .date-btn.active div, .date-btn.active b { color: #fff; }
    .sofa-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 15px; overflow: hidden; }
    .sofa-header { background: #f8fafc; padding: 10px 15px; border-bottom: 1px solid #e2e8f0; font-weight: bold; color: #1e293b; font-size: 14px; text-transform: uppercase; }
    .stat-row { display: flex; justify-content: space-between; padding: 8px 15px; border-bottom: 1px solid #f1f5f9; font-size: 13px; }
    .stat-label { color: #64748b; font-weight: 500; }
    .lineup-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 10px; }
    .team-col ul { list-style: none; padding: 0; margin: 0; }
    .team-col li { font-size: 13px; padding: 4px 0; border-bottom: 1px solid #f1f5f9; }
    .form-circle { width: 18px; height: 18px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 10px; font-weight: bold; margin-left: 2px; }
    @media (max-width: 480px) { .date-btn b { font-size: 8px; } .date-btn div { font-size: 7px; } }
</style>
'''

def slugify(t): 
    return re.sub(r'[^a-z0-9]+', '-', str(t).lower()).strip('-')

# --- DATA HELPERS ---
def get_sofa_data(data_type, date_str, match_id):
    path = f"data/{data_type}/{date_str}.json"
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data.get(str(match_id))
            except: return None
    return None

def format_form_circles(form_list):
    if not form_list: return ""
    html = '<div style="display: flex;">'
    for res in form_list:
        bg = "#22c55e" if res == "W" else "#ef4444" if res == "L" else "#94a3b8"
        html += f'<span class="form-circle" style="background:{bg}">{res}</span>'
    html += '</div>'
    return html

def build_lineups_html(data):
    if not data or 'home' not in data: return "<div class='p-4 text-gray-400 italic'>Lineups not confirmed yet</div>"
    h_players = "".join([f"<li>{p['player']['name']}</li>" for p in data['home'].get('players', [])[:11]])
    a_players = "".join([f"<li>{p['player']['name']}</li>" for p in data['away'].get('players', [])[:11]])
    return f'''<div class="lineup-grid">
        <div class="team-col"><b class="text-blue-600">HOME XI</b><ul>{h_players}</ul></div>
        <div class="team-col"><b class="text-red-600">AWAY XI</b><ul>{a_players}</ul></div>
    </div>'''

def build_stats_html(data):
    if not data or 'statistics' not in data: return "<div class='p-4 text-gray-400 italic'>Stats available during live match</div>"
    rows = ""
    period = next((p for p in data['statistics'] if p['period'] == 'ALL'), data['statistics'][0])
    for group in period['groups']:
        for item in group['statisticsItems']:
            rows += f'''<div class="stat-row"><span>{item['home']}</span><span class="stat-label">{item['name']}</span><span>{item['away']}</span></div>'''
    return rows

def build_h2h_html(data):
    if not data: return "<div class='p-4 text-gray-400 italic'>No H2H history available</div>"
    # Format matches the 'teamDuel' structure: {"teamDuel": {"homeWins": 6...}}
    duel = data.get('teamDuel', data)
    return f'''<div class="stat-row"><span class="text-blue-600 font-bold">{duel.get('homeWins',0)} Wins</span><span class="stat-label">Head to Head</span><span class="text-red-600 font-bold">{duel.get('awayWins',0)} Wins</span></div>
               <div class="stat-row" style="justify-content: center;"><span class="stat-label">Draws: {duel.get('draws',0)}</span></div>'''

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
for f in sorted(glob.glob("date/*.json")):
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

# --- 3. PRE-PROCESS ALL MATCHES ---
for m in all_matches:
    m_dt_local = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
    m_slug = slugify(m['fixture'])
    m_date_folder = m_dt_local.strftime('%Y%m%d')
    m_url = f"{DOMAIN}/match/{m_slug}/{m_date_folder}/"
    sitemap_urls.append(m_url)
    league = m.get('league', 'Other Football')
    mid = m['match_id']

    for c in m.get('tv_channels', []):
        for ch in c['channels']:
            if ch not in channels_data: channels_data[ch] = []
            if int(m['kickoff']) > (NOW.timestamp() - 86400):
                if not any(x['m']['match_id'] == mid for x in channels_data[ch]):
                    channels_data[ch].append({'m': m, 'dt': m_dt_local, 'league': league})

    # --- SOFA DATA INTEGRATION ---
    lineup_raw = get_sofa_data("lineups", m_date_folder, mid)
    stats_raw = get_sofa_data("statistics", m_date_folder, mid)
    h2h_raw = get_sofa_data("h2h", m_date_folder, mid)
    odds_raw = get_sofa_data("odds", m_date_folder, mid)
    form_raw = get_sofa_data("form", m_date_folder, mid)

    # Calculate Winning Probability from your Format: {"home":{"expected":88...}}
    odds_html = "<div class='p-4 text-center text-gray-400'>Odds not available</div>"
    if odds_raw:
        h_prob = odds_raw.get('home', {}).get('expected', '-')
        a_prob = odds_raw.get('away', {}).get('expected', '-') if odds_raw.get('away') else '-'
        odds_html = f'''<div class="flex justify-around p-4 items-center">
            <div class="text-center"><div class="text-[10px] text-gray-400 uppercase font-bold">Home Prob.</div><div class="text-xl font-black text-blue-600">{h_prob}%</div></div>
            <div class="h-8 w-[1px] bg-gray-200"></div>
            <div class="text-center"><div class="text-[10px] text-gray-400 uppercase font-bold">Away Prob.</div><div class="text-xl font-black text-red-600">{a_prob}%</div></div>
        </div>'''

    # Form Block
    form_html = ""
    if form_raw:
        h_form = format_form_circles(form_raw.get('homeTeam', {}).get('form'))
        a_form = format_form_circles(form_raw.get('awayTeam', {}).get('form'))
        form_html = f'''<div class="sofa-card"><div class="sofa-header">Recent Form</div>
            <div class="stat-row"><span>Home Team</span>{h_form}</div>
            <div class="stat-row"><span>Away Team</span>{a_form}</div>
        </div>'''

    # --- GENERATE INDIVIDUAL MATCH PAGE ---
    m_path = f"match/{m_slug}/{m_date_folder}"
    os.makedirs(m_path, exist_ok=True)
    venue_val = m.get('venue') or m.get('stadium') or "To Be Announced"
    
    rows = ""
    for c in m.get('tv_channels', []):
        pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="ch-pill" style="display:inline-block;background:#f1f5f9;color:#2563eb;padding:2px 8px;border-radius:4px;margin:2px;text-decoration:none;font-weight:600;border:1px solid #e2e8f0;">{ch}</a>' for ch in c['channels']])
        rows += f'<div style="display:flex;padding:12px;border-bottom:1px solid #edf2f7;background:#fff;"><div style="flex:0 0 100px;font-weight:800;color:#475569;font-size:13px;">{c["country"]}</div><div style="flex:1;">{pills}</div></div>'

    # Sofa Data Blocks
    sofa_blocks = f'''
    <div class="sofa-card"><div class="sofa-header">Winning Probability</div>{odds_html}</div>
    {form_html}
    <div class="sofa-card"><div class="sofa-header">Starting Lineups</div>{build_lineups_html(lineup_raw)}</div>
    <div class="sofa-card"><div class="sofa-header">Match Statistics</div>{build_stats_html(stats_raw)}</div>
    <div class="sofa-card"><div class="sofa-header">Head to Head</div>{build_h2h_html(h2h_raw)}</div>
    '''

    with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
        m_html = templates['match'].replace("{{FIXTURE}}", m['fixture']).replace("{{DOMAIN}}", DOMAIN)
        m_html = m_html.replace("{{BROADCAST_ROWS}}", rows).replace("{{LEAGUE}}", league)
        m_html = m_html.replace("{{SOFA_DATA}}", sofa_blocks)
        m_html = m_html.replace("{{LOCAL_DATE}}", f'<span class="auto-date" data-unix="{m["kickoff"]}">{m_dt_local.strftime("%d %b %Y")}</span>')
        m_html = m_html.replace("{{LOCAL_TIME}}", f'<span class="auto-time" data-unix="{m["kickoff"]}">{m_dt_local.strftime("%H:%M")}</span>')
        m_html = m_html.replace("{{UNIX}}", str(m['kickoff'])).replace("{{VENUE}}", venue_val) 
        mf.write(m_html)

# --- 4. DAILY LISTING PAGES ---
for i in range(7):
    day = MENU_START_DATE + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    if fname != "index.html": sitemap_urls.append(f"{DOMAIN}/{fname}")

    page_specific_menu = f'{MENU_CSS}<div class="weekly-menu-container">'
    for j in range(7):
        m_day = MENU_START_DATE + timedelta(days=j)
        m_fname = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        active_class = "active" if m_day == day else ""
        page_specific_menu += f'<a href="{DOMAIN}/{m_fname}" class="date-btn {active_class}"><div>{m_day.strftime("%a")}</div><b>{m_day.strftime("%b %d")}</b></a>'
    page_specific_menu += '</div>'

    day_matches = [m for m in all_matches if datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET).date() == day]
    day_matches.sort(key=lambda x: (x.get('league_id') not in TOP_LEAGUE_IDS, x.get('league', 'Other Football'), x['kickoff']))

    listing_html, last_league = "", ""
    for m in day_matches:
        league = m.get('league', 'Other Football')
        if league != last_league:
            listing_html += f'<div class="league-header" style="background:#1e293b;color:#fff;padding:8px 15px;font-weight:bold;font-size:12px;text-transform:uppercase;">{league}</div>'
            last_league = league
        
        m_dt = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        m_url = f"{DOMAIN}/match/{slugify(m['fixture'])}/{m_dt.strftime('%Y%m%d')}/"
        listing_html += f'''<a href="{m_url}" class="match-row" style="display:flex;align-items:center;padding:12px;background:#fff;border-bottom:1px solid #f1f5f9;text-decoration:none;">
            <div style="min-width:80px;text-align:center;border-right:1px solid #eee;margin-right:15px;">
                <div style="font-size:10px;color:#94a3b8;font-bold;" data-unix="{m['kickoff']}">{m_dt.strftime('%d %b')}</div>
                <div style="font-weight:bold;color:#2563eb;" data-unix="{m['kickoff']}">{m_dt.strftime('%H:%M')}</div>
            </div>
            <div style="color:#1e293b;font-weight:600;">{m['fixture']}</div>
        </a>'''

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
    
    c_listing = ""
    matches.sort(key=lambda x: x['m']['kickoff'])
    for item in matches: 
        m, dt, m_league = item['m'], item['dt'], item['league']
        c_listing += f'''<a href="{DOMAIN}/match/{slugify(m['fixture'])}/{dt.strftime('%Y%m%d')}/" class="match-row" style="display:flex;align-items:center;padding:12px;background:#fff;border-bottom:1px solid #f1f5f9;text-decoration:none;">
            <div style="min-width:80px;text-align:center;border-right:1px solid #eee;margin-right:15px;">
                <div style="font-size:10px;color:#94a3b8;" data-unix="{m['kickoff']}">{dt.strftime('%d %b')}</div>
                <div style="font-weight:bold;color:#2563eb;" data-unix="{m['kickoff']}">{dt.strftime('%H:%M')}</div>
            </div>
            <div><div style="color:#1e293b;font-weight:600;">{m['fixture']}</div><div style="font-size:10px;color:#6366f1;">{m_league}</div></div>
        </a>'''
        
    with open(f"{c_dir}/index.html", "w", encoding='utf-8') as cf:
        cf.write(templates['channel'].replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", c_listing).replace("{{DOMAIN}}", DOMAIN))

# --- 6. SITEMAP ---
sitemap_content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in sorted(list(set(sitemap_urls))):
    sitemap_content += f'<url><loc>{url}</loc><lastmod>{NOW.strftime("%Y-%m-%d")}</lastmod></url>'
sitemap_content += '</urlset>'
with open("sitemap.xml", "w", encoding='utf-8') as sm: sm.write(sitemap_content)

print("Success! Full code generated with Integrated SofaData.")
