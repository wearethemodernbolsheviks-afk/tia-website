/* TIA media: the station player that sits on every page, and read-aloud for the archive texts.
   Read-aloud uses the browser's own speech engine (Web Speech API), so it costs nothing and works offline. */
(() => {
  'use strict';
  if (window.TIAMedia) return;
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } },
  };
  const el = (tag, attrs = {}, html = '') => { const e = document.createElement(tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (html) e.innerHTML = html; return e; };
  const fmt = s => { s = Math.max(0, Math.floor(s || 0)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
  const MONO = "'Manolo Mono', 'Share Tech Mono', ui-monospace, monospace";

  const css = `
.tm-dock { position: fixed; left: 16px; bottom: 16px; z-index: 70; font-family: ${MONO}; color: #F2ECE4; transition: bottom 200ms ease; }
body.tts-open .tm-dock { bottom: 84px; }
.tm-pill { display: flex; align-items: center; gap: 10px; height: 40px; padding: 0 14px; background: rgba(15, 10, 11, 0.94); border: 1px solid #3A2326; color: #F2ECE4; font: 13px/1 ${MONO}; letter-spacing: 0.14em; cursor: pointer; }
.tm-pill:hover, .tm-pill:focus-visible { border-color: #E8222A; outline: none; }
.tm-pill.wait { border-color: #F2B33D; animation: tm-pulse 1.4s ease-in-out infinite; }
@keyframes tm-pulse { 50% { box-shadow: 0 0 0 4px rgba(242, 179, 61, 0.18); } }
.tm-bars { display: inline-flex; align-items: flex-end; gap: 2px; width: 14px; height: 12px; }
.tm-bars i { width: 3px; height: 3px; background: #E8222A; }
.tm-dock.on .tm-bars i { animation: tm-bar 0.9s ease-in-out infinite; }
.tm-dock.on .tm-bars i:nth-child(2) { animation-delay: -0.3s; } .tm-dock.on .tm-bars i:nth-child(3) { animation-delay: -0.6s; }
@keyframes tm-bar { 0%, 100% { height: 3px; } 50% { height: 12px; } }
.tm-now { max-width: 180px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: #A89C95; letter-spacing: 0.08em; }
.tm-panel { position: absolute; left: 0; bottom: 48px; width: min(340px, calc(100vw - 32px)); background: rgba(12, 7, 8, 0.97); border: 1px solid #3A2326; box-shadow: 0 18px 50px rgba(0, 0, 0, 0.6); display: none; }
.tm-dock.open .tm-panel { display: block; }
.tm-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid #2A1A1C; font-size: 12px; letter-spacing: 0.16em; color: #A89C95; }
.tm-head b { color: #E8222A; font-weight: 400; }
.tm-title { padding: 14px 14px 4px; font: 600 17px/1.3 Inter, system-ui, sans-serif; color: #F2ECE4; }
.tm-sub { padding: 0 14px; font-size: 12px; letter-spacing: 0.12em; color: #7A6A64; }
.tm-bar { position: relative; margin: 14px 14px 6px; height: 6px; background: #2A1A1C; cursor: pointer; }
.tm-bar span { position: absolute; left: 0; top: 0; bottom: 0; background: #E8222A; width: 0; }
.tm-time { display: flex; justify-content: space-between; padding: 0 14px; font-size: 11px; color: #7A6A64; letter-spacing: 0.1em; }
.tm-ctl { display: flex; align-items: center; gap: 8px; padding: 12px 14px; }
.tm-ctl button, .tts-bar button { background: none; border: 1px solid #3A2326; color: #F2ECE4; height: 36px; min-width: 40px; font: 14px/1 ${MONO}; cursor: pointer; }
.tm-ctl button:hover, .tts-bar button:hover, .tm-ctl button:focus-visible, .tts-bar button:focus-visible { border-color: #E8222A; outline: none; }
.tm-ctl .tm-play, .tts-bar .tts-play { background: #E8222A; border-color: #E8222A; min-width: 52px; }
.tm-ctl input[type=range] { flex: 1; accent-color: #E8222A; min-width: 60px; }
.tm-list { list-style: none; margin: 0; padding: 4px 0; border-top: 1px solid #2A1A1C; max-height: 220px; overflow: auto; }
.tm-list li button { display: flex; width: 100%; justify-content: space-between; gap: 10px; padding: 9px 14px; background: none; border: 0; color: #CFC4BC; font: 13px/1.3 ${MONO}; letter-spacing: 0.06em; text-align: left; cursor: pointer; }
.tm-list li button:hover { background: #1A1012; color: #F2ECE4; }
.tm-list li.cur button { color: #E8222A; }
.tm-foot { display: flex; justify-content: space-between; padding: 10px 14px; border-top: 1px solid #2A1A1C; font-size: 11px; letter-spacing: 0.14em; }
.tm-foot a, .tm-foot button { color: #A89C95; background: none; border: 0; font: inherit; letter-spacing: inherit; cursor: pointer; text-decoration: none; padding: 0; }
.tm-foot a:hover, .tm-foot button:hover { color: #F2ECE4; }
.tm-note { padding: 0 14px 10px; font-size: 11px; color: #F2B33D; letter-spacing: 0.08em; display: none; }
.tm-dock.wait .tm-note, .tm-dock.away .tm-note { display: block; }
.tts-bar { position: fixed; left: 50%; transform: translateX(-50%); bottom: 16px; z-index: 71; display: none; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: center; padding: 10px 12px; width: min(860px, calc(100vw - 32px)); background: rgba(12, 7, 8, 0.97); border: 1px solid #3A2326; box-shadow: 0 18px 50px rgba(0, 0, 0, 0.6); font: 12px/1 ${MONO}; letter-spacing: 0.1em; color: #A89C95; }
body.tts-open .tts-bar { display: flex; }
.tts-bar select { background: #0F0A0B; color: #F2ECE4; border: 1px solid #3A2326; height: 36px; font: 12px ${MONO}; max-width: 230px; }
.tts-bar .tts-pos { min-width: 92px; text-align: center; }
.tts-bar .tts-hint { flex-basis: 100%; text-align: center; color: #6E5F5A; font-size: 11px; }
.text .tts-cur { background: rgba(232, 34, 42, 0.1); box-shadow: -14px 0 0 rgba(232, 34, 42, 0.1), 14px 0 0 rgba(232, 34, 42, 0.1), inset 3px 0 0 #E8222A; }
.tts-listen { display: inline-flex; align-items: center; gap: 8px; }
@media (max-width: 640px) {
  .tm-dock { left: 10px; bottom: 10px; } body.tts-open .tm-dock { bottom: 128px; }
  .tm-now { display: none; }
  .tts-bar { bottom: 0; width: 100vw; border-left: 0; border-right: 0; }
  .tts-bar .tts-hint { display: none; }
}
@media (prefers-reduced-motion: reduce) { .tm-dock.on .tm-bars i, .tm-pill.wait { animation: none; } }
`;
  document.head.appendChild(el('style', { id: 'tm-style' }, css));

  /* ------------------------------------------------------------------ radio */
  const Radio = (() => {
    const KEY = 'tia-radio-v1';
    const st = Object.assign({ i: 0, t: 0, on: false, vol: 0.7, shuffle: false }, store.get(KEY, {}));
    let tracks = [];
    const audio = new Audio();
    audio.preload = 'none';
    audio.volume = st.vol;
    let duckLevel = 1;
    let ready = false;
    const isPage = !!document.querySelector('[data-radio-page]');
    const chan = 'BroadcastChannel' in window ? new BroadcastChannel('tia-radio') : null;
    const me = Math.random().toString(36).slice(2);
    let awayUntil = 0;

    const dock = el('div', { class: 'tm-dock', role: 'region', 'aria-label': 'TIA Radio' });
    dock.innerHTML = `
      <div class="tm-panel" id="tm-panel">
        <div class="tm-head"><span><b>●</b> TIA RADIO</span><span class="tm-count"></span></div>
        <div class="tm-title">—</div><div class="tm-sub">TIA LABS</div>
        <div class="tm-bar" role="slider" aria-label="Seek" tabindex="0"><span></span></div>
        <div class="tm-time"><span class="tm-cur">0:00</span><span class="tm-dur">0:00</span></div>
        <div class="tm-ctl">
          <button class="tm-prev" aria-label="Previous track">⏮</button>
          <button class="tm-play" aria-label="Play">▶</button>
          <button class="tm-next" aria-label="Next track">⏭</button>
          <input type="range" min="0" max="1" step="0.01" aria-label="Volume">
        </div>
        <div class="tm-note"></div>
        <ol class="tm-list"></ol>
        <div class="tm-foot"><button class="tm-pop" type="button">POP OUT ↗</button><a href="/radio/">STATION PAGE →</a></div>
      </div>
      <button class="tm-pill" aria-expanded="false" aria-controls="tm-panel"><span class="tm-bars" aria-hidden="true"><i></i><i></i><i></i></span><span>RADIO</span><span class="tm-now"></span></button>`;
    const $ = s => dock.querySelector(s);
    const pill = $('.tm-pill');
    const vol = $('input[type=range]');
    vol.value = st.vol;

    const save = () => { st.t = audio.currentTime || st.t; store.set(KEY, st); };
    const paint = () => {
      const tr = tracks[st.i];
      const playing = !audio.paused;
      dock.classList.toggle('on', playing);
      $('.tm-play').textContent = playing ? '❚❚' : '▶';
      $('.tm-play').setAttribute('aria-label', playing ? 'Pause' : 'Play');
      if (tr) {
        $('.tm-title').textContent = tr.title;
        $('.tm-now').textContent = playing ? tr.title : '';
        $('.tm-dur').textContent = fmt(audio.duration || tr.dur);
        $('.tm-count').textContent = `${st.i + 1} / ${tracks.length}`;
      }
      dock.querySelectorAll('.tm-list li').forEach((li, k) => li.classList.toggle('cur', k === st.i));
      document.dispatchEvent(new CustomEvent('tia-radio', { detail: { playing, track: tr, index: st.i } }));
    };
    const tick = () => {
      const d = audio.duration || (tracks[st.i] || {}).dur || 1;
      $('.tm-bar span').style.width = (100 * (audio.currentTime || 0) / d) + '%';
      $('.tm-cur').textContent = fmt(audio.currentTime);
    };
    const load = (i, t = 0) => {
      st.i = (i + tracks.length) % tracks.length;
      st.t = t;
      audio.src = tracks[st.i].src;
      audio.preload = 'auto';
      const seek = () => { try { audio.currentTime = t; } catch (e) { /* not seekable yet */ } };
      if (t) audio.addEventListener('loadedmetadata', seek, { once: true });
      paint();
    };
    const play = () => {
      if (!tracks.length) return Promise.resolve();
      if (!audio.src) load(st.i, st.t);
      chan && chan.postMessage({ type: 'claim', from: me });
      dock.classList.remove('away', 'wait');
      pill.classList.remove('wait');
      return audio.play().then(() => { st.on = true; save(); paint(); }).catch(() => {
        dock.classList.add('wait'); pill.classList.add('wait');
        $('.tm-note').textContent = 'Tap play to carry on listening.';
      });
    };
    const pause = (keepOn) => { audio.pause(); if (!keepOn) st.on = false; save(); paint(); };
    const toggle = () => (audio.paused ? play() : pause());
    const next = () => { load(st.shuffle ? Math.floor(Math.random() * tracks.length) : st.i + 1); play(); };
    const prev = () => { if (audio.currentTime > 4) { audio.currentTime = 0; return; } load(st.i - 1); play(); };

    audio.addEventListener('ended', next);
    audio.addEventListener('timeupdate', () => { tick(); if (Math.floor(audio.currentTime) % 3 === 0) save(); });
    audio.addEventListener('play', paint);
    audio.addEventListener('pause', paint);
    audio.addEventListener('loadedmetadata', paint);
    window.addEventListener('pagehide', save);
    document.addEventListener('visibilitychange', () => { if (document.hidden) save(); });

    pill.addEventListener('click', () => {
      if (dock.classList.contains('wait')) { play(); return; }
      const open = !dock.classList.contains('open');
      dock.classList.toggle('open', open);
      pill.setAttribute('aria-expanded', open);
      if (open && !audio.src && tracks.length) load(st.i, st.t);
    });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && dock.classList.contains('open')) { dock.classList.remove('open'); pill.setAttribute('aria-expanded', 'false'); pill.focus(); } });
    $('.tm-play').addEventListener('click', toggle);
    $('.tm-next').addEventListener('click', next);
    $('.tm-prev').addEventListener('click', prev);
    vol.addEventListener('input', () => { st.vol = +vol.value; audio.volume = st.vol * duckLevel; save(); });
    const seekTo = x => { const r = $('.tm-bar').getBoundingClientRect(); const d = audio.duration || (tracks[st.i] || {}).dur; if (d) { if (!audio.src) load(st.i); audio.currentTime = Math.min(d - 0.5, Math.max(0, (x - r.left) / r.width * d)); } };
    $('.tm-bar').addEventListener('click', e => seekTo(e.clientX));
    $('.tm-bar').addEventListener('keydown', e => { if (e.key === 'ArrowRight') audio.currentTime += 10; if (e.key === 'ArrowLeft') audio.currentTime -= 10; });
    $('.tm-pop').addEventListener('click', () => {
      pause(true); st.on = true; save();
      const w = window.open('/radio/?popout=1', 'tia-radio', 'width=420,height=680');
      if (!w) location.href = '/radio/';
    });

    if (chan) {
      chan.onmessage = ev => {
        const m = ev.data || {};
        if (m.from === me) return;
        if (m.type === 'claim' && !audio.paused) { pause(true); st.on = true; save(); dock.classList.add('away'); $('.tm-note').textContent = 'Playing in another window.'; }
        if (m.type === 'alive') { awayUntil = Date.now() + 5000; if (!audio.paused) pause(true); dock.classList.add('away'); $('.tm-note').textContent = 'Playing in the pop-out player.'; }
      };
      if (isPage) setInterval(() => { if (!audio.paused) chan.postMessage({ type: 'alive', from: me }); }, 2000);
    }

    fetch('/assets/radio/tracks.json').then(r => r.json()).then(j => {
      tracks = j.tracks || [];
      if (!tracks.length) return;
      if (st.i >= tracks.length) st.i = 0;
      const list = $('.tm-list');
      tracks.forEach((tr, k) => {
        const li = el('li', {}, `<button type="button"><span>${String(k + 1).padStart(2, '0')} · ${tr.title}</span><span>${fmt(tr.dur)}</span></button>`);
        li.querySelector('button').addEventListener('click', () => { load(k); play(); });
        list.appendChild(li);
      });
      ready = true;
      paint();
      document.dispatchEvent(new CustomEvent('tia-radio-ready', { detail: { tracks } }));
      // carry on from the last page, unless the pop-out is playing
      setTimeout(() => { if (st.on && Date.now() > awayUntil && !isPage && !document.querySelector('[data-no-radio-dock]')) { load(st.i, st.t); play(); } }, 300);
    }).catch(() => { dock.style.display = 'none'; });

    const mount = () => { if (!document.querySelector('[data-no-radio-dock]')) document.body.appendChild(dock); };
    if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount);

    return {
      play, pause: () => pause(), toggle, next, prev, load: (i) => { load(i); return play(); },
      duck(on) { duckLevel = on ? 0.18 : 1; audio.volume = st.vol * duckLevel; },
      get tracks() { return tracks; }, get index() { return st.i; }, get playing() { return !audio.paused; }, get ready() { return ready; },
      audio, state: st,
    };
  })();

  /* ------------------------------------------------------------- read aloud */
  const TTS = (() => {
    const article = document.querySelector('article.text');
    if (!article || !('speechSynthesis' in window)) return null;
    const synth = window.speechSynthesis;
    const lang = (article.getAttribute('lang') || document.documentElement.lang || 'en').toLowerCase();
    const KEY = 'tia-tts-v1';
    const pref = Object.assign({ rate: 1, voice: {} }, store.get(KEY, {}));
    const blocks = [...article.querySelectorAll(':scope > p, :scope > h2, :scope > h3, :scope > h4, :scope > blockquote, :scope > ul > li, :scope > ol > li, :scope > div.q')]
      .filter(b => b.textContent.trim().length > 1);
    if (!blocks.length) return null;
    let idx = 0, sent = 0, sentences = [], speaking = false, voices = [], gen = 0, fails = 0;

    const bar = el('div', { class: 'tts-bar', role: 'region', 'aria-label': 'Read aloud' });
    bar.innerHTML = `
      <button class="tts-prev" aria-label="Previous paragraph">⏮</button>
      <button class="tts-play" aria-label="Pause">❚❚</button>
      <button class="tts-next" aria-label="Next paragraph">⏭</button>
      <span class="tts-pos" aria-live="off">¶ 1 / ${blocks.length}</span>
      <select class="tts-rate" aria-label="Speed">${[0.75, 0.9, 1, 1.15, 1.3, 1.5, 1.75, 2].map(r => `<option value="${r}">${r}×</option>`).join('')}</select>
      <select class="tts-voice" aria-label="Voice"></select>
      <button class="tts-close" aria-label="Stop reading aloud">✕</button>
      <span class="tts-hint">Double-click any paragraph to read from there · Voices come from your device</span>`;
    const $ = s => bar.querySelector(s);
    $('.tts-rate').value = String(pref.rate);

    const pickVoices = () => {
      voices = synth.getVoices();
      const mine = voices.filter(v => v.lang.toLowerCase().startsWith(lang.slice(0, 2)));
      const list = mine.length ? mine : voices;
      const sel = $('.tts-voice');
      sel.innerHTML = list.map(v => `<option value="${v.voiceURI}">${v.name.replace(/Microsoft |Google /, '')} · ${v.lang}</option>`).join('');
      const want = pref.voice[lang];
      const best = list.find(v => v.voiceURI === want) || list.find(v => /natural|neural|premium|enhanced/i.test(v.name)) || list.find(v => /google/i.test(v.name)) || list.find(v => v.default) || list[0];
      if (best) sel.value = best.voiceURI;
    };
    pickVoices();
    if (synth.onvoiceschanged !== undefined) synth.addEventListener('voiceschanged', pickVoices);

    const split = t => {
      t = t.replace(/\s+/g, ' ').trim();
      const parts = t.match(/[^.!?;:]+(?:[.!?;:]+["'”’)\]]*|$)/g) || [t];
      const out = [];
      for (let p of parts) {
        p = p.trim();
        while (p.length > 220) { let k = p.lastIndexOf(',', 200); if (k < 60) k = p.lastIndexOf(' ', 200); if (k < 1) k = 200; out.push(p.slice(0, k + 1)); p = p.slice(k + 1).trim(); }
        if (p) out.push(p);
      }
      return out;
    };
    const mark = () => {
      blocks.forEach(b => b.classList.remove('tts-cur'));
      const b = blocks[idx];
      if (!b) return;
      b.classList.add('tts-cur');
      $('.tts-pos').textContent = `¶ ${idx + 1} / ${blocks.length}`;
      const r = b.getBoundingClientRect();
      if (r.top < 80 || r.bottom > innerHeight - 120) b.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    };
    const speakNext = (g) => {
      if (g !== gen || !speaking) return;
      if (sent >= sentences.length) {
        idx += 1; sent = 0;
        if (idx >= blocks.length) { stop(); return; }
        sentences = split(blocks[idx].textContent); mark();
      }
      const u = new SpeechSynthesisUtterance(sentences[sent]);
      const v = voices.find(x => x.voiceURI === $('.tts-voice').value);
      if (v) { u.voice = v; u.lang = v.lang; } else u.lang = lang;
      u.rate = +$('.tts-rate').value;
      const heading = /^H[234]$/.test(blocks[idx].tagName);
      u.onend = () => { if (g !== gen) return; sent += 1; setTimeout(() => speakNext(g), heading && sent >= sentences.length ? 350 : 0); };
      u.onend = ((orig) => () => { fails = 0; orig(); })(u.onend);
      u.onerror = (e) => {
        if (g !== gen || e.error === 'interrupted' || e.error === 'canceled') return;
        fails += 1;
        if (fails >= 3) { pause(); $('.tts-pos').textContent = 'NO VOICE'; $('.tts-hint').textContent = 'This device has no speech voice for this language. Add one in your system settings, or try another browser.'; return; }
        sent += 1; speakNext(g);
      };
      synth.speak(u);
    };
    const startAt = (i) => {
      gen += 1; synth.cancel();
      idx = Math.max(0, Math.min(blocks.length - 1, i)); sent = 0;
      sentences = split(blocks[idx].textContent);
      speaking = true;
      document.body.classList.add('tts-open');
      $('.tts-play').textContent = '❚❚'; $('.tts-play').setAttribute('aria-label', 'Pause');
      Radio.duck(true);
      mark();
      const g = gen;
      setTimeout(() => speakNext(g), 60);
    };
    const pause = () => { speaking = false; gen += 1; synth.cancel(); $('.tts-play').textContent = '▶'; $('.tts-play').setAttribute('aria-label', 'Resume'); Radio.duck(false); };
    const resume = () => { speaking = true; Radio.duck(true); $('.tts-play').textContent = '❚❚'; $('.tts-play').setAttribute('aria-label', 'Pause'); const g = ++gen; speakNext(g); };
    const stop = () => { pause(); document.body.classList.remove('tts-open'); blocks.forEach(b => b.classList.remove('tts-cur')); };
    const firstVisible = () => { const k = blocks.findIndex(b => b.getBoundingClientRect().bottom > 90); return k < 0 ? 0 : k; };

    $('.tts-play').addEventListener('click', () => (speaking ? pause() : resume()));
    $('.tts-next').addEventListener('click', () => startAt(idx + 1));
    $('.tts-prev').addEventListener('click', () => startAt(sent > 0 ? idx : idx - 1));
    $('.tts-close').addEventListener('click', stop);
    $('.tts-rate').addEventListener('change', () => { pref.rate = +$('.tts-rate').value; store.set(KEY, pref); if (speaking) startAt(idx); });
    $('.tts-voice').addEventListener('change', () => { pref.voice[lang] = $('.tts-voice').value; store.set(KEY, pref); if (speaking) startAt(idx); });
    article.addEventListener('dblclick', e => {
      const b = e.target.closest('p, h2, h3, h4, blockquote, li, div.q');
      const k = blocks.indexOf(b);
      if (k >= 0) { window.getSelection && window.getSelection().removeAllRanges(); startAt(k); }
    });
    window.addEventListener('pagehide', () => synth.cancel());

    const act = document.querySelector('.rd-act');
    if (act) {
      const btn = el("button", { type: "button", class: (act.children[1] || act.children[0] || {}).className || "", 'data-tts-start': '' }, '<span class="tts-listen">▶ Listen</span>');
      btn.addEventListener('click', () => startAt(firstVisible()));
      act.insertBefore(btn, act.children[1] || null);
    }
    const mount = () => document.body.appendChild(bar);
    if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount);
    return { startAt, pause, resume, stop };
  })();

  window.TIAMedia = { Radio, TTS };
})();
