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
            'BOLSHEVIK': 'bolsheviks', 'SPARTACIST': 'spartacists', 'COMMUNIST LEFT': 'left'}
CHIPS = [('all', 'ALL'), ('precursor', 'PRECURSOR'), ('founders', 'FOUNDERS'),
         ('second', 'SECOND INTERNATIONAL'), ('bolsheviks', 'BOLSHEVIKS'),
         ('spartacists', 'SPARTACISTS'), ('left', 'COMMUNIST LEFT')]
DISPLAY = {'hegel': 'G. W. F. Hegel', 'marx': 'Karl Marx', 'engels': 'Friedrich Engels',
           'kautsky': 'Karl Kautsky', 'lenin': 'V. I. Lenin', 'trotsky': 'Leon Trotsky',
           'luxemburg': 'Rosa Luxemburg', 'bukharin': 'N. I. Bukharin', 'bordiga': 'Amadeo Bordiga'}


# Full-colour posters used as moving backgrounds (no duotone).
POSTER = {'hegel': 'p_hp_napoleon', 'marx': 'p_mon_marx_chemnitz', 'engels': 'p_mon_magnitogorsk',
          'kautsky': 'p_share_the_land', 'lenin': 'p_mon_lenin_head', 'trotsky': 'p_raise_it_higher',
          'luxemburg': 'p_rom_romantics', 'bukharin': 'p_mon_worker_kolkhoz', 'bordiga': 'p_audit_no_country'}
AUTHOR_WALL = {
    'hegel': ['p_hp_marianne', 'p_hp_napoleon', 'p_mon_moon', 'p_mon_motherland_bw'],
    'marx': ['p_mon_magnitogorsk', 'p_mon_worker_kolkhoz', 'p_mon_motherland_bw', 'p_audit_no_country'],
    'engels': ['p_mon_marx_chemnitz', 'p_rom_five_year', 'p_mon_magnitogorsk', 'p_share_the_land'],
    'kautsky': ['p_hp_marianne', 'p_share_the_land', 'p_rom_come_back', 'p_mon_worker_kolkhoz'],
    'lenin': ['p_nine_days', 'p_mon_motherland_flags', 'p_raise_it_higher', 'p_mon_moon'],
    'trotsky': ['p_mon_motherland_sunset', 'p_raise_it_higher', 'p_nine_days', 'p_mon_motherland_flags'],
    'luxemburg': ['p_rom_romantics', 'p_hp_marianne', 'p_rom_come_back', 'p_raise_it_higher'],
    'bukharin': ['p_rom_five_year', 'p_mon_worker_kolkhoz', 'p_mon_towers', 'p_share_the_land'],
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
NAV_EXTRA = '<a href="/#watch">WATCH</a>\n      <a href="/dispatches/">DISPATCHES</a>'
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
DSP_WAIT = '<p class="dsp-wait mn">LOADING DISPATCHES FROM SUBSTACK…</p>'


BASE_CSS = re.search(r'<style>\n(.*?)</style>', ARCH_TPL, re.S).group(1)
OVERLAYS = re.search(r'(<div aria-hidden="true">\n  <div class="ov-lines">.*?\n</div>\n)', ARCH_TPL, re.S).group(1)
HEADER = re.search(r'(<header class="tbar">.*?</header>)', ARCH_TPL, re.S).group(1)
FOOTER = re.search(r'(<footer.*?</footer>)', ARCH_TPL, re.S).group(1)
TIMELINE = re.search(r'(<figure class="it-rv".*?</figure>)', ARCH_TPL, re.S).group(1)
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900'
         '&amp;family=Lora:ital,wght@0,400;0,600;1,400&amp;family=Share+Tech+Mono&amp;display=swap" rel="stylesheet">')

EXTRA_CSS = """
@media (max-width: 1500px) { .tbar .wrap > span.mn:last-child { display: none; } }
/* the whole poster, shown no bigger than the sharp 2x copy allows, set against the dark page on the right */
.page-bg { position: fixed; top: 0; right: 0; width: min(58vw, calc(100vh * var(--ar, 0.8)), 1440px); aspect-ratio: var(--ar, 0.8); max-height: 100vh; z-index: -1; pointer-events: none; background-image: var(--p1); background-image: image-set(var(--p1) 1x, var(--p2) 2x); background-size: cover; background-position: center top; -webkit-mask-image: linear-gradient(to right, transparent 0%, rgba(0, 0, 0, 0.55) 22%, #000 48%), linear-gradient(to bottom, #000 70%, transparent); mask-image: linear-gradient(to right, transparent 0%, rgba(0, 0, 0, 0.55) 22%, #000 48%), linear-gradient(to bottom, #000 70%, transparent); -webkit-mask-composite: source-in; mask-composite: intersect; }
.page-bg::after { content: ""; position: absolute; inset: 0; background: linear-gradient(to bottom, rgba(9, 5, 6, 0.25), rgba(9, 5, 6, 0.1) 40%, rgba(9, 5, 6, 0.55)), repeating-linear-gradient(to bottom, rgba(9, 5, 6, 0.16) 0 1px, transparent 1px 3px); }
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
.dos-body .cnt { margin: 6px 0 0; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-size: 12px; letter-spacing: 0.12em; color: #A89C95; }
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
.row .st.wait { color: #E8A33A; }
.row.wk .ld { align-self: center; transform: none; }
a.row:hover .ti { color: #FF5A60; }
.note { margin: 0 0 32px; padding: 16px 18px; border: 1px solid #E8A33A; background: rgba(232, 163, 58, 0.07); font-size: 16px; color: #EADFCB; }
.note b { font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-weight: 400; letter-spacing: 0.12em; color: #E8A33A; margin-right: 8px; }
.btn { display: inline-flex; align-items: center; min-height: 48px; padding: 0 18px; box-sizing: border-box; background: #C81D25; color: #FFFFFF; font-family: Inter, sans-serif; font-weight: 800; font-size: 16px; }
.btn:hover { background: #E8222A; color: #FFFFFF; }
.btn.gh { background: transparent; border: 1px solid #3A2326; color: #F2ECE4; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-weight: 400; font-size: 14px; letter-spacing: 0.1em; }
.btn.gh:hover { border-color: #E8222A; color: #FF5A60; }
.pn { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; margin-top: 48px; padding-top: 18px; border-top: 1px solid #3A2326; font-size: 14px; letter-spacing: 0.12em; }
.pn a { color: #FF5A60; }
.stats { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 24px; }
.stats div { min-width: 120px; padding: 12px 14px; border: 1px solid #3A2326; background: rgba(9, 5, 6, 0.8); }
.stats b { display: block; font-family: Inter, sans-serif; font-weight: 900; font-size: 34px; line-height: 1; color: #F2ECE4; }
.stats span { display: block; margin-top: 6px; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-size: 12px; letter-spacing: 0.12em; color: #A89C95; }
.au-grid { display: grid; grid-template-columns: minmax(0, 380px) minmax(0, 1fr); gap: 40px; align-items: end; margin-top: 22px; }
.au-img { height: 440px; border: 1px solid #3A2326; }
@media (max-width: 860px) { .au-grid { grid-template-columns: 1fr; } .au-img { height: 340px; } }
#ar-results { scroll-margin-top: 90px; }
.res-box { padding: 18px; border: 1px solid #3A2326; background: rgba(9, 5, 6, 0.85); }
.res-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; font-size: 14px; letter-spacing: 0.12em; color: #A89C95; }
.res-head b { font-weight: 400; color: #F2ECE4; }
.hit-list { list-style: none; margin: 0; padding: 0; }
.hit-list li { padding: 14px 0; border-bottom: 1px solid #241618; }
.hit-list .hw { font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-size: 13px; letter-spacing: 0.1em; color: #A89C95; }
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
.rd-h1 { margin: 16px 0 0; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-weight: 400; font-size: clamp(32px, 4.4vw, 62px); line-height: 1.04; color: #F2ECE4; text-transform: uppercase; }
.rd-sub { margin: 12px 0 0; max-width: 760px; font-size: 18px; color: #CFC4BC; }
.rd-ed { margin: 14px 0 0; max-width: 760px; font-size: 15px; color: #A89C95; }
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
.text > [id]::before { content: counter(pp); position: absolute; left: -64px; top: 0.45em; width: 46px; text-align: right; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-size: 11px; line-height: 1; letter-spacing: 0.06em; color: #4A2B2E; }
.text > [id]:hover::before { color: #E8222A; }
.text h2 { margin: 2.2em 0 1em; padding-top: 18px; border-top: 1px solid #3A2326; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-weight: 400; font-size: 21px; line-height: 1.35; letter-spacing: 0.08em; color: #FF5A60; }
.text h2::before { top: 1.6em !important; }
.text .cap { text-align: center; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-size: 15px; line-height: 1.5; letter-spacing: 0.1em; color: #A89C95; margin-bottom: 0.6em; }
.text .sig { text-align: right; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-size: 15px; letter-spacing: 0.1em; color: #A89C95; }
.text .lb { white-space: pre-line; }
.text .ctr { white-space: pre-line; text-align: center; color: #CFC4BC; }
.text .q { padding-left: 22px; border-left: 2px solid #4A2B2E; color: #D3C9BF; }
.text .q::before { left: -64px; }
.text .fn { font-size: 16px; color: #BFB3AA; }
.text .tn { padding: 12px 16px; border: 1px dashed #3A2326; font-family: Inter, system-ui, sans-serif; font-size: 14px; color: #A89C95; }
.text pre { overflow-x: auto; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-size: 14px; line-height: 1.5; color: #CFC4BC; white-space: pre; }
.text hr { border: 0; height: auto; text-align: center; margin: 2em 0; }
.text hr::after { content: "*   *   *"; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; color: #7A4246; }
.text em { font-style: italic; color: #F2ECE4; }
.text .flash { animation: rd-flash 3s ease-out 1; }
@keyframes rd-flash { 0%, 30% { background: rgba(232, 34, 42, 0.16); box-shadow: 0 0 0 10px rgba(232, 34, 42, 0.16); } 100% { background: transparent; box-shadow: 0 0 0 10px transparent; } }
@media (max-width: 700px) { .text { padding-left: 0; font-size: 18px; } .text > [id]::before { display: none; } }
.rd-end { margin-top: 56px; padding-top: 18px; border-top: 1px solid #3A2326; font-size: 14px; letter-spacing: 0.12em; color: #A89C95; }
@media (max-width: 760px) { .tbar { position: static; } .text > * { scroll-margin-top: 16px; } .toc-m { position: sticky; top: 0; z-index: 5; } }
@media (prefers-reduced-motion: reduce) { .rd-prog, .text .flash { animation: none !important; } }
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
        a['display'] = DISPLAY[a['slug']]
        a['short'] = a['slug'].upper()
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
    return s


def plain(s, lang):
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
            elif len(one) <= 80 and is_caps(one.replace('_', '')):
                items.append(('cand', one))
            elif len(lines[0]) - len(lines[0].lstrip()) >= 20 and len(one) < 60:
                items.append(('sig', one))
            elif front and len(one) < 100:
                items.append(('ctr', one))
            else:
                items.append(('p', one))
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
        <a href="{a['url']}" class="dos-img" tabindex="-1" aria-hidden="true"><img src="{a['img']}" alt=""><span class="hc tl"></span><span class="hc tr"></span><span class="hc bl"></span><span class="hc br"></span><span class="co r" style="top: 26%; right: 10px"><b>{a['hex']}</b><i></i></span><span class="it-bscan" style="position: absolute; left: 0; right: 0; height: 2px; background: #FF5A60; box-shadow: 0 0 10px rgba(232, 34, 42, 0.8){delay}"></span></a>
        <div class="dos-body">
          <h3><a href="{a['url']}">{a['name']}</a></h3>
          <p class="yr">{a['yr']}</p>
          <p class="role">{a['role']}</p>
          <ul>{''.join(lis)}</ul>
          <p class="cnt">{f'<b>{len(hosted)} FULL TEXT{"S" if len(hosted) != 1 else ""}</b>' if hosted else 'NO FULL TEXTS YET'} · <a href="{a['url']}works/" style="color: inherit; border-bottom: 1px dotted #4A2B2E">{len(a.get('bib', [])):,} ITEMS FILED</a></p>
          <a href="{a['url']}" class="open">OPEN DOSSIER →</a>
        </div>
      </article>"""


def work_row(w, byslug, show_author=False, me=None):
    title = esc(w['title'])
    small = []
    if w.get('subtitle'):
        small.append(esc(w['subtitle']))
    others = [s for s in w['authors'] if s != me]
    if me and others:
        small.append('With ' + ' and '.join(byslug[s]['display'] for s in others))
    sm = f'<small>{" · ".join(small)}</small>' if small else ''
    by = f'<span class="by">{" + ".join(byslug[s]["short"] for s in w["authors"])}</span>' if show_author else ''
    st = '<span class="st ok">[READ →]</span>' if w['kind'] == 'hosted' else '<span class="st ln">[MIA ↗]</span>'
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

def build_reader(a, w, byslug, others):
    lang = w.get('lang', 'en')
    raw = (CONTENT / 'texts' / f'{w["id"]}.txt').read_text(encoding='utf-8')
    text = prep(raw, lang)
    items = parse(text, lang)
    body_html, toc, index = render_text(items, lang)
    nwords = len(re.findall(r'\w+', text))
    mins = round(nwords / 230)
    rt = f'{mins // 60} H {mins % 60:02d} MIN' if mins >= 60 else f'{mins} MIN'
    folder = ROOT / 'archive' / a['slug'] / w['slug']
    folder.mkdir(parents=True, exist_ok=True)

    by = byline(w, byslug)
    txt_head = '\n'.join(filter(None, [
        w['title'].upper(), w.get('subtitle', ''), '', by, w['year'], '', w['edition'],
        'Public domain. Prepared for the TIA archive: ' + SITE + w['path'], '', '-' * 60, '', '']))
    (folder / f'{w["slug"]}.txt').write_text(txt_head + text.strip() + '\n', encoding='utf-8')

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
    pn += f'<a href="{nxt["path"]}">{esc(nxt["title"].upper())} →</a>' if nxt else '<a href="/archive/">INDEX OF MARXISTS →</a>'
    pn += '</div>'

    sub = f'<p class="rd-sub">{esc(w["subtitle"])}</p>' if w.get('subtitle') else ''
    body = f"""<div class="rd-prog" aria-hidden="true"></div>
<div class="rd-poster" aria-hidden="true" style="--ar: {poster_ar(POSTER[a['slug']])}; background-image: url('/assets/bgp/{POSTER[a['slug']]}-1x.webp'); background-image: image-set(url('/assets/bgp/{POSTER[a['slug']]}-1x.webp') 1x, url('/assets/bgp/{POSTER[a['slug']]}.webp') 2x)"></div>
<section style="position: relative; border-bottom: 1px solid #2B1B1D">
  <div class="wrap rd-hero-wrap" style="padding-top: 26px; padding-bottom: clamp(32px, 4vw, 52px)">
    {crumbs(('ARCHIVE', '/archive/'), (a['short'], a['url']), (w['title'].upper(), None))}
    <div class="rd-head">
      <a href="{a['url']}" class="bust" aria-label="{attr(a['display'])} dossier"><img src="{a['img']}" alt=""><span class="hc tl"></span><span class="hc tr"></span><span class="hc bl"></span><span class="hc br"></span><span class="it-bscan" aria-hidden="true" style="position: absolute; left: 0; right: 0; height: 2px; background: #FF5A60; box-shadow: 0 0 10px rgba(232, 34, 42, 0.8)"></span></a>
      <div style="flex: 1 1 520px; min-width: 0">
        <span class="tag">FULL TEXT · {a['short']} · {esc(w['year'])}</span>
        <h1 class="rd-h1 it-glitch">{esc(w['title'])}</h1>
        {sub}
        <p class="src">{esc(by.upper())} · {esc(w['year'])} · {words(nwords)} WORDS · {rt} · {'ENGLISH' if lang == 'en' else 'DEUTSCH'}</p>
        <p class="rd-ed">{esc(w['edition'])} Public domain.</p>
        <div class="rd-act"><a class="btn" href="#p1">Start reading</a><a class="btn gh" href="{w['slug']}.txt" download>DOWNLOAD .TXT</a><a class="btn gh" href="{a['url']}">{a['short']} DOSSIER</a></div>
      </div>
    </div>
  </div>
</section>

<section style="background: rgba(12, 7, 8, 0.6)">
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
</section>"""
    title = f'{w["title"]} · {by} · TIA Archive'
    desc = f'Full text of {w["title"]} ({w["year"]}) by {by}. {w["edition"]} Free to read and download.'
    out = page(title, desc, w['path'], body, css=READER_CSS, current_label=f'/ARCHIVE/{a["short"]}',
               foot_label=f'INVARIANCETECH.INFO/ARCHIVE/{a["slug"].upper()}/{w["slug"].upper()}')
    (folder / 'index.html').write_text(out, encoding='utf-8')
    return nwords


def build_author(a, prev_a, next_a, byslug, cols):
    hosted = [w for w in a['works'] if w['kind'] == 'hosted']
    linked = [w for w in a['works'] if w['kind'] == 'link']
    # works co-written with someone else and filed under them (the Manifesto under Engels)
    shared = [w for o in byslug.values() if o['slug'] != a['slug'] for w in o['works'] if a['slug'] in w.get('with', [])]
    allw = sorted(a['works'] + shared, key=lambda w: (year0(w['year']), w['title']))
    nh = len(hosted) + sum(1 for w in shared if w['kind'] == 'hosted')
    nl = len(linked) + sum(1 for w in shared if w['kind'] == 'link')
    years = [year0(w['year']) for w in allw]
    mycols = [c for c in cols if any(a['slug'] in w['authors'] for w in c['works'])]
    note = f'<p class="note"><b>COPYRIGHT</b>{esc(a["note"])}</p>' if a.get('note') else ''
    rows = '\n      '.join(work_row(w, byslug, me=a['slug']) for w in allw)
    colrows = '\n      '.join(collection_row(c) for c in mycols)
    bib_years = [i['y'] for i in a['bib']] or years
    bib_y0, bib_y1 = min(bib_years + years), max(bib_years + years)
    cw_link = (f'<a class="au-cw" href="{a["url"]}works/">Complete works <small>{len(a["bib"]):,} ITEMS →</small></a>' if a['bib'] else '')
    cw_more = (f'<a class="row" href="{a["url"]}works/" style="color: #FF5A60"><span>ALL {len(a["bib"]):,} WORKS AND LETTERS, BY DATE</span><span class="ld"></span><span>[COMPLETE WORKS →]</span></a>' if a['bib'] else '')
    body = f"""<section style="position: relative; overflow: hidden; border-bottom: 1px solid #2B1B1D">
  <div class="wrap" style="padding-top: 26px; padding-bottom: clamp(40px, 5vw, 64px)">
    {crumbs(('ARCHIVE', '/archive/'), (a['short'], None))}
    <div class="au-grid">
      <div class="dos-img au-img"><img src="{a['img']}" alt="{attr(a['alt'])}"><span class="hc tl"></span><span class="hc tr"></span><span class="hc bl"></span><span class="hc br"></span><span class="co r" aria-hidden="true" style="top: 22%; right: 10px"><b>{a['hex']}</b><i></i></span><span class="it-bscan" aria-hidden="true" style="position: absolute; left: 0; right: 0; height: 2px; background: #FF5A60; box-shadow: 0 0 10px rgba(232, 34, 42, 0.8)"></span></div>
      <div style="min-width: 0">
        <span class="tag">SUBJECT {a['num']} · {a['tg']}</span>
        <h1 class="mn it-glitch shade" style="margin: 18px 0 0; font-size: clamp(42px, 6vw, 92px); line-height: 1; color: #F2ECE4">{a['name']}</h1>
        <p class="src shade">{a['yr']}</p>
        <p class="shade" style="margin: 20px 0 0; max-width: 640px; font-size: 19px; color: #ECE4DC">{a['role']}</p>
        <div class="stats"><div><b>{len(a['bib']):,}</b><span>ITEMS FILED</span></div><div><b>{nh}</b><span>FULL TEXTS HERE</span></div><div><b>{bib_y0}</b><span>FIRST ITEM</span></div><div><b>{bib_y1}</b><span>LAST ITEM</span></div></div>
        {cw_link}
        <p class="mn" style="margin: 16px 0 0; font-size: 14px; letter-spacing: 0.12em"><a href="{attr(a['mia'])}" target="_blank" rel="noopener" style="color: #FF5A60">{a['short']} ON MARXISTS.ORG ↗</a></p>
      </div>
    </div>
  </div>
</section>

<section class="grid-bg" style="position: relative; overflow: hidden; background-color: rgba(12, 7, 8, 0.84)">
  <div class="wrap" style="padding-top: 44px; padding-bottom: clamp(56px, 7vw, 96px)">
    {note}
    <div class="it-rv">
      <p class="mn sec-h">KEY WORKS · IN ORDER</p>
      {rows}
      {cw_more}
      <p class="mn" style="margin: 14px 0 0; font-size: 13px; letter-spacing: 0.1em; color: #A89C95"><span style="color: #39D98A">[READ →]</span> FULL TEXT ON THIS SITE · <span>[MIA ↗]</span> OPENS THE MARXISTS INTERNET ARCHIVE</p>
    </div>
    <div class="it-rv" style="margin-top: 48px">
      <p class="mn sec-h">FILED IN COLLECTIONS</p>
      {colrows}
    </div>
    <div class="pn mn"><a href="{prev_a['url']}">← SUBJECT {prev_a['num']} · {prev_a['short']}</a><a href="/archive/">INDEX</a><a href="{next_a['url']}">SUBJECT {next_a['num']} · {next_a['short']} →</a></div>
  </div>
</section>"""
    ticker = f"DOSSIER {a['num']} /// {html.unescape(a['name'])} /// {html.unescape(a['yr'])} /// {len(a['bib']):,} ITEMS FILED /// {nh} FULL TEXTS /// {a['tg']} ///"
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
    <h1 class="mn it-glitch shade" style="margin: 18px 0 0; font-size: clamp(42px, 6vw, 92px); line-height: 1; color: #F2ECE4">{c['title']}</h1>
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


def build_index(authors, byslug, works, cols):
    hosted = sorted([w for w in works.values() if w['kind'] == 'hosted'], key=lambda w: (year0(w['year']), w['title']))
    nh, nl = len(hosted), len(works) - len(hosted)
    t = ARCH_TPL
    # hero: counts and a real search form
    t = t.replace('SRC: TIA ARCHIVE · 9 SUBJECTS · 6 TENDENCIES · 1770 — 1970',
                  f'SRC: TIA ARCHIVE · 9 SUBJECTS · {len(works)} WORKS · {nh} FULL TEXTS · 1770 — 1970')
    t = t.replace('/// 1770 — 1970 ///', f'/// {len(works)} WORKS /// {nh} FULL TEXTS /// 1770 — 1970 ///')
    t = t.replace('Every major thinker, filed by tendency. Open a dossier to read their works in order, from the first article to the last letter.',
                  'Every major thinker, filed by tendency. Open a dossier for their works in order. Texts in the public domain are here in full and searchable; the rest link to the Marxists Internet Archive.')
    search = f"""<form role="search" id="ar-form" action="/archive/" method="get" style="flex: 1 1 360px; min-width: 0; padding: 20px; background: rgba(9, 5, 6, 0.82); border: 1px solid #3A2326">
      <label for="ar-q" class="mn" style="display: block; font-size: 14px; letter-spacing: 0.14em; color: #A89C95">&gt; QUERY THE ARCHIVE</label>
      <div style="display: flex; gap: 10px; margin-top: 12px">
        <input id="ar-q" name="q" type="search" autocomplete="off" placeholder="Name, work, year or phrase" style="flex: 1; min-width: 0; min-height: 52px; box-sizing: border-box; padding: 0 14px; background: #090506; border: 2px solid #3A2326; color: #F2ECE4; font-family: Inter, sans-serif; font-size: 17px">
        <button type="submit" style="min-height: 52px; padding: 0 20px; border: 0; background: #C81D25; color: #FFFFFF; font-family: Inter, sans-serif; font-weight: 800; font-size: 16px; cursor: pointer">Search</button>
      </div>
      <p class="mn" style="margin: 12px 0 0; font-size: 12px; letter-spacing: 0.1em; color: #A89C95">SEARCHES {sum(len(a['bib']) for a in authors):,} TITLES AND THE FULL TEXT OF {nh} WORKS</p>
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
      <div id="ar-full"></div>
    </div>
  </div>
</section>
"""
    t = t.replace('<div aria-hidden="true" class="sec-bg" style="background-image: url(\'/assets/bg_archivepage.webp\')"></div>',
                  '', 1)
    t = t.replace('<h1 class="mn it-glitch" style="margin: 18px 0 0; font-size: clamp(46px, 6.6vw, 104px)', '<h1 class="mn it-glitch shade" style="margin: 18px 0 0; font-size: clamp(46px, 6.6vw, 104px)', 1)
    t = t.replace('<p style="margin: 22px 0 0; max-width: 620px; font-size: 19px; color: #DCD2CA">', '<p style="margin: 22px 0 0; max-width: 620px; padding: 14px 16px; background: rgba(9, 5, 6, 0.72); border-left: 2px solid #E8222A; font-size: 19px; color: #ECE4DC">', 1)
    hero_end = t.index('</section>', t.index('id="ar-form"')) + len('</section>')
    t = t[:hero_end] + '\n' + results + t[hero_end:]

    # main section: filters, timeline, dossiers, texts, collections
    counts = {k: sum(1 for a in authors if a['tendency'] == k) for k, _ in CHIPS}
    counts['all'] = len(authors)
    chips = '\n      '.join(
        f'<button type="button" class="chip{" on" if k == "all" else ""}" data-f="{k}" aria-pressed="{"true" if k == "all" else "false"}">{label}<span>{counts[k]}</span></button>'
        for k, label in CHIPS)
    cards = '\n\n'.join(dossier_card(a, i) for i, a in enumerate(authors))
    text_rows = '\n      '.join(work_row(w, byslug, show_author=True) for w in hosted)
    col_rows = '\n      '.join(collection_row(c) for c in cols)
    main = f"""<section class="grid-bg" style="position: relative; overflow: hidden; background-color: rgba(12, 7, 8, 0.84)">
  <div class="wrap" style="padding-top: 36px; padding-bottom: clamp(56px, 7vw, 96px)">
    <div role="group" aria-label="Filter by tendency" style="display: flex; flex-wrap: wrap; gap: 8px">
      {chips}
    </div>

    {TIMELINE}

    <div id="ar-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr)); gap: 20px; margin-top: 32px">

{cards}
    </div>

    <div class="it-rv" id="texts" style="margin-top: 56px">
      <div style="display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 10px; border-bottom: 1px solid #3A2326; padding-bottom: 10px">
        <p class="mn" style="margin: 0; font-size: 18px; letter-spacing: 0.1em">READING ROOM · {nh} FULL TEXTS</p>
        <span class="mn" style="font-size: 13px; letter-spacing: 0.1em; color: #A89C95">PUBLIC DOMAIN · FREE TO READ AND DOWNLOAD</span>
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
    t = t.replace('</style>', EXTRA_CSS + '</style>', 1)
    t = t.replace('<body>\n<div style="position: relative; background: #090506;', '<body>\n' + page_bg(INDEX_POSTER) + '<div style="position: relative;', 1)
    assert 'class="page-bg"' in t
    t = t.replace(re.search(r'<link href="https://fonts.googleapis.com/css2[^>]*>', t).group(), FONTS.split('\n')[1])
    t = t.replace('</body>', '<script src="/assets/archive.js" defer></script>\n<script src="/assets/tia-media.js" defer></script>\n</body>')
    (ROOT / 'archive' / 'index.html').write_text(t, encoding='utf-8')


def build_home(authors, works, cols):
    t = HOME_TPL
    nh = sum(1 for w in works.values() if w['kind'] == 'hosted')
    for a in authors:
        t = t.replace(f'<a href="/archive/" style="display: block; text-align: center"><div style="position: relative; overflow: hidden"><img src="/assets/hex_{a["slug"]}.png"',
                      f'<a href="{a["url"]}" style="display: block; text-align: center"><div style="position: relative; overflow: hidden"><img src="/assets/hex_{a["slug"]}.png"')
    for c in cols:
        old = re.search(rf'<a href="[^"]*" class="row"><span style="color: #A89C95">{c["code"]}</span>.*?</a>', t)
        if old:
            t = t.replace(old.group(), collection_row(c))
    t = t.replace('<a href="#watch">WATCH</a>', '<a href="#watch">WATCH</a>\n      <a href="#dispatches">DISPATCHES</a>', 1)
    section = f"""
<section id="dispatches" class="grid-bg" style="position: relative; overflow: hidden; background-color: #0C0708; border-top: 1px solid #2B1B1D">
  <div aria-hidden="true" class="sec-bg" style="left: auto; width: min(620px, 48%); height: 100%; background-image: url('/assets/bgp/p_mon_tiananmen.webp'); background-size: cover; background-position: center top; background-repeat: no-repeat; opacity: 0.32; -webkit-mask-image: linear-gradient(to right, transparent, #000 55%), linear-gradient(to bottom, #000 60%, transparent); mask-image: linear-gradient(to right, transparent, #000 55%), linear-gradient(to bottom, #000 60%, transparent); -webkit-mask-composite: source-in; mask-composite: intersect"></div>
  <div class="wrap" style="padding-top: clamp(56px, 7vw, 100px); padding-bottom: clamp(56px, 7vw, 100px)">
    <div class="it-rv" style="display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 20px">
      <div>
        <span class="tag">FILE 05-B</span>
        <h2 class="h2">DISPATCHES</h2>
        <p class="src">SRC: TIA ON SUBSTACK · BY EMAIL</p>
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 10px"><a class="dsp-btn" href="{SUBSTACK}/subscribe" target="_blank" rel="noopener">Subscribe on Substack</a><a class="dsp-btn gh" href="/dispatches/">All dispatches →</a></div>
    </div>
    <p class="it-rv" style="margin: 22px 0 0; max-width: 660px; font-size: 19px; color: #CFC4BC">Written dispatches from the Authority: analysis, history and the programme, sent out by email and filed here as they go out.</p>
    <div class="dsp-grid" data-dispatches data-limit="3" aria-busy="true">{DSP_WAIT}</div>
  </div>
</section>
"""
    i = t.index('</section>', t.index('<section id="watch"')) + len('</section>')
    t = t[:i] + '\n' + section + t[i:]
    t = t.replace('</style>', DSP_CSS + '</style>', 1)
    t = t.replace('</body>', '<script src="/assets/dispatches.js" defer></script>\n<script src="/assets/tia-media.js" defer></script>\n</body>', 1)
    t = t.replace('SRC: TIA ARCHIVE · 9 SUBJECTS · 8 COLLECTIONS', f'SRC: TIA ARCHIVE · 9 SUBJECTS · {nh} FULL TEXTS · 8 COLLECTIONS')
    t = re.sub(r'<div role="search" class="panel" style="padding: 22px">(.*?)</p>\n        </div>',
               lambda m: '<form role="search" class="panel" action="/archive/" method="get" style="padding: 22px">' + m.group(1) + '</p>\n        </form>',
               t, count=1, flags=re.S)
    t = t.replace('<input id="it-q" type="search"', '<input id="it-q" name="q" type="search" autocomplete="off"')
    t = re.sub(r'(<input id="it-q".*?\n\s*)<button type="button"', r'\1<button type="submit"', t, count=1, flags=re.S)
    t = t.replace('</style>', '.row .st.wait { color: #E8A33A; }\n</style>', 1)
    assert '<form role="search" class="panel"' in t and 'name="q"' in t
    (ROOT / 'index.html').write_text(t, encoding='utf-8')


def build_catalogue_json(authors, byslug, works, cols):
    data = {
        'authors': [{'slug': a['slug'], 'name': a['display'], 'short': a['short'], 'years': html.unescape(a['yr']),
                     'tg': a['tg'], 'role': html.unescape(a['role']), 'img': a['img'], 'url': a['url']} for a in authors],
        'works': [{'id': w['id'], 'title': w['title'], 'sub': w.get('subtitle', ''), 'year': w['year'],
                   'authors': w['authors'], 'kind': w['kind'], 'url': work_href(w), 'lang': w.get('lang', 'en')}
                  for w in sorted(works.values(), key=lambda w: (year0(w['year']), w['title']))],
        'collections': [{'code': c['code'], 'title': c['title'], 'url': c.get('url', '')} for c in cols],
    }
    (ROOT / 'archive' / 'catalogue.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def build_sitemap(authors, works, cols):
    urls = ['/', '/archive/', '/dispatches/', '/arcade/', '/arcade/plan1/', '/arcade/behind-jupiter/', '/arcade/red-moon/', '/arcade/wither/', '/arcade/all-power/', '/shop/']
    urls += [a['url'] for a in authors]
    urls += [a['url'] + 'works/' for a in authors if a.get('bib')]
    urls += [w['path'] for w in sorted(works.values(), key=lambda w: w['id']) if w['kind'] == 'hosted']
    urls += [c['url'] for c in cols if c.get('url', '').startswith('/')]
    body = '\n'.join(f'  <url><loc>{SITE}{u}</loc></url>' for u in urls)
    (ROOT / 'sitemap.xml').write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n',
        encoding='utf-8')
    return len(urls)


# ---------------------------------------------------------------- complete works (bibliographies)

BIB_BASE = {
    'hegel': 'https://www.marxists.org/reference/archive/hegel/',
    'lenin': 'https://www.marxists.org/archive/lenin/works/',
    'trotsky': 'https://www.marxists.org/archive/trotsky/',
}
BIB_SOURCE = {
    'hegel': 'Hegel\'s principal writings and lecture courses. Links open the Hegel section of the Marxists Internet Archive.',
    'marx': 'Every item in the 50 volumes of the Marx-Engels Collected Works: books, articles, manuscripts, speeches and letters, by date. Links open the Marxists Internet Archive\'s index for that year; texts in the public domain open here.',
    'engels': 'Every item in the 50 volumes of the Marx-Engels Collected Works: books, articles, manuscripts, speeches and letters, by date. Links open the Marxists Internet Archive\'s index for that year; texts in the public domain open here.',
    'kautsky': 'Every work in the Kautsky section of the Marxists Internet Archive.',
    'lenin': 'Every entry in the date index of the Lenin Internet Archive, which follows the Collected Works. Works in several parts are listed once.',
    'trotsky': 'Every work in the Trotsky index of the Marxists Internet Archive.',
    'luxemburg': 'Every work in the Luxemburg section of the Marxists Internet Archive.',
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
.cw-y h2 { margin: 0; display: flex; justify-content: space-between; align-items: baseline; gap: 12px; border-bottom: 1px solid #3A2326; padding-bottom: 8px; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-weight: 400; font-size: 28px; color: #FF5A60; }
.cw-y h2 span { font-size: 12px; letter-spacing: 0.12em; color: #A89C95; }
.cw { list-style: none; margin: 0; padding: 0; columns: 2 440px; column-gap: 44px; }
.cw li { break-inside: avoid; display: flex; gap: 12px; padding: 7px 0; border-bottom: 1px solid #1E1214; font-size: 15.5px; line-height: 1.4; }
.cw li .d { flex: 0 0 56px; padding-top: 3px; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-size: 12px; letter-spacing: 0.04em; color: #8A7B75; }
.cw li a { color: #E6DDD3; }
.cw li a:hover { color: #FF5A60; }
.cw li.l a { color: #B3A79F; }
.cw li b { margin-left: 8px; font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-weight: 400; font-size: 11px; letter-spacing: 0.12em; color: #39D98A; }
.no-letters .cw li.l { display: none; }
.cw-y[hidden], .cw li[hidden] { display: none; }
.au-cw { display: inline-flex; align-items: center; gap: 12px; margin-top: 22px; min-height: 52px; padding: 0 20px; background: #C81D25; color: #FFFFFF; font-family: Inter, sans-serif; font-weight: 800; font-size: 17px; }
.au-cw:hover { background: #E8222A; color: #FFFFFF; }
.au-cw small { font-family: 'Manolo Mono', 'Share Tech Mono', monospace; font-weight: 400; font-size: 13px; letter-spacing: 0.1em; opacity: 0.85; }
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
    {crumbs(('ARCHIVE', '/archive/'), (a['short'], a['url']), ('COMPLETE WORKS', None))}
    <span class="tag" style="margin-top: 22px">SUBJECT {a['num']} · COMPLETE WORKS</span>
    <h1 class="mn it-glitch shade" style="margin: 18px 0 0; font-size: clamp(40px, 5.6vw, 86px); line-height: 1; color: #F2ECE4">{a['name']}</h1>
    <p class="src shade">{len(items):,} ITEMS · {len(items) - nl:,} WORKS{f' · {nl:,} LETTERS' if nl else ''} · {years[0]} — {years[-1]}</p>
    <p class="shade" style="margin: 20px 0 0; max-width: 760px; padding: 14px 16px; background: rgba(9, 5, 6, 0.72); border-left: 2px solid #E8222A; font-size: 17px; color: #ECE4DC">{esc(BIB_SOURCE.get(a['slug'], ''))}</p>
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
    <span class="tag" style="margin-top: 22px">FILE 05-B · SUBSTACK</span>
    <h1 class="mn it-glitch shade" style="margin: 18px 0 0; font-size: clamp(44px, 6.2vw, 100px); line-height: 1; color: #F2ECE4">DISPATCHES</h1>
    <p class="src shade" data-dispatches-count>TECHNICAL INVARIANCE AUTHORITY ON SUBSTACK</p>
    <p class="shade" style="margin: 20px 0 0; max-width: 680px; padding: 14px 16px; background: rgba(9, 5, 6, 0.72); border-left: 2px solid #E8222A; font-size: 19px; color: #ECE4DC">Written dispatches from the Authority: analysis, history and the programme. Every post goes out by email first and is listed here, newest first.</p>
    <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px"><a class="dsp-btn" href="{SUBSTACK}/subscribe" target="_blank" rel="noopener">Subscribe by email</a><a class="dsp-btn gh" href="{SUBSTACK}/" target="_blank" rel="noopener">Open on Substack ↗</a></div>
  </div>
</section>

<section class="grid-bg" style="position: relative; background-color: rgba(12, 7, 8, 0.86)">
  <div class="wrap" style="padding-top: 12px; padding-bottom: clamp(56px, 7vw, 96px)">
    <div class="dsp-grid" data-dispatches aria-busy="true">{DSP_WAIT}</div>
  </div>
</section>"""
    out = page('Dispatches · Technical Invariance Authority',
               'Written dispatches from the Technical Invariance Authority on Substack: analysis, history and the programme, newest first.',
               '/dispatches/', body, css=DSP_CSS, ticker='DISPATCHES /// TIA ON SUBSTACK /// ANALYSIS · HISTORY · THE PROGRAMME /// SUBSCRIBE BY EMAIL ///',
               current_label='/DISPATCHES', bg=DISPATCH_POSTER, script=False)
    out = out.replace('aria-current="page" style="color: #FF5A60; border-bottom: 2px solid #E8222A">ARCHIVE</a>', '>ARCHIVE</a>', 1)
    out = out.replace('<a href="/dispatches/">DISPATCHES</a>', '<a href="/dispatches/" aria-current="page" style="color: #FF5A60; border-bottom: 2px solid #E8222A">DISPATCHES</a>', 1)
    out = out.replace('</body>', '<script src="/assets/dispatches.js" defer></script>\n</body>', 1)
    d = ROOT / 'dispatches'
    d.mkdir(exist_ok=True)
    (d / 'index.html').write_text(out, encoding='utf-8')


def main():
    authors, byslug, works, cols = load()
    # clear old generated output so removed works disappear
    for a in authors:
        shutil.rmtree(ROOT / 'archive' / a['slug'], ignore_errors=True)
    shutil.rmtree(ROOT / 'archive' / 'collections', ignore_errors=True)
    shutil.rmtree(ROOT / 'archive' / 'text', ignore_errors=True)
    for a in authors:
        a['bib'] = load_bibliography(a, byslug)
    total = 0
    for a in authors:
        for w in a['works']:
            if w['kind'] == 'hosted':
                n = build_reader(a, w, byslug, authors)
                total += n
                print(f'  text  {w["path"]:<58} {n:>8,} words')
    for i, a in enumerate(authors):
        build_author(a, authors[i - 1], authors[(i + 1) % len(authors)], byslug, cols)
        build_complete_works(a, byslug)
    for c in cols:
        if c.get('url', '').startswith('/'):
            build_collection(c, byslug, cols)
    build_index(authors, byslug, works, cols)
    build_home(authors, works, cols)
    build_dispatches()
    build_catalogue_json(authors, byslug, works, cols)
    nb = build_bibliography_json(authors)
    print(f'  complete works: {nb:,} items ' + ', '.join(f"{a['slug']} {len(a['bib']):,}" for a in authors))
    n = build_sitemap(authors, works, cols)
    nh = sum(1 for w in works.values() if w['kind'] == 'hosted')
    print(f'{len(authors)} authors, {len(works)} works ({nh} full texts, {total:,} words), '
          f'{sum(1 for c in cols if c.get("url", "").startswith("/"))} collection pages, {n} sitemap URLs')


if __name__ == '__main__':
    main()
