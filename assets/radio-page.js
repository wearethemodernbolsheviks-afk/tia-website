/* The TIA Radio station page: a big front end for the shared player in tia-media.js. */
(() => {
  'use strict';
  const root = document.querySelector('[data-radio-page]');
  if (!root) return;
  const popout = new URLSearchParams(location.search).get('popout') === '1';
  if (popout) document.body.classList.add('popout');
  const fmt = s => { s = Math.max(0, Math.floor(s || 0)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
  const q = s => root.querySelector(s);

  const start = () => {
    const R = window.TIAMedia && window.TIAMedia.Radio;
    if (!R) return setTimeout(start, 50);
    const audio = R.audio;
    const list = q('[data-rp-list]');
    const vol = q('[data-rp-vol]');
    const shuf = q('[data-rp-shuffle]');
    vol.value = R.state.vol;
    shuf.checked = !!R.state.shuffle;

    const render = () => {
      const tr = R.tracks[R.index];
      if (!tr) return;
      q('[data-rp-title]').textContent = tr.title;
      q('[data-rp-meta]').textContent = `${tr.artist.toUpperCase()} · ${tr.bpm} BPM`;
      q('[data-rp-pos]').textContent = `${R.index + 1} / ${R.tracks.length}`;
      q('[data-rp-dur]').textContent = fmt(audio.duration || tr.dur);
      const play = q('[data-rp="play"]');
      play.textContent = R.playing ? '❚❚ PAUSE' : '▶ PLAY';
      play.setAttribute('aria-label', R.playing ? 'Pause' : 'Play');
      list.querySelectorAll('li').forEach((li, k) => li.classList.toggle('cur', k === R.index));
      document.title = (R.playing ? '▶ ' : '') + tr.title + ' · TIA Radio';
    };
    const fill = () => {
      list.innerHTML = '';
      R.tracks.forEach((tr, k) => {
        const li = document.createElement('li');
        li.innerHTML = `<button type="button"><span class="n">${String(k + 1).padStart(2, '0')}</span><span>${tr.title}</span><span class="b">${tr.bpm} BPM</span><span>${fmt(tr.dur)}</span></button>`;
        li.querySelector('button').addEventListener('click', () => { R.load(k); });
        list.appendChild(li);
      });
      render();
    };
    if (R.ready) fill(); else document.addEventListener('tia-radio-ready', fill, { once: true });
    document.addEventListener('tia-radio', render);
    audio.addEventListener('timeupdate', () => {
      const d = audio.duration || 1;
      q('[data-rp-bar] span').style.width = (100 * audio.currentTime / d) + '%';
      q('[data-rp-cur]').textContent = fmt(audio.currentTime);
    });
    q('[data-rp="play"]').addEventListener('click', () => { R.toggle(); ensureViz(); });
    q('[data-rp="next"]').addEventListener('click', () => { R.next(); ensureViz(); });
    q('[data-rp="prev"]').addEventListener('click', () => { R.prev(); ensureViz(); });
    q('[data-rp="pop"]').addEventListener('click', () => {
      if (popout) return;
      R.pause();
      R.state.on = true;
      const w = window.open('/radio/?popout=1', 'tia-radio', 'width=420,height=680');
      if (!w) R.play();
    });
    if (popout) q('[data-rp="pop"]').hidden = true;
    vol.addEventListener('input', () => { R.state.vol = +vol.value; audio.volume = +vol.value; try { localStorage.setItem('tia-radio-v1', JSON.stringify(R.state)); } catch (e) { /* ignore */ } });
    shuf.addEventListener('change', () => { R.state.shuffle = shuf.checked; });
    q('[data-rp-bar]').addEventListener('click', e => {
      const r = e.currentTarget.getBoundingClientRect();
      if (audio.duration) audio.currentTime = (e.clientX - r.left) / r.width * audio.duration;
    });
    document.addEventListener('keydown', e => {
      if (e.target.closest('input, select, textarea')) return;
      if (e.code === 'Space') { e.preventDefault(); R.toggle(); ensureViz(); }
      if (e.key === 'ArrowRight' && e.shiftKey) R.next();
      if (e.key === 'ArrowLeft' && e.shiftKey) R.prev();
    });

    // visualiser: a real spectrum once the listener has pressed play, a slow sweep before that
    const cv = q('.rp-viz');
    const g = cv.getContext('2d');
    let analyser = null, data = null;
    function ensureViz() {
      if (analyser || !window.AudioContext) return;
      try {
        const ac = new AudioContext();
        const src = ac.createMediaElementSource(audio);
        analyser = ac.createAnalyser();
        analyser.fftSize = 256;
        src.connect(analyser);
        analyser.connect(ac.destination);
        data = new Uint8Array(analyser.frequencyBinCount);
        if (ac.state === 'suspended') ac.resume();
      } catch (e) { analyser = null; }
    }
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const draw = (t) => {
      const w = cv.width = cv.clientWidth * (window.devicePixelRatio || 1);
      const h = cv.height = cv.clientHeight * (window.devicePixelRatio || 1);
      g.clearRect(0, 0, w, h);
      g.strokeStyle = 'rgba(58,35,38,0.6)';
      g.lineWidth = 1;
      for (let x = 0; x < w; x += w / 16) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke(); }
      const n = 48;
      const bw = w / n;
      for (let i = 0; i < n; i++) {
        let v;
        if (analyser && R.playing) { analyser.getByteFrequencyData(data); v = data[Math.floor(i * data.length / n * 0.85)] / 255; }
        else v = R.playing ? 0.3 + 0.25 * Math.sin(t / 300 + i * 0.5) : 0.04 + 0.03 * Math.sin(t / 900 + i * 0.3);
        const bh = Math.max(2, v * h * 0.92);
        g.fillStyle = i % 8 === 0 ? '#FF5A60' : '#E8222A';
        g.fillRect(i * bw + 2, h - bh, bw - 4, bh);
      }
      if (!reduce) requestAnimationFrame(draw);
    };
    requestAnimationFrame(draw);
    const autoplay = () => { if (R.state.on) R.play(); };
    if (R.ready) setTimeout(autoplay, 200); else document.addEventListener('tia-radio-ready', () => setTimeout(autoplay, 200), { once: true });
  };
  start();
})();
