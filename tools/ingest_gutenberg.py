"""Copy public-domain texts from Project Gutenberg mirrors into content/texts/.

Strips the Gutenberg header, footer and licence boilerplate, leaving the work itself.
Usage: python3 tools/ingest_gutenberg.py <cloned-mirrors-dir>
"""
import os, re, sys

WORKS = {  # text id -> Gutenberg eBook number
    'marx-engels-1848-manifesto': 61,
    'marx-1852-eighteenth-brumaire': 1346,
    'engels-1845-condition-working-class': 17306,
    'engels-1852-revolution-counter-revolution': 32966,
    'engels-1878-landmarks-anti-duhring': 31933,
    'engels-1880-socialism-utopian-scientific': 39257,
    'engels-1886-feuerbach': 27814,
    'hegel-1817-logic': 55108,
    'lenin-1918-letter-american-workingmen': 35232,
    'luxemburg-1906-massenstreik': 31614,
    'trotsky-1918-our-revolution': 36303,
    'trotsky-1914-bolsheviki-world-peace': 40273,
    'trotsky-1920-terrorism-communism': 38982,
    'hegel-1817-philosophy-of-mind': 39064,
    'hegel-1805-history-of-philosophy-1': 51635,
    'hegel-1805-history-of-philosophy-2': 51636,
    'hegel-1805-history-of-philosophy-3': 58169,
    'hegel-1807-phaenomenologie': 6698,
    'hegel-1812-wissenschaft-der-logik-1': 6729,
    'hegel-1812-wissenschaft-der-logik-2': 6834,
    'marx-engels-1844-briefwechsel-1': 64327,
    'luxemburg-1916-briefe-aus-dem-gefaengnis': 26964,
}

# Passages by other writers that are still in copyright in life+70 countries, removed before hosting.
CUTS = {
    # 1922 American edition: foreword by Max Bedacht and preface by H. N. Brailsford
    'trotsky-1920-terrorism-communism': (r'^Foreword\s*$', r'^Introduction\s*$'),
}
DROP_LINES = {
    'trotsky-1920-terrorism-communism': [r'^FOREWORD\s+V\s*$', r'^PREFACE\s+XI\s*$', r'^With a Preface by\s*$',
                                         r'^H\. N\. BRAILSFORD\s*$', r'^and Foreword by Max Bedact\s*$'],
}

def read_best(d, n):
    for name, enc in ((f'{n}-0.txt', 'utf-8'), (f'{n}-8.txt', 'latin-1'), (f'{n}.txt', 'utf-8'), (f'{n}.txt', 'latin-1')):
        p = os.path.join(d, name)
        if os.path.exists(p):
            try:
                return open(p, encoding=enc).read()
            except UnicodeDecodeError:
                continue
    raise SystemExit(f'no text for {n}')

def clean(t):
    t = t.replace('\r\n', '\n').replace('﻿', '')
    s = re.search(r'^\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG(?:(?!\*\*\*).){0,300}?\*\*\*', t, re.M | re.S)
    if s:
        t = t[s.end():]
    e = re.search(r'^\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG', t, re.M)
    if e:
        t = t[:e.start()]
    e = re.search(r'^End of (the )?Project Gutenberg', t, re.M | re.I)
    if e:
        t = t[:e.start()]
    t = re.sub(r'\A(.{0,3000}?)^[ \t]*\[\s*(Anmerkungen zur Transkription|Transcriber.s Notes?)\b.*?^[ \t]*\][ \t]*$', r'\1', t, count=1, flags=re.S | re.M | re.I)
    blocks = re.split(r'\n\s*\n', t.strip('\n'))
    out = []
    for i, b in enumerate(blocks):
        bs = b.strip()
        if i < 6 and (re.match(r'^(Produced by|E-text prepared by|Transcribed (by|from)|Note: Images of the original|This (e)?book was produced|\(This book was produced)', bs, re.I) or re.search(r'\S+@\S+\.\w+', bs)):
            continue
        if re.fullmatch(r'\[Illustrations?(:[^\]]*)?\]', bs, re.S):
            continue
        if 'Project Gutenberg' in bs or 'pgdp.net' in bs or 'Projekt-DE' in bs or 'gutenberg2000' in bs:
            continue
        if i < 12 and re.match(r'^\[?\s*(Anmerkungen zur Transkription|Transcriber.s Note)', bs, re.I) and bs.endswith(']'):
            continue
        out.append(b.rstrip())
    t = '\n\n'.join(out).strip()
    # a transcriber's list of corrections at the very end
    m = None
    for m in re.finditer(r'^\s*(Anmerkungen zur Transkription|TRANSCRIBER.S NOTES?):?\s*$', t, re.M | re.I):
        pass
    if m and m.start() > len(t) * 0.9:
        t = t[:m.start()].rstrip()
    return t + '\n'

if __name__ == '__main__':
    src = sys.argv[1]
    dst = os.path.join(os.path.dirname(__file__), '..', 'content', 'texts')
    for tid, n in WORKS.items():
        txt = clean(read_best(os.path.join(src, str(n)), n))
        if tid in CUTS:
            a, b = CUTS[tid]
            ma = re.search(a, txt, re.M)
            mb = re.search(b, txt[ma.end():], re.M) if ma else None
            if ma and mb:
                txt = txt[:ma.start()] + txt[ma.end() + mb.start():]
        for pat in DROP_LINES.get(tid, []):
            txt = re.sub(pat + r'\n?', '', txt, flags=re.M)
        open(os.path.join(dst, tid + '.txt'), 'w', encoding='utf-8').write(txt)
        print(f'{tid:48s} {len(txt):>8d} chars')
