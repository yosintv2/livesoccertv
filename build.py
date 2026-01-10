import json, os, re, glob, logging 
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring

# --- CONFIG ---
DOMAIN = "https://tv.cricfoot.net"
INPUT_FOLDER = "date"
OUTPUT_FOLDER = "public"
PRIORITY_IDS = [23, 17] # Serie A and Premier League

logging.basicConfig(level=logging.INFO, format='%(message)s')

class Generator:
    def __init__(self):
        self.matches = []
        self.channels_db = {}
        self.sitemap_urls = [f"{DOMAIN}/"]
        for d in [INPUT_FOLDER, OUTPUT_FOLDER]: os.makedirs(d, exist_ok=True)

    def slugify(self, text):
        return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')

    def run(self):
        with open('home_template.html', 'r', encoding='utf-8') as f: home_t = f.read()
        with open('match_template.html', 'r', encoding='utf-8') as f: match_t = f.read()
        with open('channel_template.html', 'r', encoding='utf-8') as f: channel_t = f.read()

        for f_path in glob.glob(f"{INPUT_FOLDER}/*.json"):
            with open(f_path, 'r', encoding='utf-8') as f: self.matches.extend(json.load(f))
        
        # PRIORITY SORT: League IDs 23/17 first, then kickoff
        self.matches.sort(key=lambda x: (x.get('league_id') not in PRIORITY_IDS, x['kickoff']))

        for m in self.matches:
            m_dt = datetime.fromtimestamp(m['kickoff'])
            m_slug = self.slugify(m['fixture'])
            date_id = m_dt.strftime('%Y%m%d')
            m_dir = os.path.join(OUTPUT_FOLDER, "match", m_slug, date_id)
            os.makedirs(m_dir, exist_ok=True)

            rows = ""
            for item in m.get('tv_channels', []):
                pills = "".join([f'<a href="{DOMAIN}/channel/{self.slugify(ch)}/" class="ch-pill">{ch}</a>' for ch in item['channels']])
                rows += f'<tr class="border-b"><td class="p-4 font-bold text-slate-600 text-sm">{item["country"]}</td><td class="p-4">{pills}</td></tr>'
                for ch in item['channels']: self.channels_db.setdefault(ch, []).append(m)

            m_html = match_t.replace("{{FIXTURE}}", m['fixture']).replace("{{TIME_UNIX}}", str(m['kickoff'])).replace("{{LEAGUE}}", m.get('league', 'Soccer')).replace("{{VENUE}}", m.get('venue', 'TBA')).replace("{{BROADCAST_ROWS}}", rows).replace("{{DOMAIN}}", DOMAIN)
            with open(os.path.join(m_dir, "index.html"), "w", encoding='utf-8') as f: f.write(m_html)
            self.sitemap_urls.append(f"{DOMAIN}/match/{m_slug}/{date_id}/")

        # HOME PAGE GENERATION
        today = datetime.now().date()
        friday = today - timedelta(days=(today.weekday() - 4) % 7)
        week = [friday + timedelta(days=i) for i in range(7)]

        for day in week:
            day_str = day.strftime('%Y-%m-%d')
            menu = "".join([f'<a href="{DOMAIN}/' + ('' if d == today else d.strftime('%Y-%m-%d')) + f'" class="date-btn {"active-day" if d == day else ""}">{d.strftime("%a")}<br>{d.strftime("%b %d")}</a>' for d in week])
            
            day_m = [m for m in self.matches if datetime.fromtimestamp(m['kickoff']).date() == day]
            listing, last_league = "", ""
            for m in day_m:
                if m['league'] != last_league:
                    listing += f'<div class="league-header">{m["league"]}</div>'
                    last_league = m['league']
                m_slug = self.slugify(m['fixture'])
                listing += f'<a href="{DOMAIN}/match/{m_slug}/{datetime.fromtimestamp(m["kickoff"]).strftime("%Y%m%d")}/" class="match-row"><div class="match-time" data-unix="{m["kickoff"]}"></div><div class="match-info">{m["fixture"]}</div></a>'

            final_h = home_t.replace("{{MATCH_LISTING}}", listing).replace("{{DOMAIN}}", DOMAIN).replace("{{PAGE_TITLE}}", f"Live Football TV - {day_str}").replace("{{WEEKLY_MENU}}", menu)
            
            if day == today:
                with open(os.path.join(OUTPUT_FOLDER, "index.html"), "w", encoding='utf-8') as f: f.write(final_h)
            else:
                d_dir = os.path.join(OUTPUT_FOLDER, day_str)
                os.makedirs(d_dir, exist_ok=True)
                with open(os.path.join(d_dir, "index.html"), "w", encoding='utf-8') as f: f.write(final_h)
                self.sitemap_urls.append(f"{DOMAIN}/{day_str}/")

        # CHANNELS & SITEMAP
        for name, ms in self.channels_db.items():
            slug = self.slugify(name)
            c_dir = os.path.join(OUTPUT_FOLDER, "channel", slug)
            os.makedirs(c_dir, exist_ok=True)
            c_list = "".join([f'<div class="p-4 border-b font-bold text-slate-700">{x["fixture"]}</div>' for x in ms])
            with open(os.path.join(c_dir, "index.html"), "w", encoding='utf-8') as f: f.write(channel_t.replace("{{CHANNEL_NAME}}", name).replace("{{LISTING}}", c_list).replace("{{DOMAIN}}", DOMAIN))
            self.sitemap_urls.append(f"{DOMAIN}/channel/{slug}/")

        root = Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for loc in self.sitemap_urls: SubElement(SubElement(root, 'url'), 'loc').text = loc
        with open(os.path.join(OUTPUT_FOLDER, "sitemap.xml"), "wb") as f: f.write(tostring(root))
        logging.info("DONE!")

if __name__ == "__main__": Generator().run()
