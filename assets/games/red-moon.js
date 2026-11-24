/* RED MOON TERMINAL — SIM-03. The Red Moon files, playable: a signal-watch terminal aboard the R/V Meridian. */
(() => {
  'use strict';
  const G = window.TIAGame;
  const root = document.getElementById('game');
  const KEY = 'tia-redmoon-v1';
  const P = Object.assign({ read: {}, unlocked: {}, decoded: {}, tune: false, unredacted: false, replied: null, tide: false }, G.store.get(KEY, {}));
  const save = () => G.store.set(KEY, P);

  /* ---------------------------------------------------------------- the files */
  const BR = [
    ['A', '2089', 'BUKHARIN LIVED', 'SAMARA', 'THE STATE WITHERED', 'NO WAGES.', 'THE', 'Incompatible with shareholder value'],
    ['B', '1985', 'OPPENHEIMER WON', 'BERKELEY', 'THE BOMB WAS NEVER DROPPED', 'NO PRICES.', 'DOOR', 'Not monetisable'],
    ['C', '1954', 'LENIN LIVED', 'MOSCOW', 'LENIN SAW 1954', 'NO STATE.', 'ONLY', 'Would void all revenue'],
    ['D', '2002', 'SCORCHED EARTH', 'ASH BELT', 'THE EARTH WAS SCORCHED', 'NO BORDERS.', 'OPENS', 'Jurisdiction undefined'],
    ['E', '2131', 'ORBITAL SOVIET', 'ORBIT', 'A SOVIET ABOVE THE CLOUDS', 'NO OWNERS.', 'FROM', 'Threatens the asset class'],
    ['F', '1991', 'THE UNION HELD', 'MOSCOW', 'THE RED FLAG NEVER CAME DOWN', 'NO MORE BOMBS.', 'YOUR', 'Conflicts with defence contracts'],
    ['G', '1985', 'TWO UNIONS, ONE FLAG', 'TWO CAPITALS', 'ONE FLAG OVER BOTH UNIONS', 'OPEN THE DOOR.', 'SIDE.', 'Unclear. Recommend no reply.'],
  ];
  const PK = BR.map((b, i) => '0x' + (0x45 + i).toString(16).toUpperCase());
  const KEYSHIFT = 9;
  const TUNE = ['G', 'C', 'B', 'D', 'C', 'G', 'E', 'A', 'F'];
  const shift = (s, k) => s.replace(/[A-Z]/g, c => String.fromCharCode((c.charCodeAt(0) - 65 + k + 26 * 10) % 26 + 65));
  const packetPlain = (i) => {
    const [L, yr, nm, city, stat, demand, word] = BR[i];
    return `MEMORY · BRANCH ${L} · ${yr} · ${nm}\nLOCATION   ${city}\nOUTCOME    ${stat}\nTIDES      +4%\nRED MOON   SIGHTED\nDEMAND FRAGMENT ${i + 1}/7   ${demand}\nCARD WORD  ${word}`;
  };

  const FILES = {
    'README.txt': { t: () => `R/V MERIDIAN · DEEP-FIELD SURVEY · SIGNAL WATCH TERMINAL\n\nThis terminal holds the signal watch logs, the tide table and the packets received\nfrom ENTRY 4471. Type ${cmd('help')} for commands. Type ${cmd('ls')} to see what is here.\n\nStart with the log: ${cmd('cat logs/day218.txt')}` },
    'logs/day218.txt': { t: () => `R/V MERIDIAN · SIGNAL WATCH · DAY 218\n\n04:10  Entry 4471 again. Period 9.0 s. Not a pulsar.\n06:30  Tide gauge +4.1%. Captain says fault. The spare says the same.\n11:00  Put it through the audio chain. It has a rhythm. Almost notes.\n19:45  Moonrise. Two of them. Nobody said it at dinner.\n23:50  Can't sleep. Wrote the spikes down as letters. Only A to G.\n01:15  The letters repeat every nine minutes. It is a tune. I know this tune.\n\n[ ${cmd('play signal')} to hear it · ${cmd('tide')} for the gauge ]` },
    'logs/day219.txt': { t: () => `R/V MERIDIAN · SIGNAL WATCH · DAY 219\n\n[ PAGE MISSING ]\n\nThe page has been torn out of the log. The tide table may say why.` },
    'logs/day220.txt': {
      lock: '4.00', hint: 'The tide table has one number that should not exist.',
      t: () => `R/V MERIDIAN · SIGNAL WATCH · DAY 220\n\nPage 219 is gone. I didn't tear it out.\n02:00  Someone did. Rubbed a pencil over this page. Look.\n\n        ░░░▒▒▒▓▓▓▓▓▓▓▓▒▒▒░░░\n      ░▒▓  DECODE  WITH  THE  ▓▒░\n     ░▒▓   PERIOD.  SEVEN       ▓▒░\n      ░▒▓  PACKETS.  SEVEN    ▓▒░\n        ░░▒▒▓▓ BRANCHES ▓▓▒▒░░\n\n05:29  Signal changed at exactly 05:29:45. Same as the old test footage.\n08:00  Channel 7 asked a question. Y or N.\n08:05  Captain: we do not answer.\n\n[ The packets are in ${cmd('ls packets')} · ${cmd('decode 0x45')} needs a key ]`,
    },
    'helios/demands_review.txt': { t: () => demandsReview() },
    'helios/investor_notice.txt': { t: () => `HELIOS-ORBITAL HOLDINGS · INSURANCE DIVISION · NOTICE 2/Ω · EFFECTIVE IMMEDIATELY\n\nLUNAR EVENT EXCLUSION\nNotice to all policyholders and shareholders\n\nWith effect from the date of this notice, all policies issued by Helios-Orbital Holdings\nand its subsidiaries are amended to exclude the following. No premium will be refunded.\n\n4.1  No claim arising from a tidal deviation above 4% will be honoured, whatever its cause.\n4.2  Insured parties standing under the Object at moonrise are excluded from all cover.\n4.3  Nothing in any policy covers loss of value in currency, wages or prices.\n4.4  Events originating behind the central aperture of the Object (the "Door") are excluded.\n4.5  Damage caused by any party passing through the Door, in either direction, is excluded.\n4.6  Any memory, image or signal received from the Object is inadmissible as evidence of loss.\n4.7  Yield from nuclear devices used against the Object is not insured, whether or not authorised.\n4.8  Shareholders will be notified when, and only when, the exclusion period ends.\n\nQuestions about this notice will not be answered.\n\nSCHEDULE A · THE OBJECT\nDesignation        LUNA-2, "the Red Moon"\nApparent diameter  1.7 × Luna, growing\nTidal deviation    +4.0% worldwide, rising\nCentral aperture   OPEN\nInsurable          NO` },
    'helios/careers.txt': { t: () => `HELIOS-ORBITAL · CAREERS · We are hiring.\n\nIMMEDIATE START · URGENT\nLUNAR LIAISON\nLocation: under the Object · Hours: moonrise to moonset\n\nThe role\n  • Represent Helios-Orbital in talks with the Object.\n  • Explain our position. Secure a counter-offer.\n  • Report back. (Previous liaisons did not report back.)\n\nYou will need\n  • Fluent Russian, German or Chinese. English will not be understood.\n  • Comfortable with long silences.\n  • No equity in the company, past or present.\n  • Must not have read the demands.\n\nPay\n  • To be agreed.\n  • Note from HR: candidates keep asking us what a wage is.\n\nApplicants: 0 · Applications close at Day 0.` },
    'berkeley/bulletin.txt': {
      tune: true, hint: 'Name the tune the signal plays: name <tune>.',
      t: () => `HOME TERMINAL // COUNCIL DISTRICT 12 · BERKELEY            1985 · 07:02\n\nGOOD MORNING, CITIZEN.\n\nYOUR DAY\n  Energy allotment ........ RENEWED\n  Transit ................. FREE, ALL LINES\n  Childcare ............... OPEN · ELM ST.\n  Rent .................... ABOLISHED 1936\n\nCOUNCIL NOTICES\n  Sky watch continues. The visitor is friendly.\n  Observatory open to all tonight, 9 PM.\n  The other branch can hear us. Vote on whether to answer: polls close at moonset.\n  Chair addresses Council, 8 PM.\n\nSKY CAMERA 3 · OBSERVATORY HILL\n  VESSEL VISIBLE THROUGH THE DOOR: R/V MERIDIAN · 34°08'S 12°41'W\n\nDISTRICT 12 VOTE · ANSWER THEM?\n  YES 1,204     NO 3          counting · moonset 05:29\n\n/// GRID SURPLUS 4.1% THIS WEEK /// SHIP SIGHTED THROUGH THE DOOR, SOUTH ATLANTIC\n/// THEY ASKED US A QUESTION /// WE CAN HEAR THEM ///\n\n[ The ship in the picture is yours. ]` },
    'notes_final.txt': {
      after: 'reply',
      t: () => `NOTES.TXT · BRANCH 0                                  LAST SAVED: DAY 0\n\n01 why red          15 the demands. found them. seven.\n02 all 7. ALL SEVEN 16 same demand seven times\n03 tides??          17 no wages\n04 not politics     18 no prices\n05 ASTRONOMY        19 no state\n06 same night       20 no borders\n07 check sky        21 no owners\n08 dont sleep       22 no more bombs\n09 it moves         23 open the door\n10 WHO SENT IT      24 the door only opens from your side\n11 its not random\n12 its addressed    25 It was never a demand.\n13 look up          26 It was an invitation.\n14 LOOK UP\n                    → USSR 2089` },
  };
  PK.forEach((pk, i) => { FILES['packets/' + pk] = { packet: i, t: () => packetView(i) }; });

  function demandsReview() {
    const rows = BR.map(([L, yr, , , , demand, , assess], i) => {
      const show = P.unredacted ? demand.padEnd(16) : (P.decoded[PK[i]] ? '▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒' : '████████████████');
      return `0${i + 1}  ${L}  ${yr}  ${show}  ${assess.padEnd(34)} REJECTED`;
    }).join('\n');
    return `HELIOS-ORBITAL HOLDINGS · INTERNAL · BOARD ONLY            DOC NO LUN-0447\n\nLUNAR OBJECT DEMANDS · Automated review summary\nReviewer: HELIOS-AI v4 (Compliance) · Items reviewed: 7 of 7 · Average time per item: 0.4 s\nHuman review: Not required · Source: Gravitational channel, lunar core\n\n#   SRC     DEMAND            ASSESSMENT                         DECISION\n${rows}\n\nBoard resolution 17/Ω: no response is to be sent.\n${P.unredacted ? 'Demand text RESTORED from the decoded packets.' : 'Demand text withheld under Lunar Event exclusion, clause 4.'}${!P.unredacted && countDecoded() === 7 ? `\n\n[ All seven packets are decoded. ${cmd('unredact')} ]` : ''}`;
  }
  function packetView(i) {
    const pk = PK[i];
    if (P.decoded[pk]) return `PACKET ${pk} · ${i + 1}/7 · DECODED\n\n${packetPlain(i)}`;
    return `PACKET ${pk} · ${i + 1}/7 · ENCODED · CHECKSUM PENDING\n\n${shift(packetPlain(i), KEYSHIFT)}\n\n[ ${cmd('decode ' + pk)} <key> ]`;
  }
  const countDecoded = () => PK.filter(p => P.decoded[p]).length;
  const visible = (path) => {
    const f = FILES[path];
    if (f.after === 'reply') return !!P.replied;
    return true;
  };
  const locked = (path) => {
    const f = FILES[path];
    if (f.lock && !P.unlocked[path]) return true;
    if (f.tune && !P.tune) return true;
    return false;
  };

  /* ---------------------------------------------------------------- layout */
  root.innerHTML = `
    <div class="rm-head"><span>R/V MERIDIAN // DEEP-FIELD SURVEY // CHANNEL 7</span><span class="rm-sp"></span><span>SURVEY DAY 220 · <b data-k="clock">08:00</b></span></div>
    <div class="rm-body">
      <div class="rm-term scan" data-k="term" aria-label="Terminal" role="log" aria-live="polite"></div>
      <aside class="rm-side">
        <div class="rm-moon" aria-hidden="true"><canvas width="300" height="160" data-k="wave"></canvas></div>
        <h2>OBJECTIVES</h2><ol class="rm-obj" data-k="obj"></ol>
        <h2>FILES</h2><ul class="rm-files" data-k="files"></ul>
        <div class="rm-side-btns"><button type="button" data-k="hint">HINT</button><button type="button" data-k="reset">START OVER</button></div>
      </aside>
    </div>
    <form class="rm-in" data-k="form" autocomplete="off"><label for="rm-cmd">&gt;</label><input id="rm-cmd" data-k="input" spellcheck="false" autocapitalize="off" aria-label="Command"><button type="submit">RUN</button></form>`;
  const $ = k => root.querySelector(`[data-k="${k}"]`);
  const term = $('term'), input = $('input');
  function cmd(c) { return `\u0001${c}\u0002`; }
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const fmt = s => esc(s).replace(/\u0001(.*?)\u0002/g, (m, c) => `<button type="button" class="rm-c" data-run="${c.replace(/"/g, '&quot;')}">${c}</button>`);

  let queue = Promise.resolve();
  let skip = false;
  const print = (text, cls = '') => {
    queue = queue.then(() => new Promise(res => {
      const el = document.createElement('div'); el.className = 'rm-out ' + cls;
      term.appendChild(el);
      const full = fmt(text);
      if (G.reduced || text.length > 1600 || skip) { el.innerHTML = full; term.scrollTop = term.scrollHeight; res(); return; }
      const plain = text.replace(/[\u0001\u0002]/g, '');
      let i = 0;
      const step = () => {
        if (skip) { el.innerHTML = full; term.scrollTop = term.scrollHeight; res(); return; }
        i = Math.min(plain.length, i + 9);
        el.textContent = plain.slice(0, i);
        term.scrollTop = term.scrollHeight;
        if (i < plain.length) requestAnimationFrame(step); else { el.innerHTML = full; term.scrollTop = term.scrollHeight; res(); }
      };
      step();
    }));
    return queue;
  };
  const echo = (c) => { const el = document.createElement('div'); el.className = 'rm-echo'; el.textContent = '> ' + c; term.appendChild(el); term.scrollTop = term.scrollHeight; };

  /* ---------------------------------------------------------------- side panel */
  const objectives = () => [
    ['Read the signal watch log', !!P.read['logs/day218.txt']],
    ['Check the tide table', P.tide],
    ['Recover the log for day 220', !!P.unlocked['logs/day220.txt']],
    ['Name the tune in the signal', P.tune],
    [`Decode the packets (${countDecoded()}/7)`, countDecoded() === 7],
    ['Restore the redacted demands', P.unredacted],
    ['Answer channel 7', !!P.replied],
  ];
  const paintSide = () => {
    $('obj').innerHTML = objectives().map(([t, d]) => `<li class="${d ? 'done' : ''}">${d ? '■' : '□'} ${esc(t)}</li>`).join('');
    $('files').innerHTML = Object.keys(FILES).filter(visible).map(f => {
      const lk = locked(f); const rd = P.read[f] || (FILES[f].packet !== undefined && P.decoded[PK[FILES[f].packet]]);
      return `<li><button type="button" data-run="cat ${f}" class="${lk ? 'lk' : rd ? 'rd' : ''}">${lk ? '⌧' : rd ? '■' : '□'} ${f}</button></li>`;
    }).join('');
  };

  /* ---------------------------------------------------------------- commands */
  const resolve = (arg) => {
    if (!arg) return null;
    const a = arg.replace(/^\.?\//, '');
    if (FILES[a]) return a;
    const hit = Object.keys(FILES).filter(f => f.toLowerCase() === a.toLowerCase() || f.split('/').pop().toLowerCase() === a.toLowerCase() || f.toLowerCase().endsWith('/' + a.toLowerCase()));
    if (hit.length === 1) return hit[0];
    const pk = a.toUpperCase().replace(/^0X/, '0x');
    if (FILES['packets/' + pk]) return 'packets/' + pk;
    return null;
  };
  const playNotes = (notes, base = 0) => { notes.forEach((n, i) => G.tone({ f: G.NOTES[n] * (base ? 2 : 1), d: 0.32, delay: i * 0.36, type: 'triangle', v: 0.16 })); };
  const C = {
    help: () => print(`COMMANDS\n  ${cmd('ls')} [folder]          list files\n  ${cmd('cat')} <file>           read a file (or tap it on the right)\n  ${cmd('tide')}                 print the tide gauge table\n  ${cmd('play signal')}          play Entry 4471 through the audio chain\n  ${cmd('spectrum')}             show the signal as a picture\n  ${cmd('decode')} <packet> <key> decode a packet, e.g. decode 0x45 3\n  ${cmd('unlock')} <file> <code>   open a locked file\n  ${cmd('name')} <tune>          tell the terminal what the tune is\n  ${cmd('unredact')}             restore the redacted demands\n  ${cmd('reply')} y|n            answer channel 7\n  ${cmd('sky')}                  look up\n  ${cmd('status')}  ${cmd('hint')}  ${cmd('clear')}`),
    ls: (args) => {
      const dir = (args[0] || '').replace(/\/$/, '');
      const list = Object.keys(FILES).filter(visible).filter(f => !dir || f.startsWith(dir + '/'));
      if (!list.length) return print(`ls: ${dir}: no such folder`, 'err');
      return print(list.map(f => `${locked(f) ? '[LOCKED] ' : '         '}${cmd('cat ' + f)}`).join('\n'));
    },
    cat: (args) => {
      const f = resolve(args[0]);
      if (!f || !visible(f)) return print(`cat: ${args[0] || ''}: no such file`, 'err');
      if (locked(f)) {
        const F = FILES[f];
        return print(F.tune ? `${f}: LOCKED · KEYED TO THE SIGNAL.\nThis file opens when the terminal is told the name of the tune: ${cmd('name')} <tune>` : `${f}: LOCKED · ENTER CODE: ${cmd('unlock ' + f)} <code>\n${F.hint}`, 'warn');
      }
      P.read[f] = true; save(); paintSide();
      return print(FILES[f].t());
    },
    tide: () => {
      P.tide = true; save(); paintSide();
      return print(`R/V MERIDIAN · TIDE WATCH · PRINTOUT\nTIDAL DEVIATION vs. 30-year mean · port gauge and spare agree to ±0.00\n\nDAY   PORT     SPARE    NOTE\n214   +4.12%   +4.12%   steady\n215   +4.15%   +4.15%   steady\n216   +4.15%   +4.15%   steady\n217   +4.11%   +4.11%   dip\n218   +4.00%   +4.00%   exactly 4.00. nothing is exactly 4.00\n219   +4.21%   +4.21%   page missing from log\n220   +4.16%   +4.16%\n\nONLY THE DECIMALS MOVE.`);
    },
    play: (args) => {
      const what = (args[0] || 'signal').toLowerCase();
      G.unlock();
      if (what === 'signal' || what === '4471' || what === 'entry4471') {
        playNotes(TUNE);
        return print(`ENTRY 4471 · AUDIO CHAIN · PERIOD 9.0 S\n\n♪  ${TUNE.join(' ')}  ♪\n\nThe letters repeat every nine minutes. Every branch knows this tune.\n[ when you know it: ${cmd('name')} <tune> ]`);
      }
      const f = resolve(what);
      if (f && FILES[f].packet !== undefined) { const notes = BR[FILES[f].packet][0]; playNotes([notes, notes, 'C', notes]); return print(`PACKET ${PK[FILES[f].packet]} · carrier tone ${notes}`); }
      return print('play: nothing to play. Try ' + cmd('play signal'), 'err');
    },
    spectrum: () => {
      const F = { L: ['1000', '1000', '1000', '1000', '1111'], O: ['0110', '1001', '1001', '1001', '0110'], K: ['1001', '1010', '1100', '1010', '1001'], U: ['1001', '1001', '1001', '1001', '0110'], P: ['1110', '1001', '1110', '1000', '1000'], ' ': ['00', '00', '00', '00', '00'] };
      const word = 'LOOK UP';
      const rows = [0, 1, 2, 3, 4].map(r => word.split('').map(ch => F[ch][r].replace(/1/g, '▓').replace(/0/g, '░') + '░').join(''));
      const pad = s => '░░░' + s + '░░░';
      const lines = ['9k ┤' + pad('░'.repeat(rows[0].length)), ...rows.map((r, i) => (i === 2 ? '6k ┤' : '   ┤') + pad(r)), '3k ┤' + pad('░'.repeat(rows[0].length)), '   ┤' + '▂▃▅▇▅▃'.repeat(Math.ceil((rows[0].length + 6) / 6)).slice(0, rows[0].length + 6), '0  ┼' + '─'.repeat(rows[0].length + 6)];
      return print(`ENTRY 4471 · SPECTRUM · 0–9 kHz · 9.0 s window\n\n${lines.join('\n')}\n\nThere is a picture in the noise, written in the high band. Underneath it the carrier\nrepeats every 9.0 s. Somebody on this ship wrote that period down for a reason.`);
    },
    decode: (args) => {
      const f = resolve(args[0]);
      if (!f || FILES[f].packet === undefined) return print(`decode: give a packet, e.g. ${cmd('decode 0x45')} <key>. Packets: ${PK.map(p => cmd('cat ' + p)).join(' ')}`, 'err');
      const i = FILES[f].packet, pk = PK[i];
      if (P.decoded[pk]) return print(packetView(i));
      const k = parseInt(args[1], 10);
      if (isNaN(k)) return print(`decode ${pk}: needs a key (a number). The pencil rubbing on day 220 says what it is.`, 'warn');
      if (((k % 26) + 26) % 26 !== KEYSHIFT) {
        G.tone({ f: 140, d: 0.25, type: 'sawtooth', v: 0.08 });
        return print(`DECODING ${pk} WITH KEY ${k} ...\n\n${shift(packetPlain(i), KEYSHIFT - k).split('\n').slice(0, 3).join('\n')}\n\nCHECKSUM FAIL. That is not the key.`, 'err');
      }
      P.decoded[pk] = true; save(); paintSide();
      G.tone({ f: 523, f2: 1046, d: 0.3, type: 'triangle', v: 0.12 });
      let extra = '';
      const n = countDecoded();
      if (n === 7) extra = `\n\nALL SEVEN PACKETS DECODED.\nCARD WORDS, IN ORDER: ${BR.map(b => b[6]).join(' ')}\nThe demands in the packets match the redactions in ${cmd('cat helios/demands_review.txt')}. Run ${cmd('unredact')}.`;
      else extra = `\n\n${n}/7 decoded. Next: ${cmd('decode ' + PK.find(p => !P.decoded[p]) + ' ' + KEYSHIFT)}`;
      return print(`DECODING ${pk} WITH KEY ${k} ... 100%\n\n${packetPlain(i)}${extra}`, 'ok');
    },
    unlock: (args) => {
      const f = resolve(args[0]);
      if (!f) return print('unlock: which file?', 'err');
      const F = FILES[f];
      if (!F.lock) return print(F.tune ? `${f} is keyed to the signal. Use ${cmd('name')} <tune>.` : `${f} is not locked.`, 'warn');
      if (P.unlocked[f]) return C.cat([f]);
      const code = (args[1] || '').replace('%', '').replace(/^\+/, '');
      if (code === F.lock || code === F.lock.replace('.', '') || parseFloat(code) === parseFloat(F.lock)) {
        P.unlocked[f] = true; save(); paintSide(); G.tone({ f: 660, f2: 990, d: 0.25, type: 'triangle', v: 0.12 });
        return print(`CODE ACCEPTED · ${f} RECOVERED`, 'ok').then(() => C.cat([f]));
      }
      G.tone({ f: 140, d: 0.2, type: 'sawtooth', v: 0.08 });
      return print(`unlock ${f}: wrong code. ${F.hint}`, 'err');
    },
    name: (args) => {
      const t = args.join(' ').toLowerCase().replace(/[^a-z]/g, '');
      if (!t) return print(`name: what is the tune? ${cmd('play signal')} again if you need to.`, 'warn');
      if (/internationale|international|lintern/.test(t)) {
        P.tune = true; save(); paintSide(); G.unlock(); playNotes(TUNE, 1);
        return print(`MATCH · THE INTERNATIONALE\nThe one tune every branch shares. The signal is not noise. It is addressed.\n\nA file keyed to the signal has opened: ${cmd('cat berkeley/bulletin.txt')}`, 'ok');
      }
      return print(`NO MATCH for "${args.join(' ')}". It is the anthem of the workers of every country.`, 'err');
    },
    unredact: () => {
      if (countDecoded() < 7) return print(`unredact: ${countDecoded()}/7 packets decoded. Each packet carries one demand fragment.`, 'warn');
      P.unredacted = true; save(); paintSide();
      G.tone({ f: 392, f2: 784, d: 0.5, type: 'triangle', v: 0.12 });
      return print(`RESTORING DEMAND TEXT FROM DECODED PACKETS ...\n\n${demandsReview()}\n\nSeven branches. The same demand seven times.\nChannel 7 is still asking its question: ${cmd('reply y')} or ${cmd('reply n')}`, 'ok');
    },
    reply: (args) => {
      const a = (args[0] || '').toLowerCase();
      if (!P.unredacted) return print(`reply: the crew vote opens once the demands are known. ${countDecoded()}/7 packets decoded.`, 'warn');
      if (a !== 'y' && a !== 'n') return print(`reply: Y or N. ${cmd('reply y')}  ${cmd('reply n')}`, 'warn');
      P.replied = a; save(); paintSide();
      if (a === 'n') {
        G.tone({ f: 220, f2: 110, d: 0.8, type: 'sawtooth', v: 0.1 });
        return print(`TRANSMITTING N ON CHANNEL 7 ...\n\nCAPTAIN: "WE DO NOT ANSWER."\n\nThe tide comes in at +4.21%. Board resolution 17/Ω holds. The door stays open,\nand nobody walks through it.\n\nENDING · NO REPLY\nThe crew vote is open for twenty-four hours. You can still ${cmd('reply y')}.`, 'warn');
      }
      G.unlock(); playNotes(TUNE, 1);
      return print(`TRANSMITTING Y ON CHANNEL 7 ...\n\n> INCOMING · SOURCE: NO KNOWN SKY · ENTRY 4471\n"THIS IS SAMARA."\n"THE YEAR IS 2089."\n"WE CAN HEAR YOU."\n\nIn Berkeley, in 1985, the count closes at moonset: YES 1,204, NO 3.\nA new file has been written: ${cmd('cat notes_final.txt')}`, 'ok').then(() => print(`ENDING · THE INVITATION\n\nIt was never a demand. It was an invitation.\nRead what it came out of: ${cmd('open ussr')}  · or fly to the fleet: ${cmd('open jupiter')}`, 'ok'));
    },
    open: (args) => {
      const a = (args[0] || '').toLowerCase();
      if (a === 'ussr' || a === 'ussr2089') { location.href = '/#ussr2089'; return Promise.resolve(); }
      if (a === 'jupiter') { location.href = '/arcade/behind-jupiter/'; return Promise.resolve(); }
      return C.cat(args);
    },
    sky: () => print(`            .        *                  .\n      *           ____          .\n               .-'    '-.            *\n     .       .'  RED     '.     .\n            /    MOON   ◯ \\        (the white one)\n   *       |   1.7 ×      |    .\n            \\  LUNA     ./\n         .   '.  ▓▓   .'        *\n               '-.__.-'    .\n      .                          .\n\nTwo moons. The red one is ${P.replied === 'y' ? 'closer. Its door is open, and something is coming through.' : 'growing. Its central aperture is OPEN.'}`),
    status: () => print(objectives().map(([t, d]) => `${d ? '[x]' : '[ ]'} ${t}`).join('\n')),
    hint: () => {
      let h;
      if (!P.read['logs/day218.txt']) h = `Read the log: ${cmd('cat logs/day218.txt')}`;
      else if (!P.tide) h = `The tide gauge is mentioned in the log: ${cmd('tide')}`;
      else if (!P.unlocked['logs/day220.txt']) h = `Day 219's page is missing. One tide value is "exactly" something. Try ${cmd('unlock logs/day220.txt')} with it.`;
      else if (countDecoded() < 7) h = `"Decode with the period." The log gives the period in seconds. ${cmd('decode ' + PK.find(p => !P.decoded[p]))} <period>`;
      else if (!P.tune) h = `Optional, but worth it: ${cmd('play signal')} and name the tune with ${cmd('name')}.`;
      else if (!P.unredacted) h = cmd('unredact');
      else if (!P.replied) h = `Channel 7 asked a question. ${cmd('reply y')} or ${cmd('reply n')}`;
      else h = `You have answered. Look at the ${cmd('sky')}, or start over from the panel.`;
      return print('HINT · ' + h, 'warn');
    },
    clear: () => { term.innerHTML = ''; return Promise.resolve(); },
    reset: () => { Object.assign(P, { read: {}, unlocked: {}, decoded: {}, tune: false, unredacted: false, replied: null, tide: false }); save(); term.innerHTML = ''; paintSide(); return boot(); },
  };
  C.read = C.cat; C.more = C.cat; C.less = C.cat; C.dir = C.ls; C['?'] = C.help;

  const history = []; let hpos = 0;
  const run = (line) => {
    line = line.trim(); if (!line) return;
    skip = true; queue.then(() => { skip = false; });
    history.push(line); hpos = history.length;
    echo(line);
    const [c, ...args] = line.split(/\s+/);
    const f = C[c.toLowerCase()];
    queue = queue.then(() => { skip = false; });
    if (f) f(args); else print(`${c}: command not found. Type ${cmd('help')}.`, 'err');
  };
  $('form').addEventListener('submit', e => { e.preventDefault(); G.unlock(); run(input.value); input.value = ''; });
  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowUp') { e.preventDefault(); hpos = Math.max(0, hpos - 1); input.value = history[hpos] || ''; }
    if (e.key === 'ArrowDown') { e.preventDefault(); hpos = Math.min(history.length, hpos + 1); input.value = history[hpos] || ''; }
    if (e.key === 'Tab') {
      e.preventDefault();
      const parts = input.value.split(/\s+/);
      const last = parts.pop() || '';
      const pool = parts.length ? Object.keys(FILES).filter(visible).concat(PK) : Object.keys(C);
      const m = pool.filter(x => x.toLowerCase().startsWith(last.toLowerCase()));
      if (m.length === 1) { parts.push(m[0]); input.value = parts.join(' ') + ' '; }
      else if (m.length > 1) print(m.join('   '));
    }
  });
  root.addEventListener('click', e => {
    const b = e.target.closest('[data-run]');
    if (b) { G.unlock(); run(b.getAttribute('data-run')); input.focus({ preventScroll: true }); }
  });
  $('hint').addEventListener('click', () => run('hint'));
  $('reset').addEventListener('click', () => { if (confirmReset()) run('reset'); });
  function confirmReset() { const b = $('reset'); if (b.dataset.arm) { delete b.dataset.arm; b.textContent = 'START OVER'; return true; } b.dataset.arm = '1'; b.textContent = 'TAP AGAIN TO WIPE'; setTimeout(() => { delete b.dataset.arm; b.textContent = 'START OVER'; }, 3000); return false; }
  term.addEventListener('click', () => { if (!window.getSelection().toString()) input.focus({ preventScroll: true }); });

  /* ---------------------------------------------------------------- signal scope */
  const wave = $('wave').getContext('2d');
  let clockMin = 8 * 60;
  setInterval(() => { clockMin = (clockMin + 1) % 1440; $('clock').textContent = String(Math.floor(clockMin / 60)).padStart(2, '0') + ':' + String(clockMin % 60).padStart(2, '0'); }, 9000);
  const drawWave = (t) => {
    const c = wave.canvas, w = c.width, h = c.height;
    wave.fillStyle = '#0A0607'; wave.fillRect(0, 0, w, h);
    wave.strokeStyle = 'rgba(58,35,38,0.8)'; wave.lineWidth = 1;
    for (let x = 0; x < w; x += 30) { wave.beginPath(); wave.moveTo(x, 0); wave.lineTo(x, h); wave.stroke(); }
    // the red moon behind the trace
    const mr = 46 + (P.replied === 'y' ? 14 : 0);
    const gr = wave.createRadialGradient(w - 70, 60, 4, w - 70, 60, mr);
    gr.addColorStop(0, '#FF7A70'); gr.addColorStop(1, 'rgba(200,29,37,0.15)');
    wave.fillStyle = gr; wave.beginPath(); wave.arc(w - 70, 60, mr, 0, Math.PI * 2); wave.fill();
    wave.fillStyle = '#0A0607'; wave.beginPath(); wave.arc(w - 70, 60, mr * 0.28, 0, Math.PI * 2); wave.fill();
    wave.strokeStyle = '#F2B33D'; wave.lineWidth = 2; wave.beginPath();
    for (let x = 0; x < w; x++) {
      const k = (x + t / 40) / 30;
      const pulse = Math.exp(-Math.pow(((t / 1000) % 9) - x / w * 9, 2) * 3);
      const y = h * 0.62 + Math.sin(k * 2.1) * 6 + Math.sin(k * 5.3) * 3 + pulse * Math.sin(x * 0.9) * 28;
      x ? wave.lineTo(x, y) : wave.moveTo(x, y);
    }
    wave.stroke();
    wave.fillStyle = '#A89C95'; wave.font = "11px 'Share Tech Mono', monospace"; wave.fillText('ENTRY 4471 · PERIOD 9.0 S', 8, h - 8);
    if (!G.reduced) requestAnimationFrame(drawWave);
  };
  requestAnimationFrame(drawWave);

  /* ---------------------------------------------------------------- boot */
  function boot() {
    print(`HELIOS-ORBITAL MARINE SYSTEMS · R/V MERIDIAN · SIGNAL WATCH TERMINAL v2.20\nLINK ......... OK      GAUGE ......... +4.16%      CHANNEL 7 ......... OPEN\n`);
    if (Object.keys(P.read).length || countDecoded()) return print(`Session restored. ${cmd('status')} · ${cmd('hint')}`, 'warn');
    return print(`> INCOMING · SOURCE: NO KNOWN SKY · ENTRY 4471\n\nThe crew left this terminal running. Read what they found.\nTap any underlined command, or type it below. ${cmd('cat README.txt')}`);
  }
  paintSide();
  boot();
  let musicStarted = false;
  const startMusic = () => { if (musicStarted) return; musicStarted = true; G.music('/assets/radio/red-moon-carrier.mp3'); };
  root.addEventListener('pointerdown', startMusic, { once: true });
  input.addEventListener('keydown', startMusic, { once: true });
  setTimeout(() => input.focus({ preventScroll: true }), 300);
})();
