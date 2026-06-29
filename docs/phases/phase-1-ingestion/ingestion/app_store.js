/**
 * Fetch recent Spotify App Store reviews (id=324684580).
 * Paginates until REVIEW_WINDOW_WEEKS is exhausted or MAX_PAGES reached.
 * Outputs JSON array to stdout.
 */
const store = require('app-store-scraper');

const APP_ID = 324684580;
const WEEKS = parseInt(process.env.REVIEW_WINDOW_WEEKS || '12', 10);
const MAX_PAGES = parseInt(process.env.APP_STORE_MAX_PAGES || '15', 10);

function cutoffDate() {
  const d = new Date();
  d.setDate(d.getDate() - WEEKS * 7);
  return d;
}

function toRecord(r) {
  return {
    source: 'app_store',
    date: r.updated instanceof Date ? r.updated.toISOString() : new Date(r.updated).toISOString(),
    rating: r.score,
    title: r.title || '',
    text: r.text || '',
  };
}

async function fetchReviews() {
  const since = cutoffDate();
  const all = [];
  const seen = new Set();

  for (let page = 1; page <= MAX_PAGES; page++) {
    const batch = await store.reviews({
      id: APP_ID,
      sort: store.sort.RECENT,
      page,
    });

    if (!batch || batch.length === 0) break;

    let oldestInPage = null;
    for (const r of batch) {
      const updated = r.updated instanceof Date ? r.updated : new Date(r.updated);
      if (!oldestInPage || updated < oldestInPage) oldestInPage = updated;
      if (updated < since) continue;
      const key = `${r.title}|${r.text}`;
      if (seen.has(key)) continue;
      seen.add(key);
      all.push(toRecord(r));
    }

    if (oldestInPage && oldestInPage < since) break;
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
