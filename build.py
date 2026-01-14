import json, os, re, glob 
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
LOCAL_OFFSET = timezone(timedelta(hours=5)) 

NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date() 

MENU_START_DATE = TODAY_DATE - timedelta(days=3)
MENU_END_DATE = TODAY_DATE + timedelta(days=3)

TOP_LEAGUE_IDS = [17, 35, 23, 7, 8, 34, 679]

MENU_CSS = '''
<style>
    .weekly-menu-container { display: flex; width: 100%; gap: 4px; padding: 10px 5px; box-sizing: border-box; justify-content: space-between; overflow-x: auto; }
    .date-btn { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 8px 2px; text-decoration: none; border-radius: 6px; background: #fff; border: 1px solid #e2e8f0; min-width: 60px; transition: all 0.2s; }
    .date-btn div { font-size: 9px; text-transform: uppercase; color: #64748b; font-weight: bold; }
    .date-btn b { font-size: 10px; color: #1e293b; white-space: nowrap; }
    .date-btn.active { background: #2563eb; border-color: #2563eb; }
    .date-btn.active div, .date-btn.active b { color: #fff; }
    
    .sofa-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; margin-bottom: 20px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .sofa-header { background: #f1f5f9; padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-weight: 800; color: #334155; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; border-bottom: 1px solid #f8fafc; font-size: 14px; }
    .stat-label { color: #64748b; font-weight: 600; font-size: 12px; text-transform: uppercase; text-align: center; flex: 1; }
    .stat-value { font-weight: 700; color: #1e293b; width: 40px; }
    
    .lineup-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-top: 1px solid #f1f5f9; }
    .team-col { padding: 15px; }
    .team-col:first-child { border-right: 1px solid #f1f5f9; }
    .team-col b { display: block; margin-bottom: 10px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
    .team-col ul { list-style: none; padding: 0; margin: 0; }
    .team-col li { font-size: 13px; padding: 6px 0; color: #475569; border-bottom: 1px dashed #f1f5f9; }
    
    .form-container { display: flex; gap: 6px; }
    .form-circle { width: 22px; height: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: 800; box-shadow: inset 0 -2px 0 rgba(0,0,0,0.1); }
    
    @media (max-width: 480px) { .date-btn b { font-size: 8px; } .date-btn div { font-size: 7px; } }
</style>
'''

def slugify(t): 
    return re.sub(r'[^a-z0-9]+', '-', str(t).lower()).strip('-')

def get_team_names(fixture):
    """Splits 'Arsenal vs Chelsea' into ['Arsenal', 'Chelsea']"""
    if " vs " in fixture:
        return [t.strip() for t in fixture.split(" vs ")]
    elif " - " in fixture:
        return [t.strip() for t in fixture.split(" - ")]
    return ["Home", "Away"]

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
    if not form_list or not isinstance(form_list, list): return '<span class="text-gray-400">N/A</span>'
    html = '<div class="form-container">'
    for res in form_list:
        bg = "#10b981" if res == "W" else "#ef4444" if res == "L" else "#64748b"
        html += f'<span class="form-circle" style="background:{bg}">{res}</span>'
    html += '</div>'
    return html

def build_lineups_html(data, teams):
    if not isinstance(data, dict) or 'home' not in data: 
        return "<div class='p-4 text-gray-400 italic'>Lineups not confirmed yet</div>"
    h_players = "".join([f"<li>{p['player']['name']}</li>" for p in data['home'].get('players', [])[:11]])
    a_players = "".join([f"<li>{p['player']['name']}</li>" for p in data['away'].get('players', [])[:11]])
    return f'''<div class="lineup-grid">
        <div class="team-col"><b class="text-blue-600">{teams[0]} XI</b><ul>{h_players}</ul></div>
        <div class="team-col"><b class="text-red-600">{teams[1]} XI</b><ul>{a_players}</ul></div>
    </div>'''

def build_stats_html(data):
    if not isinstance(data, dict) or 'statistics' not in data: 
        return "<div class='p-4 text-gray-400 italic'>Stats available during live match</div>"
    rows = ""
    try:
        period = next((p for p in data['statistics'] if p['period'] == 'ALL'), data['statistics'][0])
        for group in period['groups']:
            for item in group['statisticsItems']:
                rows += f'''<div class="stat-row">
                    <span class="stat-value" style="text-align:left;">{item['home']}</span>
                    <span class="stat-label">{item['name']}</span>
                    <span class="stat-value" style="text-align:right;">{item['away']}</span>
                </div>'''
        return rows
    except: return "<div class='p-4 text-gray-400 italic'>Stats format error</div>"

def build_h2h_html(data, teams):
    if not isinstance(data, dict): return "<div class='p-4 text-gray-400 italic text-center'>No H2H history available</div>"
    duel = data.get('teamDuel', data)
    if not isinstance(duel, dict): return "<div class='p-4 text-gray-400 italic text-center'>No H2H history available</div>"
    return f'''
        <div class="stat-row">
            <span style="font-weight:700; color:#2563eb;">{duel.get('homeWins',0)} <small>{teams[0]}</small></span>
            <span class="stat-label">Wins Comparison</span>
            <span style="font-weight:700; color:#dc2626; text-align:right;">{duel.get('awayWins',0)} <small>{teams[1]}</small></span>
        </div>
        <div class="stat-row" style="justify-content: center; background: #f8fafc;">
            <span class="stat-label" style="color:#1e293b">Total Draws: <b>{duel.get('draws',0)}</b></span>
        </div>'''

# --- 1. LOAD TEMPLATES ---
templates = {}
for name in ['home', 'match', 'channel']:
    with open(f'{name}_template.html', 'r', encoding='utf-8') as f:
        templates[name] = f.read()

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
    teams = get_team_names(m['fixture'])
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

    # Sofa Data
    lineup_raw = get_sofa_data("lineups", m_date_folder, mid)
    stats_raw = get_sofa_data("statistics", m_date_folder, mid)
    h2h_raw = get_sofa_data("h2h", m_date_folder, mid)
    odds_raw = get_sofa_data("odds", m_date_folder, mid)
    form_raw = get_sofa_data("form", m_date_folder, mid)

    # Probability
    odds_html = "<div class='p-4 text-center text-gray-400 italic'>Win Probability N/A</div>"
    if isinstance(odds_raw, dict):
        h_prob = odds_raw.get('home', {}).get('expected', '-') if odds_raw.get('home') else '-'
        a_prob = odds_raw.get('away', {}).get('expected', '-') if odds_raw.get('away') else '-'
        odds_html = f'''<div class="flex justify-around p-5 items-center">
            <div class="text-center"><div style="font-size:10px; color:#64748b; font-weight:700; margin-bottom:4px;">{teams[0].upper()}</div><div style="font-size:24px; font-weight:900; color:#2563eb;">{h_prob}%</div></div>
            <div style="height:40px; width:1px; background:#e2e8f0;"></div>
            <div class="text-center"><div style="font-size:10px; color:#64748b; font-weight:700; margin-bottom:4px;">{teams[1].upper()}</div><div style="font-size:24px; font-weight:900; color:#dc2626;">{a_prob}%</div></div>
        </div>'''

    # Form
    form_html = ""
    if isinstance(form_raw, dict):
        h_f = form_raw.get('homeTeam', {}).get('form')
        a_f = form_raw.get('awayTeam', {}).get('form')
        if h_f or a_f:
            form_html = f'''<div class="sofa-card"><div class="sofa-header">Recent Form</div>
                <div class="stat-row"><span>{teams[0]}</span>{format_form_circles(h_f)}</div>
                <div class="stat-row"><span>{teams[1]}</span>{format_form_circles(a_f)}</div>
            </div>'''

    m_path = f"match/{m_slug}/{m_date_folder}"
    os.makedirs(m_path, exist_ok=True)
    
    rows = ""
    for c in m.get('tv_channels', []):
        pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="ch-pill" style="display:inline-block;background:#f1f5f9;color:#2563eb;padding:4px 10px;border-radius:6px;margin:2px;text-decoration:none;font-size:12px;font-weight:700;border:1px solid #e2e8f0;">{ch}</a>' for ch in c['channels']])
        rows += f'<div style="display:flex;padding:12px;border-bottom:1px solid #edf2f7;background:#fff;align-items:center;"><div style="flex:0 0 100px;font-weight:800;color:#64748b;font-size:11px;text-transform:uppercase;">{c["country"]}</div><div style="flex:1;">{pills}</div></div>'

    sofa_blocks = f'''
    <div class="sofa-card"><div class="sofa-header">Win Probability</div>{odds_html}</div>
    {form_html}
    <div class="sofa-card"><div class="sofa-header">Confirmed Lineups</div>{build_lineups_html(lineup_raw, teams)}</div>
    <div class="sofa-card"><div class="sofa-header">Match Statistics</div>{build_stats_html(stats_raw)}</div>
    <div class="sofa-card"><div class="sofa-header">Head to Head</div>{build_h2h_html(h2h_raw, teams)}</div>
    '''

    with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
        m_html = templates['match'].replace("{{FIXTURE}}", m['fixture']).replace("{{DOMAIN}}", DOMAIN)
        m_html = m_html.replace("{{BROADCAST_ROWS}}", rows).replace("{{LEAGUE}}", league)
        m_html = m_html.replace("{{SOFA_DATA}}", sofa_blocks)
        m_html = m_html.replace("{{LOCAL_DATE}}", m_dt_local.strftime("%d %b %Y"))
        m_html = m_html.replace("{{LOCAL_TIME}}", m_dt_local.strftime("%H:%M"))
        m_html = m_html.replace("{{UNIX}}", str(m['kickoff'])).replace("{{VENUE}}", m.get('venue', 'TBA')) 
        mf.write(m_html)

# --- 4. DAILY LISTING PAGES ---
for i in range(7):
    day = MENU_START_DATE + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    
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
        listing_html += f'''<a href="{m_url}" class="match-row" style="display:flex;align-items:center;padding:14px;background:#fff;border-bottom:1px solid #f1f5f9;text-decoration:none;">
            <div style="min-width:70px;text-align:center;border-right:1px solid #eee;margin-right:15px;">
                <div style="font-size:10px;color:#94a3b8;font-weight:bold;">{m_dt.strftime('%d %b')}</div>
                <div style="font-weight:900;color:#2563eb;">{m_dt.strftime('%H:%M')}</div>
            </div>
            <div style="color:#1e293b;font-weight:700;font-size:15px;">{m['fixture']}</div>
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
    c_listing = ""
    matches.sort(key=lambda x: x['m']['kickoff'])
    for item in matches: 
        m, dt, m_league = item['m'], item['dt'], item['league']
        c_listing += f'''<a href="{DOMAIN}/match/{slugify(m['fixture'])}/{dt.strftime('%Y%m%d')}/" class="match-row" style="display:flex;align-items:center;padding:14px;background:#fff;border-bottom:1px solid #f1f5f9;text-decoration:none;">
            <div style="min-width:70px;text-align:center;border-right:1px solid #eee;margin-right:15px;">
                <div style="font-size:10px;color:#94a3b8;font-weight:bold;">{dt.strftime('%d %b')}</div>
                <div style="font-weight:900;color:#2563eb;">{dt.strftime('%H:%M')}</div>
            </div>
            <div><div style="color:#1e293b;font-weight:700;font-size:15px;">{m['fixture']}</div><div style="font-size:10px;color:#6366f1;font-weight:600;">{m_league}</div></div>
        </a>'''
    with open(f"{c_dir}/index.html", "w", encoding='utf-8') as cf:
        cf.write(templates['channel'].replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", c_listing).replace("{{DOMAIN}}", DOMAIN))

# --- 6. SITEMAP ---
sitemap_content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in sorted(list(set(sitemap_urls))):
    sitemap_content += f'<url><loc>{url}</loc><lastmod>{NOW.strftime("%Y-%m-%d")}</lastmod></url>'
sitemap_content += '</urlset>'
with open("sitemap.xml", "w", encoding='utf-8') as sm: sm.write(sitemap_content)

print("Build Successful: Visuals Updated.")
