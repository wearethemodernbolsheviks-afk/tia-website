/* Shared helpers for the TIA Arcade games: sound switch, a tiny synth for effects, music, best scores. */
(() => {
  'use strict';
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } },
  };
  let on = store.get('tia-game-sound', true);
  let ac = null;
  let master = null;
  const listeners = [];
  const ctx = () => {
    if (!ac && (window.AudioContext || window.webkitAudioContext)) {
      ac = new (window.AudioContext || window.webkitAudioContext)();
      master = ac.createGain();
      master.gain.value = on ? 0.5 : 0;
      master.connect(ac.destination);
    }
    if (ac && ac.state === 'suspended') ac.resume();
    return ac;
  };
  const music = new Audio();
  music.loop = true;
  music.volume = 0.45;
  let musicWanted = false;

  const btn = document.getElementById('g-sound');
  const paint = () => { if (btn) { btn.textContent = on ? 'SOUND ON' : 'SOUND OFF'; btn.setAttribute('aria-pressed', on); } };
  const set = (v) => {
    on = v; store.set('tia-game-sound', on); paint();
    if (master) master.gain.value = on ? 0.5 : 0;
    if (!on) music.pause(); else if (musicWanted) music.play().catch(() => {});
    listeners.forEach(f => f(on));
  };
  if (btn) btn.addEventListener('click', () => { ctx(); set(!on); });
  paint();

  const tone = (o) => {
    const a = ctx(); if (!a || !on) return;
    const t = a.currentTime + (o.delay || 0);
    const osc = a.createOscillator();
    const g = a.createGain();
    osc.type = o.type || 'square';
    osc.frequency.setValueAtTime(o.f || 440, t);
    if (o.f2) osc.frequency.exponentialRampToValueAtTime(Math.max(20, o.f2), t + (o.d || 0.1));
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(o.v || 0.15, t + 0.005);
    g.gain.exponentialRampToValueAtTime(0.0001, t + (o.d || 0.1));
    osc.connect(g); g.connect(master);
    osc.start(t); osc.stop(t + (o.d || 0.1) + 0.02);
  };
  const noise = (o) => {
    const a = ctx(); if (!a || !on) return;
    const d = o.d || 0.3;
    const buf = a.createBuffer(1, Math.floor(a.sampleRate * d), a.sampleRate);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < ch.length; i++) ch[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / ch.length, o.curve || 2);
    const src = a.createBufferSource(); src.buffer = buf;
    const f = a.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = o.cut || 1800;
    const g = a.createGain(); g.gain.value = o.v || 0.3;
    src.connect(f); f.connect(g); g.connect(master);
    src.start(a.currentTime + (o.delay || 0));
  };
  const NOTES = { C: 261.63, D: 293.66, E: 329.63, F: 349.23, G: 392.0, A: 440.0, B: 493.88 };

  window.TIAGame = {
    store,
    get sound() { return on; },
    onSound(f) { listeners.push(f); },
    unlock() { ctx(); },
    tone, noise, NOTES,
    music(src) {
      musicWanted = true;
      if (music.src.indexOf(src) < 0) music.src = src;
      const R = window.TIAMedia && window.TIAMedia.Radio;
      if (R && R.playing) R.pause();
      if (on) music.play().catch(() => {});
    },
    stopMusic() { musicWanted = false; music.pause(); },
    best(key, score) {
      const k = 'tia-best-' + key;
      const b = store.get(k, 0);
      if (score !== undefined && score > b) { store.set(k, score); return { best: score, isNew: true }; }
      return { best: b, isNew: false };
    },
    reduced: matchMedia('(prefers-reduced-motion: reduce)').matches,
  };
})();
