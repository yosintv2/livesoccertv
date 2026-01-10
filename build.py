import json
import os
import re
import glob
import logging
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring

# --- Configuration ---
DOMAIN = "https://tv.cricfoot.net"
INPUT_FOLDER = "date"
OUTPUT_FOLDER = "public"
TOP_LEAGUES = ["Premier League", "Champions League", "La Liga", "Serie A", "Bundesliga"]

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class SoccerDataEngine:
    """Handles data processing and SEO slug generation."""
    @staticmethod
    def slugify(text):
        text = text.lower().strip()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        return re.sub(r'[\s-]+', '-', text).strip('-')

    @staticmethod
    def get_friday_to_thursday_range(ref_date):
        """Calculates the specific Friday-to-Thursday window."""
        idx = (ref_date.weekday() - 4) % 7
        friday = ref_date - timedelta(days=idx)
        return [friday + timedelta(days=i) for i in range(7)]

class StaticSiteGenerator:
    def __init__(self):
        self.engine = SoccerDataEngine()
        self.matches = []
        self.channels_db = {}
        self.sitemap_urls = [DOMAIN + "/"]
        self.load_templates()

    def load_templates(self):
        try:
            with open('home_template.html', 'r') as f: self.home_t = f.read()
            with open('match_template.html', 'r') as f: self.match_t = f.read()
            with open('channel_template.html', 'r') as f: self.channel_t = f.read()
        except FileNotFoundError as e:
            logging.error(f"Template missing: {e}")
            exit(1)

    def fetch_data(self):
        files = glob.glob(f"{INPUT_FOLDER}/*.json")
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                self.matches.extend(json.load(f))
        logging.info(f"Loaded {len(self.matches)} matches.")

    def generate_match_pages(self):
        """Creates /match/slug/date-id/index.html hierarchy."""
        for m in self.matches:
            m_date = datetime.fromtimestamp(m['kickoff'])
            slug = self.engine.slugify(m['fixture'])
            date_id = m_date.strftime('%Y%m%d')
            dir_path = os.path.join(OUTPUT_FOLDER, "match", slug, date_id)
            os.makedirs(dir_path, exist_ok=True)

            # Broadcaster logic
            rows = ""
            for country in m.get('tv_channels', []):
                pills = ""
                for ch in country['channels']:
                    ch_slug = self.engine.slugify(ch)
                    pills += f'<a href="{DOMAIN}/channel/{ch_slug}/" class="ch-pill">{ch}</a>'
                    self.channels_db.setdefault(ch, []).append(m)
                rows += f'<tr><td class="lbl">{country["country"]}</td><td>{pills}</td></tr>'

            output = self.match_t.replace("{{FIXTURE}}", m['fixture'])\
                                .replace("{{TIME_UNIX}}", str(m['kickoff']))\
                                .replace("{{LEAGUE}}", m.get('league', 'World Football'))\
                                .replace("{{VENUE}}", m.get('venue', 'Global Stadium'))\
                                .replace("{{BROADCAST_ROWS}}", rows)\
                                .replace("{{DOMAIN}}", DOMAIN)
            
            with open(os.path.join(dir_path, "index.html"), "w") as f: f.write(output)
            self.sitemap_urls.append(f"{DOMAIN}/match/{slug}/{date_id}/")

    def generate_daily_pages(self):
        """Generates the main 7-day schedule with active day state."""
        today = datetime.now().date()
        week_range = self.engine.get_week_range(today) if hasattr(self.engine, 'get_week_range') else self.engine.get_friday_to_thursday_range(today)

        for day in week_range:
            day_str = day.strftime('%Y-%m-%d')
            # Nav Menu
            menu = ""
            for d in week_range:
                active = "active-day" if d == day else ""
                url = f"{DOMAIN}/" if d == today else f"{DOMAIN}/{d.strftime('%Y-%m-%d')}"
                menu += f'<a href="{url}" class="date-tab {active}"><span>{d.strftime("%a")}</span>{d.strftime("%b %d")}</a>'

            # Filter and Sort
            day_matches = [m for m in self.matches if datetime.fromtimestamp(m['kickoff']).date() == day]
            day_matches.sort(key=lambda x: (x.get('league') not in TOP_LEAGUES, x['kickoff']))

            listing, last_league = "", ""
            for m in day_matches:
                league = m.get('league', 'Other')
                if league != last_league:
                    listing += f'<div class="league-header">{league}</div>'
                    last_league = league
                
                m_slug = self.engine.slugify(m['fixture'])
                m_date_id = datetime.fromtimestamp(m['kickoff']).strftime('%Y%m%d')
                listing += f'''<a href="{DOMAIN}/match/{m_slug}/{m_date_id}/" class="m-row">
                    <span class="m-time" data-unix="{m['kickoff']}"></span>
                    <span class="m-fixture">{m['fixture']}</span>
                </a>'''

            full_html = self.home_t.replace("{{MATCH_LISTING}}", listing)\
                                  .replace("{{WEEKLY_NAV}}", menu)\
                                  .replace("{{DOMAIN}}", DOMAIN)\
                                  .replace("{{TITLE}}", f"Soccer TV Guide - {day.strftime('%A')}")

            if day == today:
                with open(os.path.join(OUTPUT_FOLDER, "index.html"), "w") as f: f.write(full_html)
            else:
                # SEO: Create folder and index.html for extension-less URLs
                day_path = os.path.join(OUTPUT_FOLDER, day_str)
                os.makedirs(day_path, exist_ok=True)
                with open(os.path.join(day_path, "index.html"), "w") as f: f.write(full_html)
                self.sitemap_urls.append(f"{DOMAIN}/{day_str}/")

    def generate_channel_pages(self):
        """Builds /channel/slug/index.html pages."""
        for name, matches in self.channels_db.items():
            slug = self.engine.slugify(name)
            path = os.path.join(OUTPUT_FOLDER, "channel", slug)
            os.makedirs(path, exist_ok=True)
            
            listing = "".join([f'<div class="m-row">{m["fixture"]} - <span data-unix="{m["kickoff"]}"></span></div>' for m in matches])
            output = self.channel_t.replace("{{CHANNEL_NAME}}", name).replace("{{LISTING}}", listing).replace("{{DOMAIN}}", DOMAIN)
            with open(os.path.join(path, "index.html"), "w") as f: f.write(output)
            self.sitemap_urls.append(f"{DOMAIN}/channel/{slug}/")

    def write_sitemap(self):
        urlset = Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for loc in self.sitemap_urls:
            u = SubElement(urlset, 'url')
            SubElement(u, 'loc').text = loc
        with open(os.path.join(OUTPUT_FOLDER, "sitemap.xml"), "wb") as f:
            f.write(tostring(urlset))

    def run(self):
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        self.fetch_data()
        self.generate_match_pages()
        self.generate_daily_pages()
        self.generate_channel_pages()
        self.write_sitemap()
        logging.info("Build Complete.")

if __name__ == "__main__":
    StaticSiteGenerator().run()
