import json, os
from datetime import datetime

# CONFIG
DOMAIN = "https://yourdomain.com" # Change this!

with open('matches.json', 'r') as f:
    matches = json.load(f)
with open('home_template.html', 'r') as f:
    home_temp = f.read()
with open('match_template.html', 'r') as f:
    match_temp = f.read()

def slugify(t):
    return t.lower().replace(" ", "-").replace(".", "").replace("(", "").replace(")", "")

sitemap_urls = [DOMAIN]
match_html_list = ""
leagues = {}

# Process Individual Matches
for m in matches:
    dt = datetime.fromtimestamp(m['kickoff'])
    d_display = dt.strftime('%d %b %Y')
    d_path = dt.strftime('%d-%b-%Y').lower()
    slug = slugify(m['fixture'])
    rel_path = f"match/{slug}/{d_path}"
    os.makedirs(rel_path, exist_ok=True)

    # Build TV List
    tv_html = ""
    for country in m.get('tv_channels', []):
        pills = "".join([f'<span class="channel-pill m-1">{c}</span>' for c in country['channels']])
        tv_html += f'<div class="country-header">{country["country"]}</div><div class="p-4 flex flex-wrap">{pills}</div>'

    # Save Detail Page
    page = match_temp.replace("{{TITLE}}", f"{m['fixture']} TV Channels - {d_display}") \
                     .replace("{{FIXTURE}}", m['fixture']) \
                     .replace("{{LEAGUE}}", m['league']) \
                     .replace("{{DATE}}", d_display) \
                     .replace("{{TV_LIST}}", tv_html)
    
    with open(f"{rel_path}/index.html", "w") as f:
        f.write(page)
    
    sitemap_urls.append(f"{DOMAIN}/{rel_path}/")
    leagues.setdefault(m['league'], []).append({
        "time": dt.strftime('%H:%M'),
        "fixture": m['fixture'],
        "url": f"/{rel_path}/"
    })

# Build Home Page Listing
for league, m_list in leagues.items():
    match_html_list += f'<div class="mb-6 shadow-sm border rounded overflow-hidden"><div class="league-head">{league}</div>'
    for match in m_list:
        match_html_list += f'<a href="{match["url"]}" class="match-row"><span class="w-16 font-bold text-gray-400">{match["time"]}</span><span class="font-bold text-[#004d99]">{match["fixture"]}</span></a>'
    match_html_list += '</div>'

with open("index.html", "w") as f:
    f.write(home_temp.replace("{{MATCH_LISTING}}", match_html_list))

# Generate Sitemap.xml
sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
for url in sitemap_urls:
    sitemap_xml += f'<url><loc>{url}</loc><lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod></url>'
sitemap_xml += '</urlset>'

with open("sitemap.xml", "w") as f:
    f.write(sitemap_xml)

print(f"Done! Created {len(matches)} match pages and sitemap.")
