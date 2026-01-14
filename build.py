import json, os, re, glob
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net"
LOCAL_OFFSET = timezone(timedelta(hours=5)) 

DIST_DIR = "dist"
os.makedirs(DIST_DIR, exist_ok=True)

NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date()

MENU_START_DATE = TODAY_DATE - timedelta(days=3)
MENU_END_DATE = TODAY_DATE + timedelta(days=3)

TOP_LEAGUE_IDS = [17, 35, 23, 7, 8, 34, 679]

ADS_CODE = '''
<div class="ad-container" style="margin: 20px 0; text-align: center;">
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
    with open(f'{name}_template.html', 'r', encoding='utf-8') as f:
        templates[name] = f.read()

# --- 2. LOAD DATA ---
all_matches = []
seen_match_ids = set()

for f in glob.glob("date/*.json"):
    with open(f, 'r', encoding='utf-8') as j:
        try:
            for m in json.load(j):
                mid = m.get('match_id')
                if mid and mid not in seen_match_ids:
                    all_matches.append(m)
                    seen_match_ids.add(mid)
        except:
            continue

channels_data = {}
sitemap_urls = [DOMAIN + "/"]

# --- 3. MATCH PAGES ---
for m in all_matches:
    m_dt = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
    m_slug = slugify(m['fixture'])
    m_day = m_dt.strftime('%Y%m%d')

    m_dir = f"{DIST_DIR}/match/{m_slug}/{m_day}"
    os.makedirs(m_dir, exist_ok=True)

    sitemap_urls.append(f"{DOMAIN}/match/{m_slug}/{m_day}/")

    league = m.get('league', 'Other Football')

    for c in m.get('tv_channels', []):
        for ch in c['channels']:
            channels_data.setdefault(ch, [])
            if int(m['kickoff']) > NOW.timestamp() - 86400:
                if not any(x['m']['match_id'] == m['match_id'] for x in channels_data[ch]):
                    channels_data[ch].append({'m': m, 'dt': m_dt, 'league': league})

    rows = ""
    counter = 0
    for c in m.get('tv_channels', []):
        counter += 1
        pills = "".join(
            f'<a href="{DOMAIN}/channel/{slugify(ch)}/" style="display:inline-block;background:#f1f5f9;color:#2563eb;padding:2px 8px;border-radius:4px;margin:2px;text-decoration:none;font-weight:600;border:1px solid #e2e8f0;">{ch}</a>'
            for ch in c['channels']
        )

        rows += f'''
        <div style="display:flex;align-items:flex-start;padding:12px;border-bottom:1px solid #edf2f7;background:#fff;">
            <div style="flex:0 0 100px;font-weight:800;color:#475569;font-size:13px;">{c["country"]}</div>
            <div style="flex:1;display:flex;flex-wrap:wrap;gap:4px;">{pills}</div>
        </div>'''

        if counter % 10 == 0:
            rows += ADS_CODE

    html = templates['match']
    html = html.replace("{{FIXTURE}}", m['fixture'])
    html = html.replace("{{BROADCAST_ROWS}}", rows)
    html = html.replace("{{LEAGUE}}", league)
    html = html.replace("{{DOMAIN}}", DOMAIN)
    html = html.replace("{{VENUE}}", m.get('venue') or m.get('stadium') or "To Be Announced")
    html = html.replace("{{LOCAL_DATE}}", f'<span class="auto-date" data-unix="{m["kickoff"]}">{m_dt.strftime("%d %b %Y")}</span>')
    html = html.replace("{{LOCAL_TIME}}", f'<span class="auto-time" data-unix="{m["kickoff"]}">{m_dt.strftime("%H:%M")}</span>')
    html = html.replace("{{UNIX}}", str(m['kickoff']))

    with open(f"{m_dir}/index.html", "w", encoding="utf-8") as f:
        f.write(html)

# --- 4. DAILY PAGES (ALL DATES) ---
ALL_DATES = sorted({
    datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET).date()
    for m in all_matches
})

for day in ALL_DATES:
    fname = "index.html" if day == TODAY_DATE else f"{day}.html"
    out_path = f"{DIST_DIR}/{fname}"

    if fname != "index.html":
        sitemap_urls.append(f"{DOMAIN}/{fname}")

    menu = f'{MENU_CSS}<div class="weekly-menu-container">'
    for i in range(7):
        d = MENU_START_DATE + timedelta(days=i)
        f2 = "index.html" if d == TODAY_DATE else f"{d}.html"
        menu += f'<a href="{DOMAIN}/{f2}" class="date-btn {"active" if d == day else ""}"><div>{d:%a}</div><b>{d:%b %d}</b></a>'
    menu += '</div>'

    listing = ""
    for m in sorted(all_matches, key=lambda x: x['kickoff']):
        m_dt = datetime.fromtimestamp(int(m['kickoff']), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        if m_dt.date() != day:
            continue

        listing += f'''
        <a href="{DOMAIN}/match/{slugify(m["fixture"])}/{m_dt.strftime("%Y%m%d")}/" class="match-row flex items-center p-4 bg-white border-b border-slate-100">
            <div class="time-box" style="min-width:95px;text-align:center;border-right:1px solid #edf2f7;margin-right:10px;">
                <div class="text-[10px] uppercase text-slate-400 auto-date" data-unix="{m['kickoff']}">{m_dt:%d %b}</div>
                <div class="font-bold text-blue-600 auto-time" data-unix="{m['kickoff']}">{m_dt:%H:%M}</div>
            </div>
            <div class="flex-1">{m['fixture']}</div>
        </a>'''

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(
            templates['home']
            .replace("{{MATCH_LISTING}}", listing + ADS_CODE)
            .replace("{{WEEKLY_MENU}}", menu)
            .replace("{{DOMAIN}}", DOMAIN)
            .replace("{{PAGE_TITLE}}", f"TV Channels For {day}")
            .replace("{{SELECTED_DATE}}", day.strftime("%A, %b %d, %Y"))
        )

# --- 5. CHANNEL PAGES ---
for ch, items in channels_data.items():
    c_slug = slugify(ch)
    c_dir = f"{DIST_DIR}/channel/{c_slug}"
    os.makedirs(c_dir, exist_ok=True)

    sitemap_urls.append(f"{DOMAIN}/channel/{c_slug}/")

    listing = ""
    for item in items:
        m = item['m']
        dt = item['dt']
        listing += f'''
        <a href="{DOMAIN}/match/{slugify(m['fixture'])}/{dt.strftime('%Y%m%d')}/" class="match-row flex items-center p-4 bg-white border-b border-slate-100">
            <div class="time-box" style="min-width:95px;text-align:center;border-right:1px solid #edf2f7;margin-right:10px;">
                <div class="text-[10px] uppercase text-slate-400">{dt:%d %b}</div>
                <div class="font-bold text-blue-600">{dt:%H:%M}</div>
            </div>
            <div class="flex-1">{m['fixture']}</div>
        </a>'''

    with open(f"{c_dir}/index.html", "w", encoding="utf-8") as f:
        f.write(
            templates['channel']
            .replace("{{CHANNEL_NAME}}", ch)
            .replace("{{MATCH_LISTING}}", listing)
            .replace("{{DOMAIN}}", DOMAIN)
            .replace("{{WEEKLY_MENU}}", MENU_CSS)
        )

# --- 6. SITEMAP ---
with open(f"{DIST_DIR}/sitemap.xml", "w", encoding="utf-8") as sm:
    sm.write(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
        ''.join(f'<url><loc>{u}</loc><lastmod>{NOW:%Y-%m-%d}</lastmod></url>' for u in sorted(set(sitemap_urls))) +
        '</urlset>'
    )

print("✅ Build complete → dist/ (CSS & JS untouched)")
