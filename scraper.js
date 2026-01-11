const fs = require('fs');
const path = require('path');

// Pretend to be a real Chrome browser
const HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
    "Accept": "*/*"
};

const getTomorrowDate = () => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().split('T')[0];
};

async function fetchWithRetry(url) {
    try {
        const response = await fetch(url, { headers: HEADERS });
        if (!response.ok) return null;
        return await response.json();
    } catch (e) {
        return null;
    }
}

async function fetchMatchData(matchId) {
    const evData = await fetchWithRetry(`https://api.sofascore.com/api/v1/event/${matchId}`);
    const tvData = await fetchWithRetry(`https://api.sofascore.com/api/v1/tv/event/${matchId}/country-channels`);

    if (!evData || !evData.event) return null;
    const ev = evData.event;

    let broadcasters = [];
    if (tvData?.countryChannels) {
        const codes = Object.keys(tvData.countryChannels);
        for (const code of codes) {
            const channels = await Promise.all(tvData.countryChannels[code].map(async (chId) => {
                const d = await fetchWithRetry(`https://api.sofascore.com/api/v1/tv/channel/${chId}/schedule`);
                return d?.channel?.name || "Unknown Channel";
            }));
            const cleanChannels = [...new Set(channels)].filter(c => c !== "Unknown Channel");
            broadcasters.push({ country: code, channels: cleanChannels.length > 0 ? cleanChannels : ["TBA"] });
        }
    }

    return {
        match_id: ev.id,
        kickoff: ev.startTimestamp,
        fixture: `${ev.homeTeam.name} vs ${ev.awayTeam.name}`,
        league: ev.tournament.name,
        tv_channels: broadcasters
    };
}

async function run() {
    const date = getTomorrowDate();
    const fileName = date.replace(/-/g, '') + '.json';
    const dir = './date';

    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    console.log(`Fetching matches for ${date}...`);
    // Note: We use the 'inverse' endpoint if the main one is empty
    let data = await fetchWithRetry(`https://api.sofascore.com/api/v1/sport/football/scheduled-events/${date}`);
    
    let events = data?.events || [];
    
    if (events.length === 0) {
        console.log("Main feed empty, trying inverse feed...");
        data = await fetchWithRetry(`https://api.sofascore.com/api/v1/sport/football/scheduled-events/${date}/inverse`);
        events = data?.events || [];
    }

    console.log(`Found ${events.length} events. Starting deep scrape...`);

    const results = [];
    // Only scrape the first 50 to avoid getting banned by SofaScore (GitHub IPs are sensitive)
    const limitedEvents = events.slice(0, 50); 

    for (const event of limitedEvents) {
        const detail = await fetchMatchData(event.id);
        if (detail) {
            results.push(detail);
            console.log(`✓ Added: ${detail.fixture}`);
        }
        // Small delay to prevent rate-limiting
        await new Promise(r => setTimeout(r, 500));
    }

    fs.writeFileSync(path.join(dir, fileName), JSON.stringify(results, null, 4));
    console.log(`DONE: Saved ${results.length} matches to date/${fileName}`);
}

run();
