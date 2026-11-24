/* ALL POWER — SIM-05. The screen: an Oppie's America household terminal, Council District 12, Berkeley, 1985.
   Rules live in allpower-model.js. Progress is kept in this browser (localStorage). */
(() => {
  'use strict';
  const M = window.AllPower;
  const G = window.TIAGame || { tone() {}, store: { get: (k, d) => d, set() {} } };
  const root = document.getElementById('game');
  if (!M || !root) return;
  const KEY = 'tia-allpower-v1';

  // ------------------------------------------------------------------ numbers
  const SUPS = { '-': '⁻', 0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴', 5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹' };
  const sup = n => String(n).split('').map(c => SUPS[c] || c).join('');
  const PRE = ['k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y', 'R', 'Q'];
  const trim = x => (x < 10 ? x.toFixed(2) : x < 100 ? x.toFixed(1) : String(Math.round(x)));
  function sci(x, unit) { const e = Math.floor(Math.log10(x)); return `${(x / Math.pow(10, e)).toFixed(2)}×10${sup(e)}${unit ? ' ' + unit : ''}`; }
  function si(x, unit) {
    if (!isFinite(x)) return '∞';
    if (x < 0) return '−' + si(-x, unit);
    if (x < 1000) return `${x < 10 && x % 1 ? x.toFixed(1) : Math.round(x)} ${unit}`;
    let v = x, i = -1;
    while (v >= 1000 && i < PRE.length - 1) { v /= 1000; i++; }
    if (v >= 1000) return sci(x, unit);
    return `${trim(v)} ${PRE[i]}${unit}`;
  }
  const W = x => si(x, 'W');
  const WH = x => si(x, 'Wh');
  const WORDS = [[1e15, 'quadrillion'], [1e12, 'trillion'], [1e9, 'billion'], [1e6, 'million']];
  function num(x) {
    if (!isFinite(x)) return '∞';
    if (x < 1e6) return Math.floor(x).toLocaleString('en-US');
    if (x >= 1e18) return sci(x, '');
    for (const [v, w] of WORDS) if (x >= v) return `${trim(x / v)} ${w}`;
    return String(x);
  }
  const pct = x => (x >= 0.9995 ? '100' : x >= 0.1 ? (x * 100).toFixed(1) : (x * 100).toFixed(2)) + '%';
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const clock = t => { t = Math.floor(t); const h = Math.floor(t / 3600), m = Math.floor(t / 60) % 60, s = t % 60; return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(s).padStart(2, '0'); };

  // ------------------------------------------------------------------ state
  function load() {
    const fresh = M.newState();
    const saved = G.store.get(KEY, null);
    if (!saved || saved.v !== 1) return { s: fresh, isNew: true };
    const merge = (a, b) => { for (const k in b) { if (b[k] && typeof b[k] === 'object' && !Array.isArray(b[k]) && a[k] && typeof a[k] === 'object') merge(a[k], b[k]); else a[k] = b[k]; } return a; };
    return { s: merge(fresh, saved), isNew: false };
  }
  let { s, isNew } = load();
  const save = () => G.store.set(KEY, s);
  const hist = [];

  // ------------------------------------------------------------------ layout
  const STAGES = { 1: 'DISTRICT', 2: 'CONTINENT', 3: 'THE SUN', 4: 'THE GALAXY', 5: 'THE UNIVERSE' };
  const NEWS = [
    'CHILDCARE OPEN ON ELM ST.', 'LINE 4 RUNS EVERY 3 MIN TODAY', 'RENT ABOLISHED SINCE 1951', 'BLOCK ELECTIONS DEC 12',
    'SPARE TOMATOES ON THE PORCH AT NO. 14', 'CHAIR OPPENHEIMER ADDRESSES THE COUNCIL AT 8PM', 'THE 52ND YEAR OF THE GRID',
    'LIBRARY OPEN LATE THURSDAY', 'ALLOTMENT REVIEW DEC 01', 'TRANSIT FREE ON ALL LINES',
  ];
  const PRICES = 'BREAD 0.4 kWh · COFFEE 0.2 kWh · TRANSIT FREE · RENT ABOLISHED · CLINIC FREE · CHILDCARE FREE · RADIO SET 1.8 kWh · BICYCLE 9 kWh · CAR 410 kWh · ';
  root.innerHTML = `
  <div class="ap-screen" id="ap">
    <div class="ap-bg" aria-hidden="true"><video id="ap-globe" src="/assets/globe_paper.mp4" poster="/assets/globe_paper.jpg" muted loop playsinline preload="auto"></video></div>
    <svg class="ap-frame" id="ap-frame" aria-hidden="true" preserveAspectRatio="none"><path id="ap-frame-p" d="" /><path id="ap-frame-q" d="" /></svg>
    <div class="ap-tick"><span class="lab">COUNCIL ▸</span><div class="mq"><div class="mq-in" id="ap-news"></div></div></div>
    <div class="ap-head">
      <div class="ap-title">
        <div class="k">HOME TERMINAL // COUNCIL DISTRICT 12 · BERKELEY · NOV 1985</div>
        <h1>ALL POWER</h1>
        <div class="k2">SIM-05 · COLLECT SUNLIGHT. THEN ALL OF IT. · 1 SECOND = 1 HOUR OF GRID TIME</div>
      </div>
      <div class="ap-reads">
        <div class="rd"><span>STORED</span><b id="r-e">0 Wh</b></div>
        <div class="rd"><span>OUTPUT</span><b id="r-p">0 W</b></div>
        <div class="rd"><span>COLLECTED, ALL TIME</span><b id="r-t">0 Wh</b></div>
        <div class="rd"><span>STAGE</span><b id="r-st">1 · DISTRICT</b></div>
      </div>
    </div>
    <div class="ap-grid">
      <div class="col" id="col1"></div>
      <div class="col" id="col2"></div>
      <div class="col" id="col3"></div>
    </div>
    <div class="ap-tick bot"><span class="lab">ACCOUNT ▸</span><div class="mq"><div class="mq-in slow">${esc(PRICES).repeat(3)}</div></div></div>
    <div class="ap-over" id="ap-over" hidden></div>
  </div>`;
  const $ = id => document.getElementById(id);
  const col1 = $('col1'), col2 = $('col2'), col3 = $('col3');
  const panel = (id, title, extra = '') => `<section class="pn" id="${id}"><h2><span>${title}</span><i aria-hidden="true"></i>${extra}</h2><div class="bd"></div></section>`;

  // ------------------------------------------------------------------ panels
  let built = 0;
  function build() {
    built = s.stage + (s.bureau ? 10 : 0);
    let c1 = '';
    if (s.stage <= 2) c1 += panel('pn-col', 'COLLECTION') + panel('pn-si', 'SILICON');
    if (s.stage >= 3) c1 += panel('pn-sw', 'THE SWARM // SOL');
    if (s.stage >= 4) c1 += panel('pn-pr', s.stage === 4 ? 'PROBES // MILKY WAY' : 'PROBES // THE VOIDS');
    col1.innerHTML = c1;
    col2.innerHTML = panel('pn-proj', 'COUNCIL PROJECTS') + panel('pn-log', 'MESSAGES');
    col3.innerHTML = panel('pn-al', s.stage <= 2 ? 'ALLOTMENT // DISTRICT 12' : 'ALLOTMENT') + (s.bureau ? panel('pn-pb', 'PLANNING BUREAU') : '') +
      panel('pn-ks', 'KARDASHEV SCALE') + panel('pn-out', 'OUTPUT // LOG SCALE');
    if (s.stage <= 2) buildCollect();
    if (s.stage >= 3) buildSwarm();
    if (s.stage >= 4) buildProbes();
    buildAllot(); if (s.bureau) buildBureau(); buildKs(); buildOut();
    lastProj = null; renderProjects(); renderLog(true);
  }
  const bd = id => document.querySelector(`#${id} .bd`);

  function buildCollect() {
    bd('pn-col').innerHTML = `
      <button type="button" class="big" id="b-collect"><span>COLLECT SUNLIGHT</span><small id="b-collect-v">+250 Wh</small></button>
      <div class="rows" id="prod-rows">${M.PRODUCERS.map(pr => `
        <div class="row" data-p="${pr.id}">
          <div class="nm"><b>${pr.name}</b><small>${W(pr.w)} each · ${esc(pr.blurb)}</small></div>
          <div class="ct"><b class="n">0</b><small class="o">0 W</small></div>
          <button type="button" class="buy" data-buy="${pr.id}"><span class="c">—</span><small class="si">—</small></button>
        </div>`).join('')}</div>`;
    bd('pn-si').innerHTML = `
      <div class="kv"><span>STOCK</span><b id="si-s">0</b></div>
      <div class="kv"><span>PRICE PER UNIT</span><b id="si-p">1 Wh</b></div>
      <button type="button" class="btn" id="b-si">REFINE <span id="si-b">1,000</span> UNITS · <span id="si-c">1 kWh</span></button>
      <p class="note" id="si-auto"></p>`;
    $('b-collect').addEventListener('click', () => { const g = M.collect(s); if (g) G.tone({ f: 660, f2: 990, d: 0.06, v: 0.05, type: 'triangle' }); render(); });
    bd('pn-col').addEventListener('click', e => { const b = e.target.closest('[data-buy]'); if (b && M.buyProducer(s, b.dataset.buy)) { G.tone({ f: 440, f2: 660, d: 0.08, v: 0.06 }); render(); } });
    $('b-si').addEventListener('click', () => { if (M.buySilicon(s)) { G.tone({ f: 330, d: 0.06, v: 0.05 }); render(); } });
  }
  function buildSwarm() {
    bd('pn-sw').innerHTML = `
      <div class="kv"><span>LIGHT CAUGHT</span><b id="sw-f">0%</b></div>
      <div class="bar"><span id="sw-bar"></span></div>
      <div class="kv"><span>COLLECTORS IN ORBIT</span><b id="sw-c">0</b></div>
      <div class="kv"><span>MASS IN STORE</span><b id="sw-m">0 t</b></div>
      <div class="row"><div class="nm"><b>Mass driver</b><small id="sw-mdo">Throws lunar rock into orbit.</small></div><div class="ct"><b id="sw-md">0</b></div><button type="button" class="buy" id="b-md"><span class="c">—</span></button></div>
      <div class="row" id="sw-forow"><div class="nm"><b>Orbital foundry</b><small id="sw-foo">Turns mass into collectors, 10 a second.</small></div><div class="ct"><b id="sw-fo">0</b></div><button type="button" class="buy" id="b-fo"><span class="c">—</span></button></div>
      <p class="note" id="sw-note"></p>`;
    $('b-md').addEventListener('click', () => { if (M.buyDriver(s)) { G.tone({ f: 300, f2: 500, d: 0.08, v: 0.06 }); render(); } });
    $('b-fo').addEventListener('click', () => { if (M.buyFoundry(s)) { G.tone({ f: 350, f2: 700, d: 0.08, v: 0.06 }); render(); } });
  }
  function buildProbes() {
    const five = s.stage === 5;
    bd('pn-pr').innerHTML = `
      <div class="kv"><span>${five ? 'GALAXIES TAKEN' : 'STARS TAKEN'}</span><b id="pr-x">0</b></div>
      <div class="bar"><span id="pr-bar"></span></div>
      <div class="kv"><span>PROBES ACTIVE</span><b id="pr-n">0</b></div>
      <div class="kv"><span>NET GROWTH</span><b id="pr-g">0%/s</b></div>
      ${five ? '<div class="kv"><span>WITHIN REACH</span><b id="pr-reach">6%</b></div>' : ''}
      <button type="button" class="btn" id="b-launch">LAUNCH A PROBE · <span id="pr-c">—</span></button>
      <div class="dir"><div class="kv"><span>DIRECTIVES</span><b id="pr-dp">0 FREE</b></div>
        ${['rep', 'cap', 'shield'].map(k => `<div class="dr" data-d="${k}"><span>${{ rep: 'REPLICATE', cap: five ? 'FIND GALAXIES' : 'FIND STARS', shield: 'HOLD TOGETHER' }[k]}</span><button type="button" data-dd="-1" aria-label="Fewer points on ${k}">−</button><b>0</b><button type="button" data-dd="1" aria-label="More points on ${k}">+</button></div>`).join('')}
        <p class="note">Replicate makes probes faster than they go quiet. Hold together cuts how many go quiet. Find ${five ? 'galaxies' : 'stars'} spends them on the job.</p></div>`;
    $('b-launch').addEventListener('click', () => { if (five ? M.launch2(s) : M.launch(s)) { G.tone({ f: 200, f2: 800, d: 0.2, v: 0.06 }); render(); } });
    bd('pn-pr').addEventListener('click', e => { const b = e.target.closest('[data-dd]'); if (!b) return; const k = b.closest('[data-d]').dataset.d; if (M.setDirective(s, k, +b.dataset.dd)) render(); });
  }
  function buildAllot() {
    if (s.stage > 2) {
      bd('pn-al').innerHTML = `<p class="big-note">Every household on Earth is fully served, and will be for as long as the Sun burns.</p><div class="kv"><span>APPROVAL</span><b class="up">100</b></div>`;
      return;
    }
    bd('pn-al').innerHTML = `
      <label class="sl"><span>SHARE OF OUTPUT TO HOUSEHOLDS</span><b id="al-a">40%</b>
        <input type="range" id="al-r" min="0" max="100" step="1" value="40" aria-label="Share of output delivered to households"></label>
      <div class="kv"><span>DELIVERED</span><b id="al-d">0 W</b></div>
      <div class="kv"><span>ALLOTMENT NEEDED</span><b id="al-n">250 kW</b></div>
      <div class="kv"><span>COVERAGE</span><b id="al-c">0%</b></div>
      <div class="bar"><span id="al-bar"></span></div>
      <div class="kv"><span>APPROVAL</span><b id="al-ap">0</b></div>
      <div class="bar ap"><span id="ap-bar"></span></div>
      <p class="note">What you don't deliver is stored and spent on building. The Council grants seats as households are served.</p>`;
    $('al-r').addEventListener('input', e => { M.setAllot(s, e.target.value / 100); render(); });
  }
  function buildBureau() {
    bd('pn-pb').innerHTML = `
      <div class="kv"><span>SEATS TO GIVE</span><b id="pb-f">0</b></div>
      <div class="two"><button type="button" class="btn" id="b-calc">+ CALCULATOR <b id="pb-c">0</b></button><button type="button" class="btn" id="b-arch">+ ARCHIVE <b id="pb-a">0</b></button></div>
      <div class="kv"><span>PLANS</span><b id="pb-o">0 / 0</b></div>
      <div class="bar ops"><span id="pb-bar"></span></div>
      <div class="kv"><span>PLANS PER SECOND</span><b id="pb-r">0</b></div>
      <div class="kv"><span>INSIGHT</span><b id="pb-i">0</b></div>
      <p class="note">Calculators write plans. Archives hold them. Insight only builds while the archive is full.</p>`;
    $('b-calc').addEventListener('click', () => { if (M.seat(s, 'calc')) render(); });
    $('b-arch').addEventListener('click', () => { if (M.seat(s, 'arch')) render(); });
  }
  const KS = [[2.5e5, 'DISTRICT 12'], [4.5e11, 'CONTINENT'], [1.7e17, 'TYPE I · EARTH'], [M.LSUN, 'TYPE II · THE SUN'], [M.LGAL, 'TYPE III · GALAXY'], [M.GALAXIES * M.LGAL, 'EVERYTHING']];
  function buildKs() {
    bd('pn-ks').innerHTML = `<div class="ks"><div class="ks-track"><span id="ks-fill"></span>${KS.map(([w, l], i) => `<i style="left:${(Math.log10(w) / 50 * 100).toFixed(2)}%" title="${l}"><em>${i + 1}</em></i>`).join('')}</div></div>
      <ol class="ks-leg">${KS.map(([w, l], i) => `<li data-ks="${i}"><span>${i + 1} · ${l}</span><b>${W(w)}</b></li>`).join('')}</ol>`;
  }
  function buildOut() { bd('pn-out').innerHTML = `<svg viewBox="0 0 300 80" preserveAspectRatio="none" class="spark" aria-hidden="true"><polyline id="out-l" points="" /></svg><div class="kv"><span>PEAK THIS SESSION</span><b id="out-pk">0 W</b></div>`; }

  // ------------------------------------------------------------------ projects + log
  let lastProj = null;
  function costLine(c) {
    const parts = [];
    if (c.ops) parts.push(`${num(c.ops)} PLANS`);
    if (c.ins) parts.push(`${num(c.ins)} INSIGHT`);
    if (c.E) parts.push(WH(c.E));
    return parts.join(' · ') || 'FREE';
  }
  function renderProjects() {
    const vis = s.bureau ? M.visibleProjects(s) : [];
    const key = vis.map(p => p.id).join(',');
    const box = bd('pn-proj');
    if (key !== lastProj) {
      lastProj = key;
      box.innerHTML = !s.bureau ? '<p class="note">The Council will open a planning bureau once the district has seen what you can collect.</p>'
        : vis.length ? vis.map(p => `<button type="button" class="pj" data-pj="${p.id}"><b>${esc(p.name)}</b><span>${esc(p.desc)}</span><small>${costLine(p.cost)}</small></button>`).join('')
          : '<p class="note">Nothing on the table. Keep collecting.</p>';
    }
    box.querySelectorAll('[data-pj]').forEach(b => { b.disabled = !M.canAfford(s, M.BYID[b.dataset.pj].cost); });
  }
  let logLen = -1;
  function renderLog(force) {
    const L = s.log || [];
    if (!force && L.length === logLen && (L[L.length - 1] || {}).t === renderLog.lastT) return;
    logLen = L.length; renderLog.lastT = (L[L.length - 1] || {}).t;
    bd('pn-log').innerHTML = L.length ? `<ol class="log" aria-live="polite">${L.slice(-7).reverse().map(m => `<li><time>${clock(m.t)}</time>${esc(m.text)}</li>`).join('')}</ol>` : '<p class="note">Good morning, steward. Spare tomatoes on the porch at No. 14.</p>';
    const news = $('ap-news');
    const items = L.slice(-4).map(m => m.text.toUpperCase()).concat(NEWS);
    news.textContent = items.join('  ///  ') + '  ///  ';
  }

  // ------------------------------------------------------------------ render
  function set(id, v) { const e = $(id); if (e && e.textContent !== v) e.textContent = v; }
  function width(id, f) { const e = $(id); if (e) e.style.width = Math.max(0, Math.min(100, f * 100)).toFixed(2) + '%'; }
  function render() {
    if (built !== s.stage + (s.bureau ? 10 : 0)) build();
    const P = M.power(s);
    set('r-e', WH(s.E)); set('r-p', W(P)); set('r-t', WH(s.T)); set('r-st', `${s.stage} · ${STAGES[s.stage]}`);
    if (s.stage <= 2) {
      set('b-collect-v', `+${WH(250 * s.clickMult)}`);
      for (const pr of M.PRODUCERS) {
        const row = document.querySelector(`#prod-rows [data-p="${pr.id}"]`); if (!row) continue;
        const on = M.unlocked(s, pr); row.hidden = !on; if (!on) continue;
        const c = M.prodCost(s, pr), si = M.prodSi(s, pr);
        row.querySelector('.n').textContent = num(s.n[pr.id]);
        row.querySelector('.o').textContent = W(s.n[pr.id] * pr.w * s.mult);
        row.querySelector('.c').textContent = WH(c);
        row.querySelector('.si').textContent = `${num(si)} SILICON`;
        const b = row.querySelector('.buy'); b.disabled = s.E < c || s.S < si;
        b.classList.toggle('short-si', s.E >= c && s.S < si);
      }
      set('si-s', num(s.S)); set('si-p', `${s.siPrice.toFixed(2)} Wh`);
      const u = M.siBatch(s); set('si-b', num(u)); set('si-c', WH(M.siCost(s, u)));
      $('b-si').disabled = s.E < M.siCost(s, u);
      set('si-auto', s.autoSi ? 'The silicon works refine more whenever stock runs low.' : 'Panels need silicon. Refine it when the price is low.');
      const D = M.demand(s);
      set('al-a', Math.round(s.a * 100) + '%'); const r = $('al-r'); if (r && document.activeElement !== r) r.value = Math.round(s.a * 100);
      set('al-d', W(s.delivered)); set('al-n', W(D)); set('al-c', pct(Math.min(1, s.cov)) + (s.cov > 1 ? ` (×${s.cov.toFixed(s.cov < 10 ? 1 : 0)})` : ''));
      width('al-bar', Math.min(1, s.cov)); set('al-ap', String(Math.round(s.A))); width('ap-bar', s.A / 100);
      const ap = $('al-ap'); if (ap) ap.className = s.A >= 60 ? 'up' : s.A < 30 ? 'dn' : '';
    }
    if (s.stage >= 3) {
      const f = M.swarmF(s);
      set('sw-f', pct(f)); width('sw-bar', f); set('sw-c', num(s.C)); set('sw-m', num(s.M / 1000) + ' t');
      set('sw-md', num(s.md)); set('sw-fo', num(s.fo));
      const mc = M.mdCost(s), fc = M.foCost(s);
      $('b-md').querySelector('.c').textContent = WH(mc); $('b-md').disabled = s.E < mc;
      $('sw-forow').hidden = !s.flags.foundry || s.stage >= 4;
      $('b-md').closest('.row').hidden = s.stage >= 4;
      $('b-fo').querySelector('.c').textContent = WH(fc); $('b-fo').disabled = s.E < fc;
      set('sw-mdo', `${num(2e6 * s.massMult)} t of rock a second each.`);
      set('sw-foo', s.foRep ? 'Builds collectors, and more foundries.' : 'Turns mass into collectors, 10 a second.');
      set('sw-note', s.stage >= 4 ? 'The Sun is enclosed. The swarm runs itself now.' : !s.flags.foundry ? 'Mass drivers first. The Council will approve orbital foundries once three are running.' : f >= 0.999 ? 'The Sun is enclosed.' : 'Each collector needs 100,000 t of rock.');
    }
    if (s.stage >= 4) {
      const five = s.stage === 5;
      const x = five ? s.G : s.Sx, tot = five ? M.GALAXIES : M.STARS;
      set('pr-x', `${num(x)} / ${num(tot)}`); width('pr-bar', x / tot);
      set('pr-n', num(five ? s.N2 : s.N));
      const g = five ? M.netRep2(s) : M.netRep(s);
      set('pr-g', `${g >= 0 ? '+' : ''}${(g * 100).toFixed(1)}%/s`); const ge = $('pr-g'); if (ge) ge.className = g >= 0 ? 'up' : 'dn';
      if (five) set('pr-reach', pct(s.reach));
      const pc = five ? M.probe2Cost(s) : M.probeCost(s); set('pr-c', WH(pc)); $('b-launch').disabled = s.E < pc;
      const d = s.dir, used = d.rep + d.cap + d.shield;
      set('pr-dp', `${s.dp - used} FREE OF ${s.dp}`);
      document.querySelectorAll('#pn-pr [data-d]').forEach(row => { row.querySelector('b').textContent = d[row.dataset.d]; });
    }
    if (s.bureau) {
      set('pb-f', String(s.free)); set('pb-c', String(s.calc)); set('pb-a', String(s.arch));
      $('b-calc').disabled = $('b-arch').disabled = s.free < 1;
      const mo = M.maxOps(s); set('pb-o', `${num(s.ops)} / ${num(mo)}`); width('pb-bar', mo ? s.ops / mo : 0);
      set('pb-r', num(M.opsRate(s))); set('pb-i', s.ins < 100 ? s.ins.toFixed(1) : num(s.ins));
      $('pn-pb').classList.toggle('full', s.ops >= mo && mo > 0);
    }
    const lp = Math.log10(Math.max(1, P));
    width('ks-fill', lp / 50);
    document.querySelectorAll('#pn-ks [data-ks]').forEach(li => { const w = KS[+li.dataset.ks][0]; li.classList.toggle('ok', P >= w * 0.999); });
    const pk = hist.length ? Math.max(...hist) : 0; set('out-pk', W(Math.pow(10, pk)));
    renderProjects(); renderLog(false);
  }
  function plot() {
    const P = M.power(s); hist.push(Math.log10(Math.max(1, P))); if (hist.length > 120) hist.shift();
    const lo = Math.min(...hist), hi = Math.max(...hist, lo + 1);
    const pts = hist.map((v, i) => `${(i / 119 * 300).toFixed(1)},${(76 - (v - lo) / (hi - lo) * 70).toFixed(1)}`).join(' ');
    const l = $('out-l'); if (l) l.setAttribute('points', pts);
  }

  // ------------------------------------------------------------------ overlays
  const over = $('ap-over');
  function intro() {
    over.hidden = false;
    over.innerHTML = `<div class="card"><div class="k">FEED 05 · COUNCIL DISTRICT 12 · BERKELEY · NOV 25, 1985</div><h2>ALL POWER</h2>
      <p>The Council has made you the district's energy steward. Rent was abolished in 1951, wages and prices soon after. Everything is allotted in kilowatt-hours now, and every kilowatt-hour comes from the Sun.</p>
      <p>Collect sunlight. Give the households their share. Spend the rest on collecting more. Then keep going.</p>
      <div class="row"><button type="button" class="btn go" id="ap-go">START COLLECTING</button></div>
      <p class="small">Your progress is saved in this browser. One real second is one hour of grid time.</p></div>`;
    $('ap-go').addEventListener('click', () => { over.hidden = true; G.unlock && G.unlock(); $('b-collect') && $('b-collect').focus(); });
  }
  function ending() {
    over.hidden = false;
    over.innerHTML = `<div class="card end"><div class="k">THE 52ND YEAR OF THE GRID · COMPLETE</div><h2>ALL POWER</h2>
      <p>There is nothing left to collect. Every star in every galaxy you could reach is feeding the grid, and every household in it is served.</p>
      <div class="stat"><div>COLLECTED<b>${WH(s.T)}</b></div><div>OUTPUT<b>${W(M.power(s))}</b></div><div>TIME<b>${clock(s.ended)}</b></div><div>CLICKS<b>${num(s.clicks)}</b></div></div>
      <p class="q">“The government of persons is replaced by the administration of things, and by the conduct of processes of production.” — Engels, <i>Socialism: Utopian and Scientific</i></p>
      <div class="row"><button type="button" class="btn go" id="ap-again">START AGAIN</button><a class="btn" href="/arcade/">BACK TO THE ARCADE</a></div></div>`;
    $('ap-again').addEventListener('click', reset);
  }
  function reset() {
    s = M.newState(); hist.length = 0; save(); built = 0; logLen = -1; render(); intro();
  }

  col2.addEventListener('click', e => {
    const b = e.target.closest('[data-pj]');
    if (b && !b.disabled && M.buyProject(s, b.dataset.pj)) { G.tone({ f: 520, f2: 1040, d: 0.12, v: 0.06, type: 'triangle' }); lastProj = null; render(); save(); }
  });

  // reset link in the page footer area
  const tools = document.createElement('div');
  tools.className = 'ap-tools';
  tools.innerHTML = `<span id="ap-saved">SAVED IN THIS BROWSER</span><button type="button" id="ap-reset">START OVER</button>`;
  root.appendChild(tools);
  let armed = 0;
  $('ap-reset').addEventListener('click', e => {
    if (Date.now() - armed < 3000) { reset(); e.target.textContent = 'START OVER'; return; }
    armed = Date.now(); e.target.textContent = 'TAP AGAIN TO WIPE YOUR PROGRESS';
    setTimeout(() => { if (Date.now() - armed >= 3000) e.target.textContent = 'START OVER'; }, 3100);
  });

  // ------------------------------------------------------------------ the tube: bowed edges like the household terminal
  const scr = $('ap');
  function tube() {
    const w = scr.offsetWidth, h = scr.offsetHeight;
    if (!w || !h) return;
    const wide = w > 900, b = wide ? 16 : 6, r = wide ? 46 : 20;
    const path = (b, r, i = 0) => {
      const L = i, T = i, R = w - i, B = h - i;
      return `M ${L + r} ${T + b} Q ${w / 2} ${T - b} ${R - r} ${T + b} Q ${R - b} ${T + b} ${R - b} ${T + r} Q ${R + b} ${h / 2} ${R - b} ${B - r} Q ${R - b} ${B - b} ${R - r} ${B - b} Q ${w / 2} ${B + b} ${L + r} ${B - b} Q ${L + b} ${B - b} ${L + b} ${B - r} Q ${L - b} ${h / 2} ${L + b} ${T + r} Q ${L + b} ${T + b} ${L + r} ${T + b} Z`;
    };
    const d = path(b, r);
    scr.style.clipPath = `path('${d}')`;
    const f = $('ap-frame');
    f.setAttribute('viewBox', `0 0 ${w} ${h}`);
    $('ap-frame-p').setAttribute('d', d);
    $('ap-frame-q').setAttribute('d', path(b, r, wide ? 7 : 4));
  }
  if ('ResizeObserver' in window) new ResizeObserver(tube).observe(scr); else window.addEventListener('resize', tube);
  tube();
  const globe = $('ap-globe');
  if (!G.reduced) { const go = () => globe.play().catch(() => {}); go(); document.addEventListener('pointerdown', go, { once: true }); }

  // ------------------------------------------------------------------ run
  document.addEventListener('keydown', e => {
    if (e.target.closest && e.target.closest('input, select, textarea')) return;
    if ((e.key === 'c' || e.key === 'C') && s.stage <= 2 && over.hidden) { M.collect(s); render(); }
  });
  build(); render();
  if (s.ended) ending(); else if (isNew) intro();
  let last = performance.now(), acc = 0, lastSave = 0, lastPlot = 0;
  setInterval(() => {
    const now = performance.now();
    const dt = Math.min(1, (now - last) / 1000); last = now;
    if (!s.ended && over.hidden) {
      // integrate in small steps so fast growth stays smooth
      acc += dt; while (acc >= 0.05) { M.step(s, 0.05); acc -= 0.05; }
    }
    if (s.ended && over.hidden) { save(); ending(); }
    if (now - lastPlot > 1000) { lastPlot = now; plot(); }
    render();
    if (now - lastSave > 5000) { lastSave = now; save(); }
  }, 100);
  window.addEventListener('pagehide', save);
  document.addEventListener('visibilitychange', () => { if (document.hidden) save(); });
})();
