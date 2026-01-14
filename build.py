import json
import os
import re
import glob
import shutil
from datetime import datetime, timedelta, timezone

# ==========================================================
# CONFIGURATION
# ==========================================================
DOMAIN = "https://tv.cricfoot.net"
OUTPUT_DIR = "dist"

LOCAL_OFFSET = timezone(timedelta(hours=5))
NOW = datetime.now(LOCAL_OFFSET)
TODAY_DATE = NOW.date()

MENU_START_DATE = TODAY_DATE - timedelta(days=3)
MENU_END_DATE = TODAY_DATE + timedelta(days=3)

TOP_LEAGUE_IDS = [17, 35, 23, 7, 8, 34, 679]

# ==========================================================
# CLEAN BUILD DIRECTORY
# ==========================================================
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================================
# ADS & CSS
# ==========================================================
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
    transition: all 0.2s;
}
.date-btn div { font-size: 9px; text-transform: uppercase; color: #64748b; font-weight: bold; }
.date-btn b { font-size: 10px; color: #1e293b; white-space: nowrap; }
.date-btn.active { background: #2563eb; border-color: #2563eb; }
.date-btn.active div,
.date-btn.active b { color: #fff; }
</style>
'''

# ==========================================================
# HELPERS
# ==========================================================
def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# ==========================================================
# LOAD TEMPLATES
# ==========================================================
templates = {}
for name in ("home", "match", "channel"):
    with open(f"{name}_template.html", "r", encoding="utf-8") as f:
        templates[name] = f.read()

# ==========================================================
# LOAD MATCH DATA
# ==========================================================
all_matches = []
seen_ids = set()

for file in glob.glob("date/*.json"):
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for m in data:
                mid = m.get("match_id")
                if mid and mid not in seen_ids:
                    all_matches.append(m)
                    seen_ids.add(mid)
    except:
        continue

# ==========================================================
# PREPROCESS MATCHES
# ==========================================================
channels_data = {}
sitemap_urls = [DOMAIN + "/"]

for m in all_matches:
    kickoff = int(m["kickoff"])
    dt_local = datetime.fromtimestamp(kickoff, tz=timezone.utc).astimezone(LOCAL_OFFSET)
    slug = slugify(m["fixture"])
    date_folder = dt_local.strftime("%Y%m%d")

    match_url = f"{DOMAIN}/match/{slug}/{date_folder}/"
    sitemap_urls.append(match_url)

    league = m.get("league", "Other Football")

    # CHANNEL DATA
    for c in m.get("tv_channels", []):
        for ch in c["channels"]:
            channels_data.setdefault(ch, [])
            if kickoff > NOW.timestamp() - 86400:
                if not any(x["m"]["match_id"] == m["match_id"] for x in channels_data[ch]):
                    channels_data[ch].append({"m": m, "dt": dt_local, "league": league})

    # MATCH PAGE
    rows = ""
    count = 0
    for c in m.get("tv_channels", []):
        count += 1
        pills = "".join(
            f'<a href="{DOMAIN}/channel/{slugify(ch)}/">{ch}</a>'
            for ch in c["channels"]
        )
        rows += f"""
        <div>
            <b>{c["country"]}</b>
            <div>{pills}</div>
        </div>
        """
        if count % 10 == 0:
            rows += ADS_CODE

    venue = m.get("venue") or m.get("stadium") or "To Be Announced"

    html = templates["match"]
    html = html.replace("{{FIXTURE}}", m["fixture"])
    html = html.replace("{{DOMAIN}}", DOMAIN)
    html = html.replace("{{LEAGUE}}", league)
    html = html.replace("{{BROADCAST_ROWS}}", rows)
    html = html.replace("{{VENUE}}", venue)
    html = html.replace("{{UNIX}}", str(kickoff))
    html = html.replace("{{LOCAL_DATE}}", dt_local.strftime("%d %b %Y"))
    html = html.replace("{{LOCAL_TIME}}", dt_local.strftime("%H:%M"))

    write_file(
        f"{OUTPUT_DIR}/match/{slug}/{date_folder}/index.html",
        html
    )

# ==========================================================
# DAILY LISTING PAGES (ALL DATES)
# ==========================================================
ALL_DATES = sorted({
    datetime.fromtimestamp(int(m["kickoff"]), tz=timezone.utc)
    .astimezone(LOCAL_OFFSET).date()
    for m in all_matches
})

for day in ALL_DATES:
    fname = "index.html" if day == TODAY_DATE else f"{day}.html"
    if fname != "index.html":
        sitemap_urls.append(f"{DOMAIN}/{fname}")

    menu = MENU_CSS + '<div class="weekly-menu-container">'
    for i in range(7):
        d = MENU_START_DATE + timedelta(days=i)
        f = "index.html" if d == TODAY_DATE else f"{d}.html"
        active = "active" if d == day else ""
        menu += f'<a class="date-btn {active}" href="{DOMAIN}/{f}"><div>{d:%a}</div><b>{d:%b %d}</b></a>'
    menu += "</div>"

    matches = [
        m for m in all_matches
        if datetime.fromtimestamp(int(m["kickoff"]), tz=timezone.utc)
        .astimezone(LOCAL_OFFSET).date() == day
    ]

    matches.sort(key=lambda x: (
        x.get("league_id") not in TOP_LEAGUE_IDS,
        x.get("league", ""),
        x["kickoff"]
    ))

    listing = ""
    last_league = ""
    counter = 0

    for m in matches:
        league = m.get("league", "Other Football")
        if league != last_league:
            if last_league and counter % 3 == 0:
                listing += ADS_CODE
            listing += f"<h3>{league}</h3>"
            last_league = league
            counter += 1

        dt = datetime.fromtimestamp(int(m["kickoff"]), tz=timezone.utc).astimezone(LOCAL_OFFSET)
        listing += f"""
        <a href="{DOMAIN}/match/{slugify(m['fixture'])}/{dt:%Y%m%d}/">
            {dt:%H:%M} — {m['fixture']}
        </a>
        """

    listing += ADS_CODE if listing else ""

    page = templates["home"]
    page = page.replace("{{MATCH_LISTING}}", listing)
    page = page.replace("{{WEEKLY_MENU}}", menu)
    page = page.replace("{{DOMAIN}}", DOMAIN)
    page = page.replace("{{SELECTED_DATE}}", day.strftime("%A, %b %d, %Y"))
    page = page.replace("{{PAGE_TITLE}}", f"TV Channels For {day:%A, %b %d, %Y}")

    write_file(f"{OUTPUT_DIR}/{fname}", page)

# ==========================================================
# CHANNEL PAGES
# ==========================================================
for ch, items in channels_data.items():
    slug = slugify(ch)
    sitemap_urls.append(f"{DOMAIN}/channel/{slug}/")

    listing = ""
    items.sort(key=lambda x: x["m"]["kickoff"])
    for item in items:
        m = item["m"]
        dt = item["dt"]
        listing += f"""
        <a href="{DOMAIN}/match/{slugify(m['fixture'])}/{dt:%Y%m%d}/">
            {dt:%H:%M} — {m['fixture']} ({item['league']})
        </a>
        """

    page = templates["channel"]
    page = page.replace("{{CHANNEL_NAME}}", ch)
    page = page.replace("{{MATCH_LISTING}}", listing)
    page = page.replace("{{DOMAIN}}", DOMAIN)
    page = page.replace("{{WEEKLY_MENU}}", MENU_CSS)

    write_file(f"{OUTPUT_DIR}/channel/{slug}/index.html", page)

# ==========================================================
# SITEMAP
# ==========================================================
sitemap = '<?xml version="1.0" encoding="UTF-8"?>'
sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in sorted(set(sitemap_urls)):
    sitemap += f"<url><loc>{url}</loc><lastmod>{NOW:%Y-%m-%d}</lastmod></url>"
sitemap += "</urlset>"

write_file(f"{OUTPUT_DIR}/sitemap.xml", sitemap)

print("✅ Build complete — clean, stable, SEO-safe.")
