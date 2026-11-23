/* TIA archive: tendency filters, catalogue and full-text search, reader highlights.
   No dependencies. Data: /archive/catalogue.json and /archive/text/<id>.json */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // Lower-case, strip accents and straighten quotes without changing string length,
  // so a match position in the folded text is the same position in the original.
  function fold(s) {
    var out = '';
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      var code = c.charCodeAt(0);
      if (code >= 0xD800 && code <= 0xDFFF) { out += c; continue; }
      if (c === '’' || c === '‘') { out += "'"; continue; }
      if (c === '“' || c === '”' || c === '»' || c === '«') { out += '"'; continue; }
      if (code > 127) {
        var b = c.normalize('NFD')[0].toLowerCase();
        out += b.length === 1 ? b : c;
      } else {
        out += c.toLowerCase();
      }
    }
    return out;
  }
  function escHTML(s) {
    return s.replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
  }
  function markAll(text, needle, folded) {
    // wrap every folded match of needle in <mark>, escaping the rest
    var f = folded || fold(text), out = '', i = 0, j;
    if (!needle) return escHTML(text);
    while ((j = f.indexOf(needle, i)) !== -1) {
      out += escHTML(text.slice(i, j)) + '<mark>' + escHTML(text.slice(j, j + needle.length)) + '</mark>';
      i = j + needle.length;
    }
    return out + escHTML(text.slice(i));
  }

  /* ---------------- tendency filters (archive index) ---------------- */
  var chips = $$('.chip[data-f]');
  var cards = $$('.dos[data-t]');
  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      var f = chip.getAttribute('data-f');
      chips.forEach(function (c) {
        var on = c === chip;
        c.classList.toggle('on', on);
        c.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      cards.forEach(function (d) { d.hidden = !(f === 'all' || d.getAttribute('data-t') === f); });
    });
  });

  /* ---------------- search (archive index) ---------------- */
  var form = $('#ar-form');
  if (form) {
    var input = $('#ar-q');
    var panel = $('#ar-results');
    var status = $('#ar-status');
    var bar = $('#ar-bar');
    var catBox = $('#ar-cat');
    var fullBox = $('#ar-full');
    var catalogue = null;
    var texts = {};
    var run = 0;

    var getCatalogue = function () {
      if (catalogue) return Promise.resolve(catalogue);
      return fetch('/archive/catalogue.json').then(function (r) { return r.json(); }).then(function (c) {
        c.byAuthor = {};
        c.authors.forEach(function (a) { c.byAuthor[a.slug] = a; a.hay = fold([a.name, a.short, a.years, a.tg, a.role].join(' ')); });
        c.works.forEach(function (w) {
          w.names = w.authors.map(function (s) { return c.byAuthor[s].name; }).join(' and ');
          w.hay = fold([w.title, w.sub, w.year, w.names, w.authors.join(' ')].join(' '));
        });
        catalogue = c;
        return c;
      });
    };
    var bib = null;
    var getBib = function () {
      if (bib) return Promise.resolve(bib);
      return fetch('/archive/bibliography.json').then(function (r) { return r.json(); }).then(function (b) {
        b.f = b.i.map(function (row) { return fold(row[2]); });
        bib = b;
        return b;
      });
    };
    var bibBox = $('#ar-bib');
    var searchBib = function (my, tokens, q) {
      if (!bibBox) return;
      getBib().then(function (b) {
        if (my !== run) return;
        var hits = [];
        for (var i = 0; i < b.f.length; i++) {
          var ok = true;
          for (var t = 0; t < tokens.length; t++) { if (b.f[i].indexOf(tokens[t]) === -1) { ok = false; break; } }
          if (ok) hits.push(b.i[i]);
        }
        if (!hits.length) { bibBox.innerHTML = ''; return; }
        var names = catalogue ? catalogue.byAuthor : {};
        var h = '<div style="margin-top: 22px"><p class="mn" style="margin: 0; padding-bottom: 8px; border-bottom: 1px solid #3A2326; font-size: 14px; letter-spacing: 0.1em">IN THE COMPLETE WORKS <span style="color: #A89C95">· ' + hits.length + ' TITLE' + (hits.length === 1 ? '' : 'S') + '</span></p><ul class="hit-list">';
        hits.slice(0, 40).forEach(function (row) {
          var slug = b.a[row[0]], a = names[slug];
          var url = row[3].charAt(0) === '~' ? 'https://www.marxists.org/' + row[3].slice(1) : row[3];
          var ext = url.indexOf('http') === 0;
          h += '<li style="padding: 10px 0"><span class="hw">' + row[1] + ' · <a href="/archive/' + slug + '/works/#y' + row[1] + '">' + escHTML(a ? a.short : slug.toUpperCase()) + '</a> · ' +
            '<a href="' + escHTML(url) + '"' + (ext ? ' target="_blank" rel="noopener"' : '') + ' style="color: #F2ECE4">' + markAll(row[2], tokens.length === 1 ? tokens[0] : '') + (ext ? ' ↗' : ' [READ →]') + '</a>' +
            (row[4] ? ' <span style="color: #7A6A64">LETTER</span>' : '') + '</span></li>';
        });
        h += '</ul>';
        if (hits.length > 40) h += '<p class="mn" style="margin: 10px 0 0; font-size: 13px; letter-spacing: 0.1em; color: #A89C95">+ ' + (hits.length - 40) + ' MORE · ADD A WORD OR A YEAR TO NARROW IT DOWN</p>';
        h += '</div>';
        bibBox.innerHTML = h;
      }).catch(function () {});
    };
    var getText = function (id) {
      if (texts[id]) return Promise.resolve(texts[id]);
      return fetch('/archive/text/' + id + '.json').then(function (r) { return r.json(); }).then(function (t) {
        t.f = t.p.map(function (p) { return fold(p[1]); });
        texts[id] = t;
        return t;
      });
    };

    var snippet = function (text, at, len) {
      var a = Math.max(0, at - 110), b = Math.min(text.length, at + len + 150);
      while (a > 0 && text[a] !== ' ') a--;
      while (b < text.length && text[b] !== ' ') b++;
      return { s: text.slice(a, b).trim() };
    };

    var search = function (q) {
      var my = ++run;
      var needle = fold(q.trim()).replace(/\s+/g, ' ');
      if (!needle) { clear(); return; }
      panel.hidden = false;
      status.innerHTML = 'SEARCHING FOR <b>“' + escHTML(q.trim()) + '”</b>';
      bar.style.width = '4%';
      catBox.innerHTML = '';
      fullBox.innerHTML = '';
      if (bibBox) bibBox.innerHTML = '';
      var tokens = needle.split(' ');
      // German umlauts are often spelled out in old English editions (Dühring, Duehring)
      var needles = [needle];
      if (/[äöüÄÖÜ]/.test(q)) {
        needles.push(fold(q.trim().replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/Ä/g, 'Ae').replace(/Ö/g, 'Oe').replace(/Ü/g, 'Ue')).replace(/\s+/g, ' '));
      }
      getCatalogue().then(function (c) {
        if (my !== run) return;
        var match = function (hay) { return tokens.every(function (t) { return hay.indexOf(t) !== -1; }); };
        var authors = c.authors.filter(function (a) { return match(a.hay); });
        var works = c.works.filter(function (w) { return match(w.hay); });
        var html = '';
        if (authors.length || works.length) {
          html += '<ul class="hit-list" style="margin-top: 12px">';
          authors.forEach(function (a) {
            html += '<li><span class="hw">SUBJECT · <a href="' + a.url + '">' + escHTML(a.name.toUpperCase()) + ' →</a></span>' +
              '<q style="font-family: Inter, sans-serif; font-size: 15px">' + escHTML(a.years) + '. ' + escHTML(a.role) + '</q></li>';
          });
          works.forEach(function (w) {
            var ext = w.kind !== 'hosted';
            html += '<li><span class="hw">' + escHTML(w.year) + ' · ' + escHTML(w.names.toUpperCase()) + ' · ' +
              '<a href="' + escHTML(w.url) + '"' + (ext ? ' target="_blank" rel="noopener"' : '') + '>' +
              markAll(w.title, tokens.length === 1 ? tokens[0] : '') + (ext ? ' [MIA ↗]' : ' [READ →]') + '</a></span></li>';
          });
          html += '</ul>';
        }
        catBox.innerHTML = html;
        searchBib(my, tokens, q);
        var hosted = c.works.filter(function (w) { return w.kind === 'hosted'; });
        if (needle.length < 3) {
          finish(authors.length + works.length, 0, 0, q);
          return;
        }
        var done = 0, hits = 0, inTexts = 0;
        var chain = Promise.resolve();
        hosted.forEach(function (w) {
          chain = chain.then(function () {
            if (my !== run) return;
            return getText(w.id).then(function (t) {
              if (my !== run) return;
              var found = [];
              for (var i = 0; i < t.f.length; i++) {
                for (var v = 0; v < needles.length; v++) {
                  var nd = needles[v], at = t.f[i].indexOf(nd);
                  if (at === -1) continue;
                  var count = 0, k = at;
                  while (k !== -1) { count++; k = t.f[i].indexOf(nd, k + nd.length); }
                  hits += count;
                  found.push([t.p[i][0], t.p[i][1], at, nd]);
                  break;
                }
              }
              done++;
              bar.style.width = Math.round(4 + 96 * done / hosted.length) + '%';
              status.innerHTML = 'SCANNING FULL TEXTS ' + done + '/' + hosted.length + ' · <b>' + hits + '</b> MATCHES';
              if (!found.length) return;
              inTexts++;
              var section = document.createElement('div');
              section.style.marginTop = '22px';
              var h = '<p class="mn" style="margin: 0; padding-bottom: 8px; border-bottom: 1px solid #3A2326; font-size: 14px; letter-spacing: 0.1em">' +
                '<a href="' + w.url + '" style="color: #F2ECE4">' + escHTML(w.title.toUpperCase()) + '</a>' +
                ' <span style="color: #A89C95">· ' + escHTML(w.names.toUpperCase()) + ' · ' + escHTML(w.year) + ' · ' + found.length + ' PASSAGE' + (found.length === 1 ? '' : 'S') + '</span></p><ul class="hit-list">';
              found.slice(0, 5).forEach(function (f) {
                var sn = snippet(f[1], f[2], f[3].length);
                h += '<li><span class="hw"><a href="' + w.url + '?hl=' + encodeURIComponent(f[3]) + '#p' + f[0] + '">¶ ' + f[0] + ' →</a></span><q>' + markAll(sn.s, f[3]) + '</q></li>';
              });
              h += '</ul>';
              if (found.length > 5) {
                h += '<p class="mn" style="margin: 10px 0 0; font-size: 13px; letter-spacing: 0.1em; color: #A89C95">+ ' + (found.length - 5) +
                  ' MORE · <a href="' + w.url + '?hl=' + encodeURIComponent(found[5][3]) + '#p' + found[5][0] + '" style="color: #FF5A60">CONTINUE IN THE TEXT →</a></p>';
              }
              section.innerHTML = h;
              fullBox.appendChild(section);
            });
          });
        });
        chain.then(function () { if (my === run) finish(authors.length + works.length, hits, inTexts, q); })
          .catch(function () { if (my === run) status.textContent = 'FULL-TEXT INDEX UNAVAILABLE · TRY AGAIN'; });
      }).catch(function () { status.textContent = 'INDEX UNAVAILABLE · CHECK YOUR CONNECTION'; });
    };

    var finish = function (nCat, hits, inTexts, q) {
      bar.style.width = '100%';
      var parts = [];
      parts.push('<b>' + nCat + '</b> IN THE CATALOGUE');
      if (fold(q.trim()).length >= 3) parts.push('<b>' + hits + '</b> PASSAGES IN ' + inTexts + ' FULL TEXT' + (inTexts === 1 ? '' : 'S'));
      status.innerHTML = '“' + escHTML(q.trim()) + '” · ' + parts.join(' · ');
      if (!nCat && !hits && !(bibBox && bibBox.innerHTML)) {
        catBox.innerHTML = '<p style="margin: 16px 0 0; color: #CFC4BC">Nothing filed under that yet. Try a surname, a year or a phrase from the text, or browse the dossiers below.</p>';
      }
    };

    var clear = function () {
      run++;
      panel.hidden = true;
      catBox.innerHTML = '';
      fullBox.innerHTML = '';
      if (bibBox) bibBox.innerHTML = '';
      input.value = '';
      try { history.replaceState(null, '', location.pathname); } catch (e) {}
    };

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = input.value;
      try { history.replaceState(null, '', q.trim() ? '?q=' + encodeURIComponent(q.trim()) : location.pathname); } catch (err) {}
      search(q);
    });
    $('#ar-clear').addEventListener('click', function () { clear(); input.focus(); });

    var q0 = new URLSearchParams(location.search).get('q');
    if (q0) {
      input.value = q0;
      search(q0);
      panel.scrollIntoView({ block: 'start' });
    }
  }

  /* ---------------- complete works pages ---------------- */
  var cwq = $('#cw-q');
  if (cwq) {
    var cwRows = $$('.cw li').map(function (li) { return { el: li, f: fold(li.textContent), l: li.classList.contains('l') }; });
    var cwSecs = $$('.cw-y');
    var cwCount = $('#cw-count');
    var showLetters = true;
    var cwApply = function () {
      var toks = fold(cwq.value.trim()).split(/\s+/).filter(Boolean);
      var n = 0;
      cwRows.forEach(function (r) {
        var ok = (showLetters || !r.l) && toks.every(function (t) { return r.f.indexOf(t) !== -1; });
        r.el.hidden = !ok;
        if (ok) n++;
      });
      cwSecs.forEach(function (sec) { sec.hidden = !sec.querySelector('li:not([hidden])'); });
      cwCount.textContent = n.toLocaleString('en') + ' SHOWN';
    };
    var cwT;
    cwq.addEventListener('input', function () { clearTimeout(cwT); cwT = setTimeout(cwApply, 120); });
    var lb = $('#cw-letters');
    if (lb) lb.addEventListener('click', function () {
      showLetters = !showLetters;
      lb.classList.toggle('on', showLetters);
      lb.setAttribute('aria-pressed', showLetters ? 'true' : 'false');
      cwApply();
    });
  }

  /* ---------------- reader pages ---------------- */
  var article = $('article.text');
  if (article) {
    var hl = new URLSearchParams(location.search).get('hl');
    var target = location.hash ? document.getElementById(location.hash.slice(1)) : null;
    if (hl && target) {
      var needle = fold(hl.trim()).replace(/\s+/g, ' ');
      var walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT, null);
      var nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach(function (node) {
        var t = node.nodeValue, f = fold(t).replace(/\s/g, ' ');
        if (f.indexOf(needle) === -1) return;
        var span = document.createElement('span');
        span.innerHTML = markAll(t, needle, f);
        node.parentNode.replaceChild(span, node);
      });
      target.classList.add('flash');
      setTimeout(function () { target.scrollIntoView({ block: 'center' }); }, 60);
    } else if (target) {
      target.classList.add('flash');
    }

    // contents: mark the section being read
    var links = $$('.toc a');
    if (links.length && 'IntersectionObserver' in window) {
      var map = {};
      links.forEach(function (a) { map[a.getAttribute('href').slice(1)] = a; });
      var current = null;
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting && map[en.target.id]) {
            if (current) current.classList.remove('on');
            current = map[en.target.id];
            current.classList.add('on');
            var toc = current.closest('.toc');
            if (toc) {
              var top = current.offsetTop - toc.clientHeight / 2;
              toc.scrollTo({ top: top, behavior: 'smooth' });
            }
          }
        });
      }, { rootMargin: '0px 0px -70% 0px' });
      $$('article.text h2[id]').forEach(function (h) { io.observe(h); });
    }
    $$('.toc-m a').forEach(function (a) { a.addEventListener('click', function () { a.closest('details').open = false; }); });
  }
})();
