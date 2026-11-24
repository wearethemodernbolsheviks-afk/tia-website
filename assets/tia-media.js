/* TIA media: read-aloud for the archive texts.
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
.tts-bar { position: fixed; left: 50%; transform: translateX(-50%); bottom: 16px; z-index: 71; display: none; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: center; padding: 10px 12px; width: min(860px, calc(100vw - 32px)); background: rgba(12, 7, 8, 0.97); border: 1px solid #3A2326; box-shadow: 0 18px 50px rgba(0, 0, 0, 0.6); font: 12px/1 ${MONO}; letter-spacing: 0.1em; color: #A89C95; }
body.tts-open .tts-bar { display: flex; }
.tts-bar select { background: #0F0A0B; color: #F2ECE4; border: 1px solid #3A2326; height: 36px; font: 12px ${MONO}; max-width: 230px; }
.tts-bar .tts-pos { min-width: 92px; text-align: center; }
.tts-bar .tts-hint { flex-basis: 100%; text-align: center; color: #8A7B75; font-size: 11px; }
.text .tts-cur { background: rgba(232, 34, 42, 0.1); box-shadow: -14px 0 0 rgba(232, 34, 42, 0.1), 14px 0 0 rgba(232, 34, 42, 0.1), inset 3px 0 0 #E8222A; }
.tts-listen { display: inline-flex; align-items: center; gap: 8px; }
@media (max-width: 640px) {
  .tts-bar { bottom: 0; width: 100vw; border-left: 0; border-right: 0; }
  .tts-bar .tts-hint { display: none; }
}
`;
  document.head.appendChild(el('style', { id: 'tm-style' }, css));

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
      mark();
      const g = gen;
      setTimeout(() => speakNext(g), 60);
    };
    const pause = () => { speaking = false; gen += 1; synth.cancel(); $('.tts-play').textContent = '▶'; $('.tts-play').setAttribute('aria-label', 'Resume'); };
    const resume = () => { speaking = true; $('.tts-play').textContent = '❚❚'; $('.tts-play').setAttribute('aria-label', 'Pause'); const g = ++gen; speakNext(g); };
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

  window.TIAMedia = { TTS };
})();
