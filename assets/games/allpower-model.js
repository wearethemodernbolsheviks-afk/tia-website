/* ALL POWER — SIM-05. The game's rules, with no screen code, so the browser and a test bot share them.
   One real second is one hour of grid time, so a 400 W panel banks 400 Wh a second. */
(function (root) {
  'use strict';
  const LSUN = 3.828e26;            // W, the Sun
  const STARS = 2e11;               // stars in the galaxy
  const LSTAR = 1.9e26;             // W, an average star after lifting losses
  const GALAXIES = 2e12;            // galaxies in the observable universe
  const LGAL = STARS * LSTAR;       // W, one galaxy
  const D1 = 250e3;                 // W, Council District 12
  const D2 = 450e9;                 // W, the continent in 1985
  const CF = 2e9;                   // collectors for 63% of the Sun

  const PRODUCERS = [
    { id: 'roof', name: 'Rooftop panel', w: 400, cost: 1000, g: 1.1, si: 200, flag: null,
      blurb: 'A panel on a house on Elm St.' },
    { id: 'array', name: 'Community array', w: 2e4, cost: 4e4, g: 1.11, si: 5000, flag: 'arrays',
      blurb: 'Shared by a block, voted for by the block.' },
    { id: 'farm', name: 'Solar farm', w: 2e6, cost: 5e6, g: 1.11, si: 2.5e5, flag: 'farms',
      blurb: 'Forty acres of glass east of Richmond.' },
    { id: 'desert', name: 'Desert array', w: 1e9, cost: 3e9, g: 1.1, si: 1e8, flag: 'desert',
      blurb: 'The Mojave, a square mile at a time.' },
    { id: 'belt', name: 'Sunbelt corridor', w: 1e11, cost: 4e11, g: 1.1, si: 5e9, flag: 'belt',
      blurb: 'Glass from El Paso to Savannah.' },
  ];

  // cost: E in Wh, ops, ins (insight). req: when it appears. fx: what it does.
  const PROJECTS = [
    // ---------------------------------------------------------------- district
    { id: 'mirror', st: 1, name: 'Angle the mirrors', desc: 'Every hand collection is worth four times as much.', cost: { ops: 250 },
      req: s => s.T >= 2000, fx: s => { s.clickMult *= 4; } },
    { id: 'arrays', st: 1, name: 'Block election: community arrays', desc: 'The blocks vote to share bigger arrays.', cost: { ops: 600 },
      req: s => s.n.roof >= 8, fx: s => { s.flags.arrays = 1; } },
    { id: 'works', st: 1, name: 'Silicon works', desc: 'The district refines its own silicon whenever it runs low.', cost: { ops: 900, E: 2e4 },
      req: s => s.siBought >= 3, fx: s => { s.autoSi = true; } },
    { id: 'perov', st: 1, name: 'Perovskite tandem cells', desc: 'Every panel collects 50% more.', cost: { ops: 1200, E: 1e5 },
      req: s => s.n.array >= 1, fx: s => { s.mult *= 1.5; } },
    { id: 'cards', st: 1, name: 'Card index', desc: 'Each archive seat holds 2.5 times as many plans.', cost: { ops: 1400 },
      req: s => s.arch >= 2, fx: s => { s.capMult *= 2.5; } },
    { id: 'coop', st: 1, name: 'Panel co-operative', desc: 'Everything costs 20% less to build.', cost: { ops: 1800, ins: 4 },
      req: s => s.n.array >= 3, fx: s => { s.costMult *= 0.8; } },
    { id: 'track', st: 1, name: 'Sun trackers', desc: 'Panels follow the sun across the sky: 40% more.', cost: { ops: 2200, E: 6e5 },
      req: s => s.done.perov, fx: s => { s.mult *= 1.4; } },
    { id: 'certs', st: 1, name: 'Energy certificates', desc: 'Wages and prices go. Every household gets its share in kWh, and the Council trusts you twice as fast.', cost: { ops: 2000, ins: 8 },
      req: s => s.A >= 45, fx: s => { s.apprMult *= 2; } },
    { id: 'dgrid', st: 1, name: 'District grid', desc: 'Unlocks solar farms.', cost: { ops: 3000, E: 2e6 },
      req: s => s.n.array >= 5, fx: s => { s.flags.farms = 1; } },
    { id: 'cont', st: 1, name: 'The Continental Grid', desc: 'Connect the district to the continent. The allotment you have to meet grows to 450 GW.', cost: { ops: 5000, ins: 20, E: 2e7 },
      req: s => s.flags.farms && s.cov >= 1, fx: s => { s.stage = 2; } },
    // ---------------------------------------------------------------- continent
    { id: 'mojave', st: 2, name: 'The Mojave Plan', desc: 'Unlocks desert arrays.', cost: { ops: 6000, E: 2e8 },
      req: s => true, fx: s => { s.flags.desert = 1; } },
    { id: 'sunbelt', st: 2, name: 'The Sunbelt corridor', desc: 'Unlocks Sunbelt corridors: 100 GW each.', cost: { ops: 14000, ins: 30, E: 1e12 },
      req: s => s.n.desert >= 10, fx: s => { s.flags.belt = 1; } },
    { id: 'drums', st: 2, name: 'Magnetic drum memory', desc: 'Each archive seat holds four times as many plans.', cost: { ops: 7000 },
      req: s => true, fx: s => { s.capMult *= 4; } },
    { id: 'thin', st: 2, name: 'Thin-film printing', desc: 'Panels need a fifth of the silicon and cost 15% less.', cost: { ops: 8000, ins: 25 },
      req: s => s.n.desert >= 1, fx: s => { s.siMult *= 0.2; s.costMult *= 0.85; } },
    { id: 'hvdc', st: 2, name: 'HVDC trunk lines', desc: 'Less is lost on the wires: 60% more delivered.', cost: { ops: 9000, E: 5e9 },
      req: s => s.n.desert >= 1, fx: s => { s.mult *= 1.6; } },
    { id: 'compu', st: 2, name: 'Planning computers', desc: 'Calculator seats work three times as fast.', cost: { ops: 12000, ins: 40 },
      req: s => s.done.drums, fx: s => { s.rateMult *= 3; } },
    { id: 'rent', st: 2, name: 'Rent abolished', desc: 'Housing is allotted like energy. Approval never falls below 60.', cost: { ops: 10000 },
      req: s => s.done.certs, fx: s => { s.apprFloor = 60; } },
    { id: 'scgrid', st: 2, name: 'Superconducting grid', desc: 'The grid stops losing anything: output doubles.', cost: { ops: 16000, ins: 60, E: 1e11 },
      req: s => s.done.hvdc, fx: s => { s.mult *= 2; } },
    { id: 'moon', st: 2, name: 'The Moon branch', desc: 'The continent is lit. Build mass drivers on the Moon and start on the Sun itself.', cost: { ops: 25000, ins: 120, E: 1e13 },
      req: s => s.cov >= 1 && power(s) >= 1.5 * D2, fx: s => { s.stage = 3; s.seatNext = Math.max(s.seatNext, s.T * 10); } },
    // ---------------------------------------------------------------- the Sun
    { id: 'quantum', st: 3, name: 'Quantum planning', desc: 'Calculator seats work ten times as fast.', cost: { ops: 25000 },
      req: s => true, fx: s => { s.rateMult *= 10; } },
    { id: 'foundry', st: 3, name: 'Orbital foundries', desc: 'Foundries in orbit turn lunar mass into sunlight collectors.', cost: { ops: 30000, ins: 120, E: 1e14 },
      req: s => s.md >= 3, fx: s => { s.flags.foundry = 1; } },
    { id: 'statite', st: 3, name: 'Thin-film statites', desc: 'Collectors weigh almost nothing and catch twice the light.', cost: { ops: 40000 },
      req: s => s.C >= 1e4, fx: s => { s.swarmEff *= 2; } },
    { id: 'diamond', st: 3, name: 'Diamondoid archive', desc: 'Each archive seat holds ten times as many plans.', cost: { ops: 45000 },
      req: s => s.done.quantum, fx: s => { s.capMult *= 10; } },
    { id: 'mercury', st: 3, name: 'Take Mercury apart', desc: 'Mass drivers on Mercury: ten thousand times the mass.', cost: { ops: 60000, ins: 250, E: 1e18 },
      req: s => s.C >= 1e5, fx: s => { s.massMult *= 1e4; } },
    { id: 'selfrep', st: 3, name: 'Self-replicating foundries', desc: 'Foundries build foundries.', cost: { ops: 90000, ins: 400 },
      req: s => s.done.mercury, fx: s => { s.foRep = 0.04; } },
    { id: 'phase', st: 3, name: 'Phased swarm control', desc: 'The swarm moves as one mirror: 40% more light.', cost: { ops: 120000, ins: 600 },
      req: s => swarmF(s) >= 0.4, fx: s => { s.swarmEff *= 1.4; } },
    { id: 'seed', st: 3, name: 'Seed the galaxy', desc: 'The Sun is enclosed. Send a probe that builds more of itself at every star it reaches.', cost: { ops: 150000, ins: 900, E: 1e28 },
      req: s => swarmF(s) >= 0.999, fx: s => { s.stage = 4; s.N = 1; s.seatNext = Math.max(s.seatNext, s.T * 10); } },
    // ---------------------------------------------------------------- the galaxy
    { id: 'stellarc', st: 4, name: 'Stellar computing', desc: 'Calculator seats work ten times as fast, and each archive seat holds ten times as much.', cost: { ops: 150000 },
      req: s => true, fx: s => { s.rateMult *= 10; s.capMult *= 10; } },
    { id: 'fidelity', st: 4, name: 'Copy fidelity', desc: 'Half as many probes go quiet.', cost: { ops: 180000, ins: 700 },
      req: s => s.N >= 50, fx: s => { s.drift *= 0.5; } },
    { id: 'dir1', st: 4, name: 'A new directive', desc: 'Two more directive points to give the probes.', cost: { ops: 200000, ins: 800 },
      req: s => s.N >= 1000, fx: s => { s.dp += 2; } },
    { id: 'relays', st: 4, name: 'Spiral-arm relays', desc: 'Probes find stars three times as fast.', cost: { ops: 250000, ins: 1000, E: 1e33 },
      req: s => s.Sx >= 1e6, fx: s => { s.capt *= 3; } },
    { id: 'lift', st: 4, name: 'Stellar lifting', desc: 'Take the stars apart slowly: twice the light from each.', cost: { ops: 300000, ins: 1200 },
      req: s => s.Sx >= 1e8, fx: s => { s.eff4 *= 2; } },
    { id: 'core', st: 4, name: 'Tap the core', desc: 'The black hole at the centre of the galaxy: 50% more light, and insight comes twice as fast.', cost: { ops: 400000, ins: 2000 },
      req: s => s.Sx >= 1e10, fx: s => { s.eff4 *= 1.5; s.insMult *= 2; } },
    { id: 'inter', st: 4, name: 'Intergalactic seeds', desc: 'The galaxy is enclosed. Send probes across the voids.', cost: { ops: 500000, ins: 3000, E: 1e38 },
      req: s => s.Sx >= 0.999 * STARS, fx: s => { s.stage = 5; s.N2 = 1; s.seatNext = Math.max(s.seatNext, s.T * 10); } },
    // ---------------------------------------------------------------- the universe
    { id: 'matri', st: 5, name: 'Matrioshka planning', desc: 'Calculator seats work ten times as fast, and each archive seat holds ten times as much.', cost: { ops: 500000 },
      req: s => true, fx: s => { s.rateMult *= 10; s.capMult *= 10; } },
    { id: 'dir2', st: 5, name: 'A second directive', desc: 'Three more directive points.', cost: { ops: 600000, ins: 3000 },
      req: s => s.N2 >= 100, fx: s => { s.dp += 3; } },
    { id: 'voids', st: 5, name: 'Void crossings', desc: 'Probes reach galaxies three times as fast.', cost: { ops: 800000, ins: 4000 },
      req: s => s.G >= 1e3, fx: s => { s.capt2 *= 3; } },
    { id: 'glift', st: 5, name: 'Galactic lifting', desc: 'Twice the light from every galaxy.', cost: { ops: 1e6, ins: 5000 },
      req: s => s.G >= 1e7, fx: s => { s.eff5 *= 2; } },
    { id: 'horizon', st: 5, name: 'Horizon relays', desc: 'The universe is expanding. Relays at the edge keep the far galaxies within reach.', cost: { ops: 1.5e6, ins: 8000, E: 1e48 },
      req: s => s.G >= 0.9 * 0.06 * GALAXIES, fx: s => { s.reach = 1; } },
    { id: 'allpower', st: 5, name: 'ALL POWER', desc: 'There is nothing left to collect.', cost: { ops: 2e6, ins: 12000 },
      req: s => s.G >= 0.9999 * GALAXIES, fx: s => { s.ended = s.t; } },
  ];
  const BYID = {};
  PROJECTS.forEach(p => { BYID[p.id] = p; });

  function newState() {
    return {
      v: 1, t: 0, stage: 1, E: 0, T: 0, P: 0, cov: 0, delivered: 0,
      n: { roof: 0, array: 0, farm: 0, desert: 0, belt: 0 },
      S: 1000, siPrice: 1, siBought: 0, autoSi: false,
      a: 0.4, A: 15, apprMult: 1, apprFloor: 0, H: 0,
      bureau: false, seats: 0, free: 0, seatNext: 1500, calc: 0, arch: 0, ops: 0, ins: 0,
      flags: {}, done: {},
      mult: 1, clickMult: 1, costMult: 1, siMult: 1, rateMult: 1, capMult: 1, insMult: 1,
      M: 0, md: 0, fo: 0, C: 0, massMult: 1, swarmEff: 0.25, foRep: 0,
      N: 0, Sx: 0, dp: 3, dir: { rep: 1, cap: 1, shield: 1 }, rep: 0.03, drift: 0.025, capt: 0.3, eff4: 0.3,
      N2: 0, G: 0, reach: 0.06, rep2: 0.025, drift2: 0.02, capt2: 0.004, eff5: 0.3,
      launches: 0, launches2: 0, clicks: 0, ended: 0, seen: {}, log: [],
    };
  }

  // ------------------------------------------------------------------ readouts
  function ground(s) { let p = 0; for (const pr of PRODUCERS) p += s.n[pr.id] * pr.w; return p * s.mult; }
  function swarmF(s) { return 1 - Math.exp(-s.C / CF); }
  function swarmP(s) { return LSUN * swarmF(s) * Math.min(1, s.swarmEff); }
  function galaxyP(s) { return s.Sx * LSTAR * Math.min(1, s.eff4); }
  function universeP(s) { return s.G * LGAL * Math.min(1, s.eff5); }
  function power(s) { return ground(s) + swarmP(s) + galaxyP(s) + universeP(s); }
  function demand(s) { return s.stage === 1 ? D1 : s.stage === 2 ? D2 : 0; }
  function maxOps(s) { return s.arch * 1000 * s.capMult; }
  function opsRate(s) { return s.calc * 5 * s.rateMult; }
  function insRate(s) { return s.ops >= maxOps(s) && s.calc > 0 ? opsRate(s) * 0.01 * s.insMult : 0; }
  function unlocked(s, pr) { return !pr.flag || s.flags[pr.flag]; }
  function prodCost(s, pr, k = 0) { return pr.cost * Math.pow(pr.g, s.n[pr.id] + k) * s.costMult; }
  function prodSi(s, pr) { return pr.si * s.siMult; }
  function siBatch(s) { let need = 0; for (const pr of PRODUCERS) if (unlocked(s, pr)) need = Math.max(need, prodSi(s, pr)); return Math.max(1000, Math.pow(10, Math.ceil(Math.log10(need * 5)))); }
  function siCost(s, units) { return units * s.siPrice; }
  function mdCost(s) { return 1e10 * Math.pow(1.08, s.md) * s.costMult; }
  function foCost(s) { return 5e10 * Math.pow(1.08, Math.floor(s.fo)) * s.costMult; }
  function probeCost(s) { return 1e29 * Math.pow(1.6, s.launches); }
  function probe2Cost(s) { return 1e40 * Math.pow(1.6, s.launches2); }
  function directive(s) { const d = s.dir; return { rep: d.rep, cap: d.cap, shield: d.shield }; }
  function netRep(s) { const d = s.dir; return s.rep * (1 + 0.5 * d.rep) - s.drift / (1 + 0.6 * d.shield); }
  function netRep2(s) { const d = s.dir; return s.rep2 * (1 + 0.5 * d.rep) - s.drift2 / (1 + 0.6 * d.shield); }
  function canAfford(s, c) { return (c.E || 0) <= s.E && (c.ops || 0) <= s.ops && (c.ins || 0) <= s.ins; }

  // ------------------------------------------------------------------ actions
  function say(s, text) { (s.log = s.log || []).push({ t: s.t, text }); if (s.log.length > 40) s.log.shift(); }
  function collect(s) {
    if (s.stage > 2) return 0;
    const g = 250 * s.clickMult;
    s.E += g; s.T += g; s.clicks += 1; return g;
  }
  function buyProducer(s, id) {
    const pr = PRODUCERS.find(p => p.id === id);
    if (!pr || !unlocked(s, pr) || s.stage > 2) return false;
    const c = prodCost(s, pr), si = prodSi(s, pr);
    if (s.E < c || s.S < si) return false;
    s.E -= c; s.S -= si; s.n[id] += 1;
    if (s.n[id] === 1) say(s, `First ${pr.name.toLowerCase()} connected.`);
    return true;
  }
  function buySilicon(s) {
    const u = siBatch(s), c = siCost(s, u);
    if (s.E < c) return false;
    s.E -= c; s.S += u; s.siBought += 1; return true;
  }
  function setAllot(s, a) { s.a = Math.max(0, Math.min(1, a)); }
  function seat(s, kind) {
    if (s.free < 1) return false;
    s.free -= 1; if (kind === 'calc') s.calc += 1; else s.arch += 1; return true;
  }
  function buyProject(s, id) {
    const p = BYID[id];
    if (!p || s.done[id] || p.st !== s.stage && !(p.st < s.stage)) return false;
    if (!p.req(s) || !canAfford(s, p.cost)) return false;
    s.E -= p.cost.E || 0; s.ops -= p.cost.ops || 0; s.ins -= p.cost.ins || 0;
    s.done[id] = 1; p.fx(s);
    say(s, `${p.name}: done.`);
    return true;
  }
  function visibleProjects(s) { return PROJECTS.filter(p => !s.done[p.id] && p.st <= s.stage && p.req(s)); }
  function buyDriver(s) { if (s.stage < 3) return false; const c = mdCost(s); if (s.E < c) return false; s.E -= c; s.md += 1; return true; }
  function buyFoundry(s) { if (s.stage < 3 || !s.flags.foundry) return false; const c = foCost(s); if (s.E < c) return false; s.E -= c; s.fo += 1; return true; }
  function launch(s) { if (s.stage !== 4) return false; const c = probeCost(s); if (s.E < c) return false; s.E -= c; s.N += 1; s.launches += 1; return true; }
  function launch2(s) { if (s.stage !== 5) return false; const c = probe2Cost(s); if (s.E < c) return false; s.E -= c; s.N2 += 1; s.launches2 += 1; return true; }
  function setDirective(s, k, delta) {
    const d = s.dir, used = d.rep + d.cap + d.shield;
    if (delta > 0 && used >= s.dp) return false;
    if (delta < 0 && d[k] <= 0) return false;
    d[k] += delta; return true;
  }

  // ------------------------------------------------------------------ time
  function step(s, dt, rnd = Math.random) {
    if (s.ended) return;
    const P = power(s);
    s.P = P;
    if (s.stage <= 2) {
      const D = demand(s);
      s.delivered = s.a * P;
      s.cov = s.delivered / D;
      const target = Math.max(s.apprFloor, 100 * Math.pow(Math.min(1, s.cov), 0.6));
      s.A += (target - s.A) * Math.min(1, 0.15 * dt);
      s.E += (1 - s.a) * P * dt;
      s.H += s.delivered * dt * (s.A / 100) * s.apprMult;
      while (s.bureau && s.H >= s.seatNext) { s.seats += 1; s.free += 1; s.seatNext *= 2; say(s, 'The Council grants you another seat.'); }
    } else {
      s.delivered = 0; s.cov = 1; s.A = 100;
      s.E += P * dt;
      while (s.T >= s.seatNext) { s.seats += 1; s.free += 1; s.seatNext *= 10; say(s, 'The Council grants you another seat.'); }
    }
    s.T += P * dt;
    if (!s.bureau && s.T >= 3000) {
      s.bureau = true; s.calc = 1; s.arch = 1; s.seats = 2; s.seatNext = Math.max(s.seatNext, s.H * 2 || 1500);
      say(s, 'The Council opens a planning bureau for you: one calculator seat, one archive seat.');
    }
    // planning
    const mo = maxOps(s);
    if (s.ops < mo) s.ops = Math.min(mo, s.ops + opsRate(s) * dt);
    else s.ins += insRate(s) * dt;
    // silicon
    s.siPrice = Math.max(0.6, Math.min(1.6, s.siPrice + (rnd() - 0.5) * 0.04 * dt * 10 + (1 - s.siPrice) * 0.01 * dt));
    if (s.autoSi && s.stage <= 2) {
      let need = 0;
      for (const pr of PRODUCERS) if (unlocked(s, pr)) need = Math.max(need, prodSi(s, pr) * 4);
      let guard = 0;
      while (s.S < need && guard++ < 20) { const u = siBatch(s), c = siCost(s, u); if (s.E < c * 2) break; s.E -= c; s.S += u; }
    }
    // the Sun
    if (s.stage >= 3) {
      s.M += s.md * 2e9 * s.massMult * dt;
      if (s.flags.foundry && s.fo > 0) {
        let want = s.fo * 10 * dt;
        const kg = 1e8;
        if (s.M < want * kg) want = s.M / kg;
        s.C += want; s.M -= want * kg;
        if (s.foRep) {
          const nf = s.fo * s.foRep * dt, kgf = 1e10;
          if (s.M >= nf * kgf) { s.fo += nf; s.M -= nf * kgf; }
        }
      }
      if (!s.seen.half && swarmF(s) >= 0.5) { s.seen.half = 1; say(s, 'Half the Sun\'s light now passes through the swarm.'); }
      if (!s.seen.type2 && swarmF(s) >= 0.999) { s.seen.type2 = 1; say(s, 'The Sun is enclosed. Kardashev Type II.'); }
    }
    // the galaxy
    if (s.stage >= 4 && s.N > 0) {
      const d = s.dir;
      s.N = Math.max(0, s.N + s.N * netRep(s) * dt * (s.Sx >= STARS ? 0 : 1));
      s.Sx = Math.min(STARS, s.Sx + s.N * s.capt * (1 + 0.7 * d.cap) * dt);
      if (!s.seen.type3 && s.Sx >= 0.999 * STARS) { s.seen.type3 = 1; say(s, 'Every star in the galaxy feeds the grid. Kardashev Type III.'); }
    }
    // the universe
    if (s.stage >= 5 && s.N2 > 0) {
      const d = s.dir, lim = s.reach * GALAXIES;
      s.N2 = Math.max(0, s.N2 + s.N2 * netRep2(s) * dt * (s.G >= lim ? 0 : 1));
      s.G = Math.min(lim, s.G + s.N2 * s.capt2 * (1 + 0.7 * d.cap) * dt);
      if (!s.seen.edge && s.reach < 1 && s.G >= 0.999 * lim) { s.seen.edge = 1; say(s, 'The rest of the universe is slipping past the horizon.'); }
    }
    s.t += dt;
  }

  const API = {
    LSUN, STARS, LSTAR, GALAXIES, LGAL, D1, D2, PRODUCERS, PROJECTS, BYID,
    newState, step, power, ground, swarmF, swarmP, galaxyP, universeP, demand, maxOps, opsRate, insRate,
    unlocked, prodCost, prodSi, siBatch, siCost, mdCost, foCost, probeCost, probe2Cost, netRep, netRep2, canAfford,
    collect, buyProducer, buySilicon, setAllot, seat, buyProject, visibleProjects, buyDriver, buyFoundry, launch, launch2, setDirective, directive,
    say,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.AllPower = API;
})(typeof window !== 'undefined' ? window : globalThis);
