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
    blocks = re.split(r'\n\s*\n', t.strip('\n'))
    out = []
    for i, b in enumerate(blocks):
        bs = b.strip()
        if i < 6 and (re.match(r'^(Produced by|E-text prepared by|Transcribed (by|from)|Note: Images of the original|This (e)?book was produced|\(This book was produced)', bs, re.I) or re.search(r'\S+@\S+\.\w+', bs)):
            continue
        if re.fullmatch(r'\[Illustrations?(:[^\]]*)?\]', bs, re.S):
            continue
        if 'Project Gutenberg' in bs or 'pgdp.net' in bs:
            continue
        out.append(b.rstrip())
    return '\n\n'.join(out).strip() + '\n'

if __name__ == '__main__':
    src = sys.argv[1]
    dst = os.path.join(os.path.dirname(__file__), '..', 'content', 'texts')
    for tid, n in WORKS.items():
        txt = clean(read_best(os.path.join(src, str(n)), n))
        open(os.path.join(dst, tid + '.txt'), 'w', encoding='utf-8').write(txt)
        print(f'{tid:48s} {len(txt):>8d} chars')
