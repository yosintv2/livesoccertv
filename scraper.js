const fs = require('fs');
const path = require('path');

// Helper to get date string for "Tomorrow"
const getTomorrowDate = () => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().split('T')[0];
};

async function fetchMatchData(matchId) {
    try {
        const evR = await fetch(`https://api.sofascore.com/api/v1/event/${matchId}`);
        const tvR = await fetch(`https://api.sofascore.com/api/v1/tv/event/${matchId}/country-channels`);
        
        const evData = await evR.json();
        const tvData = await tvR.json();
        const ev = evData.event;

        let broadcasters = [];
        if (tvData?.countryChannels) {
            const codes = Object.keys(tvData.countryChannels);
            for (const code of codes) {
                const channels = await Promise.all(tvData.countryChannels[code].map(async (chId) => {
                    try {
                        const res = await fetch(`https://api.sofascore.com/api/v1/tv/channel/${chId}/schedule`);
                        const d = await res.json();
                        return d.channel?.name || "Unknown Channel";
                    } catch { return "Unknown Channel"; }
                }));
                broadcasters.push({ country: code, channels: [...new Set(channels)] });
            }
        }

        return {
            match_id: ev.id,
            kickoff: ev.startTimestamp,
            fixture: `${ev.homeTeam.name} vs ${ev.awayTeam.name}`,
            league: ev.tournament.name,
            tv_channels: broadcasters
        };
    } catch (e) { return null; }
}

async function run() {
    const date = getTomorrowDate();
    const fileName = date.replace(/-/g, '') + '.json';
    const dir = './date';

    if (!fs.existsSync(dir)) fs.mkdirSync(dir);

    console.log(`Fetching matches for ${date}...`);
    const r = await fetch(`https://api.sofascore.com/api/v1/sport/football/scheduled-events/${date}`);
    const data = await r.json();
    const events = data.events || [];

    const results = [];
    // Processing in chunks to avoid rate limits
    for (const event of events) {
        console.log(`Processing: ${event.homeTeam.name} vs ${event.awayTeam.name}`);
        const detail = await fetchMatchData(event.id);
        if (detail) results.push(detail);
    }

    fs.writeFileSync(path.join(dir, fileName), JSON.stringify(results, null, 4));
    console.log(`Saved ${results.length} matches to ${fileName}`);
}

run();
