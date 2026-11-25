"""Put Engels's The Origin of the Family, Private Property and the State on the site.

The text is Ernest Untermann's English translation (Chicago, Charles H. Kerr & Company, 1902),
with his preface and notes. Untermann died in 1956, so the translation is in the public domain
in life-plus-70 countries only from 1 January 2027. The repository is public, so the text must
not be committed before then. This script refuses to run earlier.

On or after 1 January 2027:
    python3 tools/publish_origin.py            # clones the source, writes the text, updates the catalogue
    python3 tools/build_archive.py
then commit and push.

Options:
    --mirror DIR   use an existing clone of the source instead of cloning it
    --test OUT     write the text to OUT only, any date, without touching the catalogue
                   (for checking the script; never commit OUT before 2027)
"""
import datetime, json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_gutenberg import read_best, clean

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TID = 'engels-1884-origin-family'
EBOOK = 33111
MIRROR = 'https://github.com/GITenberg/The-Origin-of-the-Family-Private-Property-and-the-State_33111.git'
FREE_FROM = datetime.date(2027, 1, 1)

HEADER = [
    'THE ORIGIN OF THE FAMILY, PRIVATE PROPERTY AND THE STATE',
    'by Frederick Engels',
    'Translated by Ernest Untermann',
    "_Engels's_ Der Ursprung der Familie, des Privateigentums und des Staats _(1884), on the "
    "origins of the family, of private property and of the state, drawing on Lewis H. Morgan's "
    "studies of early society. This is Ernest Untermann's translation, first published by Charles H. Kerr & "
    "Company of Chicago in 1902, with his preface and notes, as printed in 1908. It renders the "
    "fourth German edition of 1891._",
]
SIGNATURES = {'ERNEST UNTERMANN.': 'Ernest Untermann', 'FREDERICK ENGELS.': 'Frederick Engels',
              'Chicago, August, 1902.': 'Chicago, August 1902', 'London, June 16th, 1891.': 'London, June 16th, 1891'}
EDITION ='Translated by Ernest Untermann. Chicago, Charles H. Kerr & Company, 1902.'


def fetch(mirror):
    if mirror:
        return mirror
    d = tempfile.mkdtemp(prefix='origin-')
    subprocess.run(['git', 'clone', '-q', '--depth', '1', MIRROR, d], check=True)
    return d


def fmt(t):
    blocks = [b for b in re.split(r'\n[ \t]*\n', t.strip('\n')) if b.strip()]
    first = lambda b: b.strip().split('\n')[0].strip()
    # title page, copyright line and the book's page-numbered contents
    i = next(k for k, b in enumerate(blocks) if first(b) == "TRANSLATOR'S PREFACE.")
    blocks = blocks[i:]
    out = []
    k = 0
    while k < len(blocks):
        b = blocks[k]
        s = b.strip()
        if s in ('THE ORIGIN OF THE FAMILY', 'THE END.'):
            k += 1
            continue
        if s in ('FOOTNOTES:', 'FOOTNOTE:'):
            out.append('* * *')
            k += 1
            continue
        m = re.fullmatch(r"\[(\d+)\] (Author's|Translator's) note\.", s)
        if m:
            # the note's label stands alone in this edition; its text follows
            k += 1
            paras = []
            while k < len(blocks) and not re.match(r'\[\d+\]', blocks[k].strip()) \
                    and not re.fullmatch(r'[A-Z .:]+', blocks[k].strip()) and blocks[k].strip() != '* * *':
                paras.append([l.strip() for l in blocks[k].strip().split('\n')])
                k += 1
            label = '' if m.group(2) == "Author's" else '_Translator\'s note._ '
            out.append(f'[{m.group(1)}] {label}{" ".join(paras[0]) if paras else ""}'.rstrip())
            # a note running to several paragraphs (only note 17, quoting Heinrich Cunow at length)
            out.extend('\n'.join('    ' + l for l in p) for p in paras[1:])
            continue
        if s in SIGNATURES:
            # signatures and their dates, set to the right
            out.append(' ' * 24 + SIGNATURES[s])
            k += 1
            continue
        if re.fullmatch(r'\[\d+\] .*', s, re.S):
            out.append(' '.join(s.split()))
            k += 1
            continue
        out.append(b.rstrip())
        k += 1
    text = '\n\n'.join(HEADER + out) + '\n'
    assert text.count(' ' * 24 + 'Frederick Engels') == 2 and ' ' * 24 + 'Ernest Untermann' in text
    return text


def set_catalogue():
    p = os.path.join(ROOT, 'content', 'catalogue.json')
    src = open(p, encoding='utf-8').read()
    cat = json.loads(src)
    w = next(w for a in cat['authors'] for w in a['works'] if w['id'] == TID)
    if w.get('kind') == 'hosted':
        return False
    old = json.dumps(w, ensure_ascii=False)
    assert old in src, 'catalogue entry not on one line'
    new = {'id': TID, 'slug': 'origin-of-the-family', 'title': w['title'], 'year': w['year'], 'kind': 'hosted',
           'key': w.get('key', False), 'lang': 'en', 'edition': EDITION, 'pg': EBOOK, 'cols': w['cols']}
    if not new['key']:
        del new['key']
    open(p, 'w', encoding='utf-8').write(src.replace(old, json.dumps(new, ensure_ascii=False)))
    return True


def main():
    args = sys.argv[1:]
    mirror = args[args.index('--mirror') + 1] if '--mirror' in args else None
    test = args[args.index('--test') + 1] if '--test' in args else None
    if not test and datetime.date.today() < FREE_FROM:
        raise SystemExit(f'Not before {FREE_FROM}: Untermann\'s translation is still in copyright in '
                         'life-plus-70 countries, and this repository is public.')
    text = fmt(clean(read_best(fetch(mirror), EBOOK)))
    out = test or os.path.join(ROOT, 'content', 'texts', TID + '.txt')
    open(out, 'w', encoding='utf-8').write(text)
    print(f'{out}: {len(text.split()):,} words')
    if not test:
        print('catalogue updated' if set_catalogue() else 'catalogue already hosted')


if __name__ == '__main__':
    main()
