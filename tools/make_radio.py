#!/usr/bin/env python3
"""Compose and render the TIA Radio tracks. Original music, written from scratch in numpy.

    python3 tools/make_radio.py            # all tracks
    python3 tools/make_radio.py 2          # only track 2

Writes assets/radio/<slug>.mp3 and assets/radio/tracks.json (needs ffmpeg).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve, lfilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets' / 'radio'
SR = 44100
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
        'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def chord(name, octave=4):
    """'Am', 'F', 'Bb', 'Gm', 'A' -> midi notes of a triad plus the seventh for minors."""
    minor = name.endswith('m')
    root = NOTE[name[:-1] if minor else name] + 12 * (octave + 1)
    return [root, root + (3 if minor else 4), root + 7, root + (10 if minor else 11)]


def env(n, a, d, s, r, sus_len=None):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sus_len = n - a - d - r if sus_len is None else sus_len
    sus_len = max(0, sus_len)
    e = np.concatenate([np.linspace(0, 1, max(a, 1)), np.linspace(1, s, max(d, 1)), np.full(sus_len, s),
                        np.linspace(s, 0, max(r, 1))])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((f * t + phase) % 1.0) - 1


def pulse(f, n, width=0.5):
    t = np.arange(n) / SR
    return np.where((f * t) % 1.0 < width, 1.0, -1.0)


def tri(f, n):
    return 2 * np.abs(saw(f, n)) - 1


def onepole(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x)


def lowpass_sweep(x, c0, c1):
    """One-pole lowpass whose cutoff moves from c0 to c1 (done in blocks)."""
    out = np.empty_like(x)
    blocks = 64
    edges = np.linspace(0, len(x), blocks + 1).astype(int)
    zi = np.zeros(1)
    for b in range(blocks):
        c = c0 + (c1 - c0) * b / (blocks - 1)
        a = np.exp(-2 * np.pi * c / SR)
        seg = x[edges[b]:edges[b + 1]]
        y, zi = lfilter([1 - a], [1, -a], seg, zi=zi)
        out[edges[b]:edges[b + 1]] = y
    return out


def highpass(x, cutoff):
    return x - onepole(x, cutoff)


def reverb_ir(seconds, seed, damp=6000):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((2, n)) * np.exp(-t * 6.9 / seconds)
    ir[0] = onepole(ir[0], damp)
    ir[1] = onepole(ir[1], damp)
    ir[:, :int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    return ir / np.sqrt((ir ** 2).sum(axis=1, keepdims=True))


class Track:
    def __init__(self, bpm, bars, seed):
        self.bpm = bpm
        self.beat = 60.0 / bpm
        self.bars = bars
        self.n = int(bars * 4 * self.beat * SR) + SR * 4
        self.bus = {k: np.zeros((2, self.n)) for k in ('drums', 'bass', 'pad', 'arp', 'lead', 'fx')}
        self.kick_env = np.zeros(self.n)
        self.rng = np.random.default_rng(seed)

    def at(self, bar, beat=0.0):
        return int(((bar * 4) + beat) * self.beat * SR)

    def add(self, bus, start, sig, pan=0.0, gain=1.0):
        if start >= self.n:
            return
        sig = sig[:self.n - start] * gain
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.bus[bus][0, start:start + len(sig)] += sig * l * 1.41
        self.bus[bus][1, start:start + len(sig)] += sig * r * 1.41

    # ---- instruments
    def kick(self, start, gain=1.0):
        n = int(0.45 * SR)
        t = np.arange(n) / SR
        f = 45 + 95 * np.exp(-t * 28)
        ph = 2 * np.pi * np.cumsum(f) / SR
        s = np.sin(ph) * np.exp(-t * 7.5) + 0.25 * np.exp(-t * 90) * self.rng.standard_normal(n) * 0.3
        self.add('drums', start, np.tanh(s * 1.6), gain=0.9 * gain)
        k = np.exp(-np.arange(int(0.3 * SR)) / SR * 9)
        e = min(len(k), self.n - start)
        self.kick_env[start:start + e] = np.maximum(self.kick_env[start:start + e], k[:e])

    def snare(self, start, gain=1.0):
        n = int(0.28 * SR)
        t = np.arange(n) / SR
        noise = highpass(self.rng.standard_normal(n), 900) * np.exp(-t * 16)
        tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 25)
        self.add('drums', start, 0.55 * noise + 0.45 * tone, pan=0.05, gain=0.5 * gain)

    def clap(self, start, gain=1.0):
        n = int(0.3 * SR)
        t = np.arange(n) / SR
        e = sum(np.exp(-np.clip(t - d, 0, None) * 60) * (t >= d) for d in (0, 0.011, 0.022)) + np.exp(-t * 12) * 0.6
        s = highpass(onepole(self.rng.standard_normal(n), 3500), 700) * e
        self.add('drums', start, s, pan=-0.05, gain=0.45 * gain)

    def hat(self, start, open_=False, gain=1.0, pan=0.2):
        n = int((0.22 if open_ else 0.05) * SR)
        t = np.arange(n) / SR
        s = highpass(self.rng.standard_normal(n), 7000) * np.exp(-t * (14 if open_ else 70))
        self.add('drums', start, s, pan=pan, gain=0.22 * gain)

    def bassnote(self, start, midi, dur, cutoff=700, gain=1.0, kind='saw'):
        n = int(dur * SR)
        f = hz(midi)
        osc = saw(f, n) + 0.5 * saw(f * 0.5, n) if kind == 'saw' else pulse(f, n, 0.42) * 0.7 + 0.4 * np.sin(2 * np.pi * f * 0.5 * np.arange(n) / SR)
        e = env(n, 0.004, 0.12, 0.6, 0.05)
        sig = lowpass_sweep(osc, cutoff * 2.2, cutoff) * e
        self.add('bass', start, np.tanh(sig * 1.4), gain=0.32 * gain)

    def padchord(self, start, notes, dur, cutoff=1800, gain=1.0, bright=1.0):
        n = int(dur * SR)
        sig = np.zeros(n)
        for m in notes:
            for d in (-0.11, 0.0, 0.09):
                sig += saw(hz(m) * 2 ** (d / 12), n, phase=self.rng.random())
        sig /= len(notes) * 3
        e = env(n, min(1.2, dur * 0.35), 0.4, 0.85, min(1.4, dur * 0.4))
        sig = onepole(onepole(sig, cutoff * bright), cutoff * 1.6 * bright) * e
        self.add('pad', start, sig, pan=self.rng.uniform(-0.3, 0.3), gain=0.55 * gain)

    def pluck(self, start, midi, dur=0.25, gain=1.0, pan=0.0, bus='arp', width=0.35, cutoff=3200):
        n = int(max(dur, 0.12) * SR) + int(0.25 * SR)
        f = hz(midi)
        osc = pulse(f, n, width) * 0.6 + saw(f * 1.003, n) * 0.4
        t = np.arange(n) / SR
        sig = lowpass_sweep(osc * np.exp(-t * 7), cutoff, cutoff * 0.25)
        self.add(bus, start, sig, pan=pan, gain=0.22 * gain)

    def leadnote(self, start, midi, dur, gain=1.0, pan=0.0):
        n = int(dur * SR)
        t = np.arange(n) / SR
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t * 3 - 0.3, 0, 1)
        ph = 2 * np.pi * np.cumsum(hz(midi) * vib) / SR
        osc = 0.6 * np.sin(ph) + 0.3 * (2 / np.pi) * np.arcsin(np.sin(ph)) + 0.12 * np.sin(2 * ph)
        e = env(n, 0.03, 0.2, 0.75, min(0.25, dur * 0.4))
        self.add('lead', start, onepole(osc * e, 4200), pan=pan, gain=0.24 * gain)

    def blip(self, start, f, gain=1.0, pan=0.0):
        n = int(0.09 * SR)
        t = np.arange(n) / SR
        self.add('fx', start, np.sin(2 * np.pi * f * t) * env(n, 0.002, 0.02, 0.6, 0.03), pan=pan, gain=0.12 * gain)

    def riser(self, start, dur, gain=1.0):
        n = int(dur * SR)
        t = np.linspace(0, 1, n)
        s = lowpass_sweep(self.rng.standard_normal(n), 300, 9000) * t ** 2
        self.add('fx', start, s, gain=0.18 * gain)

    # ---- mix
    def render(self, verb=2.4, master=0.9):
        duck = 1 - 0.55 * self.kick_env
        mix = np.zeros((2, self.n))
        sends = {'drums': 0.08, 'bass': 0.0, 'pad': 0.45, 'arp': 0.35, 'lead': 0.4, 'fx': 0.5}
        vol = {'drums': 1.0, 'bass': 1.0, 'pad': 0.9, 'arp': 0.8, 'lead': 0.85, 'fx': 0.8}
        wet = np.zeros((2, self.n))
        for k, b in self.bus.items():
            if k in ('pad', 'bass', 'arp'):
                b = b * duck
            mix += b * vol[k]
            wet += b * sends[k]
        ir = reverb_ir(verb, 7)
        for c in range(2):
            mix[c] += fftconvolve(wet[c], ir[c])[:self.n] * 0.35
        # gentle master: highpass rumble, soft clip, normalise
        mix = np.array([highpass(ch, 28) for ch in mix])
        mix = np.tanh(mix * 1.1)
        mix *= master / (np.max(np.abs(mix)) + 1e-9)
        # trim trailing silence to the end of the reverb tail
        last = np.nonzero(np.max(np.abs(mix), axis=0) > 1e-3)[0]
        end = last[-1] + int(0.5 * SR) if len(last) else self.n
        mix = mix[:, :end]
        fade = int(1.5 * SR)
        mix[:, -fade:] *= np.linspace(1, 0, fade)
        return mix


def motif(rng, scale, length=8, span=7):
    """A short melody: scale degrees, with a lean towards steps and a return to the tonic."""
    deg = [0]
    for _ in range(length - 1):
        step = rng.choice([-2, -1, -1, 1, 1, 2, 0, 3, -3])
        deg.append(int(np.clip(deg[-1] + step, -2, span)))
    deg[-1] = rng.choice([0, 2, 4])
    return deg


def scale_note(scale, root, d):
    o, i = divmod(d, len(scale))
    return root + scale[i] + 12 * o


MINOR = [0, 2, 3, 5, 7, 8, 10]
PHRYG = [0, 1, 3, 5, 7, 8, 10]
DORIAN = [0, 2, 3, 5, 7, 9, 10]


def compose(spec):
    """Arrange one track from a small spec."""
    bpm, prog, key, scale, seed = spec['bpm'], spec['prog'], spec['key'], spec['scale'], spec['seed']
    form = spec['form']            # list of (section, bars)
    bars = sum(b for _, b in form)
    T = Track(bpm, bars, seed)
    rng = T.rng
    root = NOTE[key] + 60
    m1 = motif(rng, scale)
    m2 = motif(rng, scale)
    rhythm = spec.get('rhythm', [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5])
    bar = 0
    for sec, nb in form:
        for i in range(nb):
            b = bar + i
            ch = chord(prog[b % len(prog)], 3)
            ch_hi = [m + 12 for m in ch]
            s = T.at(b)
            whole = 4 * T.beat
            energy = {'intro': 0.3, 'build': 0.6, 'main': 1.0, 'break': 0.45, 'main2': 1.0, 'outro': 0.35}[sec]
            # pad
            if spec.get('pad', True):
                T.padchord(s, ch_hi[:3] + [ch_hi[3]], whole * 1.02, cutoff=900 + 1400 * energy,
                            gain={'intro': 2.2, 'outro': 2.0, 'break': 1.5}.get(sec, 0.9))
            # drums
            if sec in ('main', 'main2') or (sec == 'build' and spec.get('build_drums', True)):
                style = spec.get('drums', 'four')
                for q in range(4):
                    if style == 'four' or (style == 'half' and q in (0, 2)) or (style == 'break' and q in (0,) ) or \
                            (style == 'broken' and q in (0,)):
                        T.kick(T.at(b, q), gain=0.8 if sec == 'build' else 1.0)
                    if style == 'broken' and q == 2:
                        T.kick(T.at(b, 2.5))
                    if sec != 'build' and ((style in ('four', 'broken') and q in (1, 3)) or (style == 'half' and q == 2)):
                        (T.clap if spec.get('clap') else T.snare)(T.at(b, q))
                    T.hat(T.at(b, q + 0.5), open_=(style == 'four' and sec != 'build'), gain=0.8)
                    if spec.get('sixteenths') and sec != 'build':
                        T.hat(T.at(b, q + 0.25), gain=0.35, pan=-0.25)
                        T.hat(T.at(b, q + 0.75), gain=0.35, pan=-0.25)
            # bass
            if sec in ('main', 'main2', 'build') or (sec == 'break' and spec.get('break_bass')):
                pat = spec.get('bass', [0, 0.5, 1.5, 2, 2.5, 3.5])
                for p in pat:
                    note = ch[0] - 12 + (12 if (p * 2) % 2 == 1 and spec.get('octave_bass') else 0)
                    T.bassnote(T.at(b, p), note, T.beat * 0.45, cutoff=380 + 500 * energy, kind=spec.get('bass_kind', 'saw'))
            # arpeggio
            if sec in ('build', 'main', 'main2', 'break') and spec.get('arp', True):
                order = [0, 1, 2, 3, 2, 1, 2, 3] if spec.get('arp_up_down') else [0, 2, 1, 3, 0, 2, 3, 1]
                step = spec.get('arp_step', 0.5)
                k = 0
                q = 0.0
                while q < 4 - 1e-6:
                    T.pluck(T.at(b, q), ch_hi[order[k % len(order)]] + 12, dur=T.beat * step,
                            gain=0.7 + 0.3 * energy, pan=0.35 if k % 2 else -0.35,
                            cutoff=1600 + 2600 * energy)
                    k += 1
                    q += step
            # lead: phrases of two bars, A A' B A
            if sec in ('main', 'main2') and spec.get('lead', True):
                phrase = (i // 2) % 4
                mot = m1 if phrase in (0, 1, 3) else m2
                half = i % 2
                for j, r in enumerate(rhythm):
                    idx = j + half * len(rhythm) // 2
                    if idx >= len(mot) * (half + 1) or (half == 0 and j >= len(rhythm) // 2) and False:
                        continue
                    if j >= len(mot):
                        break
                    d = mot[j] + (1 if phrase == 1 and j == len(mot) - 1 else 0)
                    if half:
                        d = mot[len(mot) - 1 - j]
                    dur = (rhythm[j + 1] - r if j + 1 < len(rhythm) else 4 - r) * T.beat
                    T.leadnote(T.at(b, r), scale_note(scale, root + 12 * spec.get('lead_oct', 0), d), dur * 0.95, gain=0.9)
            # fx
            if spec.get('blips') and sec in ('intro', 'break', 'outro', 'main', 'main2'):
                for q in range(8):
                    if rng.random() < 0.18:
                        T.blip(T.at(b, q * 0.5), hz(scale_note(scale, root + 24, rng.integers(0, 8))), pan=rng.uniform(-0.7, 0.7))
            if sec == 'build' and i == nb - 1:
                T.riser(T.at(b), whole)
        bar += nb
    return T.render(verb=spec.get('verb', 2.4))


TRACKS = [
    {'slug': 'plan-fulfilled', 'title': 'Plan Fulfilled', 'bpm': 116, 'key': 'A', 'scale': MINOR, 'seed': 11,
     'prog': ['Am', 'F', 'C', 'G'], 'form': [('intro', 8), ('build', 8), ('main', 16), ('break', 8), ('main2', 16), ('outro', 8)],
     'drums': 'four', 'sixteenths': True, 'arp_step': 0.25},
    {'slug': 'behind-jupiter', 'title': 'Behind Jupiter', 'bpm': 128, 'key': 'D', 'scale': MINOR, 'seed': 26,
     'prog': ['Dm', 'Bb', 'Gm', 'A'], 'form': [('intro', 4), ('build', 8), ('main', 16), ('break', 8), ('main2', 16), ('outro', 4)],
     'drums': 'four', 'sixteenths': True, 'clap': True, 'arp_step': 0.25, 'arp_up_down': True, 'octave_bass': True,
     'bass': [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]},
    {'slug': 'red-moon-carrier', 'title': 'Red Moon Carrier Wave', 'bpm': 84, 'key': 'E', 'scale': PHRYG, 'seed': 404,
     'prog': ['Em', 'F', 'Em', 'Dm'], 'form': [('intro', 8), ('build', 8), ('main', 12), ('break', 8), ('main2', 12), ('outro', 8)],
     'drums': 'half', 'blips': True, 'lead': False, 'arp_step': 0.5, 'bass_kind': 'pulse', 'bass': [0, 1.5, 2.5], 'verb': 3.6},
    {'slug': 'administration-of-things', 'title': 'The Administration of Things', 'bpm': 100, 'key': 'C', 'scale': MINOR, 'seed': 3,
     'prog': ['Cm', 'Ab', 'Eb', 'Bb'], 'form': [('intro', 8), ('build', 8), ('main', 16), ('break', 8), ('main2', 16), ('outro', 8)],
     'drums': 'broken', 'clap': True, 'arp_step': 0.5, 'bass': [0, 0.75, 1.5, 2.5, 3, 3.5],
     'rhythm': [0, 1, 1.5, 2, 3, 3.5]},
    {'slug': 'long-generation', 'title': 'The Long Generation', 'bpm': 74, 'key': 'F#', 'scale': DORIAN, 'seed': 8,
     'prog': ['F#m', 'D', 'A', 'E'], 'form': [('intro', 8), ('build', 4), ('main', 12), ('break', 8), ('main2', 12), ('outro', 8)],
     'drums': 'half', 'build_drums': False, 'arp_step': 0.5, 'arp_up_down': True, 'bass': [0, 2.5], 'verb': 3.2,
     'rhythm': [0, 1.5, 2, 3], 'lead_oct': 0},
    {'slug': 'storm-heaven', 'title': 'Storm Heaven', 'bpm': 136, 'key': 'G', 'scale': MINOR, 'seed': 1871,
     'prog': ['Gm', 'Eb', 'Bb', 'F'], 'form': [('intro', 4), ('build', 8), ('main', 16), ('break', 4), ('main2', 16), ('outro', 4)],
     'drums': 'four', 'sixteenths': True, 'clap': True, 'arp_step': 0.25, 'octave_bass': True,
     'bass': [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5], 'lead_oct': 0},
]


def main(only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, spec in enumerate(TRACKS, 1):
        mp3 = OUT / f"{spec['slug']}.mp3"
        if only is None or only == i:
            mix = compose(spec)
            pcm = (np.clip(mix.T, -1, 1) * 32767).astype('<i2').tobytes()
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', '-',
                            '-c:a', 'libmp3lame', '-b:a', '160k', '-metadata', f"title={spec['title']}",
                            '-metadata', 'artist=TIA Labs', '-metadata', 'album=TIA Radio', str(mp3)], input=pcm, check=True)
            print('wrote', mp3.name, f'{mix.shape[1] / SR:.0f}s')
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(mp3)],
                                   capture_output=True, text=True).stdout.strip() or 0)
        manifest.append({'id': spec['slug'], 'title': spec['title'], 'artist': 'TIA Labs', 'src': f"/assets/radio/{spec['slug']}.mp3",
                         'dur': round(dur), 'bpm': spec['bpm']})
    (OUT / 'tracks.json').write_text(json.dumps({'station': 'TIA Radio', 'tracks': manifest}, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
