"""Put Capital, Volumes II and III, in Ernest Untermann's translation, on the site.

Untermann's translations (Chicago, Charles H. Kerr & Company, 1907 and 1909) are in the public domain in
life-plus-70 countries only from 1 January 2027, since he died in 1956. The texts were prepared in 2026 and
are kept in this public repository only in encrypted form (content/pending/capital-2-3.tar.gz.enc), so that
nothing readable is published before then. The key is held in the scheduled task that runs this script.

On or after 1 January 2027:
    TIA_PENDING_KEY=<key> python3 tools/publish_capital23.py
    python3 tools/build_archive.py
then commit and push.

The script refuses to run earlier, writes the two texts and their pictures of tables and formulas into
content/texts/, adds both volumes to the catalogue after Volume I, and deletes the encrypted bundle.
Option --test OUT_DIR unpacks into OUT_DIR on any date and changes nothing in the repository.
"""
import datetime, json, os, subprocess, sys, tarfile, tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BUNDLE = os.path.join(ROOT, 'content', 'pending', 'capital-2-3.tar.gz.enc')
FREE_FROM = datetime.date(2027, 1, 1)
AFTER = 'marx-1867-capital-1'
ENTRIES = [
    {'id': 'marx-1885-capital-2', 'slug': 'capital-volume-two', 'title': 'Capital, Volume II',
     'subtitle': 'A Critique of Political Economy: The Process of Circulation of Capital', 'year': '1885',
     'kind': 'hosted', 'lang': 'en',
     'edition': 'Edited by Frederick Engels. Translated from the second German edition by Ernest Untermann. '
                'Chicago, Charles H. Kerr & Company, 1907.',
     'de': '24-000', 'cols': ['marx-and-engels']},
    {'id': 'marx-1894-capital-3', 'slug': 'capital-volume-three', 'title': 'Capital, Volume III',
     'subtitle': 'A Critique of Political Economy: The Process of Capitalist Production as a Whole', 'year': '1894',
     'kind': 'hosted', 'lang': 'en',
     'edition': 'Edited by Frederick Engels. Translated by Ernest Untermann. Chicago, Charles H. Kerr & Company, 1909.',
     'de': '25-000', 'cols': ['marx-and-engels']},
]


def unpack(dest, key):
    with tempfile.TemporaryDirectory() as tmp:
        tgz = os.path.join(tmp, 'bundle.tar.gz')
        subprocess.run(['openssl', 'enc', '-d', '-aes-256-cbc', '-pbkdf2', '-iter', '200000', '-in', BUNDLE,
                        '-out', tgz, '-pass', 'env:TIA_PENDING_KEY'], check=True, env={**os.environ, 'TIA_PENDING_KEY': key})
        with tarfile.open(tgz) as t:
            for m in t.getmembers():
                if m.name.startswith('/') or '..' in m.name.split('/') or not (m.isfile() or m.isdir()):
                    raise SystemExit(f'unexpected path in bundle: {m.name}')
            try:
                t.extractall(dest, filter='data')
            except TypeError:          # Python before 3.12
                t.extractall(dest)


def add_catalogue():
    p = os.path.join(ROOT, 'content', 'catalogue.json')
    src = open(p, encoding='utf-8').read()
    cat = json.loads(src)
    marx = next(a for a in cat['authors'] if a['slug'] == 'marx')
    have = {w['id']: w for w in marx['works']}
    changed = False
    # the volumes are listed already as linked works marked "coming": replace those entries
    for e in ENTRIES:
        w = have.get(e['id'])
        if w and w.get('kind') != 'hosted':
            line = json.dumps(w, ensure_ascii=False)
            assert src.count(line) == 1, f'catalogue entry {e["id"]} not found on one line'
            src = src.replace(line, json.dumps(e, ensure_ascii=False))
            changed = True
    anchor = next(w for w in marx['works'] if w['id'] == AFTER)
    line = json.dumps(anchor, ensure_ascii=False)
    assert src.count(line) == 1, 'catalogue entry for Volume I not found on one line'
    i = src.index(line) + len(line)
    indent = src[src.rindex('\n', 0, src.index(line)) + 1:src.index(line)]
    add = ''.join(',\n' + indent + json.dumps(e, ensure_ascii=False) for e in ENTRIES if e['id'] not in have)
    if add:
        src = src[:i] + add + src[i:]
        changed = True
    if changed:
        json.loads(src)
        open(p, 'w', encoding='utf-8').write(src)
    return changed


def main():
    args = sys.argv[1:]
    test = args[args.index('--test') + 1] if '--test' in args else None
    if not test and datetime.date.today() < FREE_FROM:
        raise SystemExit(f"Not before {FREE_FROM}: Untermann's translations are still in copyright in "
                         'life-plus-70 countries, and this repository is public.')
    key = os.environ.get('TIA_PENDING_KEY')
    if not key:
        raise SystemExit('Set TIA_PENDING_KEY to the key from the scheduled task.')
    if not os.path.exists(BUNDLE):
        raise SystemExit('No bundle: the volumes are probably published already.')
    unpack(test or ROOT, key)
    if test:
        print('unpacked into', test)
        return
    for e in ENTRIES:
        f = os.path.join(ROOT, 'content', 'texts', e['id'] + '.txt')
        print(f'{e["id"]}: {len(open(f, encoding="utf-8").read().split()):,} words')
    print('catalogue updated' if add_catalogue() else 'catalogue already has both volumes')
    os.remove(BUNDLE)
    print('encrypted bundle removed')


if __name__ == '__main__':
    main()
