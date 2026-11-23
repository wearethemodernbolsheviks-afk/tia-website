// Cloudflare Worker for invariancetech.info.
// Static files are served straight from the repository. This script only runs for
// paths with no matching file: it answers /api/substack and serves the 404 page otherwise.

const PUB = 'https://technicalinvariance.substack.com';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === '/api/substack') return substack(request, ctx);
    const notFound = await env.ASSETS.fetch(new URL('/404.html', url));
    return new Response(notFound.body, { status: 404, headers: notFound.headers });
  },
};

async function substack(request, ctx) {
  const cache = caches.default;
  const key = new Request(new URL('/api/substack', request.url).toString());
  const hit = await cache.match(key);
  if (hit) return hit;

  let posts = [];
  try {
    const r = await fetch(`${PUB}/api/v1/archive?sort=new&offset=0&limit=50`, {
      headers: { Accept: 'application/json', 'User-Agent': 'invariancetech.info' },
    });
    if (r.ok) {
      const data = await r.json();
      posts = (Array.isArray(data) ? data : []).map((p) => ({
        title: p.title || '',
        subtitle: p.subtitle || p.description || '',
        date: p.post_date || '',
        url: p.canonical_url || `${PUB}/p/${p.slug}`,
        image: p.cover_image || '',
        paid: Boolean(p.audience && p.audience !== 'everyone'),
      }));
    }
  } catch (e) {}

  if (!posts.length) {
    try {
      const r = await fetch(`${PUB}/feed`, { headers: { 'User-Agent': 'invariancetech.info' } });
      if (r.ok) posts = parseRss(await r.text());
    } catch (e) {}
  }

  const res = new Response(JSON.stringify({ publication: PUB, updated: new Date().toISOString(), posts }), {
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'public, max-age=900',
    },
  });
  ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}

function parseRss(xml) {
  const text = (s) => (s || '').replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1').replace(/<[^>]+>/g, '').trim();
  const tag = (block, name) => {
    const m = block.match(new RegExp(`<${name}[^>]*>([\\s\\S]*?)</${name}>`));
    return m ? m[1] : '';
  };
  const items = xml.match(/<item>[\s\S]*?<\/item>/g) || [];
  return items.map((it) => {
    const enc = it.match(/<enclosure[^>]+url="([^"]+)"/);
    return {
      title: text(tag(it, 'title')),
      subtitle: text(tag(it, 'description')),
      date: text(tag(it, 'pubDate')),
      url: text(tag(it, 'link')),
      image: enc ? enc[1] : '',
      paid: false,
    };
  });
}
