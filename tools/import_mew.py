#!/usr/bin/env python3
"""Import the German originals of Marx and Engels from a mirror of the MEW HTML edition.

    python3 tools/import_mew.py /path/to/mlwerke.de/me

Only texts that Marx and Engels wrote in German are kept. Anything the MEW editors translated
("Aus dem Englischen" and so on) is skipped, because those translations are not public domain,
and so is the editorial apparatus: forewords, notes, indexes, text variants and the editors'
translations of foreign words in angle brackets. Page numbers of the MEW edition are kept as
markers so the texts can be cited.

Angle brackets are dropped everywhere except in the files listed in KEEP_ANGLE, where the MEW
editors used them for the authors' own words (in the Critique of the Gotha Programme they mark
the passages Engels left out in 1891). There the text is kept and the brackets are shown as ⟨ ⟩.

Writes content/werke/index.json and content/werke/<band>/<file>.json.
"""
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'content' / 'werke'

LANGS = ('Englischen|Französischen|Franzosischen|Italienischen|Spanischen|Polnischen|Russischen|Dänischen|'
         'Holländischen|Niederländischen|Schwedischen|Norwegischen|Portugiesischen|Rumänischen|Ungarischen|'
         'Tschechischen|Bulgarischen|Serbischen|Griechischen|Lateinischen|Flämischen')
TRANSLATED = re.compile(r'\bAus dem (' + LANGS + r')\b|\b(Übersetzung|übersetzt) (aus dem|von der Redaktion)\b|'
                        r'\bOriginal(sprache)?:?\s*(englisch|französisch|italienisch|spanisch)', re.I)
AUTHORS = {
    'karl marx': ['marx'], 'friedrich engels': ['engels'],
    'karl marx/friedrich engels': ['marx', 'engels'], 'karl marx und friedrich engels': ['marx', 'engels'],
    'friedrich engels/karl marx': ['engels', 'marx'],
}
BLOCK = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'li', 'center', 'dd', 'dt', 'pre', 'address'}
SKIP = {'script', 'style', 'head', 'title', 'noscript'}
INLINE = {'i': 'i', 'em': 'i', 'b': 'b', 'strong': 'b', 'sup': 'sup', 'sub': 'sub', 'u': 'i'}

# Files whose angle brackets hold the authors' text, with the note a reader needs. MEW 19 says of
# the Critique: "Stellen, die 1891 ausgelassen und durch Punkte ersetzt wurden, sind in spitze
# Klammern gesetzt."
KEEP_ANGLE = {
    'me19_013.htm': 'Text in ⟨ ⟩ was left out when Engels first published the Critique in 1891.',
}
# The mirror turned some bracketed passages into fake tags (<nicht nur="">). Most have a correct
# escaped copy beside them and are simply removed; these two have none and are restored here.
REPAIR = {
    'me19_013.htm': [
        (r'<nicht nur="">', '&lt;nicht nur&gt; '),
        (r'<man alle="" die="" eigne="" eskamotieren="" kommen="" kritik="" lassen\.="" nachdenken="" nicht="" offenbar="" '
         r'partei="" und="" wollte="" zum="">',
         '&lt;Man wollte offenbar alle Kritik eskamotieren und die eigne Partei nicht zum Nachdenken kommen lassen.&gt; '),
        # slips in the online text, read against the fake-tag copies of the same passages
        (r'Nach anbehaltenem Koalitionskongre', 'Nach abgehaltnem Koalitionskongre'),
        (r'sondern sogar fr jeden Schritt', 'sondern sogar für jeden Schritt'),
        (r'dem ich enbenfalls', 'dem ich ebenfalls'),
    ],
}
HTML_TAGS = set('a abbr address b big blockquote body br center cite code col colgroup dd div dl dt em font form h1 h2 h3 h4 h5 h6 '
                'head hr html i img input li link map area meta noscript ol p pre s script small span strike strong style '
                'sub sup table tbody td tfoot th thead title tr tt u ul'.split())


def load(f):
    b = f.read_bytes()
    try:
        return b.decode('utf-8')
    except UnicodeDecodeError:
        return b.decode('cp1252', errors='replace')


def clean_text(s):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', s)).split())


class Conv(HTMLParser):
    """Turn one MEW page into a list of blocks: [kind, html]."""

    def __init__(self, fname):
        super().__init__(convert_charrefs=True)
        self.fname = fname
        self.blocks = []
        self.cur = []          # html pieces of the current block
        self.kind = 'p'
        self.open = []         # open inline tags
        self.font = []         # font size stack
        self.small = 0
        self.big = 0
        self.skip = 0
        self.a_stack = []      # what each open <a> does: 'page', 'drop', 'keep', 'none'
        self.table = None      # rows of cells while inside a data table
        self.cell = None
        self.tdepth = 0
        self.center = False
        self.heading = None
        self.block_small = False

    # ---- block handling
    def flush(self):
        h = ''.join(self.cur)
        for t in reversed(self.open):
            h += f'</{t}>'
        self.cur = [f'<{t}>' for t in self.open]
        txt = clean_text(h)
        if txt or '<img' in h:
            kind = self.heading or ('ctr' if self.center else ('small' if self.block_small else 'p'))
            self.blocks.append([kind, h.strip()])
        self.block_small = self.small > 0
        self.cur_has_text = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag == 'table':
            self.tdepth += 1
            if self.tdepth == 1:
                self.flush()
                self.table = []
            return
        if self.table is not None:
            if tag == 'tr':
                self.table.append([])
            elif tag in ('td', 'th'):
                if not self.table:
                    self.table.append([])
                self.cell = []
                self.table[-1].append(self.cell)
            elif tag == 'br' and self.cell is not None:
                self.cell.append(' ')
            elif tag == 'a':
                self.a_stack.append(self._a_kind(a))
            elif tag == 'img' and self.cell is not None:
                self.cell.append(self._img(a))
            return
        if tag in BLOCK or tag == 'hr':
            self.flush()
            self.center = (a.get('align') or '').lower() == 'center' or tag == 'center' or \
                'center' in (a.get('style') or '').lower()
            self.heading = tag if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6') else ('fh' if self.big else None)
            cls = (a.get('class') or '')
            if cls in ('BriefOrtDatum', 'BriefAnrede', 'BriefSchluss', 'BriefUnterschrift'):
                self.heading = 'letter'
            if tag == 'hr':
                self.blocks.append(['hr', ''])
            if tag == 'blockquote':
                self.block_small = True
            return
        if tag == 'br':
            self.cur.append('<br>')
            return
        if tag == 'font':
            size = (a.get('size') or '').strip()
            self.font.append(size)
            if size in ('1', '2', '-1'):
                self.small += 1
                if not clean_text(''.join(self.cur)):
                    self.block_small = True
            if size in ('4', '5', '6', '+1', '+2', '+3'):
                self.big += 1
                if not clean_text(''.join(self.cur)):
                    self.heading = self.heading or 'fh'
            return
        if tag == 'small':
            self.small += 1
            if not clean_text(''.join(self.cur)):
                self.block_small = True
            return
        if tag in INLINE:
            t = INLINE[tag]
            self.open.append(t)
            self.cur.append(f'<{t}>')
            return
        if tag == 'a':
            k = self._a_kind(a)
            self.a_stack.append(k)
            if k.startswith('keep:'):
                self.cur.append(f'<a href="#{k[5:]}">')
            elif k.startswith('id:'):
                self.cur.append(f'<span id="{k[3:]}"></span>')
            elif k.startswith('page:'):
                self.cur.append(f'<span class="pg" data-p="{k[5:]}"></span>')
            return
        if tag == 'img':
            self.cur.append(self._img(a))

    def _img(self, a):
        src = (a.get('src') or '').split('/')[-1]
        if not re.fullmatch(r'[\w.-]+\.(gif|png|jpg)', src):
            return ''
        return f'<img src="{src}" alt="">'

    def _a_kind(self, a):
        name = a.get('name') or a.get('id') or ''
        href = a.get('href') or ''
        cls = a.get('class') or ''
        if cls == 'Seitenzahl' or re.fullmatch(r'S\d+', name):
            return 'page:' + re.sub(r'\D', '', name)
        if cls == 'SeiteVor':
            return 'drop'
        if href:
            frag = href.split('#', 1)[1] if '#' in href else ''
            file = href.split('#', 1)[0]
            local = not file or file.split('/')[-1] == self.fname
            if local and re.fullmatch(r'Z?T\d+', frag):
                return 'drop'            # text variant
            if local and frag:
                return 'keep:' + frag
            return 'none'                # links to other pages: keep the words, drop the link
        if name:
            if re.fullmatch(r'Z?T\d+', name):
                return 'none'
            return 'id:' + name
        return 'none'

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == 'table':
            self.tdepth = max(0, self.tdepth - 1)
            if self.tdepth == 0 and self.table is not None:
                rows = [[clean_text(''.join(c)) if '<img' not in ''.join(c) else ''.join(c).strip() for c in r] for r in self.table]
                rows = [r for r in rows if any(x for x in r)]
                self.table = None
                self.cell = None
                if rows:
                    self.blocks.append(['table', rows])
            return
        if self.table is not None:
            if tag in ('td', 'th'):
                self.cell = None
            elif tag == 'a' and self.a_stack:
                self.a_stack.pop()
            return
        if tag in BLOCK:
            self.flush()
            self.center = False
            self.heading = None
            return
        if tag == 'font':
            if self.font:
                size = self.font.pop()
                if size in ('1', '2', '-1'):
                    self.small = max(0, self.small - 1)
                if size in ('4', '5', '6', '+1', '+2', '+3'):
                    self.big = max(0, self.big - 1)
            return
        if tag == 'small':
            self.small = max(0, self.small - 1)
            return
        if tag in INLINE:
            t = INLINE[tag]
            if t in self.open:
                i = len(self.open) - 1 - self.open[::-1].index(t)
                after = self.open[i + 1:]
                for x in reversed(after):
                    self.cur.append(f'</{x}>')
                self.cur.append(f'</{t}>')
                self.open = self.open[:i] + after
                for x in after:
                    self.cur.append(f'<{x}>')
            return
        if tag == 'a' and self.a_stack:
            k = self.a_stack.pop()
            if k.startswith('keep:'):
                self.cur.append('</a>')

    def handle_data(self, data):
        if self.skip:
            return
        k = self.a_stack[-1] if self.a_stack else 'none'
        if k == 'drop' or k.startswith('page:'):
            return
        if self.table is not None:
            if self.cell is not None:
                self.cell.append(html.escape(data, quote=False))
            return
        self.cur.append(html.escape(data, quote=False))

    def close(self):
        super().close()
        self.flush()


def tidy(h, keep_angle=False):
    """Clean one block of html. keep_angle: the angle brackets hold the authors' text (KEEP_ANGLE)."""
    # page markers written as text: |15|, <15>
    h = re.sub(r'(?:&lt;|\|)\s*(\d{1,4})\s*(?:&gt;|\|)', r'<span class="pg" data-p="\1"></span>', h)
    if not keep_angle:
        # the editors' translations of foreign words: <...>
        for _ in range(3):
            h = re.sub(r'\s?&lt;(?:(?!&lt;|&gt;).){1,400}?&gt;', '', h, flags=re.S)
    h = re.sub(r'\{\d+\}', '', h)                       # text-variant markers
    h = re.sub(r'<a href="#[^"]*">\s*(?:&lt;=|<=|=&gt;|↑|zurück)\s*</a>', '', h)
    h = re.sub(r'(?:&lt;=|&lt;-)\s*$', '', h)
    if keep_angle:
        h = re.sub(r'&lt;\s*', '⟨', h)
        h = re.sub(r'\s*&gt;', '⟩', h)
    h = re.sub(r'<(i|b|sup|sub)>(\s*)</\1>', r'\2', h)
    h = re.sub(r'<a href="#[^"]*">(\s*)</a>', r'\1', h)
    h = h.replace('\xa0', ' ')
    h = re.sub(r'[ \t\r\n]+', ' ', h)
    h = re.sub(r'(<br>\s*)+$', '', h).strip()
    h = re.sub(r'^(<br>\s*)+', '', h).strip()
    return h


NAV_WORDS = re.compile(r'^(Inhalt|Inhaltsverzeichnis|Zurück|Weiter|Vorwort|Nachwort|Zur \w+ Auflage|Seitenanfang|'
                       r'Nächstes Kapitel|Voriges Kapitel|Übersicht|MLWerke|Marx/Engels - Werke|Kapitel|\||[<>=\s|]+)$', re.I)


def parse_file(path):
    s = load(path)
    if 'denic.de' in s or 'web.archive.org' in s:
        return None
    title = re.search(r'<title>(.*?)</title>', s, re.I | re.S)
    title = clean_text(title.group(1)) if title else ''
    src = re.search(r'Seitenzahlen verweisen auf:(.*?)(?:</p>|</small>|</font>|<hr)', s, re.I | re.S)
    srctxt = clean_text(src.group(1)) if src else ''
    pages = re.search(r'S\.\s*(\d+)\s*(?:-|–|bis)\s*(\d+)', srctxt)
    keep = path.name in KEEP_ANGLE
    if keep:
        for pat, rep in REPAIR.get(path.name, []):
            s, n = re.subn(pat, rep, s)
            if n != 1:
                print('  repair did not match once in', path.name, ':', pat[:40], file=sys.stderr)
        # the remaining fake tags duplicate an escaped passage next to them
        s = re.sub(r'</?([A-Za-zÄÖÜäöüß][^\s>/]*)(?:\s[^>]*)?>', lambda m: m.group(0) if m.group(1).lower() in HTML_TAGS else '', s)
    c = Conv(path.name)
    try:
        c.feed(s)
        c.close()
    except Exception as e:   # noqa: BLE001
        print('  parse error', path, e, file=sys.stderr)
        return None
    blocks = []
    for k, h in c.blocks:
        if k == 'table':
            blocks.append([k, h])
            continue
        h = tidy(h, keep)
        blocks.append([k, h])
    return {'file': path.name, 'title': title, 'src': srctxt, 'pages': [int(pages.group(1)), int(pages.group(2))] if pages else None,
            'raw': s, 'blocks': blocks}


FACT = re.compile(r'^(Geschrieben|Erstmal\w* veröffentlicht|Erstveröffentlicht|Veröffentlicht|Gehalten|Erschienen)', re.I)


def split_header(blocks):
    """Separate author, title, facts and the editors' header from the text proper."""
    author, title, facts = '', '', []
    i_h1 = next((i for i, (k, h) in enumerate(blocks) if k == 'h1'), None)
    if i_h1 is None:
        # older pages set the title in a large font instead of a heading
        for i, (k, h) in enumerate(blocks):
            if k == 'fh' and clean_text(h) and not re.fullmatch(r'[IVXLC]+\.?|\d+\.?', clean_text(h)) \
                    and not who_from(clean_text(h))[0]:
                i_h1 = i
                break
            if k in ('p', 'letter') and len(clean_text(h)) > 200:
                break
    if i_h1 is None:
        return None, None, [], blocks, ''
    title = clean_text(blocks[i_h1][1])
    for k, h in blocks[:i_h1]:
        t = clean_text(h) if k != 'table' else ''
        if k in ('h2', 'p', 'small', 'fh') and t and not t.startswith('Seitenzahlen') and len(t) < 80 and 'MLWerke' not in t:
            author = t
    # header runs from the h1 to the first rule (old pages) or to the first real paragraph (new pages)
    j = i_h1 + 1
    head_txt = []
    while j < len(blocks):
        k, h = blocks[j]
        if k == 'hr':
            j += 1
            break
        t = clean_text(h) if k != 'table' else ''
        if k in ('p', 'letter') and len(t) > 300 and not re.match(r'^(Geschrieben|Erstmal|Nach )', t):
            break
        if k == 'h3' or k == 'fh':
            break
        head_txt.append(t)
        j += 1
    else:
        j = i_h1 + 1
    for t in head_txt:
        for sent in re.split(r'(?<=\.)\s+(?=[A-ZÄÖÜ])', t):
            if FACT.match(sent) and len(sent) < 260:
                facts.append(sent.strip())
        if t.startswith('Seitenzahlen'):
            continue
    body = blocks[j:]
    return author, title, facts, body, ' '.join(head_txt)


def strip_apparatus(body):
    out = []
    skip = False
    for k, h in body:
        t = clean_text(h) if k != 'table' else ''
        if k != 'table' and re.fullmatch(r'(Textvarianten|Anmerkungen|Anmerkungen der Redaktion|Fußnoten der Redaktion)', t):
            skip = True
            continue
        if skip and (k in ('h1', 'h2', 'h3') or t == 'Fußnoten'):
            skip = False
        if skip:
            continue
        if k == 'table':
            flat = ' '.join(' '.join(r) for r in h)
            if re.search(r'MLWerke|Marx/Engels - Werke|Seitenzahlen verweisen|Inhalt MEW|Hauptverzeichnis', flat):
                continue
            out.append([k, h])
            continue
        if not t and '<img' not in h:
            if k == 'hr':
                out.append([k, h])
            continue
        if t.startswith('Seitenzahlen verweisen') or re.match(r'^Text und Seitenangaben beruhen', t):
            continue
        if re.fullmatch(r'\(?\d+\)?\s*', t) and k != 'p':
            continue
        # navigation rows: only link words and separators
        words = [x.strip() for x in re.split(r'\|', t)]
        if '|' in t and all(len(x) < 60 for x in words) and len(t) < 260 and '<a href="#' not in h and k in ('ctr', 'small', 'p'):
            continue
        if NAV_WORDS.match(t) and k in ('ctr', 'small', 'p'):
            continue
        out.append([k, h])
    # trim rules at the ends, and collapse runs
    while out and out[0][0] == 'hr':
        out.pop(0)
    while out and out[-1][0] == 'hr':
        out.pop()
    res = []
    for b in out:
        if b[0] == 'hr' and res and res[-1][0] == 'hr':
            continue
        res.append(b)
    return res


def classify(body):
    """Final block kinds for the reader."""
    out = []
    infn = False
    for k, h in body:
        if k == 'table':
            out.append(['table', h])
            continue
        if k == 'hr':
            out.append(['hr', ''])
            continue
        t = clean_text(h)
        if t in ('Fußnoten', 'Fussnoten', 'Anmerkungen von Marx', 'Anmerkungen von Engels'):
            infn = True
            out.append(['fnh', 'Fußnoten'])
            continue
        if infn or (re.match(r'^(<span id="[^"]+"></span>\s*)?\(\s*[\d*]+\s*\)', h) and k in ('p', 'small')):
            out.append(['fn', h])
            continue
        if k in ('h2', 'h3', 'h4', 'h5', 'h6', 'fh'):
            out.append(['h', h])
            continue
        if k == 'ctr':
            if len(t) <= 120 and not t.endswith(('.', ':', ',')) or re.fullmatch(r'[IVXLC]+\.?|\d+\.?|[A-Z]\.?', t):
                out.append(['h', h])
            elif re.fullmatch(r'[_\-*·. ]+', t):
                out.append(['hr', ''])
            else:
                out.append(['ctr', h])
            continue
        if k == 'small':
            if t.startswith('[') and t.endswith(']') and len(t) < 300:
                out.append(['src', h])
            else:
                out.append(['q', h])
            continue
        if k == 'letter':
            out.append(['ctr' if False else 'lt', h])
            continue
        out.append(['p', h])
    return out


YEAR = re.compile(r'\b(18[2-9]\d)\b')
# years each MEW volume covers, to keep stray dates in the text from being taken as the date of writing
SPAN = {1: (1839, 1844), 2: (1844, 1846), 3: (1845, 1846), 4: (1846, 1848), 5: (1848, 1848), 6: (1848, 1849),
        7: (1849, 1851), 8: (1851, 1853), 9: (1853, 1853), 10: (1854, 1855), 11: (1855, 1856), 12: (1856, 1859),
        13: (1857, 1860), 14: (1857, 1860), 15: (1860, 1864), 16: (1864, 1868), 17: (1870, 1872), 18: (1872, 1875),
        19: (1875, 1883), 20: (1873, 1883), 21: (1883, 1889), 22: (1890, 1895), 23: (1867, 1867), 24: (1885, 1885),
        25: (1894, 1894), 26: (1861, 1863), 31: (1864, 1867), 35: (1881, 1883), 37: (1888, 1890), 38: (1891, 1892),
        39: (1893, 1895), 40: (1835, 1844), 42: (1857, 1858)}
# papers that printed what Marx and Engels wrote in English, French, Italian or Spanish; the MEW text of
# these is the editors' translation even where the mirror lost the "Aus dem Englischen" line
FOREIGN = re.compile(r'^\[?\s*["»„“]?\s*(The |Le |La |Les |L\'|Il |El |New-York Daily Tribune|New York Daily Tribune|People\'s Paper|'
                     r'Northern Star|New Moral World|Free Press|Putnam|Commonwealth|Labour Standard|Notes to the People|'
                     r'Red Republican|Réforme|Socialiste|Égalité|Plebe|Emancipaci|Critica Sociale|Reynolds|Bee-Hive|'
                     r'Volunteer Journal|New American Cyclop|Allen\'s Indian Mail|Eastern Post|Vanity Fair|Times)')
# the editors' preamble names a foreign original ...
FOREIGN_HEAD = re.compile(r'\bAus dem (' + LANGS + r')\b|\bin (englischer|französischer|italienischer|spanischer|polnischer|russischer) Sprache|'
                          r'Aus: ["»]?\s*(The |New-York)|(erschienen|veröffentlicht) in:? ["»]\s*(The |Le |La |L\'|Il )|'
                          r'Nach der englischen|Nach dem englischen|englischen Original|französischen Original|'
                          r'Nach dem Protokoll|Protokollbuch|Nach der handschriftlichen Kopie')
# ... unless the German text is a translation published in their lifetime (Engels's own, or one he checked)
HISTORIC_DE = re.compile(r'Deutsch von |Nach der Ausgabe in deutscher Sprache|Nach dem Flugblatt in deutscher Sprache|'
                         r'Nach: ["»]?(Die )?Neue Zeit|Nach: ["»]?Allgemeine Statuten|Dem vorliegenden Text liegt die Braunschweiger|In deutscher Sprache (zuerst |erstmal\w* |erstmals )?(erschienen|veröffentlicht)[^.]{0,120}\b18\d\d|'
                         r'Nach: [^.]{0,120}deutsche[nr]? (Auflage|Ausgabe)|Nach der (\w+ )?deutschen (Auflage|Ausgabe) von 18|'
                         r'Übersetzung von (Friedrich )?Engels|von (Friedrich )?Engels übersetzt|von (Friedrich )?Engels (besorgt|durchgesehen)')
GERMAN_VENUE = re.compile(r'Neue Oder-Zeitung|Die Presse|Volksstaat|Rheinische|Brüsseler|Sozialdemokrat|Social-Demokrat|Das Volk|'
                          r'Vorwärts|Reform|Arbeiter|Allgemeine|Wochenblatt|Zukunft|Volkszeitung|Volks-Zeitung|Volksblatt|Telegraph für|'
                          r'Republikaner|Westdeutsche|Neue Deutsche|Chronik|Kölnische|Belletristisches|Beobachter|Nordstern|Hermann|'
                          r'Courier|Elberfelder|Düsseldorfer|Staats-Anzeiger|Landeszeitung|Vorbote|Frankfurter|Volksfreund|Tribüne|'
                          r'Neue Zeit|Jahrbücher|Gesellschaftsspiegel|Deutsches Bürgerbuch|Revolution|Wiener|Leipziger|Berliner|Zeitung|Kalender')


FOREIGN_ANY = re.compile(r'["»„“]\s*(The (Pall Mall|Times|Daily|Morning|Manchester|People|Northern|New Moral|Commonweal|Labour|'
                         r'Free Press|Eastern|Spectator|Sun|Star|Evening|Weekly|Bee)|New-York Daily Tribune|People\'s Paper|'
                         r'Notes to the People|La Réforme|Le Socialiste|L\'Égalité|La Plebe|La Emancipaci|Critica Sociale)')


def preamble(raw):
    t = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'(?is)<head>.*?</head>', '', raw))).split())
    i = t.find('Seitenzahlen')
    t = t[i if i >= 0 else 0:]
    m = re.search(r'(\|\d{1,4}\||<\d{1,4}>)', t)
    return t[:min(m.start() if m else 1500, 1500)]


# checked by hand: written in English, French or Italian, or made up largely of the editors' translations
EXCLUDE = {'12-347', '17-129', '17-146', '17-180', '17-367', '17-412', '17-418', '17-572', '18-314', '18-597', '19-033',
           '19-407', '22-331', '22-407', '22-408', '22-439', '31-597', '40-013'}
EXCLUDE_PARTS = {'me02_229'}      # Engels wrote the dedication of the Condition of the Working Class in English
TITLE_FIX = {'02-229': 'Die Lage der arbeitenden Klasse in England', '03-011': 'Die deutsche Ideologie', '23-000': 'Das Kapital. Erster Band', '24-000': 'Das Kapital. Zweiter Band', '25-000': 'Das Kapital. Dritter Band'}
YEAR_FIX = {'40-003': 1837, '40-013': 1839, '01-172': 1843, '24-000': 1885, '25-000': 1894}
MARKER = re.compile(r'^(Geschrieben[^.]{0,160}\.\s*)?(Aus dem (' + LANGS + r')|Übersetzung aus dem \w+)\b')
ME = {'karl marx': 'marx', 'marx': 'marx', 'friedrich engels': 'engels', 'engels': 'engels', 'karl kautsky': 'kautsky'}


def who_from(text):
    """['marx'], ['marx', 'engels'] ... and the names of anyone else, from an author line."""
    t = text.strip().strip('[]').strip()
    t = re.split(r'\s+-\s+|:\s', t)[0]
    names = [x.strip().strip('[]').strip() for x in re.split(r'/| und |-(?=[A-Z])', t) if x.strip()]
    slugs = [ME[n.lower()] for n in names if n.lower() in ME]
    others = [n for n in names if n.lower() not in ME]
    if not slugs or len(t) > 70:
        return None, []
    return slugs, others


def attributions(src):
    """Author names from the newspaper and year indexes of the mirror, keyed by file name."""
    out = {}
    for f in src.glob('me_*.htm'):
        s = load(f)
        for row in re.findall(r'(?is)<tr>(.*?)</tr>', s):
            cells = re.findall(r'(?is)<td[^>]*>(.*?)</td>', row)
            if len(cells) < 2:
                continue
            links = re.findall(r'href="me\d\d/(me\d\d_\d{3}[a-z]?\.htm)', cells[1])
            if not links:
                continue
            out[links[0]] = clean_text(cells[0])
    return out


def index_titles(vol):
    f = vol / 'index.htm'
    if not f.exists():
        return {}
    s = load(f)
    return {m.group(1): clean_text(m.group(2)) for m in re.finditer(r'(?is)<a [^>]*href="(me\d\d_\d{3}[a-z]?\.htm)"[^>]*>(.*?)</a>', s)}


AUTH_PREFIX = re.compile(r'^(Karl Marx/Friedrich Engels|Karl Marx|Friedrich Engels|Marx/Engels)\s*[-:]')


def work_of(t):
    return base(t).split(' - ')[0].strip()


def base(t):
    t = re.sub(r'^"?Neue Rheinische Zeitung"?\s*-\s*', '', t)
    return re.sub(r'^(Karl Marx/Friedrich Engels|Karl Marx|Friedrich Engels|Marx/Engels)\s*[-:]\s*', '', t).strip()


def main(src):
    src = Path(src)
    OUT.mkdir(parents=True, exist_ok=True)
    works, skipped = [], []
    imgs = set()
    attr = attributions(src)
    for vol in sorted(src.glob('me[0-9][0-9]')):
        band = int(vol.name[2:])
        ititles = index_titles(vol)
        files = sorted(p for p in vol.glob('me[0-9][0-9]_[0-9][0-9][0-9]*.htm') if re.fullmatch(r'me\d\d_\d{3}[a-z]?\.htm', p.name))
        cur = None
        for p in files:
            d = parse_file(p)
            if d is None:
                continue
            author, title, facts, body, head = split_header(d['blocks'])
            ititle = ititles.get(p.name) or d['title']
            marks = [clean_text(h) for k, h in d['blocks'] if k != 'table' and len(clean_text(h)) < 260 and MARKER.match(clean_text(h))]
            pre = preamble(d['raw'])
            translated = bool(marks) or (bool(FOREIGN_HEAD.search(pre)) and not HISTORIC_DE.search(pre))
            cw, nw = work_of(cur['ititle']) if cur else '', work_of(ititle)
            same = cur is not None and len(cw) >= 6 and (nw.startswith(cw) or (cw.startswith(nw) and len(nw) >= 12 and ' - ' in base(ititle)))
            book = band in (23, 24, 25, 26, 42)
            fresh = not same and not (cur is not None and book) and (title is not None or (cur is not None and AUTH_PREFIX.match(ititle)))
            if fresh and title is None:
                title = nw
            if fresh:
                cur = {'band': band, 'title': title, 'author_raw': author, 'facts': facts, 'translated': translated,
                       'files': [], 'src': d['src'], 'head': head, 'ititle': ititle, 'first': p.name, 'pre': pre}
                works.append(cur)
            elif cur is None:
                cur = {'band': band, 'title': base(ititle).split(' - ')[0], 'author_raw': '', 'facts': [], 'translated': translated,
                       'files': [], 'src': d['src'], 'head': '', 'ititle': ititle, 'first': p.name, 'pre': pre}
                works.append(cur)
            else:
                if title is not None:
                    # a chapter page with its own heading: keep the heading in the text
                    body = [['h', html.escape(title)]] + body
                if not cur['facts'] and facts:
                    cur['facts'] = facts
            body = classify(strip_apparatus(body))
            if p.name[:-4] in EXCLUDE_PARTS:
                skipped.append((band, p.name, ititle[:70], 'written in English'))
                continue
            if FOREIGN_ANY.search(pre) and not HISTORIC_DE.search(pre):
                skipped.append((band, p.name, ititle[:70], 'first printed in a foreign-language paper (preamble)'))
                continue
            first_src = next((clean_text(h) for k, h in body[:12] if k == 'src'), '')
            if FOREIGN.match(first_src) or any(FOREIGN.search(re.sub(r'^.*?(veröffentlicht|erschienen) in:?\s*', '', f)) for f in facts if re.search('veröffentlicht|erschienen', f)):
                skipped.append((band, p.name, ititle[:70], 'first printed in a foreign-language paper: ' + first_src[:50]))
                if not cur['files'] and cur is works[-1]:
                    cur['foreign_cover'] = True
                continue
            if translated:
                cur['translated'] = True
            for k, h in body:
                if k == 'table':
                    for r in h:
                        for x in r:
                            imgs.update(re.findall(r'<img src="([^"]+)"', x))
                else:
                    imgs.update(re.findall(r'<img src="([^"]+)"', h))
            cur['files'].append({'file': p.name, 'title': ititle, 'pages': d['pages'], 'body': body, 'first_src': first_src})

    kept = []
    for w in works:
        if not w['files']:
            continue
        who, others = None, []
        for cand in (w['author_raw'], w['ititle'], w['files'][0]['title']):
            if cand:
                who, others = who_from(cand)
                if who:
                    break
        note = ''
        if not who:
            m = re.match(r'^(Marx|Engels) an ', w['title'])
            if m:
                who = [m.group(1).lower()]
        if not who and w['first'] in attr:
            a = attr[w['first']]
            if a:
                who, others = who_from(a)
            elif 'Rheinische' in w['ititle'] or 'Rheinische' in w['files'][0]['title']:
                who, note = ['marx', 'engels'], 'Unsigned article of the Neue Rheinische Zeitung, edited by Marx with Engels.'
        if not who and re.match(r'^"Neue Rheinische Zeitung"', w['ititle']):
            who, note = ['marx', 'engels'], 'Unsigned article of the Neue Rheinische Zeitung, edited by Marx with Engels.'
        if others and not note:
            note = 'With ' + ' and '.join(others) + '.'
        reason = None
        wid0 = f"{w['band']:02d}-{w['first'][5:8]}"
        if wid0 in EXCLUDE:
            reason = 'checked by hand: not a German original'
        elif w['translated']:
            reason = 'translated by the MEW editors'
        elif not who:
            reason = 'author not Marx or Engels: ' + (w['author_raw'] or w['ititle'])[:60]
        nwords = sum(len(re.findall(r'\w+', clean_text(h))) for f in w['files'] for k, h in f['body'] if k != 'table')
        if not reason and nwords < 40:
            reason = 'empty'
        if reason:
            skipped.append((w['band'], w['first'], w['title'][:70], reason))
            continue
        lo, hi = SPAN.get(w['band'], (1835, 1895))
        ok = lambda y: lo - 2 <= y <= hi + 1
        yrs = [int(y) for y in YEAR.findall(' '.join(w['facts'])) if ok(int(y))][:1]
        if not yrs:
            first = ' '.join(clean_text(h) for f in w['files'][:1] for k, h in f['body'][:8] if k in ('src', 'lt'))
            yrs = [int(y) for y in YEAR.findall(first + ' ' + w['title']) if ok(int(y))][:1]
        srcs = ' '.join(f['first_src'] for f in w['files'][:3])
        w['origin'] = 'de-venue' if GERMAN_VENUE.search(srcs) or GERMAN_VENUE.search(' '.join(w['facts'])) else \
            ('de-historic' if HISTORIC_DE.search(w['pre']) else 'unknown')
        w['who'] = who
        w['note'] = note
        w['year'] = YEAR_FIX.get(f"{w['band']:02d}-{w['first'][5:8]}") or (min(yrs) if yrs else None)
        w['words'] = nwords
        kept.append(w)

    for i, w in enumerate(kept):
        if w['year'] is None:
            near = [x['year'] for x in kept[max(0, i - 3):i + 4] if x['band'] == w['band'] and x['year']]
            w['year'] = sorted(near)[len(near) // 2] if near else SPAN.get(w['band'], (None,))[0]

    index = []
    review = []
    for w in kept:
        wid = f"{w['band']:02d}-{w['first'][5:8]}"
        parts = []
        for f in w['files']:
            pid = f['file'][:-4]
            (OUT / f"{w['band']:02d}").mkdir(exist_ok=True)
            (OUT / f"{w['band']:02d}" / f'{pid}.json').write_text(
                json.dumps({'body': f['body']}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
            pt = base(f['title'])
            bt = base(w['ititle'])
            if pt.startswith(bt):
                pt = pt[len(bt):].lstrip(' -:.')
            if not pt.strip() or pt.strip() == w['title']:
                hd = next((clean_text(h) for k, h in f['body'][:6] if k == 'h' and clean_text(h)), '')
                pt = hd or pt
            parts.append({'id': pid, 'title': pt, 'pages': f['pages'],
                          'words': sum(len(re.findall(r'\w+', clean_text(h))) for k, h in f['body'] if k != 'table')})
        pages = [p['pages'] for p in parts if p['pages']]
        e = {'id': wid, 'band': w['band'], 'title': TITLE_FIX.get(wid, w['title']), 'authors': w['who'], 'year': w['year'],
             'facts': w['facts'], 'pages': [pages[0][0], pages[-1][1]] if pages else None,
             'words': w['words'], 'parts': parts}
        if w['note']:
            e['note'] = w['note']
        brackets = [KEEP_ANGLE[p['id'] + '.htm'] for p in parts if p['id'] + '.htm' in KEEP_ANGLE]
        if brackets:
            e['brackets'] = brackets[0]
        e['origin'] = w['origin']
        review.append(f"{wid}\t{w['origin']}\t{','.join(w['who'])}\t{w['words']}\t{w['title'][:80]}\t{w['pre'][:420]}")
        index.append(e)
    (OUT / 'index.json').write_text(json.dumps({'works': index}, ensure_ascii=False, indent=0), encoding='utf-8')
    (OUT / 'skipped.tsv').write_text('band\tfile\ttitle\treason\n' + ''.join('\t'.join(map(str, s)) + '\n' for s in skipped),
                                     encoding='utf-8')
    Path(sys.argv[2] if len(sys.argv) > 2 else '/dev/null').write_text('\n'.join(review) + '\n', encoding='utf-8')
    (OUT / 'img').mkdir(exist_ok=True)
    used = set()
    for w in index:
        for pt in w['parts']:
            j = (OUT / f"{w['band']:02d}" / f"{pt['id']}.json").read_text(encoding='utf-8')
            for name in re.findall(r'<img src=\\?"([^"\\]+)', j):
                f = src / f"me{w['band']:02d}" / name
                if f.exists():
                    (OUT / 'img' / name).write_bytes(f.read_bytes())
                    used.add(name)
    tw = sum(w['words'] for w in index)
    print(f'{len(index)} works kept ({tw:,} words, {sum(len(w["parts"]) for w in index)} pages); {len(skipped)} skipped')


if __name__ == '__main__':
    main(sys.argv[1])
