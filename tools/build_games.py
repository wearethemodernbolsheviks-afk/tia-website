#!/usr/bin/env python3
"""Write the TIA Arcade game pages (arcade/<slug>/index.html) from one shared shell.

    python3 tools/build_games.py

Game logic lives in assets/games/<slug>.js, shared styles in assets/games/game.css.
"""
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = 'https://invariancetech.info'

GAMES = [
    {
        'slug': 'plan1', 'sim': 'SIM-01', 'title': 'PLAN/1',
        'desc': 'PLAN/1: run an economy with no money. Every sector eats the output of the others. Move workers where they are needed and keep every stockpile above zero for five years.',
        'help': '<span><b>1–6</b> ADD A WORKER</span><span><b>SHIFT + 1–6</b> TAKE ONE AWAY</span><span><b>SPACE</b> PAUSE</span><span><b>PHONE</b> TAP + AND −</span>',
        'body': '<div class="p1" id="game"></div>',
    },
    {
        'slug': 'behind-jupiter', 'sim': 'SIM-02', 'title': 'BEHIND JUPITER',
        'desc': 'Behind Jupiter: an arcade shooter from the world of USSR 2089. Carry the last box through the belt and past Helios-Orbital to the fleet behind Jupiter.',
        'help': '<span><b>ARROWS / WASD</b> FLY</span><span><b>SPACE</b> FIRE</span><span><b>X</b> FORCE (CLEARS THE SCREEN)</span><span><b>P</b> PAUSE</span><span><b>PHONE</b> DRAG TO FLY · FIRES BY ITSELF</span>',
        'body': '<div class="bj" id="game"><canvas id="bj-cv" aria-label="Behind Jupiter game screen" role="img"></canvas></div>',
    },
    {
        'slug': 'red-moon', 'sim': 'SIM-03', 'title': 'RED MOON TERMINAL',
        'desc': 'Red Moon Terminal: the Red Moon files, playable. Decode the packets from Entry 4471, unlock the crew logs and find what Helios-Orbital redacted.',
        'help': '<span><b>HELP</b> LIST COMMANDS</span><span><b>TAB</b> COMPLETE</span><span><b>↑ ↓</b> HISTORY</span><span><b>TAP</b> ANY UNDERLINED NAME TO RUN IT</span>',
        'body': '<h1 class="sr-only">Red Moon Terminal</h1><div class="rm" id="game"></div>',
    },
    {
        'slug': 'all-power', 'sim': 'SIM-05', 'title': 'ALL POWER', 'js': 'allpower', 'pre': ['allpower-model'],
        'desc': 'All Power: an incremental game from Oppie\'s America. Start with one rooftop panel in Berkeley, 1985, and collect sunlight until you have all of it: the continent, the Sun, the galaxy, the universe.',
        'help': '<span><b>C</b> COLLECT SUNLIGHT</span><span><b>CLICK / TAP</b> TO BUILD AND PLAN</span><span><b>1 SECOND</b> = 1 HOUR OF GRID TIME</span>',
        'body': '<div class="ap" id="game"></div>',
    },
    {
        'slug': 'wither', 'sim': 'SIM-04', 'title': 'WITHER',
        'desc': 'Wither: from Oppie\'s America 1985. Chair a world planning committee whose members no longer age, and make the state wither away before it decides to live forever.',
        'help': '<span><b>1 2 3</b> CHOOSE A DECREE</span><span><b>CLICK / TAP</b> A CARD</span><span><b>12 TERMS</b> 1950–1985</span>',
        'body': '<div class="wi" id="game"></div>',
    },
]

SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title_txt} · TIA Arcade</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{site}/arcade/{slug}/">
<meta name="theme-color" content="#090506">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon_32.png?v=3">
<link rel="icon" type="image/png" sizes="512x512" href="/assets/favicon_512.png?v=3">
<link rel="apple-touch-icon" href="/assets/favicon_180.png?v=3">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Technical Invariance Authority">
<meta property="og:title" content="{title_txt} · TIA Arcade">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{site}/arcade/{slug}/">
<meta property="og:image" content="{site}/assets/og_tia.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&amp;family=JetBrains+Mono:wght@400;500;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/games/game.css">
<link rel="stylesheet" href="/assets/games/{js}.css">
</head>
<body>
<header class="g-top">
  <a href="/" aria-label="Technical Invariance Authority home"><img src="/assets/logo_tia_full.webp" alt=""></a>
  <a class="g-back" href="/arcade/">← ARCADE</a>
  <span class="g-title"><b>{sim}</b> · {title_txt}</span>
  <span class="g-sp"></span>
  <button type="button" id="g-sound" aria-pressed="true">SOUND ON</button>
</header>
<main class="g-main">
{body}
</main>
<footer class="g-help">{help}</footer>
<script src="/assets/games/common.js" defer></script>
{pre}<script src="/assets/games/{js}.js" defer></script>
</body>
</html>
"""


def main():
    for g in GAMES:
        pre = ''.join(f'<script src="/assets/games/{p}.js" defer></script>\n' for p in g.get('pre', []))
        out = SHELL.format(site=SITE, slug=g['slug'], js=g.get('js', g['slug']), pre=pre, sim=g['sim'], title_txt=html.escape(g['title']),
                           desc=html.escape(g['desc'], quote=True), body=g['body'], help=g['help'])
        d = ROOT / 'arcade' / g['slug']
        d.mkdir(parents=True, exist_ok=True)
        (d / 'index.html').write_text(out, encoding='utf-8')
        print('wrote', d.relative_to(ROOT) / 'index.html')


if __name__ == '__main__':
    main()
