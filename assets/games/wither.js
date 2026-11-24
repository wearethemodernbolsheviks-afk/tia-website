/* WITHER — SIM-04. From Oppie's America 1985: chair the Union's planning committee from 1950 and
   make the state wither away before a committee that cannot die decides to live forever. */
(() => {
  'use strict';
  const G = window.TIAGame;
  const root = document.getElementById('game');
  const YEARS = [1950, 1953, 1956, 1959, 1962, 1965, 1968, 1971, 1974, 1977, 1980, 1983];
  const METERS = [
    { k: 'L', name: 'LEDGER', d: 'Can the plan see and move what people need? At zero, people go hungry.' },
    { k: 'C', name: 'COUNCILS', d: 'Can the workers run things themselves? This has to be high when the state goes.' },
    { k: 'K', name: 'COMMITTEE', d: 'The power of the state. Bring it down to nothing. At 100 it never leaves.' },
    { k: 'T', name: 'TRUST', d: 'Do the delegates and the people believe the Committee means to stop? At zero, the Union splits.' },
  ];
  const CARDS = [
    { id: 'publish', t: 'Publish the Ledger', q: 'Open the Continental Ledger to every council, minute by minute.', e: { C: 12, K: -10, L: -4, T: 4 } },
    { id: 'sunset', t: 'Sunset every ministry', q: 'Each ministry expires on a date unless the councils renew it.', e: { K: -13, L: -6, T: 2 } },
    { id: 'rotate', t: 'Rotate the chair', q: 'No delegate sits twice. Nobody gets used to the chair.', e: { K: -8, T: 6, C: 2 } },
    { id: 'recall', t: 'Recall at will', q: 'Any council may recall its delegate at any hour.', e: { C: 8, K: -8, T: 2 } },
    { id: 'energy', t: 'Energy accounting', q: 'Prices give way to certificates counted in joules.', e: { L: 8, C: 4, K: 2 } },
    { id: 'wage', t: 'Abolish the wage', q: 'Labour certificates first, then nothing at all.', e: { C: 10, L: -8, T: 4 }, need: { C: 30 } },
    { id: 'grain', t: 'Move the grain early', q: 'Stock it ahead of the rains, not after the failure.', e: { L: 10, T: 4, K: 4 } },
    { id: 'map', t: 'Expand the Map', q: 'More sensors, more minutes, more of the world on the Ledger.', e: { L: 12, K: 6 } },
    { id: 'emergency', t: 'Emergency powers', q: 'Just for this term. The Committee will hand them back.', e: { K: 12, L: 8, T: -4 } },
    { id: 'purchasing', t: 'Central purchasing', q: 'One office buys for the whole Union. It is very efficient.', e: { L: 6, K: 6 } },
    { id: 'grid', t: 'Hand the grid to the councils', q: 'The switches go back to the people who turned them in 1934.', e: { C: 12, K: -10, L: -6 }, need: { C: 30 } },
    { id: 'supply', t: 'Close the Ministry of Supply', q: 'Its clerks become delegates of the councils they served.', e: { K: -12, L: -7, C: 4 }, need: { L: 35 } },
    { id: 'sealed', t: 'Open the sealed room', q: 'Every Committee minute is printed the next morning.', e: { T: 8, K: -8 } },
    { id: 'texts', t: 'Teach the unabridged texts', q: 'State and Revolution, with the chapters the school editions cut.', e: { C: 6, T: 6 } },
    { id: 'clerks', t: 'Automate the clerks', q: 'The Ledger books itself. Fewer hands on the ledger.', e: { L: 8, K: -4, C: -2 } },
    { id: 'square', t: 'A council for every grid square', q: 'Self-administration down to the street.', e: { C: 14, L: -6, T: -2 }, need: { T: 30 } },
    { id: 'purge', t: 'Remove the cautious', q: 'The delegates who keep asking when the Committee will stop.', e: { K: 8, T: -10, C: -4 } },
    { id: 'delay', t: 'Delay the handover', q: 'The councils are not ready. One more term.', e: { L: 6, K: 8, T: -6 } },
    { id: 'errors', t: 'Publish the plan\'s errors', q: 'Every miscount, with the name of the office that made it.', e: { T: 8, L: 2, K: -4 } },
    { id: 'guard', t: 'Disband the Committee\'s guard', q: 'The Committee keeps no armed body of its own.', e: { K: -12, T: 4, L: -2 }, need: { C: 40 } },
    { id: 'schools', t: 'A delegate in every street', q: 'Train ten thousand people to do what the Committee does.', e: { C: 10, L: 2, K: -4, T: -2 } },
    { id: 'ration', t: 'Ration the Process by function', q: 'The Berkeley Process goes to whoever does the work that cannot wait.', e: { T: -6, K: 4, L: 4 }, from: 1962 },
    { id: 'everyone', t: 'Offer the Process to everyone', q: 'Nobody ages, or everybody does.', e: { T: 10, K: -6, L: -8 }, from: 1962 },
    { id: 'refuse', t: 'Refuse the Process to the Committee', q: 'Its members grow old again, like everyone they serve.', e: { K: -18, T: 6 }, from: 1962 },
  ];
  const EVENTS = {
    1950: { h: 'THE HALL OF COLUMNS, MOSCOW', b: 'The American Council and the Soviet state merge. On the second ballot, 298 to 13, they elect a physicist fetched from the corridor still holding his tea: “I do not want this. I accept it as one accepts a measurement.”' },
    1956: { h: 'INDIA JOINS THE UNION', b: 'Four hundred million people come onto the Ledger. The plan grows, and so does the office that runs it.', e: { L: 4, K: 4 } },
    1959: { h: 'CHINA JOINS THE UNION', b: 'The Map now covers most of the planet. The Committee has never had more to do.', e: { L: 4, K: 4 } },
    1962: { h: 'THE BERKELEY PROCESS', b: 'Announced in a footnote as “a modest improvement in tissue turnover”, it slows ageing almost to a stop. From now on, the Committee does not have to retire. Its power grows each term on its own.', e: { K: 3 } },
    1968: { h: 'THE DROUGHT OF 1969', b: 'The rains fail. If the Ledger is strong, the grain is already moving and a few hundred people die instead of millions.', drought: true },
    1980: { h: 'THE MAP IS COMPLETE', b: 'The Continental Ledger records every flow of production on the planet, by the minute. It could run the world. It could also end the running.', e: { L: 8 } },
  };
  const START = { L: 45, C: 20, K: 52, T: 50 };
  let S;

  root.innerHTML = `
    <div class="wi-wrap">
      <aside class="wi-meters" data-k="meters"></aside>
      <section class="wi-desk">
        <div class="wi-year"><span data-k="term">TERM 1 / 12</span><b data-k="year">1950</b></div>
        <article class="wi-event" data-k="event"></article>
        <p class="wi-ask" data-k="ask">Choose one decree for this term.</p>
        <div class="wi-cards" data-k="cards"></div>
        <ol class="wi-log" data-k="log" aria-label="Decrees so far"></ol>
      </section>
    </div>
    <div class="g-over" data-k="over"></div>`;
  const $ = k => root.querySelector(`[data-k="${k}"]`);
  const clamp = v => Math.max(0, Math.min(100, v));
  const arrows = (v) => (v > 0 ? '▲' : '▼').repeat(Math.min(3, Math.ceil(Math.abs(v) / 5)));

  const paintMeters = (delta = {}) => {
    $('meters').innerHTML = METERS.map(m => {
      const v = S.m[m.k];
      const d = delta[m.k];
      const warn = (m.k === 'K' ? v >= 85 : v <= 15);
      return `<div class="wi-m ${warn ? 'warn' : ''} wi-${m.k}"><div class="wi-mh"><span>${m.name}</span><b>${Math.round(v)}${d ? ` <i class="${(m.k === 'K' ? d < 0 : d > 0) ? 'up' : 'dn'}">${d > 0 ? '+' : ''}${d}</i>` : ''}</b></div>
        <div class="wi-mb"><span style="width:${v}%"></span>${m.k === 'K' ? '<em style="left:20%"></em>' : m.k === 'C' ? '<em style="left:70%"></em>' : m.k === 'L' ? '<em style="left:40%"></em>' : ''}</div><p>${m.d}</p></div>`;
    }).join('') + `<div class="wi-goal">TO WIN BY 1985 · COMMITTEE 20 OR LESS · COUNCILS 70 OR MORE · LEDGER 40 OR MORE</div>`;
  };
  const apply = (e) => { const d = {}; for (const k in e) { const before = S.m[k]; S.m[k] = clamp(S.m[k] + e[k]); d[k] = Math.round(S.m[k] - before); } return d; };
  const available = (c) => (!c.from || YEARS[S.turn] >= c.from) && !S.used.has(c.id);
  const meets = (c) => !c.need || Object.keys(c.need).every(k => S.m[k] >= c.need[k]);

  function deal() {
    const year = YEARS[S.turn];
    $('term').textContent = `TERM ${S.turn + 1} / ${YEARS.length}`;
    $('year').textContent = year;
    const ev = EVENTS[year];
    let evDelta = {};
    if (ev) {
      if (ev.e) evDelta = apply(ev.e);
      if (ev.drought) { const hit = S.m.L >= 60 ? -5 : S.m.L >= 40 ? -12 : -22; evDelta = apply({ L: hit, T: hit / 2 }); ev.b2 = S.m.L >= 55 ? 'The grain was moving before the rains failed.' : 'The grain was not where it was needed.'; }
      $('event').innerHTML = `<span class="k">${year} · NEWS</span><h2>${ev.h}</h2><p>${ev.b}${ev.b2 ? ' <b>' + ev.b2 + '</b>' : ''}</p>`;
    } else {
      const lines = ['The Union works. The question is whether it will ever stop needing you.', 'The delegates ask, again, when the Committee will hand over.', 'Another term. Another set of decrees on your desk.', 'Every improvement makes the Committee harder to give up.'];
      $('event').innerHTML = `<span class="k">${year} · THE CHAIR'S DESK</span><h2>${year < 1962 ? 'A COMPETENT COMMITTEE' : 'A COMMITTEE THAT CANNOT DIE'}</h2><p>${lines[S.turn % lines.length]}</p>`;
    }
    // drift: the state grows by itself, faster once its members stop ageing
    if (S.turn > 0) Object.assign(evDelta, mergeDelta(evDelta, apply({ K: year >= 1962 ? 3 : 1 })));
    paintMeters(evDelta);
    if (checkLoss()) return;
    const pool = CARDS.filter(available);
    const hand = [];
    while (hand.length < 3 && pool.length) hand.push(pool.splice(Math.floor(Math.random() * pool.length), 1)[0]);
    $('cards').innerHTML = hand.map((c, i) => {
      const ok = meets(c);
      const eff = Object.keys(c.e).map(k => `<span class="wi-e ${(k === 'K' ? c.e[k] < 0 : c.e[k] > 0) ? 'good' : 'bad'}">${METERS.find(m => m.k === k).name} ${arrows(c.e[k])}</span>`).join('');
      const need = c.need ? Object.keys(c.need).map(k => `${METERS.find(m => m.k === k).name} ${c.need[k]}+`).join(' · ') : '';
      return `<button type="button" class="wi-card" data-i="${i}" ${ok ? '' : 'disabled'}><span class="n">${i + 1}</span><h3>${c.t}</h3><p>${c.q}</p><div class="wi-es">${eff}</div>${need ? `<div class="wi-need ${ok ? '' : 'no'}">${ok ? 'NEEDS' : 'NOT YET · NEEDS'} ${need}</div>` : ''}</button>`;
    }).join('');
    if (!hand.some(meets)) { $('cards').insertAdjacentHTML('beforeend', `<button type="button" class="wi-card" data-i="wait"><span class="n">0</span><h3>Wait a term</h3><p>Nothing on the desk can be done yet.</p></button>`); }
    $('cards').querySelectorAll('.wi-card').forEach(b => b.addEventListener('click', () => choose(b.dataset.i === 'wait' ? null : hand[+b.dataset.i])));
    S.hand = hand;
  }
  const mergeDelta = (a, b) => { const o = Object.assign({}, a); for (const k in b) o[k] = (o[k] || 0) + b[k]; return o; };
  function choose(c) {
    if (S.done) return;
    G.unlock();
    G.tone({ f: 330, f2: 660, d: 0.15, type: 'triangle', v: 0.1 });
    let d = {};
    if (c) { S.used.add(c.id); d = apply(c.e); }
    const li = document.createElement('li');
    li.innerHTML = `<b>${YEARS[S.turn]}</b> ${c ? c.t : 'Waited'}`;
    $('log').appendChild(li);
    paintMeters(d);
    if (checkLoss()) return;
    S.turn += 1;
    if (S.turn >= YEARS.length) return finale();
    setTimeout(deal, 380);
  }
  function checkLoss() {
    let why = null;
    if (S.m.L <= 0) why = ['FAMINE', 'The Ledger went blind. Grain sat in one province while another starved. The councils could not run what nobody could see, and the Committee had already let go of it.'];
    else if (S.m.T <= 0) why = ['THE UNION SPLITS', 'The delegates stopped believing the Committee would ever hand over. Half of them walked out of the Hall of Columns and did not come back.'];
    else if (S.m.K >= 100) why = ['THE COMMITTEE VOTES ITSELF ETERNAL', 'A committee that cannot die met for eleven days in a sealed room and decided it could not be spared. The state did not wither. It stopped ageing.'];
    if (why) { end(false, why[0], why[1]); return true; }
    return false;
  }
  function finale() {
    const { L, C, K } = S.m;
    if (K <= 20 && C >= 70 && L >= 40) return end(true, 'THE STATE WITHERED', 'In 1985 there was almost nothing left of the Committee. The councils ran the grid, the Ledger was open to anyone, and the chair was the last office still standing. Oppenheimer asked to be the last piece of the state, and in the morning he was not.');
    if (K <= 20) return end(false, 'NOBODY PICKED IT UP', 'The Committee let go, but the councils were not ready to hold what it dropped. The Ledger kept counting for a world that no longer had anyone to read it.');
    if (C >= 70) return end(false, 'TWO POWERS', 'The councils could run the world, and the Committee was still there, insisting it was needed. Two powers sat in the same hall in 1985, and the argument had only begun.');
    return end(false, 'A COMPETENT COMMITTEE', '“A competent chairman will improve things, and then he will not want to stop.” By 1985 the Union was the best-run world in any branch, and it was still being run.');
  }
  function end(win, title, text) {
    S.done = true;
    G.tone({ f: win ? 392 : 196, f2: win ? 784 : 98, d: 0.8, type: 'triangle', v: 0.14 });
    const score = Math.round((100 - S.m.K) + S.m.C + S.m.L / 2 + S.m.T / 2 + (win ? 200 : 0));
    const b = G.best('wither', score);
    $('over').hidden = false;
    $('over').innerHTML = `<div class="g-card"><div class="k">${win ? '1985 · THE LAST PIECE OF THE STATE' : YEARS[Math.min(S.turn, YEARS.length - 1)] + ' · THE STATE DID NOT WITHER'}</div>
      <h2>${title}</h2><p>${text}</p>
      <div class="stat">${METERS.map(m => `<div>${m.name}<b>${Math.round(S.m[m.k])}</b></div>`).join('')}</div>
      <p class="k" style="color:#A89C95">SCORE ${score} · BEST ${b.best}${b.isNew ? ' · NEW' : ''}</p>
      <div class="q">“The state is not abolished. It withers away.” — Engels, Anti-Dühring</div>
      <div class="row"><button class="btn-g" type="button" data-again>▶ CHAIR AGAIN</button><a class="btn-g gh" href="/archive/lenin/">READ STATE AND REVOLUTION</a><a class="btn-g gh" href="/arcade/">ALL GAMES</a></div></div>`;
    $('over').querySelector('[data-again]').addEventListener('click', start);
  }
  function intro() {
    $('over').hidden = false;
    $('over').innerHTML = `<div class="g-card"><div class="k">SIM-04 · OPPIE'S AMERICA 1985 · A PREQUEL TO USSR 2089</div><h1>WITHER</h1>
      <p>In this branch the Technical Alliance and the Communist Left took the grid in 1934, and in 1950 the American Council and the Soviet state merged. They chose as chair the one man who said he would want to stop.</p>
      <p>You have twelve terms, from 1950 to 1985. Each term, pick one decree. Keep the Ledger seeing, build up the councils, keep the delegates' trust, and bring the Committee down to nothing. After 1962 its members stop ageing, and it grows by itself.</p>
      <div class="q">“They are all competent. That is the problem.”</div>
      <div class="row"><button class="btn-g" type="button" data-again>▶ TAKE THE CHAIR</button><a class="btn-g gh" href="/#ussr2089">ABOUT USSR 2089</a></div></div>`;
    $('over').querySelector('[data-again]').addEventListener('click', start);
    $('over').querySelector('[data-again]').focus();
  }
  function start() {
    G.unlock();
    S = { turn: 0, m: Object.assign({}, START), used: new Set(), done: false };
    $('log').innerHTML = '';
    $('over').hidden = true;
    deal();
  }
  document.addEventListener('keydown', e => {
    if (!S || S.done || !$('over').hidden) return;
    const n = +e.key;
    if (n >= 1 && n <= 3) { const b = $('cards').querySelector(`.wi-card[data-i="${n - 1}"]`); if (b && !b.disabled) b.click(); }
  });
  S = { turn: 0, m: Object.assign({}, START), used: new Set(), done: true };
  paintMeters();
  intro();
})();
