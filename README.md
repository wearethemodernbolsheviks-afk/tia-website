# invariancetech.info

Website of the Technical Invariance Authority: an open archive of world Marxism and a workshop for communist technology.

Plain static files. Cloudflare Pages deploys this repository on every push to `main`.

- `index.html` homepage
- `archive/` Index of Marxists: dossiers, reader pages, collections, search data
- `arcade/` simulations
- `shop/` TIA Supply Depot
- `assets/` images, video, icons and `archive.js` (filters, search, reader highlights)
- `assets/bgc/` full-colour poster crops used as archive backgrounds

## The archive

The archive pages are generated. Do not edit files under `archive/` by hand.

- `content/catalogue.json` lists every thinker's works and the collections. A work is either
  `"kind": "hosted"` (full text on this site) or `"kind": "link"` (points to where it is legally hosted).
- `content/texts/<id>.txt` holds the full text of each hosted work.
- `tools/build_archive.py` builds everything (standard library only):

```
python3 tools/build_archive.py
```

It writes the dossier pages, a reader page and `.txt` download for every hosted text, the collection
pages, `archive/catalogue.json` and `archive/text/<id>.json` for search, and updates `archive/index.html`,
`index.html` and `sitemap.xml`. Page chrome comes from `tools/templates/`.

### Adding a work

1. Add an entry to the author's `works` in `content/catalogue.json`.
2. For a full text, put the cleaned text in `content/texts/<id>.txt` and set `kind`, `slug`, `lang` and `edition`.
   Only host texts that are public domain: author and translator dead for more than 70 years, or an anonymous
   translation published before 1931. Everything else is a link.
3. Run the build, check the pages locally (`python3 -m http.server`), commit and push.

`tools/ingest_gutenberg.py` strips the header, footer and production credits from public-domain e-texts.
