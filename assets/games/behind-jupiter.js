/* BEHIND JUPITER — SIM-02. Carry the last box through the belt, past Helios-Orbital, to the fleet behind Jupiter. */
(() => {
  'use strict';
  const G = window.TIAGame;
  const wrap = document.getElementById('game');
  const cv = document.getElementById('bj-cv');
  const g = cv.getContext('2d');
  const W = 960, H = 540;
  let scale = 1, ox = 0, oy = 0, dpr = 1;
  const MONO = "'Manolo Mono', 'Share Tech Mono', monospace";
  const RED = '#E8222A', RED2 = '#FF5A60', INK = '#F2ECE4', DIM = '#A89C95', AMBER = '#F2B33D', GREEN = '#39D98A';

  // overlay + touch buttons
  const over = document.createElement('div'); over.className = 'g-over'; wrap.appendChild(over);
  const forceBtn = document.createElement('button'); forceBtn.type = 'button'; forceBtn.className = 'bj-force'; forceBtn.textContent = 'FORCE'; forceBtn.setAttribute('aria-label', 'Use Force: clears the screen'); wrap.appendChild(forceBtn);

  const fit = () => {
    const r = wrap.getBoundingClientRect();
    dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr);
    cv.style.width = r.width + 'px'; cv.style.height = r.height + 'px';
    scale = Math.min(r.width / W, r.height / H);
    ox = (r.width - W * scale) / 2; oy = (r.height - H * scale) / 2;
  };
  window.addEventListener('resize', fit);
  fit();

  /* ------------------------------------------------------------ state */
  let S = null;
  const keys = {};
  let touch = null; // {id, sx, sy, px, py}
  const rnd = (a, b) => a + Math.random() * (b - a);
  const stars = [0, 1, 2].map(l => Array.from({ length: 60 + l * 40 }, () => ({ x: rnd(0, W), y: rnd(0, H), z: 0.3 + l * 0.35 })));

  const SECTORS = [
    { name: 'SECTOR 1 · THE BELT', until: 55 },
    { name: 'SECTOR 2 · LEDGER FIELD', until: 112 },
    { name: 'SECTOR 3 · EXCLUSION ZONE', until: 9999 },
  ];

  function newGame() {
    S = {
      t: 0, score: 0, hull: 3, shield: 1, force: 2, spread: 1, inv: 2, fireCd: 0, over: false, won: false,
      p: { x: 140, y: H / 2, vx: 0, vy: 0 }, bullets: [], eb: [], foes: [], parts: [], drops: [], rings: [], texts: [],
      wave: 0, boss: null, bossDone: false, ending: 0, flash: 0, paused: false, combo: 0, comboT: 0, kills: 0,
    };
    scheduleIdx = 0;
  }

  /* ------------------------------------------------------------ spawns */
  const rockShape = (r) => Array.from({ length: 11 }, (_, i) => { const a = i / 11 * Math.PI * 2; const k = rnd(0.72, 1.08); return [Math.cos(a) * r * k, Math.sin(a) * r * k]; });
  const rock = (size, x, y, vx, vy) => {
    const r = [0, 13, 22, 36][size];
    S.foes.push({ kind: 'rock', size, x: x ?? W + 50, y: y ?? rnd(40, H - 40), vx: vx ?? -rnd(70, 140) - S.t * 0.4, vy: vy ?? rnd(-30, 30), r, hp: [0, 1, 2, 5][size], shape: rockShape(r), rot: 0, vr: rnd(-1.4, 1.4), pts: [0, 80, 40, 20][size] });
  };
  const drone = (y, phase) => S.foes.push({ kind: 'drone', x: W + 30, y, y0: y, vx: -110, r: 15, hp: 3, ph: phase || 0, fire: rnd(1, 2.4), pts: 100 });
  const dart = (y) => S.foes.push({ kind: 'dart', x: W + 30, y, vx: -90, vy: 0, r: 12, hp: 1, dash: rnd(0.6, 1.2), pts: 150 });
  const buoy = (y) => S.foes.push({ kind: 'buoy', x: W + 40, y, vx: -60, r: 22, hp: 9, fire: 1.2, pts: 300, rot: 0 });

  // timeline: [seconds, fn]
  const schedule = [];
  const at = (t, f) => schedule.push([t, f]);
  for (let t = 1; t < 52; t += 1.6) at(t, () => rock(Math.random() < 0.35 ? 3 : 2));
  [8, 14, 22, 30, 38, 46].forEach(t => at(t, () => { const y = rnd(90, H - 90); for (let k = 0; k < 4; k++) setTimeout(() => S && !S.over && drone(y, k * 0.6), k * 280); }));
  at(56, () => banner('SECTOR 2 · LEDGER FIELD', 'Helios-Orbital insures the sky. It has excluded you.'));
  for (let t = 58; t < 108; t += 2.4) at(t, () => rock(Math.random() < 0.5 ? 2 : 1));
  for (let t = 60; t < 108; t += 3.1) at(t, () => { for (let k = 0; k < 3; k++) dart(rnd(60, H - 60)); });
  [64, 76, 88, 100].forEach(t => at(t, () => buoy(rnd(100, H - 100))));
  [70, 82, 94, 104].forEach(t => at(t, () => { const y = rnd(90, H - 90); for (let k = 0; k < 5; k++) setTimeout(() => S && !S.over && drone(y + (k % 2 ? 40 : -40), k * 0.5), k * 240); }));
  at(113, () => { banner('SECTOR 3 · EXCLUSION ZONE', 'Clause 4.4: events originating behind the Object are excluded.'); });
  at(117, () => spawnBoss());
  let scheduleIdx = 0;

  const banner = (title, sub) => { S.texts.push({ title, sub, t: 0, life: 4 }); G.tone({ f: 220, f2: 440, d: 0.4, type: 'sawtooth', v: 0.06 }); };

  function spawnBoss() {
    S.boss = { x: W + 160, y: H / 2, tx: W - 150, r: 70, hp: 170, max: 170, t: 0, phase: 0, fire: 1, sweep: null, spawnT: 6, hit: 0 };
  }

  /* ------------------------------------------------------------ helpers */
  const boom = (x, y, n, col, sp = 160) => {
    for (let i = 0; i < n; i++) { const a = rnd(0, Math.PI * 2), v = rnd(30, sp); S.parts.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life: rnd(0.3, 0.9), t: 0, col }); }
    S.rings.push({ x, y, r: 4, life: 0.4, t: 0, col });
  };
  const hitPlayer = () => {
    if (S.inv > 0 || S.over || S.ending) return;
    if (S.shield > 0) { S.shield -= 1; S.inv = 1.2; G.tone({ f: 300, f2: 900, d: 0.25, type: 'sine', v: 0.15 }); boom(S.p.x, S.p.y, 14, AMBER); return; }
    S.hull -= 1; S.inv = 2; S.spread = Math.max(1, S.spread - 1); S.combo = 0;
    G.noise({ d: 0.5, cut: 900, v: 0.4 }); boom(S.p.x, S.p.y, 30, RED2, 220);
    if (S.hull <= 0) { S.over = true; setTimeout(() => endScreen(false), 900); }
  };
  const kill = (f) => {
    S.kills += 1;
    S.combo += 1; S.comboT = 2;
    const mult = 1 + Math.min(4, Math.floor(S.combo / 8));
    S.score += f.pts * mult;
    boom(f.x, f.y, f.kind === 'rock' ? 10 + f.size * 4 : 18, f.kind === 'rock' ? DIM : RED2);
    G.noise({ d: f.kind === 'rock' ? 0.25 : 0.35, cut: f.kind === 'rock' ? 700 : 1600, v: 0.22 });
    if (f.kind === 'rock' && f.size > 1) { for (let k = 0; k < 2; k++) rock(f.size - 1, f.x, f.y, f.vx * 0.8 + rnd(-40, 40), rnd(-90, 90)); }
    const roll = Math.random();
    const chance = f.kind === 'buoy' ? 1 : f.kind === 'rock' ? 0.04 : 0.12;
    if (roll < chance) {
      const kinds = ['box', 'program', 'program', 'force'];
      S.drops.push({ kind: kinds[Math.floor(Math.random() * kinds.length)], x: f.x, y: f.y, vx: -60, t: 0 });
    }
  };
  const useForce = () => {
    if (!S || S.over || S.paused || S.force <= 0 || S.ending) return;
    S.force -= 1; S.flash = 0.6;
    G.noise({ d: 1.2, cut: 500, v: 0.5, curve: 1.2 }); G.tone({ f: 80, f2: 40, d: 1, type: 'sine', v: 0.3 });
    S.eb = [];
    S.foes.slice().forEach(f => { if (f.x < W + 20) { f.hp -= 6; if (f.hp <= 0) { kill(f); f.dead = true; } } });
    S.foes = S.foes.filter(f => !f.dead);
    if (S.boss && !S.bossDone) { S.boss.hp -= 25; S.boss.hit = 0.2; }
    S.rings.push({ x: S.p.x, y: S.p.y, r: 10, life: 0.8, t: 0, col: INK, big: true });
  };
  forceBtn.addEventListener('click', e => { e.preventDefault(); useForce(); });

  /* ------------------------------------------------------------ update */
  function update(dt) {
    if (!S || S.paused) return;
    S.t += dt;
    if (S.flash > 0) S.flash -= dt;
    // timeline
    while (scheduleIdx < schedule.length && schedule[scheduleIdx][0] <= S.t) { if (!S.over) schedule[scheduleIdx][1](); scheduleIdx++; }
    // player
    const p = S.p;
    if (!S.over && !S.ending) {
      let ax = (keys.ArrowRight || keys.KeyD ? 1 : 0) - (keys.ArrowLeft || keys.KeyA ? 1 : 0);
      let ay = (keys.ArrowDown || keys.KeyS ? 1 : 0) - (keys.ArrowUp || keys.KeyW ? 1 : 0);
      if (ax && ay) { ax *= 0.7071; ay *= 0.7071; }
      if (touch) { p.x += (touch.px - p.x) * Math.min(1, dt * 14); p.y += (touch.py - p.y) * Math.min(1, dt * 14); }
      else { p.x += ax * 330 * dt; p.y += ay * 330 * dt; }
      p.x = Math.max(24, Math.min(W * 0.72, p.x)); p.y = Math.max(20, Math.min(H - 20, p.y));
      S.fireCd -= dt;
      if ((keys.Space || keys.KeyJ || touch || autoFire) && S.fireCd <= 0) {
        S.fireCd = 0.11;
        const n = S.spread, spreadA = 0.12;
        for (let k = 0; k < n; k++) { const a = (k - (n - 1) / 2) * spreadA; S.bullets.push({ x: p.x + 18, y: p.y, vx: Math.cos(a) * 760, vy: Math.sin(a) * 760 }); }
        G.tone({ f: 1400, f2: 700, d: 0.05, type: 'square', v: 0.035 });
      }
    }
    if (S.inv > 0) S.inv -= dt;
    if (S.comboT > 0) { S.comboT -= dt; if (S.comboT <= 0) S.combo = 0; }
    // bullets
    S.bullets.forEach(b => { b.x += b.vx * dt; b.y += b.vy * dt; });
    S.bullets = S.bullets.filter(b => b.x < W + 20 && b.y > -20 && b.y < H + 20 && !b.dead);
    S.eb.forEach(b => { b.x += b.vx * dt; b.y += b.vy * dt; });
    S.eb = S.eb.filter(b => b.x > -20 && b.x < W + 20 && b.y > -20 && b.y < H + 20 && !b.dead);
    // foes
    S.foes.forEach(f => {
      f.x += f.vx * dt;
      if (f.kind === 'rock') { f.y += f.vy * dt; f.rot += f.vr * dt; if (f.y < f.r || f.y > H - f.r) f.vy *= -1; }
      if (f.kind === 'drone') { f.ph += dt * 2.2; f.y = f.y0 + Math.sin(f.ph) * 70; f.fire -= dt; if (f.fire <= 0 && f.x < W - 40) { f.fire = rnd(1.6, 2.8); aimShot(f.x, f.y, 210); } }
      if (f.kind === 'dart') { f.dash -= dt; if (f.dash > 0) { f.y += (p.y - f.y) * dt * 1.6; } else { f.vx = -520; } }
      if (f.kind === 'buoy') { f.rot += dt; if (f.x < W - 120) f.vx = -12; f.fire -= dt; if (f.fire <= 0) { f.fire = 1.6; for (let k = -1; k <= 1; k++) { const a = Math.atan2(p.y - f.y, p.x - f.x) + k * 0.28; S.eb.push({ x: f.x, y: f.y, vx: Math.cos(a) * 190, vy: Math.sin(a) * 190, r: 5 }); } } }
      if (f.hit > 0) f.hit -= dt;
    });
    // collisions: bullets vs foes
    S.bullets.forEach(b => {
      for (const f of S.foes) {
        if (f.dead) continue;
        const dx = b.x - f.x, dy = b.y - f.y;
        if (dx * dx + dy * dy < (f.r + 4) * (f.r + 4)) {
          b.dead = true; f.hp -= 1; f.hit = 0.08;
          if (f.hp <= 0) { f.dead = true; kill(f); } else G.tone({ f: 260, d: 0.03, type: 'square', v: 0.03 });
          break;
        }
      }
      const B = S.boss;
      if (!b.dead && B && !S.bossDone && B.x < W + 40) {
        const dx = b.x - B.x, dy = b.y - B.y;
        if (dx * dx + dy * dy < (B.r + 6) * (B.r + 6)) { b.dead = true; B.hp -= 1; B.hit = 0.06; S.score += 5; if (B.hp <= 0) bossDown(); }
      }
    });
    S.foes = S.foes.filter(f => !f.dead && f.x > -80);
    // foes / shots vs player
    if (!S.over) {
      for (const f of S.foes) { const dx = p.x - f.x, dy = p.y - f.y; if (dx * dx + dy * dy < (f.r + 8) * (f.r + 8)) { hitPlayer(); if (f.kind !== 'buoy') { f.hp -= 3; if (f.hp <= 0) { f.dead = true; kill(f); } } } }
      for (const b of S.eb) { const dx = p.x - b.x, dy = p.y - b.y; if (dx * dx + dy * dy < (b.r + 6) * (b.r + 6)) { b.dead = true; hitPlayer(); } }
      S.foes = S.foes.filter(f => !f.dead);
    }
    // drops
    S.drops.forEach(d => { d.x += d.vx * dt; d.t += dt; const dx = p.x - d.x, dy = p.y - d.y; if (dx * dx + dy * dy < 30 * 30 && !S.over) { d.dead = true; pick(d); } });
    S.drops = S.drops.filter(d => !d.dead && d.x > -20);
    // boss
    if (S.boss && !S.bossDone) bossUpdate(dt);
    // effects
    S.parts.forEach(q => { q.t += dt; q.x += q.vx * dt; q.y += q.vy * dt; q.vx *= 0.98; q.vy *= 0.98; });
    S.parts = S.parts.filter(q => q.t < q.life);
    S.rings.forEach(r => { r.t += dt; r.r += (r.big ? 900 : 160) * dt; });
    S.rings = S.rings.filter(r => r.t < r.life);
    S.texts.forEach(t => { t.t += dt; });
    S.texts = S.texts.filter(t => t.t < t.life);
    if (S.ending) { S.ending += dt; if (S.ending > 13 && !S.won) { S.won = true; endScreen(true); } }
  }
  const aimShot = (x, y, sp) => { const a = Math.atan2(S.p.y - y, S.p.x - x); S.eb.push({ x, y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, r: 5 }); };
  const pick = (d) => {
    G.tone({ f: 660, f2: 1320, d: 0.18, type: 'triangle', v: 0.12 });
    if (d.kind === 'box') { S.shield = Math.min(3, S.shield + 1); S.texts.push({ small: 'BOX · SHIELD +1', x: S.p.x, y: S.p.y - 30, t: 0, life: 1.2 }); }
    if (d.kind === 'program') { S.spread = Math.min(5, S.spread + 1); S.texts.push({ small: 'PROGRAM · SPREAD ' + S.spread, x: S.p.x, y: S.p.y - 30, t: 0, life: 1.2 }); }
    if (d.kind === 'force') { S.force = Math.min(3, S.force + 1); S.texts.push({ small: 'FORCE +1', x: S.p.x, y: S.p.y - 30, t: 0, life: 1.2 }); }
    S.score += 50;
  };
  function bossUpdate(dt) {
    const B = S.boss;
    B.t += dt; if (B.hit > 0) B.hit -= dt;
    B.x += (B.tx - B.x) * Math.min(1, dt * 1.2);
    B.y = H / 2 + Math.sin(B.t * 0.7) * 120;
    const rage = B.hp < B.max * 0.45;
    B.fire -= dt;
    if (B.fire <= 0 && B.x < W - 60) {
      B.fire = rage ? 0.7 : 1.1;
      const n = rage ? 9 : 6;
      const base = Math.atan2(S.p.y - B.y, S.p.x - B.x);
      for (let k = 0; k < n; k++) { const a = base + (k - (n - 1) / 2) * 0.16; S.eb.push({ x: B.x - 50, y: B.y, vx: Math.cos(a) * 200, vy: Math.sin(a) * 200, r: 6 }); }
      G.tone({ f: 160, f2: 90, d: 0.2, type: 'sawtooth', v: 0.06 });
    }
    B.spawnT -= dt;
    if (B.spawnT <= 0) { B.spawnT = rage ? 5 : 7; for (let k = 0; k < 3; k++) dart(rnd(60, H - 60)); }
    // telegraphed sweep: a line warns for 1.2 s, then fires for 0.6 s
    if (!B.sweep && B.t > 8 && Math.random() < dt * (rage ? 0.22 : 0.12)) B.sweep = { y: S.p.y, t: 0 };
    if (B.sweep) {
      B.sweep.t += dt;
      if (B.sweep.t > 1.2 && B.sweep.t < 1.8 && Math.abs(S.p.y - B.sweep.y) < 16) hitPlayer();
      if (B.sweep.t > 1.8) B.sweep = null;
    }
  }
  function bossDown() {
    const B = S.boss;
    S.bossDone = true; S.score += 5000;
    for (let k = 0; k < 6; k++) setTimeout(() => S && boom(B.x + rnd(-60, 60), B.y + rnd(-60, 60), 26, k % 2 ? AMBER : RED2, 260), k * 180);
    G.noise({ d: 1.6, cut: 700, v: 0.5, curve: 1.3 });
    S.eb = []; S.foes = [];
    setTimeout(() => { if (S && !S.over) { S.ending = 0.01; banner('BEHIND JUPITER', 'Forty minutes from Earth at the speed of light.'); } }, 1400);
  }

  /* ------------------------------------------------------------ draw */
  function draw() {
    const w = cv.width, h = cv.height;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.fillStyle = '#050304'; g.fillRect(0, 0, w, h);
    g.setTransform(scale * dpr, 0, 0, scale * dpr, ox * dpr, oy * dpr);
    g.save(); g.beginPath(); g.rect(0, 0, W, H); g.clip();
    g.fillStyle = '#07040A'; g.fillRect(0, 0, W, H);
    const t = S ? S.t : performance.now() / 1000;
    // Jupiter grows as you get closer
    const prog = S ? Math.min(1, S.t / 125) : 0.15;
    drawJupiter(W * 0.86 - prog * 120, H * 0.5, 60 + prog * 240 + (S && S.ending ? Math.min(220, S.ending * 40) : 0), t);
    // stars
    stars.forEach((layer, l) => {
      g.fillStyle = l === 2 ? INK : l === 1 ? '#CFC4BC' : '#6E5F5A';
      layer.forEach(s => {
        if (S && !S.paused) { s.x -= (40 + l * 90) * s.z * (1 / 60) * (S.ending ? 0.3 : 1); if (s.x < 0) { s.x = W; s.y = rnd(0, H); } }
        g.fillRect(s.x, s.y, l + 1, l === 2 ? 2 : 1);
      });
    });
    if (S && S.ending) drawFace(S.ending);
    if (!S) { g.restore(); return; }
    // drops
    S.drops.forEach(d => {
      const c = d.kind === 'box' ? AMBER : d.kind === 'force' ? INK : GREEN;
      g.save(); g.translate(d.x, d.y); g.rotate(d.t * 2);
      g.strokeStyle = c; g.lineWidth = 2; g.strokeRect(-9, -9, 18, 18); g.restore();
      g.fillStyle = c; g.font = `11px ${MONO}`; g.textAlign = 'center'; g.fillText(d.kind === 'box' ? 'B' : d.kind === 'force' ? 'F' : 'P', d.x, d.y + 4);
    });
    // foes
    S.foes.forEach(f => {
      g.save(); g.translate(f.x, f.y);
      const hit = f.hit > 0;
      if (f.kind === 'rock') {
        g.rotate(f.rot); g.beginPath(); f.shape.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath();
        g.fillStyle = hit ? '#5A4A46' : '#1A1214'; g.fill(); g.strokeStyle = hit ? INK : '#8C7C76'; g.lineWidth = 2; g.stroke();
      } else if (f.kind === 'drone') {
        g.fillStyle = hit ? INK : AMBER; g.beginPath(); g.arc(0, 0, 9, 0, Math.PI * 2); g.fill();
        g.strokeStyle = hit ? INK : AMBER; g.lineWidth = 2; g.beginPath(); g.ellipse(0, 0, 18, 6, -0.3, 0, Math.PI * 2); g.stroke();
      } else if (f.kind === 'dart') {
        g.fillStyle = hit ? INK : RED2; g.beginPath(); g.moveTo(-14, 0); g.lineTo(10, -8); g.lineTo(4, 0); g.lineTo(10, 8); g.closePath(); g.fill();
      } else if (f.kind === 'buoy') {
        g.rotate(f.rot); g.strokeStyle = hit ? INK : AMBER; g.lineWidth = 3;
        g.strokeRect(-16, -16, 32, 32); g.rotate(Math.PI / 4); g.strokeRect(-12, -12, 24, 24);
        g.fillStyle = RED; g.fillRect(-5, -5, 10, 10);
      }
      g.restore();
    });
    if (S.boss && !S.bossDone) drawBoss(S.boss);
    // bullets
    g.fillStyle = INK; S.bullets.forEach(b => g.fillRect(b.x - 7, b.y - 1.5, 14, 3));
    S.eb.forEach(b => { g.fillStyle = AMBER; g.beginPath(); g.arc(b.x, b.y, b.r, 0, Math.PI * 2); g.fill(); g.fillStyle = '#fff'; g.beginPath(); g.arc(b.x, b.y, b.r * 0.4, 0, Math.PI * 2); g.fill(); });
    // player
    if (!S.over && !(S.inv > 0 && Math.floor(S.t * 10) % 2)) drawShip(S.p.x, S.p.y);
    // effects
    S.parts.forEach(q => { g.globalAlpha = 1 - q.t / q.life; g.fillStyle = q.col; g.fillRect(q.x - 1.5, q.y - 1.5, 3, 3); });
    S.rings.forEach(r => { g.globalAlpha = 1 - r.t / r.life; g.strokeStyle = r.col; g.lineWidth = r.big ? 4 : 2; g.beginPath(); g.arc(r.x, r.y, r.r, 0, Math.PI * 2); g.stroke(); });
    g.globalAlpha = 1;
    if (S.flash > 0) { g.fillStyle = `rgba(242,236,228,${Math.max(0, S.flash) * 0.35})`; g.fillRect(0, 0, W, H); }
    drawHud();
    g.restore();
  }
  function drawShip(x, y) {
    g.save(); g.translate(x, y);
    g.fillStyle = RED; g.beginPath(); g.moveTo(-18, -4); g.lineTo(-26, -1); g.lineTo(-26, 1); g.lineTo(-18, 4); g.closePath(); g.fill();
    const fl = 6 + Math.random() * 6; g.fillStyle = AMBER; g.fillRect(-22 - fl, -2, fl, 4);
    g.fillStyle = INK; g.beginPath(); g.moveTo(20, 0); g.lineTo(-14, -12); g.lineTo(-8, 0); g.lineTo(-14, 12); g.closePath(); g.fill();
    g.fillStyle = RED; g.fillRect(-4, -3, 10, 6);
    if (S.shield > 0) { g.strokeStyle = `rgba(242,179,61,${0.35 + 0.15 * S.shield})`; g.lineWidth = 2; g.beginPath(); g.arc(0, 0, 24, 0, Math.PI * 2); g.stroke(); }
    g.restore();
  }
  function drawBoss(B) {
    g.save(); g.translate(B.x, B.y);
    if (B.sweep) {
      const k = B.sweep.t;
      g.save(); g.translate(-B.x, -B.y);
      if (k < 1.2) { g.strokeStyle = `rgba(255,90,96,${0.25 + 0.25 * Math.sin(k * 20)})`; g.setLineDash([8, 8]); g.lineWidth = 2; g.beginPath(); g.moveTo(0, B.sweep.y); g.lineTo(B.x - 60, B.sweep.y); g.stroke(); g.setLineDash([]); }
      else { g.fillStyle = 'rgba(255,90,96,0.85)'; g.fillRect(0, B.sweep.y - 7, B.x - 60, 14); g.fillStyle = '#fff'; g.fillRect(0, B.sweep.y - 2, B.x - 60, 4); }
      g.restore();
    }
    const hit = B.hit > 0;
    g.strokeStyle = hit ? INK : '#CFC4BC'; g.lineWidth = 3; g.fillStyle = '#120C0E';
    g.beginPath(); g.moveTo(-70, -90); g.lineTo(60, -110); g.lineTo(90, 0); g.lineTo(60, 110); g.lineTo(-70, 90); g.lineTo(-40, 0); g.closePath(); g.fill(); g.stroke();
    // Helios mark: a sun disc crossed by an orbit
    g.fillStyle = hit ? INK : AMBER; g.beginPath(); g.arc(10, 0, 26, 0, Math.PI * 2); g.fill();
    g.strokeStyle = hit ? INK : AMBER; g.lineWidth = 4; g.beginPath(); g.ellipse(10, 0, 46, 13, 0, 0, Math.PI * 2); g.stroke();
    g.fillStyle = RED; [-70, 70].forEach(yy => g.fillRect(-50, yy - 8, 30, 16));
    g.restore();
    // health bar
    g.fillStyle = '#2A1A1C'; g.fillRect(W / 2 - 200, 64, 400, 8);
    g.fillStyle = AMBER; g.fillRect(W / 2 - 200, 64, 400 * Math.max(0, B.hp / B.max), 8);
    g.fillStyle = DIM; g.font = `11px ${MONO}`; g.textAlign = 'center'; g.fillText('HELIOS-ORBITAL · EXCLUSION PLATFORM', W / 2, 58);
  }
  function drawJupiter(x, y, r, t) {
    g.save(); g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.clip();
    const bands = ['#CFC4BC', '#8C2A22', '#E6D3B5', '#C81D25', '#CFC4BC', '#8C2A22', '#A89C95', '#E6D3B5', '#6E3A30'];
    const bh = (2 * r) / bands.length;
    bands.forEach((c, i) => { g.fillStyle = c; g.fillRect(x - r, y - r + i * bh + Math.sin(t * 0.2 + i) * 2, 2 * r, bh + 2); });
    g.fillStyle = '#E8222A'; g.beginPath(); g.ellipse(x - r * 0.25, y + r * 0.28, r * 0.18, r * 0.09, 0, 0, Math.PI * 2); g.fill();
    const sh = g.createRadialGradient(x - r * 0.4, y - r * 0.4, r * 0.2, x, y, r * 1.05);
    sh.addColorStop(0, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(5,3,4,0.85)');
    g.fillStyle = sh; g.fillRect(x - r, y - r, 2 * r, 2 * r);
    g.restore();
    g.fillStyle = 'rgba(5,3,4,0.62)'; g.fillRect(0, 0, W, H);
  }
  // the moon of the other Party, its near face carved into a portrait: brow, beard, open eyes
  const craters = Array.from({ length: 70 }, (_, i) => { const a = (i * 137.5) * Math.PI / 180, d = Math.sqrt((i + 0.5) / 70); return [Math.cos(a) * d, Math.sin(a) * d, 0.02 + ((i * 7919) % 13) / 260]; });
  function drawFace(k) {
    const a = Math.min(1, k / 3);
    const x = W * 0.62, y = H * 0.5, r = 40 + Math.min(1, k / 6) * 130;
    g.save(); g.globalAlpha = a;
    g.strokeStyle = `rgba(232,34,42,${0.55 + 0.25 * Math.sin(k * 2.4)})`; g.lineWidth = 3;
    g.beginPath(); g.arc(x, y, r * 1.42, 0, Math.PI * 2); g.stroke();
    // the body: old-paper yellow, dark in the middle, bright at the rim
    const body = g.createRadialGradient(x, y, r * 0.1, x, y, r);
    body.addColorStop(0, '#9C8456'); body.addColorStop(0.7, '#C7AE78'); body.addColorStop(1, '#EAD9A8');
    g.fillStyle = body; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    g.save(); g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.clip();
    g.fillStyle = 'rgba(60,40,22,0.18)';
    craters.forEach(([cx, cy, cr]) => { g.beginPath(); g.ellipse(x + cx * r * 0.95, y + cy * r * 0.95, cr * r, cr * r * 0.8, 0, 0, Math.PI * 2); g.fill(); });
    const D = 'rgba(38,24,12,0.72)', D2 = 'rgba(38,24,12,0.45)';
    // cheek shadows
    g.fillStyle = 'rgba(38,24,12,0.22)';
    g.beginPath(); g.ellipse(x - r * 0.5, y + r * 0.2, r * 0.12, r * 0.3, 0.2, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.ellipse(x + r * 0.5, y + r * 0.2, r * 0.12, r * 0.3, -0.2, 0, Math.PI * 2); g.fill();
    // the brow ridge: a straight shadow across the top, heavier over the eyes
    g.fillStyle = D;
    g.beginPath(); g.moveTo(x - r * 0.62, y - r * 0.2); g.lineTo(x - r * 0.08, y - r * 0.27); g.lineTo(x + r * 0.08, y - r * 0.27); g.lineTo(x + r * 0.62, y - r * 0.2); g.lineTo(x + r * 0.55, y - r * 0.12); g.lineTo(x - r * 0.55, y - r * 0.12); g.closePath(); g.fill();
    // eye sockets
    g.beginPath(); g.ellipse(x - r * 0.27, y - r * 0.04, r * 0.15, r * 0.085, 0.05, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.ellipse(x + r * 0.27, y - r * 0.04, r * 0.15, r * 0.085, -0.05, 0, Math.PI * 2); g.fill();
    // nose: a narrow vertical shadow down from the brow
    g.fillStyle = D2;
    g.beginPath(); g.moveTo(x - r * 0.03, y - r * 0.12); g.lineTo(x + r * 0.07, y + r * 0.22); g.lineTo(x - r * 0.1, y + r * 0.24); g.closePath(); g.fill();
    // moustache, drooping at the ends
    g.fillStyle = D;
    g.beginPath(); g.moveTo(x - r * 0.3, y + r * 0.42); g.quadraticCurveTo(x - r * 0.2, y + r * 0.27, x, y + r * 0.3); g.quadraticCurveTo(x + r * 0.2, y + r * 0.27, x + r * 0.3, y + r * 0.42); g.quadraticCurveTo(x, y + r * 0.36, x - r * 0.3, y + r * 0.42); g.fill();
    // pointed beard
    g.beginPath(); g.moveTo(x - r * 0.24, y + r * 0.46); g.quadraticCurveTo(x, y + r * 0.44, x + r * 0.24, y + r * 0.46); g.lineTo(x + r * 0.04, y + r * 0.92); g.lineTo(x - r * 0.04, y + r * 0.92); g.closePath(); g.fill();
    g.restore();
    // the eyes come round: two points of dull light
    const lit = Math.max(0, Math.min(1, (k - 2.5) / 2));
    g.fillStyle = `rgba(255,232,170,${0.25 + 0.6 * lit})`;
    g.beginPath(); g.arc(x - r * 0.27, y - r * 0.04, r * 0.035, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.arc(x + r * 0.27, y - r * 0.04, r * 0.035, 0, Math.PI * 2); g.fill();
    g.restore();
    if (k > 4) {
      const lines = ['TO THE MINISTRIES, THE EXCHANGES,', 'THE ARMIES AND THE BOARDS OF THE WORLD:', '', 'THIS IS NOT A PROGRAM.', 'IT IS A DEADLINE.'];
      g.textAlign = 'left'; g.font = `16px ${MONO}`;
      lines.forEach((l, i) => { if (k > 4 + i * 0.9) { g.fillStyle = i >= 3 ? RED2 : INK; g.fillText(l, 50, 140 + i * 28); } });
    }
  }
  function drawHud() {
    g.textAlign = 'left'; g.font = `14px ${MONO}`;
    g.fillStyle = DIM; g.fillText('SCORE', 20, 26); g.fillStyle = INK; g.fillText(String(S.score).padStart(7, '0'), 80, 26);
    if (S.combo >= 8) { g.fillStyle = AMBER; g.fillText('×' + (1 + Math.min(4, Math.floor(S.combo / 8))), 160, 26); }
    g.fillStyle = DIM; g.fillText('HULL', 210, 26);
    for (let i = 0; i < 3; i++) { g.fillStyle = i < S.hull ? RED : '#2A1A1C'; g.fillRect(256 + i * 18, 15, 12, 12); }
    g.fillStyle = DIM; g.fillText('BOX', 320, 26);
    for (let i = 0; i < 3; i++) { g.strokeStyle = AMBER; g.lineWidth = 2; if (i < S.shield) { g.fillStyle = AMBER; g.fillRect(358 + i * 18, 15, 12, 12); } else g.strokeRect(358 + i * 18, 15, 12, 12); }
    g.fillStyle = DIM; g.fillText('FORCE', 420, 26); g.fillStyle = INK; g.fillText('◆'.repeat(S.force) || '—', 474, 26);
    const sec = SECTORS.find(s => S.t < s.until) || SECTORS[2];
    g.textAlign = 'right'; g.fillStyle = DIM; g.fillText(S.ending ? 'BEHIND JUPITER' : sec.name, W - 20, 26);
    const prog = Math.min(1, S.t / 117);
    g.fillStyle = '#2A1A1C'; g.fillRect(W - 220, 34, 200, 3); g.fillStyle = RED; g.fillRect(W - 220, 34, 200 * prog, 3);
    S.texts.forEach(tx => {
      const a = Math.min(1, tx.t * 3, (tx.life - tx.t) * 2);
      g.globalAlpha = Math.max(0, a);
      if (tx.title) {
        g.textAlign = 'center'; g.fillStyle = INK; g.font = `30px ${MONO}`; g.fillText(tx.title, W / 2, H * 0.4);
        g.fillStyle = DIM; g.font = `14px ${MONO}`; g.fillText(tx.sub, W / 2, H * 0.4 + 30);
      } else { g.textAlign = 'center'; g.fillStyle = AMBER; g.font = `12px ${MONO}`; g.fillText(tx.small, tx.x, tx.y - tx.t * 20); }
      g.globalAlpha = 1;
    });
    if (S.paused) { g.fillStyle = 'rgba(5,3,4,0.6)'; g.fillRect(0, 0, W, H); g.fillStyle = INK; g.textAlign = 'center'; g.font = `28px ${MONO}`; g.fillText('PAUSED · P TO RESUME', W / 2, H / 2); }
  }

  /* ------------------------------------------------------------ loop */
  let last = performance.now();
  let autoFire = false;
  const loop = (now) => {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    update(dt); draw();
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);

  /* ------------------------------------------------------------ screens */
  function intro() {
    const best = G.best('behind-jupiter').best;
    over.hidden = false;
    over.innerHTML = `<div class="g-card"><div class="k">SIM-02 · USSR 2089 · MARCH 2141</div><h1>BEHIND<br>JUPITER</h1>
      <p>You fly the courier with the last box: Lenin and Bordiga, with the marginal notes. Get it through the belt and past Helios-Orbital, which has excluded everything behind the Object, to the fleet waiting behind Jupiter.</p>
      <p>Pick up <b style="color:#F2B33D">B</b> boxes for shields, <b style="color:#39D98A">P</b> for the program (wider fire) and <b>F</b> for force, which clears the screen.</p>
      <div class="q">“The proletarians have nothing to lose but their chains.” — The Communist Manifesto</div>
      ${best ? `<p class="k" style="color:#A89C95">BEST ON THIS DEVICE · ${best}</p>` : ''}
      <div class="row"><button class="btn-g" type="button" data-go>▶ LAUNCH</button></div></div>`;
    over.querySelector('[data-go]').addEventListener('click', begin);
    over.querySelector('[data-go]').focus();
  }
  function begin() {
    G.unlock(); newGame(); over.hidden = true; over.innerHTML = '';
    const qs = new URLSearchParams(location.search), sk = +qs.get('skip') || 0;
    if (sk) { S.t = sk; while (scheduleIdx < schedule.length && schedule[scheduleIdx][0] < sk - 0.5) scheduleIdx++; }
    if (qs.get('god')) S.inv = 1e9;
    if (qs.get('win')) setTimeout(() => { if (S.boss) S.boss.hp = 1; }, 4000);
    banner('SECTOR 1 · THE BELT', 'Clear the belt. Reach the fleet.');
    G.music('/assets/radio/behind-jupiter.mp3');
    cv.focus && cv.focus();
  }
  function endScreen(win) {
    const bonus = win ? S.hull * 2000 + S.shield * 500 : 0;
    S.score += bonus;
    const b = G.best('behind-jupiter', S.score);
    over.hidden = false;
    over.innerHTML = `<div class="g-card"><div class="k">${win ? 'MARCH 4, 2141 · THE PORTAL IS OPEN' : 'SIGNAL LOST · ' + Math.floor(S.t) + ' S'}</div>
      <h2>${win ? 'THE BOX GOT THROUGH' : 'COURIER DOWN'}</h2>
      <p>${win ? 'The fleet has the box. A face the size of a moon turns towards the Earth, and the message goes out on every carrier, in every language: you have until October 9.' : 'The box is lost in the dark. Somewhere a cell in Rotterdam waits for texts that will not come. Try again.'}</p>
      <div class="stat"><div>SCORE<b>${S.score}</b></div><div>DESTROYED<b>${S.kills}</b></div>${win ? `<div>HULL BONUS<b>${bonus}</b></div>` : ''}<div>BEST<b>${b.best}</b></div></div>
      ${b.isNew ? '<p class="k">NEW BEST ON THIS DEVICE</p>' : ''}
      <div class="row"><button class="btn-g" type="button" data-go>▶ FLY AGAIN</button><a class="btn-g gh" href="/archive/">READ THE TEXTS</a><a class="btn-g gh" href="/arcade/">ALL GAMES</a></div></div>`;
    over.querySelector('[data-go]').addEventListener('click', begin);
  }

  /* ------------------------------------------------------------ input */
  const pause = (v) => { if (!S || S.over || S.won) return; S.paused = v === undefined ? !S.paused : v; };
  window.addEventListener('keydown', e => {
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(e.code)) e.preventDefault();
    keys[e.code] = true;
    if (e.code === 'KeyX' || e.code === 'KeyK') useForce();
    if (e.code === 'KeyP' || e.code === 'Escape') pause();
    if ((e.code === 'Enter' || e.code === 'Space') && !over.hidden) { const b = over.querySelector('[data-go]'); if (b && document.activeElement !== b) b.click(); }
  });
  window.addEventListener('keyup', e => { keys[e.code] = false; });
  window.addEventListener('blur', () => { Object.keys(keys).forEach(k => { keys[k] = false; }); pause(true); });
  const toGame = (cx, cy) => { const r = cv.getBoundingClientRect(); return { x: (cx - r.left - ox) / scale, y: (cy - r.top - oy) / scale }; };
  cv.addEventListener('pointerdown', e => {
    if (e.pointerType === 'mouse') return;
    const q = toGame(e.clientX, e.clientY);
    touch = { id: e.pointerId, sx: q.x, sy: q.y, bx: S ? S.p.x : 0, by: S ? S.p.y : 0, px: S ? S.p.x : q.x, py: S ? S.p.y : q.y };
    wrap.classList.add('touching');
    cv.setPointerCapture(e.pointerId);
  });
  cv.addEventListener('pointermove', e => {
    if (!touch || e.pointerId !== touch.id) return;
    const q = toGame(e.clientX, e.clientY);
    touch.px = touch.bx + (q.x - touch.sx) * 1.4; touch.py = touch.by + (q.y - touch.sy) * 1.4;
  });
  const lift = e => { if (touch && e.pointerId === touch.id) touch = null; };
  cv.addEventListener('pointerup', lift); cv.addEventListener('pointercancel', lift);
  if (matchMedia('(pointer: coarse)').matches) { wrap.classList.add('coarse'); autoFire = true; }
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(true); });
  intro();
})();
