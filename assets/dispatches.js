/* Dispatches: latest posts from the TIA Substack, served by /api/substack (see worker/index.js). */
(function () {
  'use strict';
  var boxes = document.querySelectorAll('[data-dispatches]');
  if (!boxes.length) return;
  var PUB = 'https://technicalinvariance.substack.com';
  function esc(s) { return String(s || '').replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function day(d) {
    var t = new Date(d);
    return isNaN(t) ? '' : t.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase();
  }
  function card(p, i) {
    var img = p.image
      ? '<img src="' + esc(p.image) + '" alt="" loading="lazy">'
      : '<span class="dsp-ph" aria-hidden="true"><img src="/assets/emblem_globe.png" alt=""></span>';
    return '<a class="dsp-card" href="' + esc(p.url) + '" target="_blank" rel="noopener">' +
      '<div class="dsp-img">' + img + '<span class="dsp-no mn">DISPATCH ' + String(i + 1).padStart(2, '0') + '</span></div>' +
      '<div class="dsp-bd"><span class="dsp-d mn">' + esc(day(p.date)) + (p.paid ? ' · SUBSCRIBERS' : '') + '</span>' +
      '<span class="dsp-t">' + esc(p.title) + '</span>' +
      (p.subtitle ? '<span class="dsp-s">' + esc(p.subtitle) + '</span>' : '') +
      '<span class="dsp-go mn">READ ON SUBSTACK ↗</span></div></a>';
  }
  var note = function (msg) {
    return '<div class="dsp-empty"><p>' + msg + '</p><a class="mn" href="' + PUB + '/" target="_blank" rel="noopener">TECHNICALINVARIANCE.SUBSTACK.COM ↗</a></div>';
  };
  fetch('/api/substack', { headers: { Accept: 'application/json' } })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      var posts = (d.posts || []).filter(function (p) { return p.title && p.url; });
      Array.prototype.forEach.call(boxes, function (b) {
        var lim = parseInt(b.getAttribute('data-limit'), 10) || 100;
        b.innerHTML = posts.length
          ? posts.slice(0, lim).map(card).join('')
          : note('No dispatches yet. Subscribe and the first one arrives by email.');
        b.setAttribute('aria-busy', 'false');
      });
      var c = document.querySelector('[data-dispatches-count]');
      if (c && posts.length) c.textContent = posts.length + ' DISPATCH' + (posts.length === 1 ? '' : 'ES');
    })
    .catch(function () {
      Array.prototype.forEach.call(boxes, function (b) {
        b.innerHTML = note('The latest dispatches could not be loaded here just now. Read them all on Substack.');
        b.setAttribute('aria-busy', 'false');
      });
    });
})();
