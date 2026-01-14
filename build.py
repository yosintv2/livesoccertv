import json, os, re, glob, html
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
LOCAL_OFFSET = timezone(timedelta(hours=5)) 
NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date() 

# Center Logic: Menu starts 3 days ago and ends 3 days from now
MENU_START_DATE = TODAY_DATE - timedelta(days=3)
MENU_END_DATE = TODAY_DATE + timedelta(days=3)
TOP_LEAGUE_IDS = [17, 35, 23, 7, 8, 34, 679]

ADS_CODE = '''
<div class="ad-container" style="margin: 20px 0; text-align: center;">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5525538810839147" crossorigin="anonymous"></script>
    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-5525538810839147" data-ad-slot="4345862479" data-ad-format="auto" data-full-width-responsive="true"></ins>
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
    .sofa-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; margin-bottom: 20px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .sofa-header { background: #f1f5f9; padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-weight: 800; color: #334155; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid #f8fafc; font-size: 14px; }
    .stat-label { color: #64748b; font-weight: 600; font-size: 12px; text-transform: uppercase; text-align: center; flex: 1; }
    .form-container { display: flex; gap: 8px; align-items: center; }
    .form-circle { width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: 900; text-shadow: 0 1px 1px rgba(0,0,0,0.2); box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: 2px solid #fff; }
    @media (max-width: 480px) { .date-btn b { font-size: 8px; } .date-btn div { font-size: 7px; } }
</style>
'''

def slugify(t): 
    return re.sub(r'[^a-z0-9]+', '-', str(t).lower()).strip('-')

def get_team_names(fixture):
    if " vs " in fixture: return [t.strip() for t in fixture.split(" vs ")]
    elif " - " in fixture: return [t.strip() for t in fixture.split(" - ")]
    return ["Home", "Away"]

def get_sofa_data(data_type, date_str, match_id):
    path = f"data/{data_type}/{date_str}.json"
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                res = data.get(str(match_id))
                return res if isinstance(res, dict) else {}
            except: return {}
    return {}

def format_form_circles(form_list):
    if not form_list or not isinstance(form_list, list): return '<span style="color:#cbd5e1; font-size:12px; font-style:italic;">N/A</span>'
    html = '<div class="form-container">'
    for res in form_list:
        bg = "#10b981" if res == "W" else "#ef4444" if res == "L" else "#64748b"
        html += f'<span class="form-circle" style="background:{bg}">{res}</span>'
    return html + '</div>'

def build_lineups_html(data, teams):
    if not isinstance(data, dict) or not data.get('home'): return "<div class='p-4 text-gray-400 italic'>Lineups not confirmed yet</div>"
    h_players = "".join([f"<li>{p['player']['name']}</li>" for p in data.get('home', {}).get('players', [])[:11]])
    a_players = "".join([f"<li>{p['player']['name']}</li>" for p in data.get('away', {}).get('players', [])[:11]])
    return f'''<div style="display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid #f1f5f9;">
        <div style="padding:15px; border-right:1px solid #f1f5f9;"><b>{teams[0]} XI</b><ul style="list-style:none;padding:0;font-size:13px;">{h_players}</ul></div>
        <div style="padding:15px;"><b>{teams[1]} XI</b><ul style="list-style:none;padding:0;font-size:13px;">{a_players}</ul></div>
    </div>'''

def build_stats_html(data):
    if not isinstance(data, dict) or 'statistics' not in data: return "<div class='p-4 text-gray-400 italic'>Live stats available during match</div>"
    rows = ""
    try:
        period = next((p for p in data['statistics'] if p['period'] == 'ALL'), data['statistics'][0])
        for group in period['groups']:
            for item in group['statisticsItems']:
                rows += f'<div class="stat-row"><span>{item["home"]}</span><span class="stat-label">{item["name"]}</span><span>{item["away"]}</span></div>'
        return rows
    except: return "No stats available"

def generate_match_faqs(m, teams, h2h, odds):
    h2h_data = h2h if isinstance(h2h, dict) else {}
    odds_data = odds if isinstance(odds, dict) else {}
    h_win = h2h_data.get('homeWins', 0)
    a_win = h2h_data.get('awayWins', 0)
    prob = odds_data.get('home', {}).get('expected', '-') if isinstance(odds_data.get('home'), dict) else '-'
    
    q_a = [
        (f"Where to watch {m['fixture']} live?", f"You can watch {m['fixture']} on official channels like Sky Sports, TNT, or local broadcasters listed on our match page."),
        (f"What time is {teams[0]} vs {teams[1]}?", f"The match is scheduled for kickoff. Check our local time converter above for your exact timezone."),
        (f"What is the head to head record for {m['fixture']}?", f"{teams[0]} has won {h_win} times while {teams[1]} has won {a_win} times.")
    ]
    html_f = '<div class="sofa-card"><div class="sofa-header">FAQs</div><div style="padding:15px;">'
    schema_f = []
    for q, a in q_a:
        html_f += f'<div style="margin-bottom:12px;"><b>{q}</b><p style="color:#64748b;font-size:13px;">{a}</p></div>'
        schema_f.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}})
    return html_f + '</div></div>', schema_f

# --- 1. LOAD TEMPLATES ---
templates = {n: open(f'{n}_template.html', 'r', encoding='utf-8').read() for n in ['home', 'match', 'channel']}

# --- 2. LOAD DATA ---
all_matches, seen_ids = [], set()
for f in glob.glob("date/*.json"):
    with open(f, 'r', encoding='utf-8') as j:
        try:
            data = json.load(j)
            for m in data:
                if m.get('match_id') and m['match_id'] not in seen_ids:
                    all_matches.append(m); seen_ids.add(m['match_id'])
        except: continue

channels_data, sitemap_urls = {}, [DOMAIN + "/"]

# --- 3. PROCESS MATCH PAGES ---
for m in all_matches:
    m_dt = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
    teams = get_team_names(m['fixture'])
    m_slug = slugify(m['fixture'])
    m_date_folder = m_dt.strftime('%Y%m%d')
    m_url = f"{DOMAIN}/match/{m_slug}/{m_date_folder}/"
    sitemap_urls.append(m_url)
    
    # Sofa Data Retrieval
    mid = m['match_id']
    lineup_raw = get_sofa_data("lineups", m_date_folder, mid)
    stats_raw = get_sofa_data("statistics", m_date_folder, mid)
    h2h_raw = get_sofa_data("h2h", m_date_folder, mid)
    odds_raw = get_sofa_data("odds", m_date_folder, mid)
    form_raw = get_sofa_data("form", m_date_folder, mid)

    # UI Logic
    h_p = odds_raw.get("home", {}).get("expected", "-") if isinstance(odds_raw.get("home"), dict) else "-"
    a_p = odds_raw.get("away", {}).get("expected", "-") if isinstance(odds_raw.get("away"), dict) else "-"
    
    faq_html, faq_schema_list = generate_match_faqs(m, teams, h2h_raw.get('teamDuel', {}), odds_raw)
    
    sofa_ui = f'<div class="sofa-card"><div class="sofa-header">Win Probability</div><div class="flex justify-around p-6"><div>{teams[0]}: {h_p}%</div><div>{teams[1]}: {a_p}%</div></div></div>'
    if isinstance(form_raw, dict) and form_raw:
        sofa_ui += f'<div class="sofa-card"><div class="sofa-header">Recent Form</div>'
        sofa_ui += f'<div class="stat-row"><span>{teams[0]}</span>{format_form_circles(form_raw.get("homeTeam",{}).get("form"))}</div>'
        sofa_ui += f'<div class="stat-row"><span>{teams[1]}</span>{format_form_circles(form_raw.get("awayTeam",{}).get("form"))}</div></div>'
    sofa_ui += f'<div class="sofa-card"><div class="sofa-header">Lineups</div>{build_lineups_html(lineup_raw, teams)}</div>'
    sofa_ui += faq_html

    # Broadcast Rows
    rows = ""
    for idx, c in enumerate(m.get('tv_channels', [])):
        pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" style="display:inline-block;background:#f1f5f9;color:#2563eb;padding:4px 10px;border-radius:6px;margin:2px;text-decoration:none;font-size:12px;font-weight:700;">{ch}</a>' for ch in c['channels']])
        rows += f'<div style="display:flex;padding:12px;border-bottom:1px solid #eee;"><b>{c["country"]}</b><div style="margin-left:auto;">{pills}</div></div>'
        if (idx+1) % 10 == 0: rows += ADS_CODE

    # Write File
    m_path = f"match/{m_slug}/{m_date_folder}"
    os.makedirs(m_path, exist_ok=True)
    with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
        content = templates['match'].replace("{{FIXTURE}}", m['fixture']).replace("{{DOMAIN}}", DOMAIN)
        content = content.replace("{{BROADCAST_ROWS}}", rows).replace("{{SOFA_DATA}}", sofa_ui)
        content = content.replace("{{LOCAL_DATE}}", f'<span class="auto-date" data-unix="{m["kickoff"]}"></span>')
        content = content.replace("{{LOCAL_TIME}}", f'<span class="auto-time" data-unix="{m["kickoff"]}"></span>')
        content = content.replace("{{UNIX}}", str(m['kickoff'])).replace("{{VENUE}}", m.get('venue', 'TBA'))
        mf.write(content)

    # Populate Channel Data
    for c in m.get('tv_channels', []):
        for ch in c['channels']:
            if ch not in channels_data: channels_data[ch] = []
            channels_data[ch].append({'m': m, 'dt': m_dt})

# --- 4. DAILY LISTINGS ---
for i in range(7):
    day = MENU_START_DATE + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    sitemap_urls.append(f"{DOMAIN}/{fname}")
    
    # Menu HTML
    menu = f'{MENU_CSS}<div class="weekly-menu-container">'
    for j in range(7):
        m_day = MENU_START_DATE + timedelta(days=j)
        m_fn = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
        menu += f'<a href="{DOMAIN}/{m_fn}" class="date-btn {"active" if m_day==day else ""}"><div>{m_day.strftime("%a")}</div><b>{m_day.strftime("%b %d")}</b></a>'
    menu += '</div>'

    day_matches = [m for m in all_matches if datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET).date() == day]
    day_matches.sort(key=lambda x: (x.get('league_id') not in TOP_LEAGUE_IDS, x.get('league', ''), x['kickoff']))

    list_html, last_league = "", ""
    for m in day_matches:
        league = m.get('league', 'Other Football')
        if league != last_league:
            list_html += f'<div style="background:#1e293b;color:#fff;padding:8px 15px;font-size:12px;">{league}</div>'
            last_league = league
        list_html += f'<a href="{DOMAIN}/match/{slugify(m["fixture"])}/{datetime.fromtimestamp(m["kickoff"]).strftime("%Y%m%d")}/" style="display:flex;padding:15px;background:#fff;border-bottom:1px solid #eee;text-decoration:none;color:#333;"><div><b class="auto-time" data-unix="{m["kickoff"]}"></b></div><div style="margin-left:20px;">{m["fixture"]}</div></a>'

    with open(fname, "w", encoding='utf-8') as df:
        df.write(templates['home'].replace("{{MATCH_LISTING}}", list_html or "<p class='p-4'>No matches scheduled.</p>").replace("{{WEEKLY_MENU}}", menu).replace("{{DOMAIN}}", DOMAIN))

# --- 5. CHANNEL PAGES ---
for ch, matches in channels_data.items():
    c_slug = slugify(ch)
    os.makedirs(f"channel/{c_slug}", exist_ok=True)
    c_list = "".join([f'<a href="{DOMAIN}/match/{slugify(x["m"]["fixture"])}/{x["dt"].strftime("%Y%m%d")}/" style="display:block;padding:12px;border-bottom:1px solid #eee;text-decoration:none;color:#2563eb;">{x["m"]["fixture"]} - {x["dt"].strftime("%b %d")}</a>' for x in sorted(matches, key=lambda x: x['m']['kickoff'], reverse=True)])
    with open(f"channel/{c_slug}/index.html", "w", encoding='utf-8') as cf:
        cf.write(templates['channel'].replace("{{CHANNEL_NAME}}", ch).replace("{{MATCH_LISTING}}", c_list).replace("{{DOMAIN}}", DOMAIN))

# --- 6. SITEMAP ---
sitemap = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join([f'<url><loc>{u}</loc><lastmod>{NOW.strftime("%Y-%m-%d")}</lastmod></url>' for u in sorted(list(set(sitemap_urls)))]) + '</urlset>'
with open("sitemap.xml", "w", encoding='utf-8') as sm: sm.write(sitemap)
