#!/usr/bin/env python3
"""Build the TIA archive.

Reads  content/catalogue.json, content/texts/<id>.txt and the page templates
in tools/templates/, and writes the static archive into the site:

  archive/index.html                         index of Marxists, search, filters
  archive/<author>/index.html                one dossier page per thinker
  archive/<author>/<work>/index.html         reader page for each hosted text
  archive/<author>/<work>/<work>.txt         plain-text download
  archive/collections/<slug>/index.html      collection pages
  archive/catalogue.json                     search index (metadata)
  archive/text/<id>.json                     search index (full text, by paragraph)
  index.html                                 homepage, with archive links and search wired up
  sitemap.xml

Standard library only. Run from anywhere:  python3 tools/build_archive.py
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / 'content'
TPL = ROOT / 'tools' / 'templates'
SITE = 'https://invariancetech.info'

TENDENCY = {'PRECURSOR': 'precursor', 'FOUNDER': 'founders', 'SECOND INTERNATIONAL': 'second',
            'BOLSHEVIK': 'bolsheviks', 'SPARTACIST': 'spartacists', 'WESTERN MARXISM': 'western', 'COMMUNIST LEFT': 'left',
            'MARXISTISCHE GRUPPE': 'mg'}
CHIPS = [('all', 'ALL'), ('precursor', 'PRECURSOR'), ('founders', 'FOUNDERS'),
         ('second', 'SECOND INTERNATIONAL'), ('bolsheviks', 'BOLSHEVIKS'),
         ('spartacists', 'SPARTACISTS'), ('western', 'WESTERN MARXISM'), ('left', 'COMMUNIST LEFT'),
         ('mg', 'MARXISTISCHE GRUPPE')]
DISPLAY = {'hegel': 'G. W. F. Hegel', 'marx': 'Karl Marx', 'engels': 'Friedrich Engels',
           'lassalle': 'Ferdinand Lassalle', 'kautsky': 'Karl Kautsky', 'plekhanov': 'G. V. Plekhanov', 'lenin': 'V. I. Lenin', 'trotsky': 'Leon Trotsky',
           'luxemburg': 'Rosa Luxemburg', 'liebknecht': 'Karl Liebknecht', 'bukharin': 'N. I. Bukharin', 'lukacs': 'Georg Lukács', 'gramsci': 'Antonio Gramsci', 'bordiga': 'Amadeo Bordiga',
           'gegenstandpunkt': 'GegenStandpunkt'}


# Full-colour posters used as moving backgrounds (no duotone).
POSTER = {'hegel': 'p_hp_napoleon', 'marx': 'p_mon_marx_chemnitz', 'engels': 'p_mon_magnitogorsk',
          'lassalle': 'p_hp_marianne', 'kautsky': 'p_share_the_land', 'plekhanov': 'p_nine_days', 'lenin': 'p_mon_lenin_head', 'trotsky': 'p_raise_it_higher',
          'luxemburg': 'p_rom_romantics', 'liebknecht': 'p_rom_come_back', 'bukharin': 'p_mon_worker_kolkhoz', 'lukacs': 'p_mon_motherland_bw', 'gramsci': 'p_mon_motherland_bw', 'bordiga': 'p_audit_no_country',
          'gegenstandpunkt': 'p_mon_towers'}
AUTHOR_WALL = {
    'hegel': ['p_hp_marianne', 'p_hp_napoleon', 'p_mon_moon', 'p_mon_motherland_bw'],
    'marx': ['p_mon_magnitogorsk', 'p_mon_worker_kolkhoz', 'p_mon_motherland_bw', 'p_audit_no_country'],
    'engels': ['p_mon_marx_chemnitz', 'p_rom_five_year', 'p_mon_magnitogorsk', 'p_share_the_land'],
    'lassalle': ['p_hp_marianne', 'p_hp_napoleon', 'p_share_the_land', 'p_rom_romantics'],
    'kautsky': ['p_hp_marianne', 'p_share_the_land', 'p_rom_come_back', 'p_mon_worker_kolkhoz'],
    'lenin': ['p_nine_days', 'p_mon_motherland_flags', 'p_raise_it_higher', 'p_mon_moon'],
    'trotsky': ['p_mon_motherland_sunset', 'p_raise_it_higher', 'p_nine_days', 'p_mon_motherland_flags'],
    'luxemburg': ['p_rom_romantics', 'p_hp_marianne', 'p_rom_come_back', 'p_raise_it_higher'],
    'liebknecht': ['p_rom_come_back', 'p_raise_it_higher', 'p_hp_marianne', 'p_nine_days'],
    'bukharin': ['p_rom_five_year', 'p_mon_worker_kolkhoz', 'p_mon_towers', 'p_share_the_land'],
    'lukacs': ['p_mon_motherland_bw', 'p_rom_five_year', 'p_mon_moon', 'p_hp_napoleon'],
    'bordiga': ['p_audit_no_country', 'p_mon_towers', 'p_mon_motherland_sunset', 'p_mon_moon'],
}
COL_WALL = {
    'the-programme': ['p_audit_no_country', 'p_mon_marx_chemnitz', 'p_mon_lenin_head', 'p_raise_it_higher'],
    'marx-and-engels': ['p_mon_marx_chemnitz', 'p_mon_magnitogorsk', 'p_mon_worker_kolkhoz', 'p_hp_napoleon'],
    'second-international': ['p_share_the_land', 'p_hp_marianne', 'p_rom_come_back', 'p_mon_motherland_bw'],
    'lenin-and-october': ['p_mon_lenin_head', 'p_nine_days', 'p_raise_it_higher', 'p_mon_motherland_flags'],
    'the-german-left': ['p_rom_romantics', 'p_hp_marianne', 'p_raise_it_higher', 'p_rom_come_back'],
    'the-communist-left': ['p_audit_no_country', 'p_mon_towers', 'p_mon_moon', 'p_mon_motherland_sunset'],
}
# One poster per collection and one for the index; none is used twice.
COL_POSTER = {'the-programme': 'p_mon_motherland_bw', 'marx-and-engels': 'p_rom_five_year',
              'second-international': 'p_hp_marianne', 'lenin-and-october': 'p_nine_days',
              'the-german-left': 'p_mon_motherland_sunset', 'the-communist-left': 'p_mon_towers'}
INDEX_POSTER = 'p_mon_motherland_flags'


def wall(posters, opacity):
    """A slowly drifting wall of posters in four columns (two on phones)."""
    imgs = ', '.join(f"url('/assets/bgc/{p}.webp')" for p in posters)
    return (f'<div class="wall" aria-hidden="true" style="--o: {opacity}">'
            f'<div class="wall-in" style="background-image: {imgs}"></div></div>')


BGP_SIZES = json.loads((ROOT / 'assets' / 'bgp' / 'sizes.json').read_text(encoding='utf-8'))


def poster_ar(poster):
    w, h = BGP_SIZES.get(poster, (720, 900))
    return f'{w / h:.4f}'


def page_bg(poster):
    if not poster:
        return ''
    return (f'<div class="page-bg" aria-hidden="true" style="--ar: {poster_ar(poster)}; --p1: url(\'/assets/bgp/{poster}-1x.webp\'); '
            f'--p2: url(\'/assets/bgp/{poster}.webp\')"></div>\n')


def side_poster(poster):
    return f'<div class="side-poster" aria-hidden="true" style="background-image: url(\'/assets/bgp/{poster}.webp\')"></div>'


def esc(s):
    return html.escape(s, quote=False)


def attr(s):
    return html.escape(s, quote=True)


def year0(y):
    m = re.search(r'\d{4}', y)
    return int(m.group()) if m else 0


def words(n):
    return f'{n:,}'


# ---------------------------------------------------------------- templates

ARCH_TPL = (TPL / 'archive_index.html').read_text(encoding='utf-8')
HOME_TPL = (TPL / 'home_index.html').read_text(encoding='utf-8')
NAV_EXTRA = '<a href="/watch/">WATCH</a>\n      <a href="/dispatches/">DISPATCHES</a>'
ARCH_TPL = ARCH_TPL.replace('<a href="/#watch">WATCH</a>', NAV_EXTRA, 1)
SUBSTACK = 'https://technicalinvariance.substack.com'
DISPATCH_POSTER = 'p_rom_come_back'
DSP_CSS = """
.dsp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap: 22px; margin-top: 32px; }
.dsp-card { display: flex; flex-direction: column; background: #0F0A0B; border: 1px solid #3A2326; color: #F2ECE4; transition: border-color 200ms ease; }
.dsp-card:hover { border-color: #E8222A; color: #F2ECE4; }
.dsp-img { position: relative; aspect-ratio: 16 / 9; overflow: hidden; background-color: #090506; background-image: linear-gradient(rgba(242, 236, 228, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(242, 236, 228, 0.04) 1px, transparent 1px); background-size: 24px 24px; border-bottom: 1px solid #3A2326; }
.dsp-img > img { width: 100%; height: 100%; object-fit: cover; }
.dsp-ph { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }
.dsp-ph img { width: 76px; height: auto; opacity: 0.85; }
.dsp-no { position: absolute; left: 10px; top: 10px; padding: 3px 8px; background: rgba(9, 5, 6, 0.85); font-size: 11px; letter-spacing: 0.12em; color: #FF5A60; }
.dsp-bd { display: flex; flex-direction: column; gap: 8px; padding: 16px 18px 18px; flex: 1; }
.dsp-d { font-size: 12px; letter-spacing: 0.12em; color: #A89C95; }
.dsp-t { font-weight: 800; font-size: 20px; line-height: 1.25; }
.dsp-s { font-size: 15px; line-height: 1.5; color: #CFC4BC; }
.dsp-go { margin-top: auto; padding-top: 8px; font-size: 13px; letter-spacing: 0.12em; color: #FF5A60; }
.dsp-empty { grid-column: 1 / -1; padding: 26px; border: 1px dashed #3A2326; background: rgba(9, 5, 6, 0.75); }
.dsp-empty p { margin: 0 0 12px; color: #DCD2CA; }
.dsp-empty a { font-size: 14px; letter-spacing: 0.12em; color: #FF5A60; }
.dsp-wait { grid-column: 1 / -1; font-size: 13px; letter-spacing: 0.12em; color: #A89C95; }
.dsp-btn { display: inline-flex; align-items: center; gap: 10px; min-height: 48px; padding: 0 22px; background: #C81D25; color: #FFFFFF; font-family: Inter, sans-serif; font-weight: 800; }
.dsp-btn:hover { background: #E8222A; color: #FFFFFF; }
.dsp-btn.gh { background: transparent; border: 2px solid #F2ECE4; color: #F2ECE4; }
.dsp-btn.gh:hover { border-color: #FF5A60; color: #FF5A60; }
"""
ROOM_CSS = """
/* the household-terminal room: cream paper and red ink, as in Oppie's America and ALL POWER */
.room { --pi: #3A0A0D; --pd: #7A4A47; --pr: #CE121E; --pl: #E2C8C2; --pp: #FBF6F3; position: relative; color: var(--pi); background-color: #F4ECE6; background-image: linear-gradient(rgba(110, 8, 14, 0.055) 1px, transparent 1px), linear-gradient(90deg, rgba(110, 8, 14, 0.055) 1px, transparent 1px); background-size: 48px 48px; border-top: 3px solid #CE121E; border-bottom: 3px solid #CE121E; }
.room a { color: var(--pi); }
.room a:hover { color: var(--pr); }
.room .tag { border-color: var(--pr); color: var(--pr); background: var(--pp); }
.room .h2, .room h2 { color: var(--pi) !important; text-shadow: none !important; }
.room .src { color: var(--pd); }
.room .lede { color: #5A3431; }
.room .rbar { display: flex; justify-content: space-between; gap: 12px; margin: 0; padding: 7px 12px; background: var(--pr); color: #F6EEEA; font-size: 13px; letter-spacing: 0.14em; }
.room .dsp-card { background: var(--pp); border-color: var(--pl); color: var(--pi); box-shadow: 0 1px 0 rgba(58, 10, 13, 0.06); }
.room .dsp-card:hover { border-color: var(--pr); color: var(--pi); }
.room .dsp-img { background-color: #EADBD5; background-image: linear-gradient(rgba(110, 8, 14, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(110, 8, 14, 0.06) 1px, transparent 1px); border-bottom-color: var(--pl); }
.room .dsp-no { background: var(--pr); color: #F6EEEA; }
.room .dsp-d { color: var(--pd); }
.room .dsp-s { color: #5A3431; }
.room .dsp-go { color: var(--pr); }
.room .dsp-empty { border-color: var(--pl); background: var(--pp); }
.room .dsp-empty p { color: var(--pi); }
.room .dsp-empty a, .room .dsp-wait { color: var(--pr); }
.room .dsp-btn { color: #FFFFFF; }
.room .dsp-btn:hover { background: #A80E18; color: #FFFFFF; }
.room .dsp-btn.gh { background: transparent; border-color: var(--pi); color: var(--pi); }
.room .dsp-btn.gh:hover { border-color: var(--pr); color: var(--pr); }
.room .btn-s { display: inline-flex; align-items: center; min-height: 48px; padding: 0 22px; border: 2px solid var(--pi); color: var(--pi); font-weight: 800; }
.room .btn-s:hover { border-color: var(--pr); color: var(--pr); }
.room .btn-p { display: inline-flex; align-items: center; min-height: 48px; padding: 0 22px; background: var(--pr); color: #FFFFFF; font-weight: 800; }
.room .btn-p:hover { background: #A80E18; color: #FFFFFF; }
"""

DSP_WAIT = '<p class="dsp-wait mn">LOADING DISPATCHES FROM SUBSTACK…</p>'


BASE_CSS = re.search(r'<style>\n(.*?)</style>', ARCH_TPL, re.S).group(1)
OVERLAYS = re.search(r'(<div aria-hidden="true">\n  <div class="ov-lines">.*?\n</div>\n)', ARCH_TPL, re.S).group(1)
HEADER = re.search(r'(<header class="tbar">.*?</header>)', ARCH_TPL, re.S).group(1)
FOOTER = re.search(r'(<footer.*?</footer>)', ARCH_TPL, re.S).group(1)
TIMELINE = re.search(r'(<figure class="it-rv".*?</figure>)', ARCH_TPL, re.S).group(1)
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900'
         '&amp;family=Lora:ital,wght@0,400;0,600;1,400&amp;family=JetBrains+Mono:wght@400;500;700&amp;display=swap" rel="stylesheet">')

EXTRA_CSS = """
@media (max-width: 1500px) { .tbar .wrap > span.mn:last-child { display: none; } }
/* the whole poster, shown no bigger than the sharp 2x copy allows, set against the dark page on the right */
.page-bg { position: fixed; top: 0; right: 0; width: min(58vw, calc(100vh * var(--ar, 0.8)), 1440px); aspect-ratio: var(--ar, 0.8); max-height: 100vh; z-index: -1; pointer-events: none; background-image: var(--p1); background-image: image-set(var(--p1) 1x, var(--p2) 2x); background-size: cover; background-position: center top; -webkit-mask-image: linear-gradient(to right, transparent 0%, rgba(0, 0, 0, 0.55) 22%, #000 48%), linear-gradient(to bottom, #000 70%, transparent); mask-image: linear-gradient(to right, transparent 0%, rgba(0, 0, 0, 0.55) 22%, #000 48%), linear-gradient(to bottom, #000 70%, transparent); -webkit-mask-composite: source-in; mask-composite: intersect; }
.page-bg::after { content: ""; position: absolute; inset: 0; background: linear-gradient(to bottom, rgba(9, 5, 6, 0.25), rgba(9, 5, 6, 0.1) 40%, rgba(9, 5, 6, 0.55)); }
@media (max-width: 760px) { .page-bg { left: 0; width: 100%; max-height: none; -webkit-mask-image: linear-gradient(to bottom, #000 30%, transparent); mask-image: linear-gradient(to bottom, #000 30%, transparent); opacity: 0.5; } }
.wall { position: absolute; inset: 0; overflow: hidden; pointer-events: none; opacity: var(--o, 0.2); -webkit-mask-image: linear-gradient(to bottom, transparent, #000 10%, #000 90%, transparent); mask-image: linear-gradient(to bottom, transparent, #000 10%, #000 90%, transparent); }
.wall-in { position: absolute; left: 0; right: 0; top: -19.444vw; bottom: 0; background-repeat: repeat-y; background-size: 25% auto; background-position: 0 0, 33.333% 41%, 66.667% 17%, 100% 63%; animation: it-wall 150s linear infinite; }
@keyframes it-wall { from { transform: translateY(0); } to { transform: translateY(19.444vw); } }
@keyframes it-wall-m { from { transform: translateY(0); } to { transform: translateY(38.889vw); } }
.wall ~ .wrap, .side-poster ~ .wrap { position: relative; z-index: 1; }
.side-poster { position: absolute; top: 0; bottom: 0; right: 0; width: min(54%, 720px); background-size: cover; background-position: center top; opacity: 0.62; -webkit-mask-image: linear-gradient(to right, transparent, #000 62%); mask-image: linear-gradient(to right, transparent, #000 62%); pointer-events: none; }
.shade { text-shadow: 0 2px 18px rgba(9, 5, 6, 0.95), 0 0 2px rgba(9, 5, 6, 0.9); }
.dos-bg { position: absolute; inset: 0; background-size: cover; background-position: center; opacity: 0.22; transition: opacity 300ms ease; }
.dos:hover .dos-bg { opacity: 0.42; }
.dos-img img { position: relative; z-index: 1; }
@media (max-width: 760px) {
  .wall-in { top: -38.889vw; background-size: 50% auto; background-position: 0 0, 100% 45%, 0 0, 100% 45%; animation-name: it-wall-m; }
  .side-poster { width: 100%; opacity: 0.28; -webkit-mask-image: linear-gradient(to bottom, #000 30%, transparent); mask-image: linear-gradient(to bottom, #000 30%, transparent); }
}
@media (prefers-reduced-motion: reduce) { .wall-in, .side-poster { animation: none !important; } }
.dos[hidden] { display: none; }
.dos-body ul a { color: #DCD2CA; border-bottom: 1px dotted #4A2B2E; }
.dos-body ul a:hover { color: #FF5A60; border-bottom-color: #E8222A; }
.dos-body ul .h { color: #39D98A; font-size: 11px; letter-spacing: 0.12em; margin-left: 6px; }
.dos-body .cnt { margin: 6px 0 0; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; letter-spacing: 0.12em; color: #A89C95; }
.dos-body .cnt b { font-weight: 400; color: #39D98A; }
.dos h3 a { color: inherit; }
.crumbs { font-size: 13px; letter-spacing: 0.14em; color: #A89C95; }
.crumbs a { color: #A89C95; border-bottom: 1px solid #3A2326; }
.crumbs a:hover { color: #FF5A60; }
.sec-h { margin: 0; font-size: 18px; letter-spacing: 0.1em; border-bottom: 1px solid #3A2326; padding-bottom: 10px; }
.row.wk { align-items: flex-start; }
.row .y { flex: 0 0 auto; min-width: 92px; color: #FF5A60; }
.row .ti { min-width: 0; flex: 0 1 auto; color: #F2ECE4; }
.row .ti small { display: block; margin-top: 3px; font-family: Inter, system-ui, sans-serif; font-size: 14px; letter-spacing: 0; color: #A89C95; }
.row .by { flex: 0 0 auto; color: #A89C95; }
.row .st { flex: 0 0 auto; white-space: nowrap; }
.row .st.ok { color: #39D98A; }
.row .st.ln { color: #A89C95; }
.row .st.sn { color: #F5B83D; }
.soon-box { margin: 0 0 44px; padding: 18px 18px 8px; border: 1px solid #5A4520; background: rgba(40, 28, 8, 0.55); }
.soon-box .sec-h { color: #F5B83D; }
.soon-box .sec-h span { color: #CFC4BC; }
.soon-box > p.lede { margin: 0 0 10px; max-width: 760px; font-size: 16px; color: #ECE4DC; }
.soon-item { display: flex; gap: 16px; padding: 14px 0; border-top: 1px solid #5A4520; color: #F2ECE4; }
.soon-item .y { flex: 0 0 64px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 15px; color: #F5B83D; padding-top: 2px; }
.soon-item .t { min-width: 0; }
.soon-item b { display: block; font-family: 'JetBrains Mono', ui-monospace, monospace; font-weight: 400; font-size: 18px; line-height: 1.3; letter-spacing: 0.02em; }
.soon-item small { display: block; margin-top: 4px; font-size: 14px; line-height: 1.45; color: #B3A79F; }
.soon-item i { display: block; margin-top: 6px; font-style: normal; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; letter-spacing: 0.1em; color: #A89C95; }
.soon-item:hover b, .soon-item:hover i { color: #F5B83D; }
.row .st.wait { color: #E8A33A; }
.row.wk .ld { align-self: center; transform: none; }
a.row:hover .ti { color: #FF5A60; }
.note { margin: 0 0 32px; padding: 16px 18px; border: 1px solid #E8A33A; background: rgba(232, 163, 58, 0.07); font-size: 16px; color: #EADFCB; }
.note b { font-family: 'JetBrains Mono', ui-monospace, monospace; font-weight: 400; letter-spacing: 0.12em; color: #E8A33A; margin-right: 8px; }
.btn { display: inline-flex; align-items: center; min-height: 48px; padding: 0 18px; box-sizing: border-box; background: #C81D25; color: #FFFFFF; font-family: Inter, sans-serif; font-weight: 800; font-size: 16px; }
.btn:hover { background: #E8222A; color: #FFFFFF; }
.btn.gh { background: transparent; border: 1px solid #3A2326; color: #F2ECE4; font-family: 'JetBrains Mono', ui-monospace, monospace; font-weight: 400; font-size: 14px; letter-spacing: 0.1em; }
.btn.gh:hover { border-color: #E8222A; color: #FF5A60; }
.pn { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; margin-top: 48px; padding-top: 18px; border-top: 1px solid #3A2326; font-size: 14px; letter-spacing: 0.12em; }
.pn a { color: #FF5A60; }
.stats { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 24px; }
.stats div { min-width: 120px; padding: 12px 14px; border: 1px solid #3A2326; background: rgba(9, 5, 6, 0.8); }
.stats b { display: block; font-family: Inter, sans-serif; font-weight: 900; font-size: 34px; line-height: 1; color: #F2ECE4; }
.stats span { display: block; margin-top: 6px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; letter-spacing: 0.12em; color: #A89C95; }
.au-grid { display: grid; grid-template-columns: minmax(0, 380px) minmax(0, 1fr); gap: 40px; align-items: end; margin-top: 22px; }
.au-img { height: 440px; border: 1px solid #3A2326; }
@media (max-width: 860px) { .au-grid { grid-template-columns: 1fr; } .au-img { height: 340px; } }
#ar-results { scroll-margin-top: 90px; }
.res-box { padding: 18px; border: 1px solid #3A2326; background: rgba(9, 5, 6, 0.85); }
.res-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; font-size: 14px; letter-spacing: 0.12em; color: #A89C95; }
.res-head b { font-weight: 400; color: #F2ECE4; }
.hit-list { list-style: none; margin: 0; padding: 0; }
.hit-list li { padding: 14px 0; border-bottom: 1px solid #241618; }
.hit-list .hw { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 13px; letter-spacing: 0.1em; color: #A89C95; }
.hit-list .hw a { color: #FF5A60; }
.hit-list q { display: block; margin-top: 6px; quotes: none; font-family: Lora, Georgia, serif; font-size: 17px; line-height: 1.6; color: #DCD2CA; }
.hit-list q::before { content: "… "; color: #7A4246; }
.hit-list q::after { content: " …"; color: #7A4246; }
mark { background: rgba(232, 34, 42, 0.42); color: #FFFFFF; padding: 0 2px; }
.scan-bar { height: 2px; margin-top: 10px; background: #241618; overflow: hidden; }
.scan-bar i { display: block; height: 100%; width: 0; background: #E8222A; box-shadow: 0 0 8px rgba(232, 34, 42, 0.8); transition: width 160ms linear; }
"""

READER_CSS = """
.rd-poster { position: fixed; top: 0; right: 0; width: min(40vw, calc(100vh * var(--ar, 0.8))); aspect-ratio: var(--ar, 0.8); max-height: 100vh; z-index: 0; pointer-events: none; background-size: cover; background-position: center top; opacity: 0.34; -webkit-mask-image: linear-gradient(to right, transparent, #000 72%), linear-gradient(to bottom, #000 65%, transparent); mask-image: linear-gradient(to right, transparent, #000 72%), linear-gradient(to bottom, #000 65%, transparent); -webkit-mask-composite: source-in; mask-composite: intersect; }
.rd-hero-wrap, .rd-layout { position: relative; z-index: 1; }
@media (max-width: 1000px) { .rd-poster { width: 100%; opacity: 0.1; -webkit-mask-image: none; mask-image: none; } }
.ov-lines { opacity: 0.4; }
.ov-grain { opacity: 0.22; }
.rd-prog { display: none; }
@supports (animation-timeline: scroll()) {
  @keyframes rd-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
  .rd-prog { display: block; position: fixed; top: 0; left: 0; right: 0; height: 3px; z-index: 70; background: #E8222A; box-shadow: 0 0 10px rgba(232, 34, 42, 0.9); transform-origin: 0 50%; animation: rd-grow linear both; animation-timeline: scroll(root); }
}
.rd-head { display: flex; flex-wrap: wrap; gap: 28px 40px; align-items: flex-end; margin-top: 22px; }
.rd-head .bust { flex: 0 0 150px; height: 190px; position: relative; overflow: hidden; border: 1px solid #3A2326; background: #090506; display: flex; align-items: flex-end; justify-content: center; }
.rd-head .bust img { height: 94%; width: auto; }
.rd-h1 { margin: 16px 0 0; font-family: Inter, system-ui, sans-serif; font-weight: 900; letter-spacing: -0.012em; font-size: clamp(30px, 3.8vw, 54px); line-height: 1.02; color: #F2ECE4; text-transform: uppercase; }
.rd-sub { margin: 12px 0 0; max-width: 760px; font-size: 18px; color: #CFC4BC; }
.rd-ed { margin: 14px 0 0; max-width: 760px; font-size: 15px; color: #A89C95; }
.rd-ed a, .text a { color: #FF8A8E; border-bottom: 1px dotted #6E3A3D; overflow-wrap: anywhere; }
.rd-ed a:hover, .text a:hover { color: #FF5A60; }
.rd-act { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
.rd-layout { display: grid; grid-template-columns: 270px minmax(0, 1fr); gap: 56px; padding-top: 40px; padding-bottom: 80px; }
.rd-layout.solo { grid-template-columns: minmax(0, 880px); justify-content: center; }
.toc { position: sticky; top: 96px; align-self: start; max-height: calc(100vh - 120px); overflow: auto; padding-right: 6px; scrollbar-width: thin; scrollbar-color: #3A2326 transparent; }
.toc p, .toc-m summary { margin: 0 0 10px; font-size: 13px; letter-spacing: 0.14em; color: #A89C95; }
.toc ol, .toc-m ol { list-style: none; margin: 0; padding: 0; border-left: 1px solid #3A2326; }
.toc li a, .toc-m li a { display: block; padding: 6px 0 6px 14px; margin-left: -1px; border-left: 2px solid transparent; font-size: 12px; line-height: 1.35; letter-spacing: 0.08em; color: #CFC4BC; }
.toc li a:hover, .toc li a.on { color: #FF5A60; border-left-color: #E8222A; }
.toc-m { display: none; margin-bottom: 28px; padding: 14px 16px; border: 1px solid #3A2326; background: #0F0A0B; }
.toc-m summary { margin: 0; cursor: pointer; color: #F2ECE4; }
.toc-m ol { margin-top: 12px; max-height: 60vh; overflow: auto; }
@media (max-width: 1000px) { .rd-layout { grid-template-columns: minmax(0, 1fr); gap: 0; } .toc { display: none; } .toc-m { display: block; } }
.text { counter-reset: pp; max-width: 70ch; font-family: Lora, Georgia, serif; font-size: 19px; line-height: 1.75; color: #E6DDD3; padding-left: 64px; }
.text:lang(de) { hyphens: auto; }
.text > * { position: relative; margin: 0 0 1.05em; scroll-margin-top: 96px; }
.text > [id] { counter-increment: pp; }
.text > [id]::before { content: counter(pp); position: absolute; left: -64px; top: 0.45em; width: 46px; text-align: right; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 11px; line-height: 1; letter-spacing: 0.06em; color: #4A2B2E; }
.text > [id]:hover::before { color: #E8222A; }
.text h2 { margin: 2.2em 0 1em; padding-top: 18px; border-top: 1px solid #3A2326; font-family: 'JetBrains Mono', ui-monospace, monospace; font-weight: 400; font-size: 21px; line-height: 1.35; letter-spacing: 0.08em; color: #FF5A60; }
.text h2::before { top: 1.6em !important; }
.text .cap { text-align: center; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 15px; line-height: 1.5; letter-spacing: 0.1em; color: #A89C95; margin-bottom: 0.6em; }
.text .sig { text-align: right; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 15px; letter-spacing: 0.1em; color: #A89C95; }
.text .lb { white-space: pre-line; }
.text .ctr { white-space: pre-line; text-align: center; color: #CFC4BC; }
.text .q { padding-left: 22px; border-left: 2px solid #4A2B2E; color: #D3C9BF; }
.text .q::before { left: -64px; }
.text .fn { font-size: 16px; color: #BFB3AA; }
.text .tn { padding: 12px 16px; border: 1px dashed #3A2326; font-family: Inter, system-ui, sans-serif; font-size: 14px; color: #A89C95; }
.text pre { overflow-x: auto; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 14px; line-height: 1.5; color: #CFC4BC; white-space: pre; }
.text hr { border: 0; height: auto; text-align: center; margin: 2em 0; }
.text hr::after { content: "*   *   *"; font-family: 'JetBrains Mono', ui-monospace, monospace; color: #7A4246; }
.text em { font-style: italic; color: #F2ECE4; }
.text img { max-width: 100%; height: auto; vertical-align: middle; background: #F2ECE4; }
.text a.tx-img { border-bottom: 0; }
.text p > a.tx-img:only-child { display: block; }
.text p > a.tx-img:only-child img { display: block; margin: 0 auto; padding: 8px; box-sizing: border-box; }
.text .stk { display: inline-flex; flex-direction: column; vertical-align: middle; margin: 0 2px 0 1px; padding-left: 3px; border-left: 1px solid currentColor; border-radius: 4px 0 0 4px; font-size: 0.62em; line-height: 1.05; text-align: left; }
.text .flash { animation: rd-flash 3s ease-out 1; }
@keyframes rd-flash { 0%, 30% { background: rgba(232, 34, 42, 0.16); box-shadow: 0 0 0 10px rgba(232, 34, 42, 0.16); } 100% { background: transparent; box-shadow: 0 0 0 10px transparent; } }
@media (max-width: 700px) { .text { padding-left: 0; font-size: 18px; } .text > [id]::before { display: none; } }
.rd-end { margin-top: 56px; padding-top: 18px; border-top: 1px solid #3A2326; font-size: 14px; letter-spacing: 0.12em; color: #A89C95; }
@media (max-width: 760px) { .tbar { position: static; } .text > * { scroll-margin-top: 16px; } .toc-m { position: sticky; top: 0; z-index: 5; } }
@media (prefers-reduced-motion: reduce) { .rd-prog, .text .flash { animation: none !important; } }
/* paper reading mode: the text section turns to cream paper with dark ink; the CRT overlays step aside */
.rd-paper-t { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.rd-paper-f { position: fixed; right: 64px; bottom: 18px; z-index: 66; min-height: 40px; padding: 0 12px; border: 1px solid #3A2326; background: rgba(9, 5, 6, 0.92); color: #F2ECE4; font-size: 12px; letter-spacing: 0.12em; }
.rd-paper-f:hover { border-color: #E8222A; color: #FF5A60; }
html.paper .rd-paper-f { background: #FBF6F3; border-color: #C9B1A8; color: #3A0A0D; }
html.paper .rd-paper-f:hover { border-color: #CE121E; color: #CE121E; }
@media (max-width: 760px) { .rd-paper-f { right: 12px; bottom: 12px; } }
.rd-paper-t i { display: inline-block; width: 14px; height: 14px; border: 1px solid currentColor; background: linear-gradient(135deg, #F4ECE6 50%, #090506 50%); }
html.paper .rd-body { background: #F4ECE6 !important; border-top: 3px solid #CE121E; }
html.paper .rd-body .text { color: #2B1A17; }
html.paper .rd-body .text em { color: #1E100E; }
html.paper .rd-body .text h2 { color: #B3121B; border-top-color: #D8C3BB; }
html.paper .rd-body .text > [id]::before { color: #C9B1A8; }
html.paper .rd-body .text > [id]:hover::before { color: #CE121E; }
html.paper .rd-body .text .cap, html.paper .rd-body .text .sig, html.paper .rd-body .text .tn { color: #7A4A47; }
html.paper .rd-body .text .ctr { color: #4A2F2B; }
html.paper .rd-body .text .q { color: #3A2622; border-left-color: #D8B5AD; }
html.paper .rd-body .text .fn { color: #5A403B; }
html.paper .rd-body .text pre { color: #3A2622; }
html.paper .rd-body .text hr::after { color: #C08A84; }
html.paper .rd-body .text a { color: #B3121B; border-bottom-color: #D8A9A3; }
html.paper .rd-body .toc p, html.paper .rd-body .toc-m summary { color: #7A4A47; }
html.paper .rd-body .toc ol, html.paper .rd-body .toc-m ol { border-left-color: #D8C3BB; }
html.paper .rd-body .toc li a, html.paper .rd-body .toc-m li a { color: #4A2F2B; }
html.paper .rd-body .toc li a:hover, html.paper .rd-body .toc li a.on { color: #CE121E; border-left-color: #CE121E; }
html.paper .rd-body .toc-m { background: #FBF6F3; border-color: #D8C3BB; }
html.paper .rd-body .rd-end { color: #7A4A47; border-top-color: #D8C3BB; }
html.paper .rd-body .pn a { color: #B3121B; }
html.paper .rd-body .hit, html.paper .rd-body mark { background: #F7D6D2; color: #1E100E; }
html.paper .ov-lines, html.paper .ov-grain, html.paper .ov-band, html.paper .rd-poster, html.paper .inst-x { display: none; }
html.paper .text .flash { animation-name: rd-flash-p; }
@keyframes rd-flash-p { 0%, 30% { background: rgba(206, 18, 30, 0.12); box-shadow: 0 0 0 10px rgba(206, 18, 30, 0.12); } 100% { background: transparent; box-shadow: 0 0 0 10px transparent; } }
"""


def page(title, desc, path, body, css='', ticker=None, current_label=None, foot_label=None, script=True, bg=None):
    """Wrap body markup in the shared archive chrome."""
    canon = SITE + path
    header = HEADER
    if current_label:
        header = header.replace('TERMINAL 01 · /ARCHIVE', f'TERMINAL 01 · {esc(current_label)}')
    footer = FOOTER.replace('<span>INVARIANCETECH.INFO/ARCHIVE</span>', '<span style="overflow-wrap: anywhere; min-width: 0">INVARIANCETECH.INFO/ARCHIVE</span>')
    footer = footer.replace('INVARIANCETECH.INFO/ARCHIVE', esc(foot_label or ('INVARIANCETECH.INFO' + path.rstrip('/').upper())))
    tick = ''
    if ticker:
        t = esc(ticker)
        tick = ('<div aria-hidden="true" class="mn" style="overflow: hidden; border-bottom: 1px solid #2B1B1D; background: #100A0B; font-size: 13px; letter-spacing: 0.16em; color: #A89C95; padding: 8px 0">\n'
                '  <div class="it-ticker">\n'
                f'    <span style="padding-right: 56px; white-space: nowrap">{t}</span>\n'
                f'    <span style="padding-right: 56px; white-space: nowrap">{t}</span>\n'
                '  </div>\n</div>\n')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{attr(desc)}">
<link rel="canonical" href="{canon}">
<meta name="theme-color" content="#090506">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon_32.png?v=3">
<link rel="icon" type="image/png" sizes="512x512" href="/assets/favicon_512.png?v=3">
<link rel="apple-touch-icon" href="/assets/favicon_180.png?v=3">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Technical Invariance Authority">
<meta property="og:title" content="{attr(title)}">
<meta property="og:description" content="{attr(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE}/assets/og_tia.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@Invariance_Tech">
{FONTS}
<style>
{BASE_CSS}{EXTRA_CSS}{css}</style>
</head>
<body>
{page_bg(bg)}<div style="position: relative; color: #F2ECE4; font-family: Inter, system-ui, sans-serif; font-size: 17px; line-height: 1.55">

{OVERLAYS}
{header}

{tick}{body}

{footer}

</div>
{'<script src="/assets/archive.js" defer></script>' if script else ''}
<script src="/assets/tia-media.js" defer></script>
</body>
</html>
"""


# ---------------------------------------------------------------- data

def load():
    cat = json.loads((CONTENT / 'catalogue.json').read_text(encoding='utf-8'))
    # author facts come from the dossier cards on the archive template
    facts = {}
    for i, m in enumerate(re.finditer(r'<article class="dos it-rv">(.*?)</article>', ARCH_TPL, re.S)):
        a = m.group(1)
        num, tg = re.search(r'<span>SUBJECT (\d+)</span><span class="tg">([^<]+)</span>', a).groups()
        img, alt = re.search(r'<img src="([^"]+)" alt="([^"]+)"', a).groups()
        slug = re.search(r'hex_(\w+)\.png', img).group(1)
        facts[slug] = {
            'num': num, 'tg': tg, 'tendency': TENDENCY[tg], 'img': img, 'alt': alt,
            'hex': re.search(r'<b>(HEX [\d,]+)</b>', a).group(1),
            'name': re.search(r'<h3>([^<]+)</h3>', a).group(1),
            'yr': re.search(r'<p class="yr">([^<]+)</p>', a).group(1),
            'role': re.search(r'<p class="role">([^<]+)</p>', a).group(1),
            'order': i,
        }
    authors = []
    works = {}
    for a in cat['authors']:
        f = facts[a['slug']]
        a.update(f)
        if not (ROOT / a['img'].lstrip('/')).exists():
            a['img'] = ''               # the portrait has not arrived yet
        a['img'] = lossless(a['img'])
        a['display'] = DISPLAY[a['slug']]
        a['short'] = DISPLAY.get(a['slug'], a['slug']).split()[-1].upper()
        a['nm'] = bool(a.get('filed'))     # a dossier filed among the non-Marxists (others.json group code)
        a['url'] = f"/archive/{a['slug']}/"
        a['works'].sort(key=lambda w: (year0(w['year']), w['title']))
        for w in a['works']:
            w['author'] = a['slug']
            w['authors'] = [a['slug']] + w.get('with', [])
            w.setdefault('cols', [])
            if w['kind'] == 'hosted':
                w['path'] = f"/archive/{a['slug']}/{w['slug']}/"
            works[w['id']] = w
        authors.append(a)
    authors.sort(key=lambda a: a['order'])
    byslug = {a['slug']: a for a in authors}
    cols = cat['collections']
    for c in cols:
        c['works'] = sorted([w for w in works.values() if c['slug'] in w['cols']],
                            key=lambda w: (year0(w['year']), w['title']))
        if not c.get('url') and c.get('status') != 'compiling':
            c['url'] = f"/archive/collections/{c['slug']}/"
    return authors, byslug, works, cols


def byline(w, byslug):
    names = [byslug[s]['display'] for s in w['authors']]
    return ' and '.join(names)


def work_href(w):
    return w['path'] if w['kind'] == 'hosted' else w['url']


def work_link_attrs(w):
    if w['kind'] == 'hosted':
        return f'href="{w["path"]}"'
    return f'href="{attr(w["url"])}" target="_blank" rel="noopener"'


# ---------------------------------------------------------------- text parsing

CHAP = re.compile(r'^(CHAPTER|PART|BOOK|SECTION|APPENDIX|LECTURE|LETTER|KAPITEL|TEIL)\b|^[IVXLC]+\.?(\s|$)|^\d{1,2}\.\s+[A-Z]|^§', re.I)
TOCLINE = re.compile(r'\S\s{3,}(\d+|[ivxlc]+)\s*$', re.I)
BOXLINE = re.compile(r'^\s*\+-+\+\s*$')
CONTENTS_RE = re.compile(r'^(TABLE OF )?CONTENTS\.?$|^INHALT', re.I)
SUBHEAD = re.compile(r'^[A-H]\.\s+[A-Z][A-Za-z ,\'-]{2,44}$')
SIGWORDS = re.compile(r'\b(THE|OF|AND|IN|ON|TO|A|AN|FOR|BY|AT|DIE|DER|DAS|UND)\b')


def norm_cap(s):
    return re.sub(r'[^A-Z0-9 ]', '', s.upper().replace('_', '')).strip()


def is_caps(s):
    letters = [c for c in s if c.isalpha()]
    return len(letters) >= 1 and not any(c.islower() for c in letters)


def inline(s, lang):
    s = esc(s)
    s = re.sub(r'(?<![\w])_(?=\S)(.+?)(?<=\S)_(?![\w])', r'<em>\1</em>', s, flags=re.S)
    if lang == 'en':
        s = s.replace('--', '—')
    else:
        s = s.replace(' -- ', ' – ').replace('--', '–')
    s = re.sub(r'(https://www\.marxists\.org/[\w./%-]+[\w/])', r'<a href="\1" rel="noopener">\1</a>', s)
    # pictures of formulas and tables that a text keeps in content/texts/img/<id>/
    s = re.sub(r'\[\[IMG:([\w.-]+)(?:\|([^\]]*))?\]\]',
               lambda m: f'<a class="tx-img" href="img/{m.group(1)}" target="_blank" rel="noopener"><img src="img/{m.group(1)}" '
                         f'alt="{(m.group(2) or "").replace(chr(34), "&quot;")}" loading="lazy"></a>', s)
    # a pair of symbols set one above the other after a brace, as in M—C{L over Pm}
    s = re.sub(r'\{\{([^|{}]{1,12})\|([^|{}]{1,12})\}\}', r'<span class="stk"><span>\1</span><span>\2</span></span>', s)
    return s


def plain(s, lang):
    s = re.sub(r'\[\[IMG:[^\]]*\]\]', ' ', s)
    s = re.sub(r'\{\{([^|{}]{1,12})\|([^|{}]{1,12})\}\}', r'{\1/\2}', s)
    s = re.sub(r'(?<![\w])_(?=\S)(.+?)(?<=\S)_(?![\w])', r'\1', s, flags=re.S)
    s = s.replace('--', '—' if lang == 'en' else '–')
    return re.sub(r'\s+', ' ', s).strip()


def prep(text, lang):
    """Small per-text fixes before parsing."""
    blocks = re.split(r'\n[ \t]*\n', text.strip('\n'))
    if blocks and blocks[0].startswith('Anmerkungen zur Transkription'):
        blocks.pop(0)
        while blocks and re.search(r'Druckfehler|Fraktur|gesperrt|Antiqua|Rechtschreib|Schreibvarianten', blocks[0]):
            blocks.pop(0)
    text = '\n\n'.join(blocks)
    if lang == 'de':
        text = re.sub(r'#([^#\n]{1,60})#', r'\1', text)
    return text


def parse(text, lang):
    items = []
    front = True          # title page and front matter, before the first real paragraph
    for b in re.split(r'\n[ \t]*\n', text):
        if items and items[-1][0] in ('p', 'q') and len(items[-1][1]) >= 200:
            front = False
        if not b.strip():
            continue
        lines = b.rstrip().split('\n')
        while lines and not lines[0].strip():
            lines.pop(0)
        st = [l.strip() for l in lines]
        one = ' '.join(x for x in st if x)
        if re.fullmatch(r'[\s*.·]+', b):
            items.append(('hr', None))
            continue
        if BOXLINE.match(lines[0]):
            inner = [l.strip().strip('|').strip() for l in lines if not BOXLINE.match(l)]
            paras = [p for p in re.split(r'\n{2,}', '\n'.join(inner)) if p.strip()]
            items.append(('tn', [' '.join(p.split()) for p in paras]))
            continue
        if len(lines) == 1:
            if TOCLINE.search(lines[0]):
                items.append(('pre', lines[0].rstrip()))
            elif re.match(r'\[\d+\] ', one):
                items.append(('p', one))       # a note, even when it is short and in capitals
            elif (len(one) <= 80 or (len(one) <= 170 and CHAP.match(one.replace('_', '')))) and is_caps(one.replace('_', '')):
                items.append(('cand', one))
            elif len(lines[0]) - len(lines[0].lstrip()) >= 20 and len(one) < 60:
                items.append(('sig', one))
            elif front and len(one) < 100:
                items.append(('ctr', one))
            else:
                items.append(('p', one))
            continue
        if all(x.startswith('| ') or x == '|' for x in st if x):
            # lines marked "| " keep their breaks (formulas, schemes, lists set line by line)
            ind = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
            items.append(('qlines' if min(ind) >= 2 else 'lines', '\n'.join(x[2:] for x in st if x)))
            continue
        tabular = sum(1 for l in lines if TOCLINE.search(l) or re.search(r'\S {3,}\S', l.strip()))
        if tabular >= max(2, len(lines) // 2):
            items.append(('pre', '\n'.join(l.rstrip() for l in lines)))
            continue
        ind = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
        maxlen = max(len(x) for x in st)
        if min(ind) >= 6 and maxlen < 64:
            items.append(('ctr', '\n'.join(st)))
            continue
        quoted = min(ind) >= 2
        if front and maxlen < 64:
            items.append(('ctr', '\n'.join(st)))
            continue
        if maxlen < 52:
            items.append(('qlines' if quoted else 'lines', '\n'.join(st)))
            continue
        items.append(('q' if quoted else 'p', one))

    out = []
    i = 0
    prev_prose = False
    contents = False      # inside the book's own table of contents
    seen_prose = False
    title_page = set()    # caps lines from the title page, repeated later above chapter one
    while i < len(items):
        k, v = items[i]
        if k != 'cand':
            if k == 'p' and len(v) >= 200:
                contents = False
            if k in ('p', 'q') and len(v) >= 200:
                seen_prose = True
            if k == 'p' and SUBHEAD.match(v) and i + 1 < len(items) and items[i + 1][0] in ('p', 'q') and not contents:
                out.append(('h3', v))
            else:
                out.append(items[i])
            prev_prose = k in ('p', 'q')
            i += 1
            continue
        run = []
        while i < len(items) and items[i][0] == 'cand':
            run.append(items[i][1])
            i += 1
        nxt = items[i] if i < len(items) else None
        prose_next = nxt is not None and nxt[0] in ('p', 'q') and len(nxt[1]) >= 60
        if not seen_prose and not prose_next:
            title_page.update(norm_cap(x) for x in run)
        if CONTENTS_RE.match(run[0].replace('_', '')):
            contents = True
        # a short name ending in a full stop right after prose is a signature, not a heading
        while prev_prose and len(run) > 1 and len(run[0]) <= 30 and run[0].endswith('.') \
                and not CHAP.match(run[0]) and not SIGWORDS.search(run[0]):
            out.append(('sig', run.pop(0)))
        lead = []
        while len(run) > 1 and (run[0].startswith(('BY ', '"', '\u201c')) or (seen_prose and norm_cap(run[0]) in title_page)):
            lead.append(run.pop(0))
        for x in lead:
            out.append(('cap', x))
        chap = any(CHAP.match(x.replace('_', '')) for x in run)
        heading = (prose_next or (chap and not contents)) and not all(x.endswith(':') for x in run) \
            and len(run) <= 4 and not run[0].startswith(('"', '\u201c'))
        if (contents and not prose_next) or CONTENTS_RE.match(run[0].replace('_', '')):
            heading = False
        if heading:
            contents = False
            out.append(('h', run))
        else:
            for x in run:
                out.append(('cap', x))
        prev_prose = False
    return out


def render_text(items, lang):
    parts, toc, index = [], [], []
    n = 0
    for k, v in items:
        if k == 'hr':
            parts.append('<hr>')
            continue
        n += 1
        pid = f'p{n}'
        if k == 'h':
            label = ' · '.join(plain(x, lang).rstrip('.') for x in v)
            parts.append(f'<h2 id="{pid}">' + '<br>'.join(inline(x, lang) for x in v) + '</h2>')
            toc.append((pid, label))
            index.append([n, label])
        elif k == 'h3':
            parts.append(f'<h3 id="{pid}">{inline(v, lang)}</h3>')
            toc.append((pid, '\u00a0\u00a0' + plain(v, lang)))
            index.append([n, plain(v, lang)])
        elif k == 'tn':
            parts.append(f'<div id="{pid}" class="tn">' + ''.join(f'<p style="margin: 0 0 6px">{inline(p, lang)}</p>' for p in v) + '</div>')
            index.append([n, plain(' '.join(v), lang)])
        elif k == 'pre':
            parts.append(f'<pre id="{pid}">{esc(v)}</pre>')
            index.append([n, plain(v, lang)])
        else:
            cls = {'cap': 'cap', 'sig': 'sig', 'lines': 'lb', 'qlines': 'lb q', 'ctr': 'ctr', 'q': 'q'}.get(k, '')
            if k == 'p' and re.match(r'^(\[\d+\]|\[[A-Z]\]|FOOTNOTE|Footnote|\d+\.\s*\()', v):
                cls = 'fn'
            c = f' class="{cls}"' if cls else ''
            parts.append(f'<p id="{pid}"{c}>{inline(v, lang)}</p>')
            index.append([n, plain(v, lang)])
    return '\n'.join(parts), toc, index


# ---------------------------------------------------------------- page parts

def lossless(img):
    """The same portrait, pixel for pixel, as lossless WebP (about half the size of the PNG)."""
    m = re.fullmatch(r'/assets/hex_([\w-]+)\.png', img or '')
    return f'/assets/hexl/{m.group(1)}.webp' if m and (ROOT / 'assets' / 'hexl' / f'{m.group(1)}.webp').exists() else img


def bust_img(a, alt=''):
    if a.get('img'):
        return f'<img src="{a["img"]}" alt="{attr(alt)}" loading="lazy" decoding="async">'
    return ('<span class="mn" style="align-self: center; padding: 0 10px; text-align: center; font-size: 12px; '
            'letter-spacing: 0.14em; color: #6E5A55">NO PORTRAIT ON FILE</span>')


def dossier_card(a, i):
    hosted = [w for w in a['works'] if w['kind'] == 'hosted']
    linked = [w for w in a['works'] if w['kind'] == 'link']
    key = [w for w in a['works'] if w.get('key')][:4]
    lis = []
    for w in key:
        mark = '<span class="h">TXT</span>' if w['kind'] == 'hosted' else ''
        lis.append(f'<li><a {work_link_attrs(w)}>{esc(w["title"])}</a> ({esc(w["year"])}){mark}</li>')
    delay = f'; animation-delay: {i * 0.5:g}s' if i else ''
    return f"""      <article class="dos it-rv" id="{a['slug']}" data-t="{a['tendency']}">
        <div class="dos-top mn"><span>SUBJECT {a['num']}</span><span class="tg">{a['tg']}</span></div>
        <a href="{a['url']}" class="dos-img" tabindex="-1" aria-hidden="true">{bust_img(a)}<span class="hc tl"></span><span class="hc tr"></span><span class="hc bl"></span><span class="hc br"></span>{f'<span class="co r" style="top: 26%; right: 10px"><b>{a["hex"]}</b><i></i></span>' if a['img'] else ''}<span class="it-bscan" style="position: absolute; left: 0; right: 0; height: 2px; background: #FF5A60; box-shadow: 0 0 10px rgba(232, 34, 42, 0.8){delay}"></span></a>
        <div class="dos-body">
          <h3><a href="{a['url']}">{a['name']}</a></h3>
          <p class="yr">{a['yr']}</p>
          <p class="role">{a['role']}</p>
          <ul>{''.join(lis)}</ul>
          <p class="cnt">{f'<b>{len(hosted)} FULL TEXT{"S" if len(hosted) != 1 else ""}</b>' if hosted else ('LINKED WORKS' if a.get('links_only') else 'NO FULL TEXTS YET')} · <a href="{a['url']}works/" style="color: inherit; border-bottom: 1px dotted #4A2B2E">{len(a.get('bib', [])):,} ITEMS FILED</a></p>
          <a href="{a['url']}" class="open">OPEN DOSSIER →</a>
        </div>
      </article>"""


MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
               'November', 'December']
# what readers are told about works whose full texts open on a set day
SOON_NOTE = {'2027-01-01': "Ernest Untermann's English translations pass into the public domain on New Year's Day 2027, "
                           "seventy years after his death. The full texts open here that morning; until then each link "
                           "opens the Marxists Internet Archive's edition."}


def soon_label(d, short=False):
    y, m, day = (int(x) for x in d.split('-'))
    return f'{day} {MONTH_NAMES[m - 1][:3].upper()} {y}' if short else f'{day} {MONTH_NAMES[m - 1]} {y}'


def soon_item(w, byslug, me):
    bits = [esc(w['subtitle'])] if w.get('subtitle') else []
    others = [s for s in w['authors'] if s != me]
    if others:
        bits.append('With ' + ' and '.join(byslug[s]['display'] for s in others))
    if w.get('soon_ed'):
        bits.append(esc(w['soon_ed']))
    return (f'<a class="soon-item" {work_link_attrs(w)}><span class="y">{esc(w["year"])}</span>'
            f'<span class="t"><b>{esc(w["title"])}</b><small>{" · ".join(bits)}</small>'
            f'<i>READ IT AT MIA UNTIL THEN ↗</i></span></a>')


def work_row(w, byslug, show_author=False, me=None):
    title = esc(w['title'])
    small = []
    if w.get('subtitle'):
        small.append(esc(w['subtitle']))
    others = [s for s in w['authors'] if s != me]
    if me and me not in w['authors']:
        # filed under someone else and listed here because it answers this author (Marx's Critique on Lassalle's page)
        small.append('By ' + ' and '.join(byslug[s]['display'] for s in w['authors']))
    elif me and others:
        small.append('With ' + ' and '.join(byslug[s]['display'] for s in others))
    sm = f'<small>{" · ".join(small)}</small>' if small else ''
    by = f'<span class="by">{" + ".join(byslug[s]["short"] for s in w["authors"])}</span>' if show_author else ''
    if w.get('soon') and w['kind'] != 'hosted':
        small.append(f'Full text here from {soon_label(w["soon"])}')
        sm = f'<small>{" · ".join(small)}</small>'
    st = ('<span class="st sn">[SOON]</span>' if w.get('soon') and w['kind'] != 'hosted' else
          '<span class="st ok">[READ →]</span>' if w['kind'] == 'hosted' else
          '<span class="st ln">[MIA ↗]</span>' if 'marxists.org' in w.get('url', '') else '<span class="st ln">[LINK ↗]</span>')
    return (f'<a {work_link_attrs(w)} class="row wk"><span class="y">{esc(w["year"])}</span>'
            f'<span class="ti">{title}{sm}</span><span class="ld"></span>{by}{st}</a>')


def collection_row(c):
    n = len(c['works'])
    if c.get('status') == 'compiling':
        return (f'<div class="row"><span style="color: #A89C95">{c["code"]}</span><span>{c["title"]}</span>'
                f'<span class="ld"></span><span style="color: #FF5A60">{c["span"]}</span><span class="st wait">[COMPILING]</span></div>')
    ext = c['url'].startswith('http')
    tgt = ' target="_blank" rel="noopener"' if ext else ''
    label = '[YOUTUBE ↗]' if ext else f'[{n} WORKS]'
    return (f'<a href="{c["url"]}"{tgt} class="row"><span style="color: #A89C95">{c["code"]}</span><span>{c["title"]}</span>'
            f'<span class="ld"></span><span style="color: #FF5A60">{c["span"]}</span><span style="color: #39D98A">{label}</span></a>')


def crumbs(*items):
    out = []
    for label, href in items:
        out.append(f'<a href="{href}">{esc(label)}</a>' if href else f'<span style="color: #F2ECE4">{esc(label)}</span>')
    return '<nav class="crumbs mn" aria-label="Breadcrumb">' + ' / '.join(out) + '</nav>'


# ---------------------------------------------------------------- builders

CC_BY_SA = 'https://creativecommons.org/licenses/by-sa/4.0/'


def rights_html(w):
    if w.get('rights') == 'cc-by-sa':
        many = 'short-writings' in w['id']
        return (f'{"The originals are" if many else "The original is"} in the public domain. '
                f'{"The translations were" if many else "The translation was"} made for the Marxists Internet Archive, '
                'which publishes its volunteers\' work under a Creative Commons Attribution-ShareAlike licence. '
                f'This edition (reformatted, a few slips corrected) is shared under <a href="{CC_BY_SA}" rel="license noopener">CC BY-SA 4.0</a>. '
                f'Source: <a href="{attr(w["source"])}" rel="noopener">marxists.org</a>.')
    return 'Public domain.'


def rights_txt(w):
    if w.get('rights') == 'cc-by-sa':
        return ('Original in the public domain. Translation made for the Marxists Internet Archive (marxists.org), '
                'CC BY-SA. This edition (reformatted, a few slips corrected): CC BY-SA 4.0, ' + CC_BY_SA + '\n'
                'Source: ' + w['source'] + '\nPrepared for the TIA archive: ' + SITE + w['path'])
    return 'Public domain. Prepared for the TIA archive: ' + SITE + w['path']


def build_reader(a, w, byslug, others):
    lang = w.get('lang', 'en')
    raw = (CONTENT / 'texts' / f'{w["id"]}.txt').read_text(encoding='utf-8')
    text = prep(raw, lang)
    items = parse(text, lang)
    body_html, toc, index = render_text(items, lang)
    nwords = len(re.findall(r'\w+', text))
    mins = round(nwords / 230)
    rt = f'{mins // 60} H {mins % 60:02d} MIN' if mins >= 60 else f'{mins} MIN'
    folder = ROOT / w['path'].strip('/')
    poster = a.get('poster') or POSTER[a['slug']]
    folder.mkdir(parents=True, exist_ok=True)

    by = byline(w, byslug)
    txt_head = '\n'.join(filter(None, [
        w['title'].upper(), w.get('subtitle', ''), '', by, w['year'], '', w['edition'],
        rights_txt(w), '-' * 60])) + '\n\n'
    txt = re.sub(r'\[\[IMG:[^|\]]*\|?([^\]]*)\]\]', lambda m: f'[{m.group(1) or "Picture"}: see the web page]', text)
    txt = re.sub(r'\{\{([^|{}]{1,12})\|([^|{}]{1,12})\}\}', r'{\1/\2}', txt)
    (folder / f'{w["slug"]}.txt').write_text(txt_head + txt.strip() + '\n', encoding='utf-8')
    imgs = CONTENT / 'texts' / 'img' / w['id']
    if imgs.is_dir():
        (folder / 'img').mkdir(exist_ok=True)
        for f in imgs.iterdir():
            shutil.copy(f, folder / 'img' / f.name)

    (ROOT / 'archive' / 'text').mkdir(parents=True, exist_ok=True)
    (ROOT / 'archive' / 'text' / f'{w["id"]}.json').write_text(
        json.dumps({'id': w['id'], 'p': index}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    toc_items = ''.join(f'<li><a href="#{pid}">{esc(label)}</a></li>' for pid, label in toc)
    if toc:
        aside = f'<aside class="toc mn" aria-label="Contents"><p>CONTENTS · {len(toc)}</p><ol>{toc_items}</ol></aside>'
        mobile = f'<details class="toc-m mn"><summary>CONTENTS · {len(toc)} SECTIONS</summary><ol>{toc_items}</ol></details>'
        layout = 'rd-layout'
    else:
        aside, mobile, layout = '', '', 'rd-layout solo'

    hosted = [x for x in a['works'] if x['kind'] == 'hosted']
    k = hosted.index(w)
    prv = hosted[k - 1] if k > 0 else None
    nxt = hosted[k + 1] if k + 1 < len(hosted) else None
    pn = '<div class="pn mn">'
    pn += f'<a href="{prv["path"]}">← {esc(prv["title"].upper())}</a>' if prv else f'<a href="{a["url"]}">← {a["short"]} DOSSIER</a>'
    pn += (f'<a href="{nxt["path"]}">{esc(nxt["title"].upper())} →</a>' if nxt else
           f'<a href="{NM_HOME}">INDEX OF NON-MARXISTS →</a>' if a.get('nm') else '<a href="/archive/">INDEX OF MARXISTS →</a>')
    pn += '</div>'

    sub = f'<p class="rd-sub">{esc(w["subtitle"])}</p>' if w.get('subtitle') else ''
    body = f"""<script>try {{ if (localStorage.getItem('tia-read') === 'paper') document.documentElement.classList.add('paper'); }} catch (e) {{}}</script>
<div class="rd-prog" aria-hidden="true"></div>
<div class="rd-poster" aria-hidden="true" style="--ar: {poster_ar(poster)}; background-image: url('/assets/bgp/{poster}-1x.webp'); background-image: image-set(url('/assets/bgp/{poster}-1x.webp') 1x, url('/assets/bgp/{poster}.webp') 2x)"></div>
<section style="position: relative; border-bottom: 1px solid #2B1B1D">
  <div class="wrap rd-hero-wrap" style="padding-top: 26px; padding-bottom: clamp(32px, 4vw, 52px)">
    {crumbs(*([('ARCHIVE', '/archive/')] + ([('NON-MARXISTS', NM_HOME)] if a.get('nm') else []) + [(a['short'], a['url']), (w['title'].upper(), None)]))}
    <div class="rd-head">
      <a href="{a['url']}" class="bust" aria-label="{attr(a['display'])} dossier">{bust_img(a)}<span class="hc tl"></span><span class="hc tr"></span><span class="hc bl"></span><span class="hc br"></span><span class="it-bscan" aria-hidden="true" style="position: absolute; left: 0; right: 0; height: 2px; background: #FF5A60; box-shadow: 0 0 10px rgba(232, 34, 42, 0.8)"></span></a>
      <div style="flex: 1 1 520px; min-width: 0">
        <span class="tag">FULL TEXT · {a['short']} · {esc(w['year'])}</span>
        <h1 class="rd-h1 it-glitch">{esc(w['title'])}</h1>
        {sub}
        <p class="src">{esc(by.upper())} · {esc(w['year'])} · {words(nwords)} WORDS · {rt} · {'ENGLISH' if lang == 'en' else 'DEUTSCH'}</p>
        <p class="rd-ed">{esc(w['edition'])} {rights_html(w)}</p>
        <div class="rd-act"><a class="btn" href="#p1">Start reading</a>{f'<a class="btn gh" href="{WK_URL}{w["de"]}/">DEUTSCHES ORIGINAL</a>' if w.get('de') else ''}<a class="btn gh" href="{w['slug']}.txt" download>DOWNLOAD .TXT</a><button type="button" class="btn gh rd-paper-t" data-paper aria-pressed="false"><i aria-hidden="true"></i><span>PAPER MODE</span></button><a class="btn gh" href="{a['url']}">{a['short']} DOSSIER</a></div>
      </div>
    </div>
  </div>
</section>

<section class="rd-body" style="background: rgba(12, 7, 8, 0.6)">
  <div class="wrap {layout}">
    {aside}
    <div style="min-width: 0">
      {mobile}
      <article class="text" lang="{lang}">
{body_html}
      </article>
      <p class="rd-end mn">END OF TEXT · {esc(w['title'].upper())} · {esc(by.upper())}</p>
      {pn}
    </div>
  </div>
</section>
<button type="button" class="rd-paper-t rd-paper-f mn" data-paper aria-pressed="false"><i aria-hidden="true"></i><span>PAPER MODE</span></button>
<script>
(function () {{
  var root = document.documentElement, btns = document.querySelectorAll('[data-paper]');
  function show(on) {{ btns.forEach(function (b) {{ b.setAttribute('aria-pressed', on ? 'true' : 'false'); b.querySelector('span').textContent = on ? 'DARK MODE' : 'PAPER MODE'; }}); }}
  show(root.classList.contains('paper'));
  btns.forEach(function (b) {{ b.addEventListener('click', function () {{
    var on = !root.classList.contains('paper');
    root.classList.toggle('paper', on); show(on);
    try {{ localStorage.setItem('tia-read', on ? 'paper' : 'dark'); }} catch (e) {{}}
  }}); }});
}})();
</script>"""
    title = f'{w["title"]} · {by} · TIA Archive'
    desc = f'Full text of {w["title"]} ({w["year"]}) by {by}. {w["edition"]} Free to read and download.'
    out = page(title, desc, w['path'], body, css=READER_CSS, current_label=f'/ARCHIVE/{a["short"]}',
               foot_label='INVARIANCETECH.INFO' + w['path'].rstrip('/').upper())
    (folder / 'index.html').write_text(out, encoding='utf-8')
    return nwords


def build_author(a, prev_a, next_a, byslug, cols):
    hosted = [w for w in a['works'] if w['kind'] == 'hosted']
    linked = [w for w in a['works'] if w['kind'] == 'link']
    # works co-written with someone else and filed under them (the Manifesto under Engels)
    shared = [w for o in byslug.values() if o['slug'] != a['slug'] for w in o['works'] if a['slug'] in w.get('with', []) + w.get('see', [])]
    allw = sorted(a['works'] + shared, key=lambda w: (year0(w['year']), w['title']))
    nh = len(hosted) + sum(1 for w in shared if w['kind'] == 'hosted')
    nl = len(linked) + sum(1 for w in shared if w['kind'] == 'link')
    years = [year0(w['year']) for w in allw]
    mycols = [c for c in cols if any(a['slug'] in w['authors'] for w in c['works'])]
    note = f'<p class="note"><b>COPYRIGHT</b>{esc(a["note"])}</p>' if a.get('note') else ''
    rows = '\n      '.join(work_row(w, byslug, me=a['slug']) for w in allw)
    soon = [w for w in allw if w.get('soon') and w['kind'] != 'hosted']
    soon_box = ''
    for d in sorted({w['soon'] for w in soon}):
        mine = [w for w in soon if w['soon'] == d]
        soon_box += (f'<div class="soon-box it-rv"><p class="mn sec-h">ARRIVING {soon_label(d).upper()} <span data-until="{d}"></span></p>'
                     + (f'<p class="lede">{esc(SOON_NOTE[d])}</p>' if d in SOON_NOTE else '')
                     + ''.join(soon_item(w, byslug, a['slug']) for w in mine) + '</div>')
    colrows = '\n      '.join(collection_row(c) for c in mycols)
    bib_years = [i['y'] for i in a['bib']] or years
    bib_y0, bib_y1 = min(bib_years + years), max(bib_years + years)
    cw_link = (f'<a class="au-cw" href="{a["url"]}works/">Complete works <small>{len(a["bib"]):,} ITEMS →</small></a>' if a['bib'] else '')
    if a.get('wk'):
        cw_link += (f'<a class="au-cw au-wk" href="{WK_URL}">In German <small>{a["wk"]:,} ORIGINAL TEXTS →</small></a>')
    cw_more = (f'<a class="row" href="{a["url"]}works/" style="color: #FF5A60"><span>ALL {len(a["bib"]):,} {"WORKS AND LETTERS" if any(i["k"] == "letter" for i in a["bib"]) else "ITEMS"}, BY DATE</span><span class="ld"></span><span>[COMPLETE WORKS →]</span></a>' if a['bib'] else '')
    body = f"""<section style="position: relative; overflow: hidden; border-bottom: 1px solid #2B1B1D">
  <div class="wrap" style="padding-top: 26px; padding-bottom: clamp(40px, 5vw, 64px)">
    {crumbs(*([('ARCHIVE', '/archive/')] + ([('NON-MARXISTS', NM_HOME)] if a.get('nm') else []) + [(a['short'], None)]))}
    <div class="au-grid">
      <div class="dos-img au-img">{bust_img(a, a['alt'])}<span class="hc tl"></span><span class="hc tr"></span><span class="hc bl"></span><span class="hc br"></span>{f'<span class="co r" aria-hidden="true" style="top: 22%; right: 10px"><b>{a["hex"]}</b><i></i></span>' if a['img'] else ''}<span class="it-bscan" aria-hidden="true" style="position: absolute; left: 0; right: 0; height: 2px; background: #FF5A60; box-shadow: 0 0 10px rgba(232, 34, 42, 0.8)"></span></div>
      <div style="min-width: 0">
        <span class="tag">{f"{a['group']} · {esc(a['grp']['title'].upper())}" if a.get('nm') else f"SUBJECT {a['num']} · {a['tg']}"}</span>
        <h1 class="dh it-glitch shade" style="margin: 18px 0 0; font-size: clamp(36px, 5vw, 78px); line-height: 0.98; color: #F2ECE4">{a['name']}</h1>
        <p class="src shade">{a['yr']}</p>
        <p class="shade" style="margin: 20px 0 0; max-width: 640px; font-size: 19px; color: #ECE4DC">{a['role']}</p>
        <div class="stats"><div><b>{len(a['bib']):,}</b><span>ITEMS FILED</span></div><div><b>{nh}</b><span>FULL TEXTS HERE</span></div><div><b>{bib_y0}</b><span>FIRST ITEM</span></div><div><b>{bib_y1}</b><span>LAST ITEM</span></div></div>
        {cw_link}
        <p class="mn" style="margin: 16px 0 0; font-size: 14px; letter-spacing: 0.12em"><a href="{attr(a['mia'])}" target="_blank" rel="noopener" style="color: #FF5A60">{f"{a['short']} ON MARXISTS.ORG" if 'marxists.org' in a['mia'] else re.sub(r'^https?://(www[.])?', '', a['mia']).strip('/').upper()} ↗</a></p>
      </div>
    </div>
  </div>
</section>

<section class="grid-bg" style="position: relative; overflow: hidden; background-color: rgba(12, 7, 8, 0.84)">
  <div class="wrap" style="padding-top: 44px; padding-bottom: clamp(56px, 7vw, 96px)">
    {note}
    {soon_box}
    <div class="it-rv">
      <p class="mn sec-h">KEY WORKS · IN ORDER</p>
      {rows}
      {cw_more}
      <p class="mn" style="margin: 14px 0 0; font-size: 13px; letter-spacing: 0.1em; color: #A89C95">{' · '.join(x for x in ['<span style="color: #39D98A">[READ →]</span> FULL TEXT ON THIS SITE' if any(w['kind'] == 'hosted' for w in allw) else '', '<span>[MIA ↗]</span> OPENS THE MARXISTS INTERNET ARCHIVE' if any('marxists.org' in w.get('url', '') for w in allw if w['kind'] == 'link') else '', '<span>[LINK ↗]</span> OPENS ANOTHER SITE' if any('marxists.org' not in w.get('url', 'marxists.org') for w in allw if w['kind'] == 'link') else ''] if x)}{' · <span style="color: #F5B83D">[SOON]</span> FULL TEXT HERE FROM ' + soon_label(soon[0]['soon']).upper() if soon else ''}</p>
    </div>
    {f'<div class="it-rv" style="margin-top: 48px"><p class="mn sec-h">FILED IN COLLECTIONS</p>{colrows}</div>' if colrows.strip() else ''}
    {f'<div class="pn mn"><a href="{prev_a["url"]}">← {esc(prev_a["short"])}</a><a href="{NM_HOME}">ALL NON-MARXISTS</a><a href="{next_a["url"]}">{esc(next_a["short"])} →</a></div>' if a.get('nm') else
     f'<div class="pn mn"><a href="{prev_a["url"]}">← SUBJECT {prev_a["num"]} · {prev_a["short"]}</a><a href="/archive/">INDEX</a><a href="{next_a["url"]}">SUBJECT {next_a["num"]} · {next_a["short"]} →</a></div>'}
  </div>
</section>"""
    ticker = (f"{a['group']} /// NON-MARXISTS · {a['grp']['title'].upper()}" if a.get('nm') else f"DOSSIER {a['num']}") + \
        f" /// {html.unescape(a['name'])} /// {html.unescape(a['yr'])} /// {len(a['bib']):,} ITEMS FILED /// {nh} FULL TEXTS ///" + ('' if a.get('nm') else f" {a['tg']} ///")
    title = f'{a["display"]} · TIA Archive'
    desc = f'{html.unescape(a["role"])} Works by {a["display"]} in order, with full texts and sources.'
    out = page(title, desc, a['url'], body, css=CW_CSS, ticker=ticker, current_label=f'/ARCHIVE/{a["short"]}', bg=POSTER[a['slug']])
    d = ROOT / 'archive' / a['slug']
    d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text(out, encoding='utf-8')


def build_collection(c, byslug, cols):
    rows = '\n      '.join(work_row(w, byslug, show_author=True) for w in c['works'])
    nh = sum(1 for w in c['works'] if w['kind'] == 'hosted')
    others = [x for x in cols if x is not c]
    body = f"""<section style="position: relative; overflow: hidden; border-bottom: 1px solid #2B1B1D">
  <div class="wrap" style="padding-top: 26px; padding-bottom: clamp(40px, 5vw, 64px)">
    {crumbs(('ARCHIVE', '/archive/'), ('COLLECTIONS', '/archive/#collections'), (c['title'], None))}
    <span class="tag" style="margin-top: 24px">{c['code']} · COLLECTION</span>
    <h1 class="dh it-glitch shade" style="margin: 18px 0 0; font-size: clamp(36px, 5vw, 78px); line-height: 0.98; color: #F2ECE4">{c['title']}</h1>
    <p class="src shade">{c['span']} · {len(c['works'])} WORKS · {nh} FULL TEXTS</p>
    <p class="shade" style="margin: 20px 0 0; max-width: 700px; padding: 14px 16px; background: rgba(9, 5, 6, 0.72); border-left: 2px solid #E8222A; font-size: 19px; color: #ECE4DC">{esc(c['desc'])}</p>
  </div>
</section>

<section class="grid-bg" style="position: relative; overflow: hidden; background-color: rgba(12, 7, 8, 0.84)">
  <div class="wrap" style="padding-top: 44px; padding-bottom: clamp(56px, 7vw, 96px)">
    <div class="it-rv">
      <p class="mn sec-h">CONTENTS · IN ORDER</p>
      {rows}
    </div>
    <div class="it-rv" style="margin-top: 48px">
      <p class="mn sec-h">OTHER COLLECTIONS</p>
      {''.join(collection_row(x) for x in others)}
    </div>
  </div>
</section>"""
    ticker = f"{c['code']} /// {c['title']} /// {c['span']} /// {len(c['works'])} WORKS /// {nh} FULL TEXTS ///"
    out = page(f'{c["title"].title()} · TIA Archive', c['desc'], c['url'], body, ticker=ticker,
               current_label='/ARCHIVE/COLLECTIONS', bg=COL_POSTER[c['slug']])
    d = ROOT / 'archive' / 'collections' / c['slug']
    d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text(out, encoding='utf-8')


def build_index(authors, byslug, works, cols, nm=None):
    every = authors
    authors = [a for a in every if not a.get('nm')]            # the Index of Marxists proper
    nm_people = nm['people'] if nm else []                      # with the dossiers filed among them
    nm_works = [w for p in nm_people for w in p['works']]
    own_nm = [w for p in nm_people if not p.get('author') for w in p['works']]
    hosted = sorted([w for w in list(works.values()) + own_nm if w['kind'] == 'hosted'], key=lambda w: (year0(w['year']), w['title']))
    nh = len(hosted)
    mworks = {k: w for k, w in works.items() if not byslug[w['author']].get('nm')}
    nworks = len(works) + len(own_nm)
    mh = sum(1 for w in mworks.values() if w['kind'] == 'hosted')
    nmh = sum(1 for w in nm_works if w['kind'] == 'hosted')
    t = ARCH_TPL
    # hero: counts and a real search form
    t = t.replace('SRC: TIA ARCHIVE · 12 SUBJECTS · 7 TENDENCIES · 1770 — 1971',
                  f'SRC: TIA ARCHIVE · {len(authors)} MARXISTS · {len(mworks)} WORKS · {mh} FULL TEXTS · {len(CHIPS) - 1} TENDENCIES')
    t = t.replace('/// 1770 — 1971 ///', f'/// {len(mworks)} WORKS /// {mh} FULL TEXTS /// {len(nm_people)} NON-MARXISTS ///')
    for a in every:
        if a.get('nm'):
            t = re.sub(r'(INDEX OF MARXISTS ///[^<]*?) · ' + re.escape(a['short']) + r'(?= ·)', r'\1', t)
    t = t.replace('/// 12 SUBJECTS ///', f'/// {len(authors)} SUBJECTS ///')
    t = t.replace('Every major thinker, filed by tendency. Open a dossier to read their works in order, from the first article to the last letter.',
                  'Every major Marxist, filed by tendency. Open a dossier for their works in order. Texts in the public domain, and a few public-domain originals in freely licensed translations, are here in full and searchable; the rest link to the Marxists Internet Archive.')
    search = f"""<form role="search" id="ar-form" action="/archive/" method="get" style="flex: 1 1 360px; min-width: 0; padding: 20px; background: rgba(9, 5, 6, 0.82); border: 1px solid #3A2326">
      <label for="ar-q" class="mn" style="display: block; font-size: 14px; letter-spacing: 0.14em; color: #A89C95">&gt; QUERY THE ARCHIVE</label>
      <div style="display: flex; gap: 10px; margin-top: 12px">
        <input id="ar-q" name="q" type="search" autocomplete="off" placeholder="Name, work, year or phrase" style="flex: 1; min-width: 0; min-height: 52px; box-sizing: border-box; padding: 0 14px; background: #090506; border: 2px solid #3A2326; color: #F2ECE4; font-family: Inter, sans-serif; font-size: 17px">
        <button type="submit" style="min-height: 52px; padding: 0 20px; border: 0; background: #C81D25; color: #FFFFFF; font-family: Inter, sans-serif; font-weight: 800; font-size: 16px; cursor: pointer">Search</button>
      </div>
      <p class="mn" style="margin: 12px 0 0; font-size: 12px; letter-spacing: 0.1em; color: #A89C95">SEARCHES {sum(len(a['bib']) for a in every):,} TITLES AND THE FULL TEXT OF {nh} WORKS</p>
    </form>"""
    t = re.sub(r'<div role="search".*?</button>\n      </div>\n    </div>', lambda m: search, t, count=1, flags=re.S)
    results = """
<section id="ar-results" hidden style="background: #0C0708; border-bottom: 1px solid #2B1B1D">
  <div class="wrap" style="padding-top: 32px; padding-bottom: 40px">
    <div class="res-box" aria-live="polite">
      <div class="res-head mn"><span id="ar-status">SEARCHING</span><button type="button" id="ar-clear" class="chip">CLEAR ×</button></div>
      <div class="scan-bar" aria-hidden="true"><i id="ar-bar"></i></div>
      <div id="ar-cat"></div>
      <div id="ar-bib"></div>
      <div id="ar-de"></div>
      <div id="ar-full"></div>
      <div id="ar-defull"></div>
    </div>
  </div>
</section>
"""
    t = t.replace('<div aria-hidden="true" class="sec-bg" style="background-image: url(\'/assets/bg_archivepage.webp\')"></div>',
                  '', 1)
    t = t.replace('<h1 class="dh it-glitch" style="margin: 18px 0 0; font-size: clamp(38px, 5.4vw, 86px)', '<h1 class="dh it-glitch shade" style="margin: 18px 0 0; font-size: clamp(38px, 5.4vw, 86px)', 1)
    t = t.replace('<p style="margin: 22px 0 0; max-width: 620px; font-size: 19px; color: #DCD2CA">', '<p style="margin: 22px 0 0; max-width: 620px; padding: 14px 16px; background: rgba(9, 5, 6, 0.72); border-left: 2px solid #E8222A; font-size: 19px; color: #ECE4DC">', 1)
    hero_end = t.index('</section>', t.index('id="ar-form"')) + len('</section>')
    t = t[:hero_end] + '\n' + results + t[hero_end:]

    # main section: filters, timeline, dossiers, texts, collections
    counts = {k: sum(1 for a in authors if a['tendency'] == k) for k, _ in CHIPS}
    counts['all'] = len(authors) + len(nm_people)
    chip = lambda k, label, n, cls='': (f'<button type="button" class="chip{cls}{" on" if k == "all" else ""}" data-f="{k}" '
                                         f'aria-pressed="{"true" if k == "all" else "false"}">{label}<span>{n}</span></button>')
    chips = '\n      '.join(chip(k, label, counts[k]) for k, label in CHIPS if counts[k])
    if nm:
        chips += ('\n      <span class="chip-br" aria-hidden="true"></span>\n      ' + chip('nm', 'NON-MARXISTS', len(nm_people), ' nmc') + '\n      ' +
                  '\n      '.join(chip(g['slug'], g['title'].upper().replace('THE ', ''), len(g['people']), ' nmc') for g in nm['groups'] if g['people']))
    cards = '\n\n'.join(dossier_card(a, i) for i, a in enumerate(authors))
    nm_cards = '\n\n'.join(nm_card(p, i % 4) for i, p in enumerate(nm_people))
    text_rows = '\n      '.join(work_row(w, byslug, show_author=True) for w in hosted)
    col_rows = '\n      '.join(collection_row(c) for c in cols)
    main = f"""<section class="grid-bg" style="position: relative; overflow: hidden; background-color: rgba(12, 7, 8, 0.84)">
  <div class="wrap" style="padding-top: 36px; padding-bottom: clamp(56px, 7vw, 96px)">
    <div role="group" aria-label="Filter by tendency" style="display: flex; flex-wrap: wrap; gap: 8px">
      {chips}
    </div>

    {build_timeline(authors, nm)}

    <div class="ar-block" id="marxists">
      <header class="ar-bh"><h2 class="mn">THE MARXISTS · {len(authors)} DOSSIERS</h2><p>The Index proper, filed by tendency.</p></header>
      <div id="ar-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr)); gap: 20px; margin-top: 22px">

{cards}
      </div>
    </div>
{f'''
    <div class="ar-block" id="non-marxists">
      <header class="nm-hero">
        <span class="tag nm-tag">FILE 01-B · OUTSIDE THE INDEX</span>
        <h2 class="dh">INDEX OF NON-MARXISTS</h2>
        <p class="src">SRC: TIA ARCHIVE · {len(nm_people)} NON-MARXISTS · {len(nm_works)} WORKS · {nmh} FULL TEXTS · {sum(1 for g in nm['groups'] if g['people'])} GROUPS</p>
        <p class="nm-lede">{esc(nm['intro'])} Open a file for their works in order; texts in the public domain are here in full and searchable, the rest link to the Marxists Internet Archive or the published text.</p>
      </header>
      <div class="nm-grid" style="grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr)); gap: 20px">

{nm_cards}
      </div>
    </div>''' if nm else ''}

    <div class="it-rv" id="texts" style="margin-top: 56px">
      <div style="display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 10px; border-bottom: 1px solid #3A2326; padding-bottom: 10px">
        <p class="mn" style="margin: 0; font-size: 18px; letter-spacing: 0.1em">READING ROOM · {nh} FULL TEXTS</p>
        <span class="mn" style="font-size: 13px; letter-spacing: 0.1em; color: #A89C95">PUBLIC DOMAIN OR CC BY-SA · FREE TO READ AND DOWNLOAD</span>
      </div>
      {text_rows}
    </div>

    <div class="it-rv" id="collections" style="margin-top: 56px">
      <p class="mn sec-h">COLLECTIONS</p>
      {col_rows}
    </div>
  </div>
</section>"""
    start = t.index('<section class="grid-bg" style="background-color: #0C0708">')
    end = t.index('</section>', t.index('COL-08')) + len('</section>')
    t = t[:start] + main + t[end:]
    t = t.replace('</style>', EXTRA_CSS + NM_CSS + AR_CSS + '</style>', 1)
    t = t.replace('<body>\n<div style="position: relative; background: #090506;', '<body>\n' + page_bg(INDEX_POSTER) + '<div style="position: relative;', 1)
    assert 'class="page-bg"' in t
    t = t.replace(re.search(r'<link href="https://fonts.googleapis.com/css2[^>]*>', t).group(), FONTS.split('\n')[1])
    t = t.replace('</body>', '<script src="/assets/archive.js" defer></script>\n<script src="/assets/tia-media.js" defer></script>\n</body>')
    (ROOT / 'archive' / 'index.html').write_text(t, encoding='utf-8')


HOME_DESC = ('An open archive of world Marxism: the classics in full, the complete works of each writer by date, '
             'and the German originals of Marx and Engels.')


def home_head(t, title, desc, path):
    old_desc = 'An open archive of world Marxism and a workshop that builds communist technology. Essays, edits, the USSR 2089 serial, games and the TIA Supply Depot.'
    t = t.replace(f'<meta name="description" content="{old_desc}">', f'<meta name="description" content="{attr(desc)}">')
    t = t.replace(f'<meta property="og:description" content="{old_desc}">', f'<meta property="og:description" content="{attr(desc)}">')
    t = t.replace('<link rel="canonical" href="https://invariancetech.info/">', f'<link rel="canonical" href="{SITE}{path}">')
    t = t.replace('<meta property="og:url" content="https://invariancetech.info/">', f'<meta property="og:url" content="{SITE}{path}">')
    t = t.replace('<title>Technical Invariance Authority</title>', f'<title>{esc(title)}</title>')
    t = t.replace('<meta property="og:title" content="Technical Invariance Authority">', f'<meta property="og:title" content="{attr(title)}">')
    # the films have their own page; every menu points there
    t = t.replace('<a href="#watch">WATCH</a>', '<a href="/watch/">WATCH</a>\n      <a href="/dispatches/">DISPATCHES</a>', 1)
    # no technology in the ticker
    t = t.replace('/// COMMUNIST TECHNOLOGY /// SIM-01 PLAN/1 ///', '///')
    return t


def build_home(authors, works, cols, nm=None):
    t = home_head(HOME_TPL, 'Technical Invariance Authority', HOME_DESC, '/')
    nh = sum(1 for w in works.values() if w['kind'] == 'hosted')
    nh += sum(1 for p in (nm['people'] if nm else []) if not p.get('author') for w in p['works'] if w['kind'] == 'hosted')
    for a in authors:
        t = t.replace(f'<a href="/archive/" style="display: block; text-align: center"><div style="position: relative; overflow: hidden"><img src="/assets/hex_{a["slug"]}.png"',
                      f'<a href="{a["url"]}" style="display: block; text-align: center"><div style="position: relative; overflow: hidden"><img src="/assets/hex_{a["slug"]}.png"')
    for c in cols:
        old = re.search(rf'<a href="[^"]*" class="row"><span style="color: #A89C95">{c["code"]}</span>.*?</a>', t)
        if old:
            t = t.replace(old.group(), collection_row(c))
    # the home page is the hero and the archive; the arcade, films, shop and the rest keep their own pages
    i, j = t.index('<section id="arcade"'), t.index('<footer')
    t = t[:i] + t[j:]
    hero = [
        ('TIA // ARCHIVE · LABS · ARCADE · WATCH', 'TIA // THE ARCHIVE OF WORLD MARXISM'),
        ('The Technical Invariance Authority is an open archive of world Marxism and a workshop that builds communist technology: free, open-source tools for planning, organising and reading.',
         'The Technical Invariance Authority is an open archive of world Marxism: the classics in full, every writer\'s complete works by date, and Marx and Engels in their own German.'),
    ]
    for a, b in hero:
        assert a in t, a
        t = t.replace(a, b)
    t = re.sub(r'\s*<a href="/arcade/plan1/" style="display: inline-flex.*?Play PLAN/1\s*</a>', '', t, count=1, flags=re.S)
    t = re.sub(r'\s*<span style="display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; border: 1px solid #3A2326; background: rgba\(9, 5, 6, 0.7\); color: #A89C95"><span class="dot red" style="animation-delay: 0.8s"></span>LABS: BUILDING</span>', '', t, count=1)
    assert 'PLAN/1' not in t and 'LABS: BUILDING' not in t and 'communist technology' not in t.lower()
    t = t.replace('<a href="#watch" class="row">', '<a href="/watch/" class="row">')
    t = t.replace('<a href="#about" style="color: #FF5A60">SEND IT IN</a>', '<a href="https://x.com/Invariance_Tech" target="_blank" rel="noopener" style="color: #FF5A60">SEND IT IN</a>')
    t = t.replace('</style>', ROOM_CSS + '</style>', 1)
    t = t.replace('</body>', '<script src="/assets/tia-media.js" defer></script>\n</body>', 1)
    nmarx = sum(1 for a in authors if not a.get('nm'))
    t = t.replace('SRC: TIA ARCHIVE · 12 SUBJECTS · 8 COLLECTIONS', f'SRC: TIA ARCHIVE · {nmarx} SUBJECTS · {nh} FULL TEXTS · 8 COLLECTIONS')
    t = t.replace('INDEX OF MARXISTS: 12 SUBJECTS', f'INDEX OF MARXISTS: {nmarx} SUBJECTS')
    # the busts are the Index of Marxists; dossiers filed among the non-Marxists leave the row
    for a in authors:
        if a.get('nm'):
            t, k = re.subn(r'\n\s*<a href="[^"]*" style="display: block; text-align: center"><div style="position: relative; overflow: hidden">'
                           r'<img [^>]*src="/assets/hex_' + a['slug'] + r'\.png".*?</a>', '', t, count=1)
            assert k == 1, a['slug']
    t = re.sub(r'<div role="search" class="panel" style="padding: 22px">(.*?)</p>\n        </div>',
               lambda m: '<form role="search" class="panel" action="/archive/" method="get" style="padding: 22px">' + m.group(1) + '</p>\n        </form>',
               t, count=1, flags=re.S)
    t = t.replace('<input id="it-q" type="search"', '<input id="it-q" name="q" type="search" autocomplete="off"')
    t = re.sub(r'(<input id="it-q".*?\n\s*)<button type="button"', r'\1<button type="submit"', t, count=1, flags=re.S)
    t = t.replace('</style>', '.row .st.wait { color: #E8A33A; }\n</style>', 1)
    # the same pictures in lossless WebP: nothing changes on screen, the page downloads less
    t = re.sub(r'src="(/assets/hex_[\w-]+\.png)"', lambda m: f'src="{lossless(m.group(1))}"', t)
    for old, new in (("url('/assets/marx_hex_build.png')", "url('/assets/marx_hex_build.webp')"), ('src="/assets/marx_hex.png"', 'src="/assets/marx_hex.webp"')):
        assert old in t, old
        t = t.replace(old, new)
    assert '<form role="search" class="panel"' in t and 'name="q"' in t and '#watch' not in t and '#about' not in t
    (ROOT / 'index.html').write_text(t, encoding='utf-8')


def build_watch():
    """The films, which used to sit on the home page, on a page of their own."""
    t = home_head(HOME_TPL, 'Watch · Technical Invariance Authority',
                  'Edits, essays and the USSR 2089 serial from the Technical Invariance Authority, on YouTube.', '/watch/')
    t = t.replace('<a href="#top" style="display: flex; align-items: center; gap: 14px">', '<a href="/" style="display: flex; align-items: center; gap: 14px">', 1)
    i = t.index('<section class="grid-bg" style="position: relative; overflow: hidden">')
    w0 = t.index('<section id="watch"')
    w1 = t.index('</section>', w0) + len('</section>')
    f0 = t.index('<footer')
    t = t[:i] + t[w0:w1] + '\n\n' + t[f0:]
    t = t.replace('</body>', '<script src="/assets/tia-media.js" defer></script>\n</body>', 1)
    assert 'communist technology' not in t.lower()
    d = ROOT / 'watch'
    d.mkdir(exist_ok=True)
    (d / 'index.html').write_text(t, encoding='utf-8')


def build_catalogue_json(authors, byslug, works, cols, nm=None):
    data = {
        'authors': [{'slug': a['slug'], 'name': a['display'], 'short': a['short'], 'years': html.unescape(a['yr']),
                     'tg': ('NON-MARXISTS · ' + a['grp']['title'].upper()) if a.get('grp') else a['tg'],
                     'role': html.unescape(a['role']), 'img': a['img'], 'url': a['url']} for a in authors],
        'works': [{'id': w['id'], 'title': w['title'], 'sub': w.get('subtitle', ''), 'year': w['year'],
                   'authors': w['authors'], 'kind': w['kind'], 'url': work_href(w), 'lang': w.get('lang', 'en'),
                   'soon': soon_label(w['soon'], short=True) if w.get('soon') and w['kind'] != 'hosted' else ''}
                  for w in sorted(works.values(), key=lambda w: (year0(w['year']), w['title']))],
        'collections': [{'code': c['code'], 'title': c['title'], 'url': c.get('url', '')} for c in cols],
    }
    if nm:
        data['authors'] += [{'slug': p['slug'], 'name': p['name'], 'short': p['short'], 'years': p['years'],
                             'tg': 'NON-MARXISTS · ' + p['grp']['title'].upper(), 'role': p['role'], 'img': p['img'], 'url': p['url']}
                            for p in nm['people'] if not p.get('author')]
        data['works'] += [{'id': w['id'], 'title': w['title'], 'sub': w.get('subtitle', ''), 'year': w['year'],
                           'authors': w['authors'], 'kind': w['kind'], 'url': work_href(w), 'lang': w.get('lang', 'en'), 'soon': ''}
                          for p in nm['people'] if not p.get('author') for w in p['works']]
    (ROOT / 'archive' / 'catalogue.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def build_sitemap(authors, works, cols, ws=(), nm=None):
    urls = ['/', '/archive/', '/watch/', '/dispatches/', '/arcade/', '/arcade/plan1/', '/arcade/behind-jupiter/', '/arcade/red-moon/', '/arcade/wither/', '/arcade/all-power/', '/shop/']
    urls += [a['url'] for a in authors]
    urls += [a['url'] + 'works/' for a in authors if a.get('bib')]
    urls += [w['path'] for w in sorted(works.values(), key=lambda w: w['id']) if w['kind'] == 'hosted']
    urls += [c['url'] for c in cols if c.get('url', '').startswith('/')]
    if nm:
        own = [p for p in nm['people'] if not p.get('author')]
        urls += [p['url'] for p in own] + [w['path'] for p in own for w in p['works'] if w['kind'] == 'hosted']
    if ws:
        urls += [WK_URL] + [w['path'] for w in ws]
    body = '\n'.join(f'  <url><loc>{SITE}{u}</loc></url>' for u in urls)
    (ROOT / 'sitemap.xml').write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n',
        encoding='utf-8')
    return len(urls)


# ---------------------------------------------------------------- complete works (bibliographies)

BIB_BASE = {
    'gegenstandpunkt': 'https://de.gegenstandpunkt.com/',
    'hegel': 'https://www.marxists.org/reference/archive/hegel/',
    'lenin': 'https://www.marxists.org/archive/lenin/works/',
    'trotsky': 'https://www.marxists.org/archive/trotsky/',
    'liebknecht': 'https://www.marxists.org/archive/liebknecht-k/',
    'lassalle': 'https://www.marxists.org/archive/lassalle/',
    'lukacs': 'https://www.marxists.org/archive/lukacs/',
    'plekhanov': 'https://www.marxists.org/archive/plekhanov/',
}
BIB_SOURCE = {
    'gramsci': 'Gramsci\'s writings in English on the Marxists Internet Archive, from his articles of 1916 to the letters from prison, with selections from the Prison Notebooks. Links open the Marxists Internet Archive.',
    'gegenstandpunkt': 'GegenStandpunkt\'s books in German and English, its first issue of March 1992 and the issues since 2024 with every article in them. Links open the publisher\'s own site, where the journal archive lists every issue since 1992 and the article archive can be searched; the Marxistische Gruppe\'s paper MSZ has its own archive there.',
    'hegel': 'Hegel\'s principal writings and lecture courses. Links open the Hegel section of the Marxists Internet Archive.',
    'marx': 'Every item in the 50 volumes of the Marx-Engels Collected Works: books, articles, manuscripts, speeches and letters, by date. Links open the Marxists Internet Archive\'s index for that year; texts in the public domain open here.',
    'engels': 'Every item in the 50 volumes of the Marx-Engels Collected Works: books, articles, manuscripts, speeches and letters, by date. Links open the Marxists Internet Archive\'s index for that year; texts in the public domain open here.',
    'kautsky': 'Every work in the Kautsky section of the Marxists Internet Archive.',
    'plekhanov': 'Every work in the Plekhanov section of the Marxists Internet Archive.',
    'lenin': 'Every entry in the date index of the Lenin Internet Archive, which follows the Collected Works. Works in several parts are listed once.',
    'trotsky': 'Every work in the Trotsky index of the Marxists Internet Archive.',
    'luxemburg': 'Every work in the Luxemburg section of the Marxists Internet Archive.',
    'liebknecht': 'Every work in the Liebknecht section of the Marxists Internet Archive.',
    'lassalle': 'Every work in the Lassalle section of the Marxists Internet Archive, English and German.',
    'lukacs': 'Every work in the Lukács section of the Marxists Internet Archive.',
    'bukharin': 'Every work in the Bukharin library of the Marxists Internet Archive.',
    'bordiga': 'Every English translation in the Bordiga section of the Marxists Internet Archive. His Italian writings run to thousands of articles; more will be filed here as they are translated.',
}
MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}
MON_NAME = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def tnorm(t):
    return ''.join(c for c in t.lower() if c.isalnum())


def load_bibliography(a, byslug):
    f = CONTENT / 'bibliography' / f'{a["slug"]}.tsv'
    if not f.exists():
        return []
    base = BIB_BASE.get(a['slug'], f'https://www.marxists.org/archive/{a["slug"]}/')
    hosted = [w for o in byslug.values() for w in o['works'] if w['kind'] == 'hosted' and a['slug'] in w['authors']]
    hn = [(tnorm(w['title']), w) for w in hosted]
    items = []
    for line in f.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        cols = line.split('\t')
        y, t, u = cols[0], cols[1], cols[2]
        kind = cols[3] if len(cols) > 3 and cols[3] else ('letter' if re.match(r'(A )?Letters? (to|from)', t) else 'work')
        if u.startswith('~'):
            u = base + u[1:]
        elif u.startswith('/'):
            u = 'https://www.marxists.org' + u
        d = ''
        m = re.search(r'/works/\d{4}/([a-z]{3})/(\d\d)', u) if a['slug'] == 'lenin' else None
        if m and m.group(1) in MONTHS:
            day = int(m.group(2))
            d = (f'{day} ' if day else '') + MON_NAME[MONTHS[m.group(1)]]
        item = {'y': int(re.search(r'\d{4}', y).group()), 't': t, 'u': u, 'k': kind, 'd': d, 'h': None}
        n = tnorm(t)
        for hk, w in hn:
            if len(hk) >= 10 and (n == hk or n.startswith(hk)) and kind == 'work':
                item['h'] = w
                item['u'] = w['path']
                break
        items.append(item)
    items.sort(key=lambda i: i['y'])
    return items


CW_CSS = """
.cw-bar { position: sticky; top: 68px; z-index: 5; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 14px 0; background: rgba(12, 7, 8, 0.96); border-bottom: 1px solid #3A2326; }
.cw-bar input { flex: 1 1 280px; min-width: 0; min-height: 48px; box-sizing: border-box; padding: 0 14px; background: #090506; border: 2px solid #3A2326; color: #F2ECE4; font-family: Inter, sans-serif; font-size: 17px; }
.cw-bar .cnt { font-size: 13px; letter-spacing: 0.12em; color: #A89C95; }
.cw-jump { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 18px; }
.cw-jump a { padding: 5px 9px; border: 1px solid #3A2326; background: rgba(9, 5, 6, 0.7); font-size: 12px; letter-spacing: 0.1em; color: #CFC4BC; }
.cw-jump a:hover { border-color: #E8222A; color: #FF5A60; }
.cw-y { margin-top: 36px; scroll-margin-top: 150px; }
.cw-y h2 { margin: 0; display: flex; justify-content: space-between; align-items: baseline; gap: 12px; border-bottom: 1px solid #3A2326; padding-bottom: 8px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-weight: 400; font-size: 28px; color: #FF5A60; }
.cw-y h2 span { font-size: 12px; letter-spacing: 0.12em; color: #A89C95; }
.cw { list-style: none; margin: 0; padding: 0; columns: 2 440px; column-gap: 44px; }
.cw li { break-inside: avoid; display: flex; gap: 12px; padding: 7px 0; border-bottom: 1px solid #1E1214; font-size: 15.5px; line-height: 1.4; }
.cw li .d { flex: 0 0 56px; padding-top: 3px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; letter-spacing: 0.04em; color: #8A7B75; }
.cw li a { color: #E6DDD3; }
.cw li a:hover { color: #FF5A60; }
.cw li.l a { color: #B3A79F; }
.cw li b { margin-left: 8px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-weight: 400; font-size: 11px; letter-spacing: 0.12em; color: #39D98A; }
.no-letters .cw li.l { display: none; }
.cw-y[hidden], .cw li[hidden] { display: none; }
.au-cw { display: inline-flex; align-items: center; gap: 12px; margin-top: 22px; min-height: 52px; padding: 0 20px; background: #C81D25; color: #FFFFFF; font-family: Inter, sans-serif; font-weight: 800; font-size: 17px; }
.au-cw:hover { background: #E8222A; color: #FFFFFF; }
.au-wk { margin-left: 10px; background: transparent; border: 2px solid #C81D25; }
.au-wk:hover { background: rgba(200, 29, 37, 0.18); }
@media (max-width: 560px) { .au-wk { margin-left: 0; } }
.au-cw small { font-family: 'JetBrains Mono', ui-monospace, monospace; font-weight: 400; font-size: 13px; letter-spacing: 0.1em; opacity: 0.85; }
"""


def build_complete_works(a, byslug):
    items = a['bib']
    if not items:
        return
    nl = sum(1 for i in items if i['k'] == 'letter')
    years = sorted({i['y'] for i in items})
    groups = {}
    for i in items:
        groups.setdefault(i['y'], []).append(i)
    secs = []
    for y in years:
        rows = []
        for i in groups[y]:
            cls = ' class="l"' if i['k'] == 'letter' else ''
            tag = '<b>READ</b>' if i['h'] else ''
            rows.append(f'<li{cls}><span class="d">{esc(i["d"])}</span><a href="{attr(i["u"])}">{esc(i["t"])}</a>{tag}</li>')
        secs.append(f'<section class="cw-y" id="y{y}"><h2>{y}<span>{len(groups[y])} ITEM{"S" if len(groups[y]) != 1 else ""}</span></h2><ul class="cw">{"".join(rows)}</ul></section>')
    decades = sorted({y // 10 * 10 for y in years})
    jump = ''.join(f'<a href="#y{next(y for y in years if y // 10 * 10 == d)}">{d}s</a>' for d in decades)
    letters_btn = (f'<button type="button" class="chip on" id="cw-letters" aria-pressed="true">LETTERS<span>{nl:,}</span></button>' if nl else '')
    body = f"""<section style="position: relative; border-bottom: 1px solid #2B1B1D">
  <div class="wrap" style="position: relative; z-index: 1; padding-top: 26px; padding-bottom: clamp(36px, 4vw, 56px)">
    {crumbs(*([('ARCHIVE', '/archive/')] + ([('NON-MARXISTS', NM_HOME)] if a.get('nm') else []) + [(a['short'], a['url']), ('COMPLETE WORKS', None)]))}
    <span class="tag" style="margin-top: 22px">SUBJECT {a['num']} · COMPLETE WORKS</span>
    <h1 class="dh it-glitch shade" style="margin: 18px 0 0; font-size: clamp(34px, 4.6vw, 72px); line-height: 0.98; color: #F2ECE4">{a['name']}</h1>
    <p class="src shade">{len(items):,} ITEMS · {len(items) - nl:,} WORKS{f' · {nl:,} LETTERS' if nl else ''} · {years[0]} — {years[-1]}</p>
    <p class="shade" style="margin: 20px 0 0; max-width: 760px; padding: 14px 16px; background: rgba(9, 5, 6, 0.72); border-left: 2px solid #E8222A; font-size: 17px; color: #ECE4DC">{esc(BIB_SOURCE.get(a['slug'], ''))}</p>
    {f'<p class="mn shade" style="margin: 14px 0 0; font-size: 14px; letter-spacing: 0.1em"><a href="{WK_URL}" style="color: #FF5A60">THE GERMAN ORIGINALS · {a["wk"]:,} TEXTS →</a></p>' if a.get('wk') else ''}
    <nav class="cw-jump mn" aria-label="Jump to decade">{jump}</nav>
  </div>
</section>

<section class="grid-bg" style="position: relative; background-color: rgba(12, 7, 8, 0.9)">
  <div class="wrap" style="padding-bottom: clamp(56px, 7vw, 96px)">
    <div class="cw-bar mn" role="search">
      <label for="cw-q" class="sr" style="position: absolute; left: -9999px">Filter titles</label>
      <input id="cw-q" type="search" placeholder="Filter {len(items):,} titles" autocomplete="off">
      {letters_btn}
      <span class="cnt" id="cw-count" aria-live="polite">{len(items):,} SHOWN</span>
    </div>
    {''.join(secs)}
    <div class="pn mn"><a href="{a['url']}">← {a['short']} DOSSIER</a><a href="/archive/">INDEX OF MARXISTS →</a></div>
  </div>
</section>"""
    title = f'{a["display"]}: Complete Works · TIA Archive'
    desc = f'All {len(items):,} works and letters by {a["display"]}, {years[0]}–{years[-1]}, listed by date with links to every text.'
    out = page(title, desc, a['url'] + 'works/', body, css=CW_CSS, current_label=f'/ARCHIVE/{a["short"]}/WORKS',
               bg=POSTER[a['slug']])
    d = ROOT / 'archive' / a['slug'] / 'works'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text(out, encoding='utf-8')


def build_bibliography_json(authors):
    slugs = [a['slug'] for a in authors]
    rows = []
    for ai, a in enumerate(authors):
        for i in a['bib']:
            u = i['u']
            if u.startswith('https://www.marxists.org/'):
                u = '~' + u[len('https://www.marxists.org/'):]
            rows.append([ai, i['y'], i['t'], u, 1 if i['k'] == 'letter' else 0])
    (ROOT / 'archive' / 'bibliography.json').write_text(
        json.dumps({'a': slugs, 'i': rows}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return len(rows)


def build_dispatches():
    body = f"""<section style="position: relative; border-bottom: 1px solid #2B1B1D">
  <div class="wrap" style="position: relative; z-index: 1; padding-top: 26px; padding-bottom: clamp(40px, 5vw, 64px)">
    {crumbs(('HOME', '/'), ('DISPATCHES', None))}
    <span class="tag" style="margin-top: 22px">FILE 03 · SUBSTACK</span>
    <h1 class="dh it-glitch shade" style="margin: 18px 0 0; font-size: clamp(38px, 5.2vw, 84px); line-height: 0.98; color: #F2ECE4">DISPATCHES</h1>
    <p class="src shade" data-dispatches-count>TECHNICAL INVARIANCE AUTHORITY ON SUBSTACK</p>
    <p class="shade" style="margin: 20px 0 0; max-width: 680px; padding: 14px 16px; background: rgba(9, 5, 6, 0.72); border-left: 2px solid #E8222A; font-size: 19px; color: #ECE4DC">Written dispatches from the Authority: analysis, history and the programme. Every post goes out by email first and is listed here, newest first.</p>
    <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px"><a class="dsp-btn" href="{SUBSTACK}/subscribe" target="_blank" rel="noopener">Subscribe by email</a><a class="dsp-btn gh" href="{SUBSTACK}/" target="_blank" rel="noopener">Open on Substack ↗</a></div>
  </div>
</section>

<section class="room">
  <div class="wrap" style="padding-top: clamp(28px, 4vw, 48px); padding-bottom: clamp(56px, 7vw, 96px)">
    <p class="rbar mn"><span>DISPATCH FILE · NEWEST FIRST</span><span>TIA / SUBSTACK</span></p>
    <div class="dsp-grid" data-dispatches aria-busy="true" style="margin-top: 22px">{DSP_WAIT}</div>
  </div>
</section>"""
    out = page('Dispatches · Technical Invariance Authority',
               'Written dispatches from the Technical Invariance Authority on Substack: analysis, history and the programme, newest first.',
               '/dispatches/', body, css=DSP_CSS + ROOM_CSS, ticker='DISPATCHES /// TIA ON SUBSTACK /// ANALYSIS · HISTORY · THE PROGRAMME /// SUBSCRIBE BY EMAIL ///',
               current_label='/DISPATCHES', bg=DISPATCH_POSTER, script=False)
    out = out.replace('aria-current="page" style="color: #FF5A60; border-bottom: 2px solid #E8222A">ARCHIVE</a>', '>ARCHIVE</a>', 1)
    out = out.replace('<a href="/dispatches/">DISPATCHES</a>', '<a href="/dispatches/" aria-current="page" style="color: #FF5A60; border-bottom: 2px solid #E8222A">DISPATCHES</a>', 1)
    out = out.replace('</body>', '<script src="/assets/dispatches.js" defer></script>\n</body>', 1)
    d = ROOT / 'dispatches'
    d.mkdir(exist_ok=True)
    (d / 'index.html').write_text(out, encoding='utf-8')


# ---------------------------------------------------------------- German originals (Marx-Engels-Werke)

WERKE = CONTENT / 'werke'
WK_URL = '/archive/werke/'
WK_TAGS = {'i', 'b', 'sup', 'sub', 'br', 'span', 'a', 'img'}
# two images the mirror lacks, set as text: a formula in Anti-Dühring, Nero Caesar in Hebrew letters
WK_IMG_TEXT = {'term_1.gif': 'A<sup>½</sup> = √A', 'me22_468.gif': '<span lang="he" dir="rtl">נרון קסר</span>'}
WK_JUNK = re.compile(r'^\s*(Pfad:|Zurück zum Gesamtverzeichnis)')
WK_CSS = """
.rd-h1 { hyphens: auto; overflow-wrap: break-word; }
.text > p { overflow-wrap: break-word; }
.text .pg::before { content: attr(data-p); display: inline-block; margin: 0 4px; padding: 0 4px; border: 1px solid #3A2326; font-family: 'JetBrains Mono', ui-monospace, monospace; font-style: normal; font-weight: 400; font-size: 11px; line-height: 1.5; letter-spacing: 0.04em; color: #8A7B75; vertical-align: 2px; }
.text .wk-src { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 13px; line-height: 1.5; letter-spacing: 0.04em; color: #A89C95; }
.text .wk-tab { overflow-x: auto; }
.text .wk-tab table { border-collapse: collapse; font-size: 16px; line-height: 1.45; }
.text .wk-tab td { padding: 4px 12px 4px 0; vertical-align: top; border-bottom: 1px solid #2B1B1D; }
.text img { max-width: 100%; height: auto; vertical-align: middle; background: #F2ECE4; }
.text sup { font-size: 0.7em; line-height: 0; }
.text a[href^="#t"], .text a[href^="#Anm"], .text a[href^="#Z"] { border-bottom: 0; }
html.paper .rd-body .text .pg::before { color: #8A6A64; border-color: #D8C3BB; }
html.paper .rd-body .text .wk-src { color: #7A4A47; }
html.paper .rd-body .text .wk-tab td { border-bottom-color: #E2D2CB; }
"""
WK_INTRO = ('What Marx and Engels wrote in German, from the Marx-Engels-Werke (MEW, Dietz Verlag, Berlin). '
            'Writings they composed in English, French or another language appear in the MEW only in its editors\' '
            'translation, so they are left out here, and so are the editors\' introductions and notes. '
            'The page numbers of the MEW are kept in the text so that passages can be cited.')


def wk_text(h):
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', h))).strip()


def wk_plain(h):
    h = re.sub(r'<span class="pg" data-p="([^"]+)"></span>', r'|\1|', h)
    h = re.sub(r'<[^>]*>', '', re.sub(r'<br\s*/?>', '\n', h))
    return '\n'.join(re.sub(r'\s+', ' ', x).strip() for x in html.unescape(h).split('\n')).strip()


def wk_clean(h, pre):
    """Keep the markup a reader needs; drop what the mirror's broken angle brackets left behind."""
    def tag(m):
        close, name, rest = m.group(1), m.group(2).lower(), m.group(3)
        if name not in WK_TAGS:
            return ''
        if close:
            return '' if name in ('br', 'img') else f'</{name}>'
        if name == 'span':
            pg = re.search(r'data-p="([^"]+)"', rest)
            if pg:
                return f'<span class="pg" data-p="{attr(pg.group(1))}">'
            i = re.search(r'id="([^"]+)"', rest)
            return f'<span id="{pre}{attr(i.group(1))}">' if i else '<span>'
        if name == 'a':
            href = re.search(r'href="#([^"]+)"', rest)
            return f'<a href="#{pre}{attr(href.group(1))}">' if href else '<a>'
        if name == 'img':
            src = re.search(r'src="([^"]+)"', rest)
            f = src.group(1).split('/')[-1] if src else ''
            if f in WK_IMG_TEXT:
                return WK_IMG_TEXT[f]
            return f'<img src="{WK_URL}img/{attr(f)}" alt="">' if f and (WERKE / 'img' / f).exists() else ''
        return f'<{name}>'
    h = re.sub(r'<(/?)([^\s<>/]+)([^<>]*)>', tag, h)
    # a bare < in the text (a table's "<=", a quotation mark the mirror mangled)
    return re.sub(r'<(?!/?(?:i|b|sup|sub|br|span|a|img)[\s>])', '&lt;', h)


def wk_load():
    if not (WERKE / 'index.json').exists():
        return []
    ws = json.loads((WERKE / 'index.json').read_text(encoding='utf-8'))['works']
    for w in ws:
        w['path'] = f'{WK_URL}{w["id"]}/'
    return ws


def wk_body(w):
    out, toc, plain_parts, index = [], [], [], []
    n = 0
    multi = len(w['parts']) > 1
    for pi, pt in enumerate(w['parts']):
        body = json.loads((WERKE / f'{w["band"]:02d}' / f'{pt["id"]}.json').read_text(encoding='utf-8'))['body']
        # a contents page of links in front of a book's chapters
        if multi and pi == 0 and pt['words'] <= 60 and 'class="pg"' not in json.dumps(body):
            continue
        pre = f't{pi}-' if multi else 't-'
        if multi and pi == 0:
            # the MEW's own contents tables in front of the first page of a book
            first = next((i for i, (k, h) in enumerate(body) if k != 'table' and 'class="pg"' in h), len(body))
            body = [x for i, x in enumerate(body) if not (x[0] == 'table' and i < first)]
        for k, h in body:
            if k in ('hr', 'fnh'):
                if out and out[-1] != '<hr>':
                    out.append('<hr>')
                continue
            if k == 'table':
                n += 1
                rows = ''.join('<tr>' + ''.join(f'<td>{wk_clean(c, pre)}</td>' for c in r) + '</tr>' for r in h)
                out.append(f'<div id="p{n}" class="wk-tab"><table>{rows}</table></div>')
                plain_parts.append('\n'.join('\t'.join(wk_text(c) for c in r) for r in h))
                index.append([n, ' '.join(' '.join(wk_text(c) for c in r) for r in h)])
                continue
            t = wk_text(h)
            if WK_JUNK.match(t) or (not t and '<img' not in h):
                continue
            n += 1
            x = wk_clean(h, pre).strip()
            index.append([n, t])
            if k == 'h':
                out.append(f'<h2 id="p{n}">{x}</h2>')
                toc.append((f'p{n}', t))
                plain_parts.append(t.upper())
                continue
            cls = {'q': 'q', 'fn': 'fn', 'src': 'wk-src', 'ctr': 'ctr', 'lt': 'ctr'}.get(k, '')
            c = f' class="{cls}"' if cls else ''
            out.append(f'<p id="p{n}"{c}>{x}</p>')
            plain_parts.append(wk_plain(h))
    while out and out[-1] == '<hr>':
        out.pop()
    plain_txt = '\n\n'.join(plain_parts)
    return wk_links('\n'.join(out)), toc, plain_txt, index


def wk_links(h):
    """Page markers become targets; links to the editors' notes, which are left out, become plain text."""
    seen = set()

    def pg(m):
        if m.group(1) in seen:      # the mirror repeats some markers
            return '<span>'
        seen.add(m.group(1))
        return f'<span class="pg" data-p="{m.group(1)}" id="s{m.group(1)}">'
    h = re.sub(r'<span class="pg" data-p="(\d+)">', pg, h)
    ids = set(re.findall(r' id="([^"]+)"', h))

    def link(m):
        t = m.group(1)
        if t in ids:
            return m.group(0)
        page = re.match(r't\d*-S(\d+)$', t)
        if page and f's{page.group(1)}' in ids:
            return f'<a href="#s{page.group(1)}">'
        return '<a data-x>'
    h = re.sub(r'<a href="#([^"]+)">', link, h)
    return re.sub(r'<a data-x>(.*?)</a>', r'\1', h, flags=re.S)


def wk_by(w, byslug):
    return ' and '.join(byslug[s]['display'] for s in w['authors'])


def build_werk(w, prv, nxt, byslug, english):
    body_html, toc, plain_txt, index = wk_body(w)
    nwords = w['words']
    mins = max(1, round(nwords / 230))
    rt = f'{mins // 60} H {mins % 60:02d} MIN' if mins >= 60 else f'{mins} MIN'
    a = byslug[w['authors'][0]]
    by = wk_by(w, byslug)
    pages = f', S. {w["pages"][0]}–{w["pages"][1]}' if w.get('pages') else ''
    ed_bits = list(w.get('facts', []))
    if w.get('note'):
        ed_bits.append(w['note'])
    if w.get('brackets'):
        ed_bits.append(w['brackets'])
    ed_bits.append(f'Text: Marx-Engels-Werke, Band {w["band"]}{pages}. Page numbers of the MEW are shown in the text.')
    edition = ' '.join(ed_bits)
    folder = ROOT / 'archive' / 'werke' / w['id']
    folder.mkdir(parents=True, exist_ok=True)
    txt_name = f'mew-{w["id"]}.txt'
    head = '\n'.join([w['title'].upper(), '', by, str(w['year']), '', edition,
                      'Public domain. Prepared for the TIA archive: ' + SITE + w['path'], '-' * 60])
    (folder / txt_name).write_text(head + '\n\n' + plain_txt.strip() + '\n', encoding='utf-8')

    toc_items = ''.join(f'<li><a href="#{pid}">{esc(label)}</a></li>' for pid, label in toc)
    if len(toc) >= 2:
        aside = f'<aside class="toc mn" aria-label="Inhalt"><p>INHALT · {len(toc)}</p><ol>{toc_items}</ol></aside>'
        mobile = f'<details class="toc-m mn"><summary>INHALT · {len(toc)} ABSCHNITTE</summary><ol>{toc_items}</ol></details>'
        layout = 'rd-layout'
    else:
        aside, mobile, layout = '', '', 'rd-layout solo'
    pn = '<div class="pn mn">'
    pn += f'<a href="{prv["path"]}">← {esc(prv["title"].upper())}</a>' if prv else f'<a href="{WK_URL}">← ALL GERMAN TEXTS</a>'
    pn += f'<a href="{nxt["path"]}">{esc(nxt["title"].upper())} →</a>' if nxt else f'<a href="{WK_URL}">ALL GERMAN TEXTS →</a>'
    pn += '</div>'
    en = english.get(w['id'])
    if en and en['kind'] == 'hosted':
        en_btn = f'<a class="btn gh" href="{en["path"]}">ENGLISH TRANSLATION</a>'
    elif en:
        en_btn = f'<a class="btn gh" href="{byslug[en["author"]]["url"]}">ENGLISH HERE {soon_label(en["soon"], short=True)}</a>'
    else:
        en_btn = ''
    body = f"""<script>try {{ if (localStorage.getItem('tia-read') === 'paper') document.documentElement.classList.add('paper'); }} catch (e) {{}}</script>
<div class="rd-prog" aria-hidden="true"></div>
<div class="rd-poster" aria-hidden="true" style="--ar: {poster_ar(POSTER[a['slug']])}; background-image: url('/assets/bgp/{POSTER[a['slug']]}-1x.webp'); background-image: image-set(url('/assets/bgp/{POSTER[a['slug']]}-1x.webp') 1x, url('/assets/bgp/{POSTER[a['slug']]}.webp') 2x)"></div>
<section style="position: relative; border-bottom: 1px solid #2B1B1D">
  <div class="wrap rd-hero-wrap" style="padding-top: 26px; padding-bottom: clamp(32px, 4vw, 52px)">
    {crumbs(('ARCHIVE', '/archive/'), ('IN GERMAN', WK_URL), (w['title'].upper(), None))}
    <div class="rd-head">
      <a href="{a['url']}" class="bust" aria-label="{attr(a['display'])} dossier">{bust_img(a)}<span class="hc tl"></span><span class="hc tr"></span><span class="hc bl"></span><span class="hc br"></span><span class="it-bscan" aria-hidden="true" style="position: absolute; left: 0; right: 0; height: 2px; background: #FF5A60; box-shadow: 0 0 10px rgba(232, 34, 42, 0.8)"></span></a>
      <div style="flex: 1 1 520px; min-width: 0">
        <span class="tag">ORIGINAL · MEW {w['band']} · {w['year']}</span>
        <h1 class="rd-h1 it-glitch" lang="de">{esc(w['title'])}</h1>
        <p class="src">{esc(by.upper())} · {w['year']} · {words(nwords)} WORDS · {rt} · DEUTSCH</p>
        <p class="rd-ed" lang="de">{esc(edition)} <span lang="en">Public domain.</span></p>
        <div class="rd-act"><a class="btn" href="#p1">Start reading</a>{en_btn}<a class="btn gh" href="{txt_name}" download>DOWNLOAD .TXT</a><button type="button" class="btn gh rd-paper-t" data-paper aria-pressed="false"><i aria-hidden="true"></i><span>PAPER MODE</span></button><a class="btn gh" href="{WK_URL}">ALL GERMAN TEXTS</a></div>
      </div>
    </div>
  </div>
</section>

<section class="rd-body" style="background: rgba(12, 7, 8, 0.6)">
  <div class="wrap {layout}">
    {aside}
    <div style="min-width: 0">
      {mobile}
      <article class="text" lang="de">
{body_html}
      </article>
      <p class="rd-end mn">ENDE · {esc(w['title'].upper())} · {esc(by.upper())}</p>
      {pn}
    </div>
  </div>
</section>
<button type="button" class="rd-paper-t rd-paper-f mn" data-paper aria-pressed="false"><i aria-hidden="true"></i><span>PAPER MODE</span></button>
<script>
(function () {{
  var root = document.documentElement, btns = document.querySelectorAll('[data-paper]');
  function show(on) {{ btns.forEach(function (b) {{ b.setAttribute('aria-pressed', on ? 'true' : 'false'); b.querySelector('span').textContent = on ? 'DARK MODE' : 'PAPER MODE'; }}); }}
  show(root.classList.contains('paper'));
  btns.forEach(function (b) {{ b.addEventListener('click', function () {{
    var on = !root.classList.contains('paper');
    root.classList.toggle('paper', on); show(on);
    try {{ localStorage.setItem('tia-read', on ? 'paper' : 'dark'); }} catch (e) {{}}
  }}); }});
}})();
</script>"""
    title = f'{w["title"]} · {by} · TIA Archive'
    desc = f'{w["title"]} ({w["year"]}) by {by}, the German original from the Marx-Engels-Werke, Band {w["band"]}. Free to read and download.'
    out = page(title, desc, w['path'], body, css=READER_CSS + WK_CSS, current_label='/ARCHIVE/WERKE',
               foot_label=f'INVARIANCETECH.INFO/ARCHIVE/WERKE/{w["id"]}')
    (folder / 'index.html').write_text(out, encoding='utf-8')
    return index


def build_werke_search(ws, indexes):
    """Titles for the archive search, and the full text split by MEW volume so a search loads it piece by piece."""
    d = ROOT / 'archive' / 'werke' / 'text'
    d.mkdir(parents=True, exist_ok=True)
    bands = sorted({w['band'] for w in ws})
    for b in bands:
        mine = [w for w in ws if w['band'] == b]
        rows = [[i, n, t] for i, w in enumerate(mine) for n, t in indexes[w['id']]]
        (d / f'{b:02d}.json').write_text(json.dumps({'w': [w['id'] for w in mine], 'p': rows}, ensure_ascii=False,
                                                    separators=(',', ':')), encoding='utf-8')
    titles = {'bands': bands, 'w': [[w['id'], w['year'], w['band'], w['title'], w['authors']] for w in ws]}
    (ROOT / 'archive' / 'werke' / 'titles.json').write_text(json.dumps(titles, ensure_ascii=False, separators=(',', ':')),
                                                            encoding='utf-8')


def build_werke_index(ws, byslug):
    years = sorted({w['year'] for w in ws})
    groups = {}
    for w in ws:
        groups.setdefault(w['year'], []).append(w)
    secs = []
    for y in years:
        rows = []
        for w in groups[y]:
            who = ' & '.join(byslug[s]['short'] for s in w['authors'])
            rows.append(f'<li><span class="d">MEW {w["band"]}</span><a href="{w["path"]}" lang="de">{esc(w["title"])}</a>'
                        f'<b class="wk-who">{esc(who)}</b></li>')
        secs.append(f'<section class="cw-y" id="y{y}"><h2>{y}<span>{len(groups[y])} TEXT{"S" if len(groups[y]) != 1 else ""}</span></h2><ul class="cw">{"".join(rows)}</ul></section>')
    decades = sorted({y // 10 * 10 for y in years})
    jump = ''.join(f'<a href="#y{next(y for y in years if y // 10 * 10 == d)}">{d}s</a>' for d in decades)
    total = sum(w['words'] for w in ws)
    nm = sum(1 for w in ws if 'marx' in w['authors'])
    ne = sum(1 for w in ws if 'engels' in w['authors'])
    css = CW_CSS + ('.wk-ft { margin-top: 22px; max-width: 760px; padding: 16px; background: rgba(9, 5, 6, 0.82); border: 1px solid #3A2326; }\n'
                    '.wk-ft label { display: block; font-size: 13px; letter-spacing: 0.14em; color: #A89C95; }\n'
                    '.wk-ft div { display: flex; gap: 10px; margin-top: 10px; }\n'
                    '.wk-ft input { flex: 1; min-width: 0; min-height: 50px; box-sizing: border-box; padding: 0 14px; background: #090506; border: 2px solid #3A2326; color: #F2ECE4; font-family: Inter, sans-serif; font-size: 17px; }\n'
                    '.wk-ft button { min-height: 50px; padding: 0 18px; border: 0; background: #C81D25; color: #FFFFFF; font-family: Inter, sans-serif; font-weight: 800; font-size: 16px; cursor: pointer; }\n'
                    '.cw li a { min-width: 0; overflow-wrap: break-word; hyphens: auto; }\n'
                    '.cw li b.wk-who { flex: 0 0 auto; margin-left: auto; padding-left: 8px; color: #A89C95; white-space: nowrap; }\n')
    body = f"""<section style="position: relative; border-bottom: 1px solid #2B1B1D">
  <div class="wrap" style="position: relative; z-index: 1; padding-top: 26px; padding-bottom: clamp(36px, 4vw, 56px)">
    {crumbs(('ARCHIVE', '/archive/'), ('IN GERMAN', None))}
    <span class="tag" style="margin-top: 22px">MARX · ENGELS · DEUTSCH</span>
    <h1 class="dh it-glitch shade" style="margin: 18px 0 0; font-size: clamp(34px, 4.6vw, 72px); line-height: 0.98; color: #F2ECE4">Marx and Engels in German</h1>
    <p class="src shade">{len(ws):,} TEXTS · {total:,} WORDS · MARX {nm} · ENGELS {ne} · {years[0]} — {years[-1]}</p>
    <p class="shade" style="margin: 20px 0 0; max-width: 760px; padding: 14px 16px; background: rgba(9, 5, 6, 0.72); border-left: 2px solid #E8222A; font-size: 17px; color: #ECE4DC">{esc(WK_INTRO)}</p>
    <form action="/archive/" method="get" role="search" class="wk-ft">
      <input type="hidden" name="de" value="1">
      <label for="wk-ft" class="mn">SEARCH INSIDE THE TEXTS</label>
      <div><input id="wk-ft" name="q" type="search" lang="de" autocomplete="off" placeholder="e.g. Mehrwert"><button type="submit">Search</button></div>
    </form>
    <nav class="cw-jump mn" aria-label="Jump to decade">{jump}</nav>
  </div>
</section>

<section class="grid-bg" style="position: relative; background-color: rgba(12, 7, 8, 0.9)">
  <div class="wrap" style="padding-bottom: clamp(56px, 7vw, 96px)">
    <div class="cw-bar mn" role="search">
      <label for="cw-q" class="sr" style="position: absolute; left: -9999px">Filter titles</label>
      <input id="cw-q" type="search" placeholder="Filter {len(ws):,} titles, or type Marx or Engels" autocomplete="off">
      <span class="cnt" id="cw-count" aria-live="polite">{len(ws):,} SHOWN</span>
    </div>
    {''.join(secs)}
    <div class="pn mn"><a href="{byslug['marx']['url']}">← MARX DOSSIER</a><a href="{byslug['engels']['url']}">ENGELS DOSSIER →</a></div>
  </div>
</section>"""
    title = 'Marx and Engels in German · TIA Archive'
    desc = f'{len(ws):,} texts that Marx and Engels wrote in German, {years[0]}–{years[-1]}, from the Marx-Engels-Werke, free to read.'
    out = page(title, desc, WK_URL, body, css=css, current_label='/ARCHIVE/WERKE', bg=POSTER['marx'])
    d = ROOT / 'archive' / 'werke'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text(out, encoding='utf-8')


def build_werke(ws, byslug, works):
    shutil.rmtree(ROOT / 'archive' / 'werke', ignore_errors=True)
    if not ws:
        return 0
    english = {w['de']: w for w in works.values() if w.get('de') and w['kind'] == 'hosted'}
    english.update({w['de']: w for w in works.values() if w.get('de') and w.get('soon') and w['kind'] != 'hosted'})
    indexes = {}
    for i, w in enumerate(ws):
        indexes[w['id']] = build_werk(w, ws[i - 1] if i else None, ws[i + 1] if i + 1 < len(ws) else None, byslug, english)
    build_werke_index(ws, byslug)
    build_werke_search(ws, indexes)
    img = ROOT / 'archive' / 'werke' / 'img'
    img.mkdir(parents=True, exist_ok=True)
    for f in (WERKE / 'img').glob('*'):
        shutil.copy(f, img / f.name)
    return len(ws)


# ---------------------------------------------------------------- the timeline of everyone in the archive

TL_EVENTS = [(1789, 'FRENCH REVOLUTION'), (1848, 'MANIFESTO'), (1871, 'PARIS COMMUNE'), (1917, 'OCTOBER REVOLUTION'),
             (1991, 'USSR DISSOLVED')]
TL_MAJOR = {y for y, _ in TL_EVENTS}
TL_RED, TL_WHITE = '#E8222A', '#F2ECE4'
# one colour per band of the timeline; black lines get a grey edge so they show on the dark ground
TL_COLOUR = {'marxists': TL_RED, 'philosophers': '#B48CFF', 'economists': '#4DA3FF', 'utopians': '#34CFB0',
             'anarchists': '#000000', 'revisionists': '#F2C14E', 'stalinist-line': '#C9824A', 'chinese-line': '#FF6FB5',
             'national-liberation': '#4CC96B', 'yugoslav-road': TL_WHITE}
TL_EDGE = '#9A908A'


def life(s):
    ys = [int(y) for y in re.findall(r'\b(1[6-9]\d\d|20\d\d)\b', s)]
    return ys[0], (ys[1] if len(ys) > 1 else None)


def build_timeline(authors, nm):
    """Everyone in the archive on one time axis, in bands of people who stood close to each other."""
    def person(name, yrs, red, url):
        b, d = life(yrs)
        return {'n': name, 'b': b, 'd': d, 'm': red, 'url': url}
    marxists = {'title': 'THE MARXISTS', 'm': True, 'slug': 'marxists',
                'people': [person(a['short'], a['yr'], True, a['url']) for a in authors]}
    bands = []
    for g in (nm['groups'] if nm else []):
        ps = [person(p['short'], p['years'], False, p['url']) for p in nm['people'] if p['group'] == g['code']]
        if ps:
            bands.append({'title': g['title'].upper(), 'm': False, 'people': ps, 'slug': g['slug']})
    # the Marxists sit between what Marxism came out of and what came after or against it
    at = next((k + 1 for k, b in enumerate(bands) if b['slug'] == 'utopians'), 0)
    bands.insert(at, marxists)
    people = sorted((pp for b in bands for pp in b['people']), key=lambda x: (x['b'], x['n']))
    now = 2026
    y0, y1 = min(x['b'] for x in people) // 20 * 20, 2030
    X0, X1 = 60, 1165
    # a stretch of decades in which nobody in the archive was alive is cut short and marked as a break in the axis
    ga = gb = None
    reach = None
    for pp in people:
        if reach is not None and pp['b'] - reach >= 40:
            a, b = -(-(reach + 1) // 20) * 20, (pp['b'] - 1) // 20 * 20
            if b - a >= 20:
                ga, gb = a, b
                break
        reach = max(reach or 0, pp['d'] or now)
    BRK = 28 if ga else 0
    k = (X1 - X0 - BRK) / ((y1 - y0) - ((gb - ga) if ga else 0))
    def X(y):
        if not ga or y <= ga:
            return X0 + (y - y0) * k
        if y < gb:
            return X0 + (ga - y0) * k + BRK * (y - ga) / (gb - ga)
        return X0 + (ga - y0) * k + BRK + (y - gb) * k
    CH = 7.0                     # width of one character of the 10px label, with its letter-spacing
    for band in bands:
        rows = [X0 + len(band['title']) * CH + 22]     # the band's name takes the left of its first row
        for pp in sorted(band['people'], key=lambda x: (x['b'], x['n'])):
            d = pp['d'] or now
            pp['label'] = f"{pp['n']} {pp['b']}–{pp['d'] or ''}"
            x0, x1 = X(pp['b']), X(d)
            w = len(pp['label']) * CH
            pp['lx'] = x0 if x0 + w <= 1192 else 1192 - w      # a label that would run off the right edge ends there
            right = max(x1, pp['lx'] + w) + 14
            for r, free in enumerate(rows):
                if min(x0, pp['lx']) >= free:
                    rows[r] = right; pp['row'] = r; break
            else:
                rows.append(right); pp['row'] = len(rows) - 1
        band['rows'] = len(rows)
    # event labels sit in as many staggered rows as they need not to overlap
    erows, eplace = [], []
    for y, t in TL_EVENTS:
        w = len(f'{y} {t}') * CH
        a, b = X(y) - w / 2, X(y) + w / 2
        for r, free in enumerate(erows):
            if a >= free:
                erows[r] = b + 8; eplace.append(r); break
        else:
            erows.append(b + 8); eplace.append(len(erows) - 1)
    top, step, pad = 14 + 12 * len(erows) + 14, 22, 14
    y = top
    for band in bands:
        band['top'] = y
        y += 16 + step * (band['rows'] - 1) + pad
    bottom = y + 4
    H = bottom + 40
    ev = ''.join(f'<path d="M{X(y):.1f} {14 + 12 * r + 4}V{bottom - 6}"{" stroke-dasharray=\"2 5\" opacity=\"0.55\"" if y not in TL_MAJOR else ""}></path>'
                 for (y, _), r in zip(TL_EVENTS, eplace))
    evt = ''.join(f'<text x="{X(y):.1f}" y="{14 + 12 * r}"{" fill=\"#C98A87\"" if y not in TL_MAJOR else ""}>{y} {t}</text>'
                  for (y, t), r in zip(TL_EVENTS, eplace))
    seps, names, lines, dots = [], [], [], []
    for n, band in enumerate(bands):
        c = TL_COLOUR.get(band['slug'], TL_WHITE)
        dark = c == '#000000'
        edge = f' stroke="{TL_EDGE}" stroke-width="1.2"' if dark else ''
        tc = '#BDB4AE' if dark else c       # black type would vanish: the anarchists' names are grey, their lines black
        if n:
            seps.append(f'M{X0} {band["top"] - pad / 2:.0f}H{X1}')
        names.append(f'<text x="{X0}" y="{band["top"] + 10}" fill="{tc}">{esc(band["title"])}</text>')
        for pp in band['people']:
            yy = band['top'] + 16 + step * pp['row']
            x0, x1 = X(pp['b']), X(pp['d'] or now)
            under = f'<path d="M{x0:.1f} {yy}H{x1:.1f}" stroke="{TL_EDGE}" stroke-width="4.4"></path>' if dark else ''
            lines.append(f'<a href="{pp["url"]}"><title>{esc(pp["label"])}</title>{under}<path d="M{x0:.1f} {yy}H{x1:.1f}" stroke="{c}" stroke-width="2"></path>'
                         f'<text x="{pp["lx"]:.1f}" y="{yy - 6}" fill="{tc}">{esc(pp["label"])}</text></a>')
            dots.append(f'<circle cx="{x0:.1f}" cy="{yy}" r="3" fill="{c}"{edge}></circle>')
            dots.append(f'<circle cx="{x1:.1f}" cy="{yy}" r="3" fill="{c}"{edge}></circle>' if pp['d'] else
                        f'<path d="M{x1:.1f} {yy - 4}L{x1 + 7:.1f} {yy}L{x1:.1f} {yy + 4}Z" fill="{c}"{edge}></path>')
    ticks = [t for t in range(y0, 2031, 20) if not ga or not ga < t < gb]
    tk = ''.join(f'M{X(t):.1f} {bottom}V{bottom + 6}' for t in ticks)
    if ga:
        bx = X(ga) + BRK / 2
        axis = (f'<path d="M{X0} {bottom}H{bx - 7:.1f}M{bx + 7:.1f} {bottom}H{X1}" stroke="#A89C95" stroke-width="1"></path>'
                f'<path d="M{bx - 11:.1f} {bottom + 6}L{bx - 3:.1f} {bottom - 6}M{bx + 3:.1f} {bottom + 6}L{bx + 11:.1f} {bottom - 6}" stroke="#A89C95" stroke-width="1.5"></path>')
    else:
        axis = f'<path d="M{X0} {bottom}H{X1}" stroke="#A89C95" stroke-width="1"></path>'
    tkt = ''.join(f'<text x="{X(t):.1f}" y="{bottom + 22}">{t}</text>' for t in ticks if t != ga)
    aria = (f'Timeline of lifespans from {people[0]["b"]} to today, in groups. ' +
            ' '.join(f"{b['title'].title()}{' (Marxists, in red)' if b['m'] else ''}: " +
                     ', '.join(f"{x['n'].title()} {x['b']} to {x['d'] or 'now'}" for x in sorted(b['people'], key=lambda x: x['b'])) + '.'
                     for b in bands) +
            ' Markers at ' + ', '.join(f'{y} ({t.lower()})' for y, t in TL_EVENTS) + '.')
    nn = sum(1 for x in people if not x['m'])
    return f"""<figure class="it-rv" style="margin: 32px 0 0; padding: 18px 18px 10px; background: rgba(9, 5, 6, 0.85); border: 1px solid #3A2326; overflow-x: auto">
      <svg viewBox="0 0 1200 {H}" width="100%" role="img" aria-label="{attr(aria)}" style="display: block; min-width: 980px">
        <g stroke="#E8222A" stroke-width="1" stroke-dasharray="4 4" opacity="0.8">{ev}</g>
        <g font-family="'JetBrains Mono', ui-monospace, monospace" font-size="10" letter-spacing="1" fill="#FF5A60" text-anchor="middle">{evt}</g>
        <path d="{''.join(seps)}" stroke="#3A2326" stroke-width="1"></path>
        <g font-family="'JetBrains Mono', ui-monospace, monospace" font-size="10" font-weight="700" letter-spacing="1.5">{''.join(names)}</g>
        <g class="tl-p" font-family="'JetBrains Mono', ui-monospace, monospace" font-size="10" letter-spacing="1">{''.join(lines)}</g>
        <g>{''.join(dots)}</g>
        {axis}
        <g stroke="#A89C95" stroke-width="1"><path d="{tk}"></path></g>
        <g font-family="'JetBrains Mono', ui-monospace, monospace" font-size="10" fill="#A89C95" text-anchor="middle">{tkt}</g>
        <g class="it-sweep"><path d="M{X0} {top - 10}V{bottom - 6}" stroke="#FF5A60" stroke-width="1.5" opacity="0.7"></path><path d="M{X0 - 6} {bottom - 6}L{X0} {bottom - 14}L{X0 + 6} {bottom - 6}Z" fill="#FF5A60"></path></g>
      </svg>
      <figcaption class="mn" style="display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 8px; font-size: 13px; letter-spacing: 0.14em; color: #A89C95"><span>FIG. 01 · LIFESPANS IN THE ARCHIVE, {people[0]['b']} — TODAY</span><span><b style="color: {TL_RED}; font-weight: 400">━━ MARXISTS · {len(authors)}</b></span><span>{nn} NON-MARXISTS, ONE COLOUR PER GROUP</span></figcaption>
    </figure>"""



# ---------------------------------------------------------------- the Non-Marxists section

NM_URL = '/archive/non-marxists/'          # the old address of the section, now a pointer
NM_HOME = '/archive/#non-marxists'
# names that are not "first name, surname"
NM_SHORT = {'xi': 'XI', 'mao': 'MAO', 'deng': 'DENG', 'ho-chi-minh': 'HO CHI MINH', 'kim-il-sung': 'KIM IL-SUNG'}
AR_CSS = """
.chip-br { flex-basis: 100%; height: 0; }
.chip.nmc { border-color: #4A4442; }
.chip.nmc.on { background: #F2ECE4; border-color: #F2ECE4; color: #120B0C; }
.chip.nmc.on span { color: #5A4F4C; }
.ar-block { margin-top: 44px; scroll-margin-top: 90px; }
.ar-bh { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 20px; border-bottom: 1px solid #3A2326; padding-bottom: 10px; }
.ar-bh h2 { margin: 0; font-weight: 400; font-size: 18px; letter-spacing: 0.1em; color: #FF5A60; }
.nm-hero { padding-top: 40px; border-top: 1px solid #3A2326; }
.nm-hero .nm-tag { border-color: #6E6461; color: #F2ECE4; }
.nm-hero h2 { margin: 18px 0 0; font-size: clamp(34px, 5vw, 80px); line-height: 1; color: #F2ECE4; }
.nm-hero .nm-lede { margin: 22px 0 26px; max-width: 760px; padding: 14px 16px; background: rgba(9, 5, 6, 0.72); border-left: 2px solid #F2ECE4; font-size: 19px; color: #ECE4DC; }
.ar-bh p { margin: 0; max-width: 680px; font-size: 15px; color: #B3A79F; }
.ar-block[hidden] { display: none; }
.nm-dos { border-color: #3A3533; }
.nm-dos .dos-top .tg { color: #F2ECE4; }
.nm-dos .dos-body .yr { color: #CFC4BC; }
.tl-p a:hover text, .tl-p a:focus text { fill: #FF5A60; }
"""
NM_POSTER = {'NM-01': 'p_mon_moon', 'NM-02': 'p_mon_towers', 'NM-03': 'p_rom_five_year', 'NM-04': 'p_hp_marianne',
             'NM-05': 'p_share_the_land', 'NM-06': 'p_mon_worker_kolkhoz', 'NM-07': 'p_mon_tiananmen',
             'NM-08': 'p_raise_it_higher', 'NM-09': 'p_mon_motherland_bw'}
NM_INDEX_POSTER = 'p_mon_motherland_sunset'
NM_CSS = """
.nm-grp { margin-top: 52px; scroll-margin-top: 90px; }
.nm-grp > header { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 18px; border-bottom: 1px solid #3A2326; padding-bottom: 10px; }
.nm-grp > header h2 { margin: 0; font-family: 'JetBrains Mono', ui-monospace, monospace; font-weight: 400; font-size: 22px; letter-spacing: 0.08em; color: #F2ECE4; }
.nm-grp > header h2 span { color: #FF5A60; margin-right: 10px; }
.nm-grp > header p { margin: 0; max-width: 620px; font-size: 15px; color: #B3A79F; }
.nm-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap: 20px; margin-top: 22px; }
.nm-jump { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 18px; }
.nm-jump a { padding: 5px 9px; border: 1px solid #3A2326; background: rgba(9, 5, 6, 0.7); font-size: 12px; letter-spacing: 0.1em; color: #CFC4BC; }
.nm-jump a:hover { border-color: #E8222A; color: #FF5A60; }
.nm-strip { display: flex; gap: 6px; overflow: hidden; margin-top: 18px; -webkit-mask-image: linear-gradient(to right, #000 80%, transparent); mask-image: linear-gradient(to right, #000 80%, transparent); }
.nm-strip img { flex: 0 0 auto; height: 92px; width: auto; }
.nm-panel { display: block; margin-top: 56px; padding: 20px; border: 1px solid #3A2326; background: rgba(9, 5, 6, 0.82); color: #F2ECE4; }
.nm-panel:hover { border-color: #E8222A; }
.nm-panel p { margin: 8px 0 0; max-width: 760px; color: #CFC4BC; }
.nm-panel .go { display: inline-block; margin-top: 14px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 14px; letter-spacing: 0.12em; color: #FF5A60; }
"""


def nm_load(byslug):
    f = CONTENT / 'others.json'
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding='utf-8'))
    groups = {g['code']: g for g in d['groups']}
    for g in d['groups']:
        g['people'] = []
    for i, p in enumerate(d['people']):
        p['n'] = i + 1
        g = groups[p['group']]
        g['people'].append(p)
        p['nm'] = True
        p['grp'] = g
        p['display'] = p['name']
        p['short'] = NM_SHORT.get(p['slug']) or p['name'].split()[-1].upper()
        p['url'] = f"/archive/{p['slug']}/"
        img = ROOT / 'assets' / f"hex_{p['slug']}.png"
        p['img'] = lossless(f"/assets/hex_{p['slug']}.png") if img.exists() else ''
        p['poster'] = NM_POSTER.get(p['group'], NM_INDEX_POSTER)
        p['works'].sort(key=lambda w: (year0(w['year']), w['title']))
        for w in p['works']:
            w['author'] = p['slug']
            w['authors'] = [p['slug']]
            w.setdefault('cols', [])
            if w['kind'] == 'hosted':
                w['path'] = f"{p['url']}{w['slug']}/"
        byslug[p['slug']] = p
    return d


def nm_card(p, i):
    hosted = [w for w in p['works'] if w['kind'] == 'hosted']
    txt = '<span class="h">TXT</span>'
    lis = ''.join(f'<li><a {work_link_attrs(w)}>{esc(w["title"])}</a> ({esc(w["year"])})'
                  f'{txt if w["kind"] == "hosted" else ""}</li>' for w in ([w for w in p['works'] if w.get('key')] or p['works'])[:3])
    img = bust_img(p)
    delay = f'; animation-delay: {i * 0.4:g}s' if i else ''
    return f"""      <article class="dos it-rv nm-dos" id="{p['slug']}" data-t="nm {p['grp']['slug']}">
        <div class="dos-top mn"><span>FILE {p['n']:02d}</span><span class="tg">{esc(p['grp']['title'].upper())}</span></div>
        <a href="{p['url']}" class="dos-img" tabindex="-1" aria-hidden="true">{img}<span class="hc tl"></span><span class="hc tr"></span><span class="hc bl"></span><span class="hc br"></span><span class="it-bscan" style="position: absolute; left: 0; right: 0; height: 2px; background: #FF5A60; box-shadow: 0 0 10px rgba(232, 34, 42, 0.8){delay}"></span></a>
        <div class="dos-body">
          <h3><a href="{p['url']}">{esc(p['name'])}</a></h3>
          <p class="yr">{esc(p['years'])} · {esc(p['place'].upper())}</p>
          <p class="role">{esc(p['role'])}</p>
          <ul>{lis}</ul>
          <p class="cnt">{f'<b>{len(hosted)} FULL TEXT{"S" if len(hosted) != 1 else ""}</b>' if hosted else 'LINKED WORKS'} · {f'<a href="{p["url"]}works/" style="color: inherit; border-bottom: 1px dotted #4A4442">{len(p["author"]["bib"]):,} ITEMS FILED</a>' if p.get('author') and p['author'].get('bib') else f'{len(p["works"])} WORK{"S" if len(p["works"]) != 1 else ""}'}</p>
          <a href="{p['url']}" class="open">OPEN FILE →</a>
        </div>
      </article>"""


def redirect_stub(old, new, title):
    """A page left at an old address that sends readers to the new one."""
    d = ROOT / old.strip('/')
    d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · TIA Archive</title><link rel="canonical" href="{SITE}{new}"><meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={new}"><style>body {{ margin: 0; background: #090506; color: #F2ECE4; font: 17px/1.5 Inter, system-ui, sans-serif; }} a {{ color: #FF5A60; }} p {{ margin: 40px 16px; }}</style></head>
<body><p>{esc(title)} has moved: <a href="{new}">{SITE}{new}</a></p><script>location.replace({json.dumps(new)} + location.hash.replace(/^#$/, ''));</script></body></html>
""", encoding='utf-8')


def build_nm_redirects(d):
    """The section first opened at /archive/non-marxists/; its pages now sit beside the Marxists."""
    redirect_stub(NM_URL, NM_HOME, 'Non-Marxists')
    for p in d['people']:
        if p.get('author'):
            continue
        redirect_stub(f"{NM_URL}{p['slug']}/", p['url'], p['name'])
        for w in p['works']:
            if w['kind'] == 'hosted':
                redirect_stub(f"{NM_URL}{p['slug']}/{w['slug']}/", w['path'], w['title'])


def build_nm_person(p, prev_p, next_p, byslug):
    hosted = [w for w in p['works'] if w['kind'] == 'hosted']
    rows = '\n      '.join(work_row(w, byslug, me=p['slug']) for w in p['works'])
    img = (f'<img src="{p["img"]}" alt="Statue portrait of {attr(p["name"])} in red hexagons">' if p['img'] else
           '<span class="mn" style="align-self: center; font-size: 13px; letter-spacing: 0.14em; color: #6E5A55">NO PORTRAIT ON FILE</span>')
    note = f'<p class="note"><b>COPYRIGHT</b>{esc(p["note"])}</p>' if p.get('note') else ''
    mia = (f'<p class="mn" style="margin: 16px 0 0; font-size: 14px; letter-spacing: 0.12em"><a href="{attr(p["mia"])}" target="_blank" rel="noopener" style="color: #FF5A60">{esc(p["short"])} ON MARXISTS.ORG ↗</a></p>'
           if p.get('mia') else '')
    years = [year0(w['year']) for w in p['works']]
    links = [w for w in p['works'] if w['kind'] == 'link']
    legend = ' · '.join(x for x in [
        '<span style="color: #39D98A">[READ →]</span> FULL TEXT ON THIS SITE' if hosted else '',
        '<span>[MIA ↗]</span> OPENS THE MARXISTS INTERNET ARCHIVE' if any('marxists.org' in w['url'] for w in links) else '',
        '<span>[LINK ↗]</span> OPENS THE PUBLISHED TEXT ON ANOTHER SITE' if any('marxists.org' not in w['url'] for w in links) else ''] if x)
    body = f"""<section style="position: relative; overflow: hidden; border-bottom: 1px solid #2B1B1D">
  <div class="wrap" style="padding-top: 26px; padding-bottom: clamp(40px, 5vw, 64px)">
    {crumbs(('ARCHIVE', '/archive/'), ('NON-MARXISTS', NM_HOME), (p['short'], None))}
    <div class="au-grid">
      <div class="dos-img au-img">{img}<span class="hc tl"></span><span class="hc tr"></span><span class="hc bl"></span><span class="hc br"></span><span class="it-bscan" aria-hidden="true" style="position: absolute; left: 0; right: 0; height: 2px; background: #FF5A60; box-shadow: 0 0 10px rgba(232, 34, 42, 0.8)"></span></div>
      <div style="min-width: 0">
        <span class="tag">{p['group']} · {esc(p['grp']['title'].upper())}</span>
        <h1 class="dh it-glitch shade" style="margin: 18px 0 0; font-size: clamp(36px, 5vw, 78px); line-height: 0.98; color: #F2ECE4">{esc(p['name'].upper())}</h1>
        <p class="src shade">{esc(p['years'])} · {esc(p['place'].upper())}</p>
        <p class="shade" style="margin: 20px 0 0; max-width: 640px; font-size: 19px; color: #ECE4DC">{esc(p['role'])}</p>
        <div class="stats"><div><b>{len(p['works'])}</b><span>WORKS FILED</span></div><div><b>{len(hosted)}</b><span>FULL TEXTS HERE</span></div><div><b>{min(years) if years else '—'}</b><span>FIRST WORK</span></div><div><b>{max(years) if years else '—'}</b><span>LAST WORK</span></div></div>
        {mia}
      </div>
    </div>
  </div>
</section>

<section class="grid-bg" style="position: relative; overflow: hidden; background-color: rgba(12, 7, 8, 0.84)">
  <div class="wrap" style="padding-top: 44px; padding-bottom: clamp(56px, 7vw, 96px)">
    {note}
    <div class="it-rv">
      <p class="mn sec-h">WORKS · IN ORDER</p>
      {rows}
      <p class="mn" style="margin: 14px 0 0; font-size: 13px; letter-spacing: 0.1em; color: #A89C95">{legend}</p>
    </div>
    <div class="pn mn"><a href="{prev_p['url']}">← {esc(prev_p['short'])}</a><a href="{NM_HOME}">ALL NON-MARXISTS</a><a href="{next_p['url']}">{esc(next_p['short'])} →</a></div>
  </div>
</section>"""
    out = page(f'{p["name"]} · Non-Marxists · TIA Archive', f'{p["role"]} Works by {p["name"]}, with full texts and sources.',
               p['url'], body, css=CW_CSS, current_label=f'/ARCHIVE/{p["short"]}', bg=p['poster'])
    dd = ROOT / p['url'].strip('/')
    dd.mkdir(parents=True, exist_ok=True)
    (dd / 'index.html').write_text(out, encoding='utf-8')


def nm_file_dossiers(d, authors):
    """Put the full dossiers marked "filed" (Lassalle and Kautsky) among the non-Marxists of their group."""
    groups = {g['code']: g for g in d['groups']}
    order = {g['code']: i for i, g in enumerate(d['groups'])}
    for a in authors:
        if not a.get('filed'):
            continue
        g = groups[a['filed']]
        a['group'], a['grp'] = g['code'], g
        yr = html.unescape(a['yr'])
        years, _, place = yr.partition(' · ')
        d['people'].append({'slug': a['slug'], 'name': a['display'],
                            'display': a['display'], 'short': a['short'], 'years': years, 'place': place.title(),
                            'role': html.unescape(a['role']), 'img': a['img'], 'url': a['url'], 'group': g['code'], 'grp': g,
                            'works': a['works'], 'author': a, 'nm': True, 'poster': POSTER[a['slug']]})
    d['people'].sort(key=lambda p: (order[p['group']], life(p['years'])[0]))
    for g in d['groups']:
        g['people'] = [p for p in d['people'] if p['group'] == g['code']]
    for i, p in enumerate(d['people']):
        p['n'] = i + 1


def build_nm(d, byslug):
    if not d:
        return 0, 0
    people = d['people']
    total = 0
    for i, p in enumerate(people):
        if p.get('author'):
            continue                   # a full dossier, built with the Marxists' pages
        for w in p['works']:
            if w['kind'] == 'hosted':
                n = build_reader(p, w, byslug, None)
                total += n
                print(f'  text  {w["path"]:<58} {n:>8,} words')
        build_nm_person(p, people[i - 1], people[(i + 1) % len(people)], byslug)
    build_nm_redirects(d)
    return sum(1 for p in people if not p.get('author')), total


def main():
    authors, byslug, works, cols = load()
    # clear old generated output so removed works disappear
    for a in authors:
        shutil.rmtree(ROOT / 'archive' / a['slug'], ignore_errors=True)
    shutil.rmtree(ROOT / 'archive' / 'collections', ignore_errors=True)
    shutil.rmtree(ROOT / 'archive' / 'non-marxists', ignore_errors=True)
    shutil.rmtree(ROOT / 'archive' / 'text', ignore_errors=True)
    for a in authors:
        a['bib'] = load_bibliography(a, byslug)
    ws = wk_load()
    wk_ids = {w['id'] for w in ws}
    for w in works.values():
        if w.get('de') and w['de'] not in wk_ids:
            print(f'  warning: {w["id"]}: no German text {w["de"]}')
            del w['de']
    for a in authors:
        a['wk'] = sum(1 for w in ws if a['slug'] in w['authors']) if a['slug'] in ('marx', 'engels') else 0
    total = 0
    for a in authors:
        for w in a['works']:
            if w['kind'] == 'hosted':
                n = build_reader(a, w, byslug, authors)
                total += n
                print(f'  text  {w["path"]:<58} {n:>8,} words')
    marxist_slugs = set(byslug)
    nm = nm_load(byslug)
    if nm:
        taken = marxist_slugs | {'werke', 'text', 'collections', 'non-marxists', 'img'}
        clash = [p['slug'] for p in nm['people'] if p['slug'] in taken]
        assert not clash, f'non-Marxist slugs clash with archive folders: {clash}'
        for p in nm['people']:
            shutil.rmtree(ROOT / 'archive' / p['slug'], ignore_errors=True)
        nm_file_dossiers(nm, authors)
    n_nm, nm_words = build_nm(nm, byslug)
    print(f'  non-marxists: {n_nm} files, {nm_words:,} words of full text')
    marx = [a for a in authors if not a.get('nm')]
    for i, a in enumerate(marx):
        a['num'] = f'{i + 1:02d}'      # the Index of Marxists is numbered without the dossiers filed elsewhere
    for i, a in enumerate(marx):
        build_author(a, marx[i - 1], marx[(i + 1) % len(marx)], byslug, cols)
    ring = nm['people'] if nm else []
    for a in authors:
        if a.get('nm'):
            k = next(i for i, p in enumerate(ring) if p.get('author') is a)
            build_author(a, ring[k - 1], ring[(k + 1) % len(ring)], byslug, cols)
    for a in authors:
        build_complete_works(a, byslug)
    for c in cols:
        if c.get('url', '').startswith('/'):
            build_collection(c, byslug, cols)
    build_index(authors, byslug, works, cols, nm)
    build_home(authors, works, cols, nm)
    build_watch()
    build_dispatches()
    build_catalogue_json(authors, byslug, works, cols, nm)
    nb = build_bibliography_json(authors)
    print(f'  complete works: {nb:,} items ' + ', '.join(f"{a['slug']} {len(a['bib']):,}" for a in authors))
    nw = build_werke(ws, byslug, works)
    print(f'  german originals: {nw:,} texts')
    n = build_sitemap(authors, works, cols, ws, nm)
    nh = sum(1 for w in works.values() if w['kind'] == 'hosted')
    print(f'{len(authors)} authors, {len(works)} works ({nh} full texts, {total:,} words), '
          f'{sum(1 for c in cols if c.get("url", "").startswith("/"))} collection pages, {n} sitemap URLs')


if __name__ == '__main__':
    main()
