import json
import os 
from datetime import datetime

# 1. Load Data
with open('matches.json', 'r') as f:
    matches = json.load(f)

with open('template.html', 'r') as f:
    template = f.read()

def slugify(text):
    return text.lower().replace(" ", "-").replace(".", "").replace("(", "").replace(")", "")

# 2. Generate Pages
for m in matches:
    dt = datetime.fromtimestamp(m['kickoff'])
    date_str = dt.strftime('%d-%b-%Y') # e.g. 11-Jan-2026
    time_str = dt.strftime('%H:%M')
    
    # Create Path: match/team1-vs-team2/11-jan-2026/
    path = f"match/{slugify(m['fixture'])}/{slugify(date_str)}"
    os.makedirs(path, exist_ok=True)

    # Build TV List HTML
    tv_html = ""
    for country in m['tv_channels']:
        channels = "".join([f'<span class="channel-pill">{c}</span>' for c in country['channels']])
        tv_html += f"""
        <div class="country-row flex flex-col md:flex-row md:items-center justify-between gap-3">
            <span class="font-bold text-sm text-gray-700">{country['country']}</span>
            <div class="flex flex-wrap gap-2">{channels}</div>
        </div>
        """

    # Replace Template Variables
    page_content = template.replace("{{TITLE}}", f"{m['fixture']} - How to Watch Live | TV Channels | {date_str}")
    page_content = page_content.replace("{{FIXTURE}}", m['fixture'])
    page_content = page_content.replace("{{LEAGUE}}", m['league'])
    page_content = page_content.replace("{{DATE}}", date_str)
    page_content = page_content.replace("{{TIME}}", time_str)
    page_content = page_content.replace("{{VENUE}}", m.get('venue', 'TBA'))
    page_content = page_content.replace("{{TV_CHANNELS_LIST}}", tv_html)

    # Save the file
    with open(f"{path}/index.html", "w") as f:
        f.write(page_content)

print(f"Successfully generated {len(matches)} match pages.")
