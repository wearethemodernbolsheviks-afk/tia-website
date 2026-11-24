/* PLAN/1 — run an economy with no money. Six sectors, each eating the others' output.
   The model is a small input-output table (after Leontief): every unit a sector makes uses
   up fixed amounts of other goods, and households need grain, homes, power and care. */
(() => {
  'use strict';
  const SECT = [
    { id: 'STEEL', a: 2.2, color: '#E8222A' },
    { id: 'POWER', a: 2.6, color: '#F2B33D' },
    { id: 'GRAIN', a: 2.9, color: '#39D98A' },
    { id: 'HOMES', a: 1.8, color: '#E8222A' },
    { id: 'RAIL', a: 2.3, color: '#F2ECE4' },
    { id: 'LABOUR', a: 2.1, color: '#39D98A', label: 'CARE' },
  ];
  // NEED[i] = { j: units of good j used per unit of good i }
  const NEED = [
    { 1: 0.35, 4: 0.15 },
    { 0: 0.08, 4: 0.25 },
    { 1: 0.10, 4: 0.20, 0: 0.05 },
    { 0: 0.40, 1: 0.10, 4: 0.10 },
    { 0: 0.30, 1: 0.25 },
    { 2: 0.15, 3: 0.05, 1: 0.05 },
  ];
  const HOUSE = [0, 0.20, 0.55, 0.20, 0, 0.25]; // per worker per week
  const CAP = 240, WEEKS = 260, START_ALLOC = [12, 9, 14, 8, 3, 6];
  const EVENTS = [
    { t: 'DROUGHT IN THE SOUTH · GRAIN −40% FOR 8 WEEKS', s: 2, m: 0.6, d: 8 },
    { t: 'MINE FLOODED · STEEL −50% FOR 6 WEEKS', s: 0, m: 0.5, d: 6 },
    { t: 'BRIDGE DOWN AT THE RIVER · RAIL −45% FOR 6 WEEKS', s: 4, m: 0.55, d: 6 },
    { t: 'TURBINE HALL FIRE · POWER −35% FOR 5 WEEKS', s: 1, m: 0.65, d: 5 },
    { t: 'NEW TRACTORS ARRIVE · GRAIN +30% FOR 10 WEEKS', s: 2, m: 1.3, d: 10 },
    { t: 'NEW BLAST FURNACE LIT · STEEL +25% FOR 10 WEEKS', s: 0, m: 1.25, d: 10 },
    { t: 'FAMILIES ARRIVE FROM THE COUNTRYSIDE · +4 WORKERS', arrive: 4 },
    { t: 'FLU IN THE CITY · CARE −40% FOR 6 WEEKS', s: 5, m: 0.6, d: 6 },
  ];

  function Model(seed) {
    let r = seed || (Date.now() % 100000);
    const rnd = () => { r = (r * 16807) % 2147483647; return (r - 1) / 2147483646; };
    const m = {
      week: 0, stock: [70, 70, 110, 70, 80, 70], alloc: START_ALLOC.slice(), workers: 52, growth: 0,
      mods: [1, 1, 1, 1, 1, 1], modT: [0, 0, 0, 0, 0, 0], flow: [0, 0, 0, 0, 0, 0], out: [0, 0, 0, 0, 0, 0],
      zeroRun: [0, 0, 0, 0, 0, 0], shortWeeks: 0, produced: 0, wasted: 0, hist: SECT.map(() => []), event: null,
      nextEvent: 18 + Math.floor(rnd() * 10), over: null, peakWorkers: 52,
    };
    m.free = () => m.workers - m.alloc.reduce((a, b) => a + b, 0);
    m.season = () => { const w = (m.week + 9) % 52; return w < 9 || w >= 48 ? 'WINTER' : w < 22 ? 'SPRING' : w < 35 ? 'SUMMER' : 'AUTUMN'; };
    const seasonal = (i) => {
      const s = m.season();
      if (i === 2) return { WINTER: 0.55, SPRING: 0.95, SUMMER: 1.15, AUTUMN: 1.45 }[s];
      return 1;
    };
    const houseNeed = (j) => {
      let n = HOUSE[j] * m.workers;
      if (j === 1 && m.season() === 'WINTER') n *= 1.7;
      return n;
    };
    m.step = () => {
      if (m.over) return;
      // planned output, before checking inputs
      const plan = SECT.map((s, i) => s.a * m.alloc[i] * m.mods[i] * seasonal(i));
      // households take their share first: people before machines
      const avail = m.stock.slice();
      const hh = SECT.map((s, j) => Math.min(avail[j], houseNeed(j)));
      const hhShort = SECT.map((s, j) => houseNeed(j) - hh[j] > 0.01);
      hh.forEach((v, j) => { avail[j] -= v; });
      // inputs for production: scale every sector by its scarcest input
      const want = [0, 0, 0, 0, 0, 0];
      plan.forEach((q, i) => { for (const j in NEED[i]) want[j] += q * NEED[i][j]; });
      const ratio = want.map((w, j) => (w <= 0 ? 1 : Math.min(1, avail[j] / w)));
      const out = plan.map((q, i) => { let e = 1; for (const j in NEED[i]) e = Math.min(e, ratio[j]); return q * e; });
      const used = [0, 0, 0, 0, 0, 0];
      out.forEach((q, i) => { for (const j in NEED[i]) used[j] += q * NEED[i][j]; });
      const before = m.stock.slice();
      m.stock = m.stock.map((s, j) => {
        let v = s - hh[j] - used[j] + out[j];
        if (v > CAP) { m.wasted += v - CAP; v = CAP; }
        return Math.max(0, v);
      });
      m.flow = m.stock.map((s, j) => s - before[j]);
      m.out = out;
      m.produced += out.reduce((a, b) => a + b, 0);
      // workers trained by the care sector
      m.growth += out[5] * 0.012;
      while (m.growth >= 1) { m.growth -= 1; m.workers += 1; m.newWorker = 6; }
      m.peakWorkers = Math.max(m.peakWorkers, m.workers);
      // shortages
      let anyShort = false;
      m.stock.forEach((s, j) => {
        const short = s < 0.5 || (hhShort[j] && HOUSE[j] > 0);
        m.zeroRun[j] = short ? m.zeroRun[j] + 1 : 0;
        if (short) anyShort = true;
      });
      if (anyShort) m.shortWeeks += 1;
      // events
      m.mods = m.mods.map((v, i) => { if (m.modT[i] > 0) { m.modT[i] -= 1; return m.modT[i] === 0 ? 1 : v; } return v; });
      if (m.event && m.event.left > 0) { m.event.left -= 1; if (m.event.left <= 0) m.event = null; }
      if (m.week >= m.nextEvent) {
        const e = EVENTS[Math.floor(rnd() * EVENTS.length)];
        if (e.arrive) { m.workers += e.arrive; m.event = { t: e.t, left: 4, good: true }; }
        else { m.mods[e.s] = e.m; m.modT[e.s] = e.d; m.event = { t: e.t, left: e.d, good: e.m > 1 }; }
        m.nextEvent = m.week + 16 + Math.floor(rnd() * 14);
      }
      m.stock.forEach((s, j) => { m.hist[j].push(s); if (m.hist[j].length > 60) m.hist[j].shift(); });
      m.week += 1;
      // a stockpile empty for eight straight weeks breaks the plan
      const broke = m.zeroRun.findIndex(z => z >= 8);
      if (broke >= 0) m.over = { win: false, why: `${SECT[broke].label || SECT[broke].id} RAN OUT FOR EIGHT WEEKS` };
      else if (m.week >= WEEKS) m.over = { win: true };
    };
    m.score = () => Math.max(0, Math.round(m.produced + 40 * (m.workers - 52) - 25 * m.shortWeeks - 0.5 * m.wasted));
    return m;
  }

  if (typeof module !== 'undefined') { module.exports = { Model, SECT, NEED, HOUSE }; return; }

  /* ---------------------------------------------------------------- view */
  const G = window.TIAGame;
  const root = document.getElementById('game');
  root.innerHTML = `
    <div class="p1-bar">
      <span>YEAR <b data-k="year">1</b> / 5</span><span>WEEK <b data-k="week">1</b></span><span data-k="season">WINTER</span>
      <span>WORKERS <b data-k="workers">52</b></span><span>UNASSIGNED <b data-k="free">0</b></span>
      <span>SHORT WEEKS <b data-k="short">0</b></span><span>OUTPUT <b data-k="score">0</b></span>
      <span class="p1-sp"></span><button type="button" data-k="pause">❚❚ PAUSE</button>
    </div>
    <div class="p1-ev" data-k="event" aria-live="polite">THE PLAN BEGINS. KEEP EVERY STOCKPILE ABOVE ZERO FOR FIVE YEARS.</div>
    <div class="p1-grid"></div>
    <div class="g-over" data-k="over"></div>`;
  const $ = k => root.querySelector(`[data-k="${k}"]`);
  const grid = root.querySelector('.p1-grid');
  SECT.forEach((s, i) => {
    const needs = Object.keys(NEED[i]).map(j => SECT[j].label || SECT[j].id).join(' · ');
    const card = document.createElement('section');
    card.className = 'p1-s';
    card.innerHTML = `
      <header><span class="n">${i + 1}</span><h2>${s.label || s.id}</h2><span class="fl" data-f></span></header>
      <div class="lv"><div class="lvf" data-l></div><span class="lvn" data-n>60</span></div>
      <canvas width="240" height="44" data-c aria-hidden="true"></canvas>
      <p class="nd">${needs ? 'USES ' + needs : 'NO INPUTS'}</p>
      <div class="wk"><button type="button" data-m aria-label="Take a worker from ${s.label || s.id}">−</button><span><b data-w>0</b> WORKERS</span><button type="button" data-p aria-label="Add a worker to ${s.label || s.id}">+</button></div>`;
    grid.appendChild(card);
  });
  const cards = [...grid.children];

  let m = null, timer = null, paused = false, speed = 700;
  const intro = () => {
    const best = G.best('plan1').best;
    $('over').hidden = false;
    $('over').innerHTML = `<div class="g-card"><div class="k">SIM-01 · PLAN/1</div><h1>NO MONEY.<br>ONLY THE PLAN.</h1>
      <p>Six sectors feed each other. Steel needs power and rail. Rail needs steel and power. Homes need steel. Everyone eats grain, needs a home, heat in winter and care. Care trains new workers.</p>
      <p>Move workers between sectors. Keep every stockpile above zero for five years. A stockpile empty for eight weeks running ends the plan. When nobody is free, pressing + takes a worker from the sector with the most to spare.</p>
      <div class="q">Watch the rail. The plan you inherit has three people running it.</div>
      ${best ? `<p class="k" style="color:#A89C95">BEST OUTPUT ON THIS DEVICE · ${best}</p>` : ''}
      <div class="row"><button class="btn-g" type="button" data-start>▶ START THE PLAN</button></div></div>`;
    $('over').querySelector('[data-start]').addEventListener('click', start);
    $('over').querySelector('[data-start]').focus();
  };
  const start = () => {
    G.unlock();
    m = Model();
    paused = false;
    $('over').hidden = true;
    $('pause').textContent = '❚❚ PAUSE';
    clearInterval(timer);
    timer = setInterval(tick, speed);
    render();
    G.music('/assets/radio/plan-fulfilled.mp3');
  };
  const tick = () => {
    if (paused || !m) return;
    const wasEvent = m.event && m.event.t;
    m.step();
    if (m.event && m.event.t !== wasEvent) G.tone({ f: m.event.good ? 660 : 180, f2: m.event.good ? 990 : 120, d: 0.25, type: 'triangle', v: 0.12 });
    if (m.newWorker === 6) G.tone({ f: 880, d: 0.08, type: 'sine', v: 0.08 });
    render();
    if (m.over) end();
  };
  const spark = (cv, h, color) => {
    const g = cv.getContext('2d');
    g.clearRect(0, 0, cv.width, cv.height);
    g.strokeStyle = '#2A1A1C'; g.beginPath(); g.moveTo(0, cv.height - 1); g.lineTo(cv.width, cv.height - 1); g.stroke();
    if (h.length < 2) return;
    g.strokeStyle = color; g.lineWidth = 2; g.beginPath();
    h.forEach((v, k) => { const x = k / 59 * cv.width; const y = cv.height - 2 - (v / CAP) * (cv.height - 4); k ? g.lineTo(x, y) : g.moveTo(x, y); });
    g.stroke();
  };
  const render = () => {
    if (!m) return;
    $('year').textContent = Math.min(5, Math.floor(m.week / 52) + 1);
    $('week').textContent = (m.week % 52) + 1;
    $('season').textContent = m.season();
    $('workers').textContent = m.workers;
    $('free').textContent = m.free();
    $('free').parentElement.classList.toggle('hot', m.free() > 0);
    $('short').textContent = m.shortWeeks;
    $('score').textContent = m.score();
    if (m.event) { $('event').textContent = m.event.t; $('event').className = 'p1-ev ' + (m.event.good ? 'good' : 'bad'); }
    else if (m.newWorker > 0) { $('event').textContent = 'THE CARE SECTOR TRAINED A NEW WORKER · ASSIGN THEM'; $('event').className = 'p1-ev good'; m.newWorker -= 1; }
    else { $('event').textContent = `${m.season()} · ${m.season() === 'WINTER' ? 'HOMES BURN MORE POWER · GRAIN GROWS SLOWLY' : m.season() === 'AUTUMN' ? 'HARVEST · STORE GRAIN FOR THE WINTER' : 'KEEP EVERY STOCKPILE ABOVE ZERO'}`; $('event').className = 'p1-ev'; }
    cards.forEach((c, i) => {
      const s = m.stock[i];
      c.querySelector('[data-n]').textContent = Math.round(s);
      c.querySelector('[data-l]').style.width = (100 * s / CAP) + '%';
      const f = m.flow[i];
      const fl = c.querySelector('[data-f]');
      fl.textContent = (f >= 0 ? '+' : '−') + Math.abs(f).toFixed(1) + ' / WK';
      fl.className = 'fl ' + (f < -0.05 ? 'neg' : f > 0.05 ? 'pos' : '');
      c.querySelector('[data-w]').textContent = m.alloc[i];
      c.classList.toggle('low', s < 20);
      c.classList.toggle('zero', s < 0.5);
      c.classList.toggle('full', s >= CAP - 0.5);
      spark(c.querySelector('[data-c]'), m.hist[i], s < 20 ? '#FF5A60' : SECT[i].color);
    });
  };
  const move = (i, d) => {
    if (!m || m.over) return;
    if (d > 0 && m.free() <= 0) {
      // take a worker from the sector with the biggest surplus
      let best = -1, bf = -1e9;
      m.alloc.forEach((w, k) => { if (k !== i && w > 0 && m.stock[k] + m.flow[k] * 6 > bf) { bf = m.stock[k] + m.flow[k] * 6; best = k; } });
      if (best < 0) return;
      m.alloc[best] -= 1;
      flash(best, 'out');
    }
    if (d < 0 && m.alloc[i] <= 0) return;
    m.alloc[i] += d;
    G.tone({ f: d > 0 ? 520 : 340, d: 0.05, type: 'square', v: 0.05 });
    flash(i, d > 0 ? 'in' : 'out');
    render();
  };
  const flash = (i, cls) => { const c = cards[i]; c.classList.remove('in', 'out'); void c.offsetWidth; c.classList.add(cls); };
  cards.forEach((c, i) => {
    c.querySelector('[data-p]').addEventListener('click', () => move(i, 1));
    c.querySelector('[data-m]').addEventListener('click', () => move(i, -1));
  });
  const togglePause = () => { if (!m || m.over) return; paused = !paused; $('pause').textContent = paused ? '▶ RESUME' : '❚❚ PAUSE'; };
  $('pause').addEventListener('click', togglePause);
  document.addEventListener('keydown', e => {
    if (e.target.closest('input, textarea, select')) return;
    const k = e.code.match(/^Digit([1-6])$/) || e.code.match(/^Numpad([1-6])$/);
    if (k) { e.preventDefault(); move(+k[1] - 1, e.shiftKey ? -1 : 1); }
    if (e.code === 'Space' && m && !m.over) { e.preventDefault(); togglePause(); }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden && m && !m.over && !paused) togglePause(); });
  const end = () => {
    clearInterval(timer);
    const sc = m.score();
    const b = G.best('plan1', m.over.win ? sc : 0);
    const win = m.over.win;
    G.tone({ f: win ? 523 : 220, f2: win ? 1046 : 110, d: 0.6, type: 'triangle', v: 0.14 });
    $('over').hidden = false;
    $('over').innerHTML = `<div class="g-card"><div class="k">${win ? 'FIVE YEARS · PLAN FULFILLED' : 'WEEK ' + m.week + ' · PLAN BROKEN'}</div>
      <h2>${win ? 'PLAN FULFILLED' : 'SHORTAGE'}</h2>
      <p>${win ? 'Five years without money and without a breakdown. Every sector fed every other, and the people were fed first.' : m.over.why + '. The sectors that needed it stopped, and the shortage spread down the table.'}</p>
      <div class="stat"><div>OUTPUT<b>${sc}</b></div><div>WORKERS<b>${m.workers}</b></div><div>SHORT WEEKS<b>${m.shortWeeks}</b></div><div>WASTED<b>${Math.round(m.wasted)}</b></div></div>
      ${win && b.isNew ? '<p class="k">NEW BEST ON THIS DEVICE</p>' : b.best ? `<p class="k" style="color:#A89C95">BEST · ${b.best}</p>` : ''}
      <div class="q">“Within the co-operative society based on common ownership of the means of production, the producers do not exchange their products.” — Marx, Critique of the Gotha Programme</div>
      <div class="row"><button class="btn-g" type="button" data-again>▶ PLAN AGAIN</button><a class="btn-g gh" href="/arcade/">ALL GAMES</a></div></div>`;
    $('over').querySelector('[data-again]').addEventListener('click', start);
  };
  intro();
})();
