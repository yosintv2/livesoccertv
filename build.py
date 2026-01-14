import json, os, re, glob, html
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
LOCAL_OFFSET = timezone(timedelta(hours=5)) 
NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date() 

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
    .stat-value { font-weight: 700; color: #1e293b; width: 45px; }
    .lineup-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-top: 1px solid #f1f5f9; }
    .team-col { padding: 15px; }
    .team-col:first-child { border-right: 1px solid #f1f5f9; }
    .team-col b { display: block; margin-bottom: 10px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
    .team-col ul { list-style: none; padding: 0; margin: 0; }
    .team-col li { font-size: 13px; padding: 6px 0; color: #475569; border-bottom: 1px dashed #f1f5f9; }
    .form-container { display: flex; gap: 8px; align-items: center; }
    .form-circle { width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: 900; text-shadow: 0 1px 1px rgba(0,0,0,0.2); box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: 2px solid #fff; }
    .team-name-label { font-weight: 700; color: #334155; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
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
    if not form_list or not isinstance(form_list, list): return '<span style="color:#cbd5e1; font-size:12px; font-style:italic;">No data</span>'
    html = '<div class="form-container">'
    for res in form_list:
        bg = "#10b981" if res == "W" else "#ef4444" if res == "L" else "#64748b"
        html += f'<span class="form-circle" style="background:{bg}">{res}</span>'
    return html + '</div>'

def build_lineups_html(data, teams):
    if not isinstance(data, dict) or not data.get('home'): return "<div class='p-4 text-gray-400 italic'>Lineups not confirmed yet</div>"
    h_players = "".join([f"<li>{p['player']['name']}</li>" for p in data.get('home', {}).get('players', [])[:11]])
    a_players = "".join([f"<li>{p['player']['name']}</li>" for p in data.get('away', {}).get('players', [])[:11]])
    return f'''<div class="lineup-grid"><div class="team-col"><b>{teams[0]} XI</b><ul>{h_players}</ul></div><div class="team-col"><b>{teams[1]} XI</b><ul>{a_players}</ul></div></div>'''

def build_stats_html(data):
    if not isinstance(data, dict) or 'statistics' not in data: return "<div class='p-4 text-gray-400 italic'>Stats available during live match</div>"
    rows = ""
    try:
        period = next((p for p in data['statistics'] if p['period'] == 'ALL'), data['statistics'][0])
        for group in period['groups']:
            for item in group['statisticsItems']:
                rows += f'<div class="stat-row"><span>{item["home"]}</span><span class="stat-label">{item["name"]}</span><span>{item["away"]}</span></div>'
        return rows
    except: return "No stats"

def generate_match_faqs(m, teams, h2h, odds):
    # Null-safe extraction for FAQ data
    h2h_data = h2h if isinstance(h2h, dict) else {}
    odds_data = odds if isinstance(odds, dict) else {}
    
    h_win = h2h_data.get('homeWins', 0)
    a_win = h2h_data.get('awayWins', 0)
    draws = h2h_data.get('draws', 0)
    prob = odds_data.get('home', {}).get('expected', '-') if isinstance(odds_data.get('home'), dict) else '-'

    q_a = [
        (f"Where to watch {m['fixture']} live?", f"You can watch {m['fixture']} on official channels like Sky Sports, TNT, or local broadcasters listed on our match page."),
        (f"What time is {teams[0]} vs {teams[1]}?", f"The match is scheduled for kickoff. Check our local time converter above for your exact timezone."),
        (f"Who is predicted to win {m['fixture']}?", f"Based on probability data, {teams[0]} has a {prob}% win chance."),
        (f"What are the {teams[0]} vs {teams[1]} lineups?", "Official lineups are usually announced 1 hour before kickoff. We update them live on this page."),
        (f"What is the head to head record for {m['fixture']}?", f"{teams[0]} has won {h_win} times while {teams[1]} has won {a_win} times."),
        (f"Where is {m['fixture']} match being played?", f"The match venue is {m.get('venue', 'TBA')}."),
        (f"What are the latest betting odds for {teams[0]}?", f"Expected winning probability for the home team is {prob}%."),
        (f"Which channel is showing {teams[1]} match today?", "Check the 'Broadcasters' section on our site for a full list of global TV channels."),
        (f"How many draws between {teams[0]} and {teams[1]}?", f"There have been {draws} draws in recent encounters."),
        (f"Is {teams[0]} in good form?", "You can check the 'Recent Form' bubble chart above to see the last 5 match results."),
        (f"Who are the key players in {teams[1]} lineup?", "Refer to our 'Confirmed Lineups' section for the full starting XI."),
        (f"What are the match statistics for {m['fixture']}?", "Live stats like possession and shots are updated in our Statistics card during the game."),
        (f"Are there any free streams for {m['fixture']}?", "We only list official TV broadcasters. We recommend legal viewing via local sports channels."),
        (f"Will {teams[0]} win today?", f"Probability stats favor {teams[0]} with {prob}%."),
        (f"How to check live score for {m['fixture']}?", "This page updates broadcast information and key match data in real-time.")
    ]
    html_f = '<div class="sofa-card"><div class="sofa-header">Frequently Asked Questions</div><div style="padding:15px;">'
    schema_f = []
    for q, a in q_a:
        html_f += f'<div style="margin-bottom:12px;"><b>{q}</b><p style="color:#64748b;font-size:13px;">{a}</p></div>'
        schema_f.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}})
    return html_f + '</div></div>', schema_f

# --- LOAD DATA & TEMPLATES ---
templates = {n: open(f'{n}_template.html', 'r', encoding='utf-8').read() for n in ['home', 'match', 'channel']}
all_matches = []
seen_ids = set()
for f in sorted(glob.glob("date/*.json")):
    with open(f, 'r', encoding='utf-8') as j:
        try:
            matches_data = json.load(j)
            for m in matches_data:
                if m.get('match_id') and m['match_id'] not in seen_ids:
                    all_matches.append(m); seen_ids.add(m['match_id'])
        except: continue

channels_data = {}
sitemap_urls = [DOMAIN + "/"]

# --- PROCESS ALL MATCHES ---
for m in all_matches:
    m_dt = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
    teams = get_team_names(m['fixture'])
    m_slug = slugify(m['fixture'])
    m_date_folder = m_dt.strftime('%Y%m%d')
    m_url = f"{DOMAIN}/match/{m_slug}/{m_date_folder}/"
    sitemap_urls.append(m_url)
    
    mid = m['match_id']
    lineup_raw = get_sofa_data("lineups", m_date_folder, mid)
    stats_raw = get_sofa_data("statistics", m_date_folder, mid)
    h2h_raw = get_sofa_data("h2h", m_date_folder, mid)
    odds_raw = get_sofa_data("odds", m_date_folder, mid)
    form_raw = get_sofa_data("form", m_date_folder, mid)

    # FAQ & Schema
    h2h_duel = h2h_raw.get('teamDuel', {}) if isinstance(h2h_raw, dict) else {}
    faq_html, faq_schema_list = generate_match_faqs(m, teams, h2h_duel, odds_raw)
    
    # UI Odds Logic
    h_p = "-"
    a_p = "-"
    if isinstance(odds_raw, dict):
        h_p = odds_raw.get("home", {}).get("expected", "-") if isinstance(odds_raw.get("home"), dict) else "-"
        a_p = odds_raw.get("away", {}).get("expected", "-") if isinstance(odds_raw.get("away"), dict) else "-"
    
    odds_ui = f'<div class="flex justify-around p-6"><div>{teams[0]}: {h_p}%</div><div>{teams[1]}: {a_p}%</div></div>'
    
    form_ui = ""
    if isinstance(form_raw, dict) and form_raw:
        form_ui = f'<div class="sofa-card"><div class="sofa-header">Recent Form</div>'
        form_ui += f'<div class="stat-row"><span>{teams[0]}</span>{format_form_circles(form_raw.get("homeTeam",{}).get("form"))}</div>'
        form_ui += f'<div class="stat-row"><span>{teams[1]}</span>{format_form_circles(form_raw.get("awayTeam",{}).get("form"))}</div></div>'

    sofa_blocks = f'<div class="sofa-card"><div class="sofa-header">Win Probability</div>{odds_ui}</div>'
    sofa_blocks += form_ui
    sofa_blocks += f'<div class="sofa-card"><div class="sofa-header">Lineups</div>{build_lineups_html(lineup_raw, teams)}</div>'
    sofa_blocks += f'<div class="sofa-card"><div class="sofa-header">Stats</div>{build_stats_html(stats_raw)}</div>'
    sofa_blocks += faq_html

    rows = ""
    for idx, c in enumerate(m.get('tv_channels', [])):
        pills = "".join([f'<a href="{DOMAIN}/channel/{slugify(ch)}/" class="ch-pill" style="display:inline-block;background:#f1f5f9;color:#2563eb;padding:5px 12px;border-radius:6px;margin:3px;text-decoration:none;font-size:12px;font-weight:700;border:1px solid #cbd5e1;">{ch}</a>' for ch in c['channels']])
        rows += f'<div style="display:flex;padding:12px;border-bottom:1px solid #eee;"><b>{c["country"]}</b><div style="margin-left:auto;">{pills}</div></div>'
        if (idx+1) % 3 == 0: rows += ADS_CODE

    schema_data = {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": m['fixture'],
        "startDate": m_dt.isoformat(),
        "location": {"@type": "Place", "name": m.get('venue', 'TBA')},
        "homeTeam": {"@type": "SportsTeam", "name": teams[0]},
        "awayTeam": {"@type": "SportsTeam", "name": teams[1]}
    }
    faq_schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_schema_list}

    m_path = f"match/{m_slug}/{m_date_folder}"
    os.makedirs(m_path, exist_ok=True)
    with open(f"{m_path}/index.html", "w", encoding='utf-8') as mf:
        content = templates['match'].replace("{{FIXTURE}}", m['fixture']).replace("{{DOMAIN}}", DOMAIN)
        content = content.replace("{{BROADCAST_ROWS}}", rows).replace("{{SOFA_DATA}}", sofa_blocks)
        content = content.replace("{{LOCAL_DATE}}", f'<span class="auto-date" data-unix="{m["kickoff"]}"></span>')
        content = content.replace("{{LOCAL_TIME}}", f'<span class="auto-time" data-unix="{m["kickoff"]}"></span>')
        content = content.replace("{{UNIX}}", str(m['kickoff'])).replace("{{VENUE}}", m.get('venue', 'TBA'))
        meta = f'<script type="application/ld+json">{json.dumps(schema_data)}</script>'
        meta += f'<script type="application/ld+json">{json.dumps(faq_schema)}</script>'
        mf.write(content.replace("</head>", f"{meta}</head>"))

    for c in m.get('tv_channels', []):
        for ch in c['channels']:
            if ch not in channels_data: channels_data[ch] = []
            channels_data[ch].append({'m': m, 'dt': m_dt, 'league': m.get('league', 'Other')})

# --- DAILY LISTINGS ---
for i in range(7):
    day = MENU_START_DATE + timedelta(days=i)
    fname = "index.html" if day == TODAY_DATE else f"{day.strftime('%Y-%m-%d')}.html"
    sitemap_urls.append(f"{DOMAIN}/{fname}")
    
    day_matches = [m for m in all_matches if datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET).date() == day]
    day_matches.sort(key=lambda x: (x.get('league_id') not in TOP_LEAGUE_IDS, x.get('league', ''), x['kickoff']))

    listing_html, last_league = ADS_CODE, ""
    for idx, m in enumerate(day_matches):
        league = m.get('league', 'Other Football')
        if league != last_league:
            listing_html += f'<div class="league-header" style="background:#1e293b;color:#fff;padding:8px 15px;font-size:12px;">{league}</div>'
            last_league = league
        listing_html += f'''<a href="{DOMAIN}/match/{slugify(m['fixture'])}/{datetime.fromtimestamp(m['kickoff']).strftime('%Y%m%d')}/" class="match-row" style="display:flex;padding:15px;background:#fff;border-bottom:1px solid #eee;text-decoration:none;color:#333;">
            <div style="min-width:80px;text-align:center;">
                <div class="auto-date" data-unix="{m['kickoff']}" style="font-size:10px;color:#888;"></div>
                <div class="auto-time" data-unix="{m['kickoff']}" style="font-weight:bold;color:#2563eb;"></div>
            </div>
            <div style="margin-left:15px;font-weight:600;">{m['fixture']}</div>
        </a>'''
        if (idx+1) % 10 == 0: listing_html += ADS_CODE

    with open(fname, "w", encoding='utf-8') as df:
        menu = f'{MENU_CSS}<div class="weekly-menu-container">'
        for j in range(7):
            m_day = MENU_START_DATE + timedelta(days=j)
            m_fn = "index.html" if m_day == TODAY_DATE else f"{m_day.strftime('%Y-%m-%d')}.html"
            menu += f'<a href="{DOMAIN}/{m_fn}" class="date-btn {"active" if m_day==day else ""}"><div>{m_day.strftime("%a")}</div><b>{m_day.strftime("%b %d")}</b></a>'
        df.write(templates['home'].replace("{{MATCH_LISTING}}", listing_html).replace("{{WEEKLY_MENU}}", menu + '</div>').replace("{{DOMAIN}}", DOMAIN))

# --- CHANNEL PAGES ---
for ch_name, matches in channels_data.items():
    c_slug = slugify(ch_name)
    os.makedirs(f"channel/{c_slug}", exist_ok=True)
    c_listing = ADS_CODE
    matches.sort(key=lambda x: x['m']['kickoff'], reverse=True)
    for m_item in matches:
        m = m_item['m']
        c_listing += f'<a href="{DOMAIN}/match/{slugify(m["fixture"])}/{m_item["dt"].strftime("%Y%m%d")}/" style="display:block;padding:15px;border-bottom:1px solid #eee;text-decoration:none;color:#333;">{m["fixture"]}</a>'
    with open(f"channel/{c_slug}/index.html", "w", encoding='utf-8') as cf:
        cf.write(templates['channel'].replace("{{CHANNEL_NAME}}", ch_name).replace("{{MATCH_LISTING}}", c_listing).replace("{{DOMAIN}}", DOMAIN))

# --- SITEMAP ---
sitemap = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in sorted(list(set(sitemap_urls))):
    sitemap += f'<url><loc>{url}</loc><lastmod>{NOW.strftime("%Y-%m-%d")}</lastmod></url>'
with open("sitemap.xml", "w", encoding='utf-8') as sm: sm.write(sitemap + '</urlset>')
