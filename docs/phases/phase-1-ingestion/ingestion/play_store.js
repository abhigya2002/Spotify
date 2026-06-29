/**
 * Fetch recent Spotify Play Store reviews (com.spotify.music).
 * google-play-scraper v10 is ESM — use default export from require().
 */
const gplayModule = require('google-play-scraper');
const gplay = gplayModule.default || gplayModule;

const APP_ID = 'com.spotify.music';
const WEEKS = parseInt(process.env.REVIEW_WINDOW_WEEKS || '12', 10);
const MAX_PAGES = parseInt(process.env.PLAY_STORE_MAX_PAGES || '20', 10);

function cutoffMs() {
  return Date.now() - WEEKS * 7 * 24 * 60 * 60 * 1000;
}

function toRecord(r) {
  return {
    source: 'play_store',
    date: new Date(r.date).toISOString(),
    rating: r.score,
    title: r.title || '',
    text: r.text || '',
  };
}

async function fetchReviews() {
  const since = cutoffMs();
  const all = [];
  const seen = new Set();
  let token = undefined;

  for (let page = 0; page < MAX_PAGES; page++) {
    const opts = {
      appId: APP_ID,
      sort: gplay.sort.NEWEST,
      num: 150,
      paginate: true,
    };
    if (token) opts.nextPaginationToken = token;

    const result = await gplay.reviews(opts);
    const batch = result.data || [];
    if (batch.length === 0) break;

    let oldestInPage = Infinity;
    for (const r of batch) {
      const ts = new Date(r.date).getTime();
      if (ts < oldestInPage) oldestInPage = ts;
      if (ts < since) continue;
      const key = `${r.title}|${r.text}`;
      if (seen.has(key)) continue;
      seen.add(key);
      all.push(toRecord(r));
    }

    token = result.nextPaginationToken;
    if (!token || oldestInPage < since) break;
  }

  return all;
}

fetchReviews()
  .then((reviews) => {
    process.stdout.write(JSON.stringify(reviews));
  })
  .catch((e) => {
    console.error(e);
    process.exit(1);
  });
