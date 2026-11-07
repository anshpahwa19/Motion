"""Scene 1 score + sound design + mix (all synthesized, 48 kHz stereo).

    python sound.py            -> project/assets/audio/scene01_mix.wav (+ stems)

Every cue time is derived from config/scene01_timing.py (frame -> seconds),
so picture and sound stay locked if the edit changes.
"""
import os, sys, json
import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import scene01_timing as T

SR = 48000
DUR = T.LAST_FRAME / T.FPS
N = int(DUR * SR)
OUT = os.path.join(HERE, '..', 'assets', 'audio')
rng = np.random.default_rng(11)


def fs(f):            # frame -> seconds (frame 1 starts at t=0)
    return (f - 1) / T.FPS


def buf(st=True):
    return np.zeros((N, 2)) if st else np.zeros(N)


def place(dst, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.stack([x * l * 1.414, x * r * 1.414], 1)
    if i >= N:
        return
    j = min(N, i + len(x)); x = x[:j - i]
    if i < 0:
        x = x[-i:]; i = 0
    dst[i:i + len(x)] += x * gain


def tvec(d):
    return np.arange(int(d * SR)) / SR


def sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output='sos')


def filt(x, kind, f, order=2):
    return signal.sosfilt(sos(kind, f, order), x, axis=0)


def noise(d):
    return rng.standard_normal(int(d * SR))


def pink(d):
    n = int(d * SR); X = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR); f[0] = 1
    return np.fft.irfft(X / np.sqrt(f), n) * 30


def adsr(n, a, d, s, r, sr=SR):
    a, d, r = int(a * sr), int(d * sr), int(r * sr)
    e = np.ones(n) * s
    e[:a] = np.linspace(0, 1, a) if a else e[:a]
    e[a:a + d] = np.linspace(1, s, len(e[a:a + d]))
    if r:
        e[-r:] *= np.linspace(1, 0, len(e[-r:]))
    return e


def reverb(x, t60=2.4, wet=0.35, pre=0.02, seed=1, bright=6000):
    g = np.random.default_rng(seed)
    n = int(t60 * SR)
    t = np.arange(n) / SR
    irs = []
    for c in range(2):
        ir = g.standard_normal(n) * np.exp(-6.9 * t / t60)
        ir = filt(ir, 'low', bright)
        ir[:int(pre * SR)] = 0
        irs.append(ir / np.sqrt((ir ** 2).sum()))
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    y = np.stack([signal.fftconvolve(x[:, c], irs[c])[:len(x)] for c in range(2)], 1)
    return x * (1 - wet) + y * wet * 1.6


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}


def nm(s):
    name, octv = (s[:-1], int(s[-1]))
    name = name.replace('Bb', 'A#').replace('Eb', 'D#')
    return 12 * (octv + 1) + NOTE[name]


def piano(note, dur, vel=0.5):
    f0 = midi(nm(note) if isinstance(note, str) else note)
    L = dur + 2.5
    t = tvec(L)
    B = 0.00035
    y = np.zeros_like(t)
    for n in range(1, 14):
        fn = n * f0 * np.sqrt(1 + B * n * n)
        if fn > 14000:
            break
        decay = (0.55 + 0.42 * n) * (f0 / 261.6) ** 0.35
        amp = (1 / n ** 1.15) * (0.6 + 0.4 * vel) ** (n * 0.25)
        for det in (-0.7, 0.0, 0.8):                       # three strings, slight detune
            y += amp * np.exp(-t * decay) * np.sin(2 * np.pi * fn * (1 + det * 1e-4) * t + rng.uniform(0, 6.28))
    # two-stage decay (prompt + aftersound)
    y *= 0.65 * np.exp(-t * 1.2) + 0.35
    ham = filt(noise(0.012), 'low', 2500 + 3000 * vel) * np.exp(-np.arange(int(0.012 * SR)) / (0.003 * SR))
    y[:len(ham)] += ham * 0.6
    rel = np.ones_like(t); k = int(dur * SR)
    rel[k:] = np.exp(-(np.arange(len(t) - k)) / (0.35 * SR))
    y = y * rel * vel
    y = filt(y, 'low', 1800 + 6000 * vel)
    return y / 6


def tick(strength=1.0):
    d = 0.06; t = tvec(d)
    y = filt(noise(d), 'band', [2500, 6000]) * np.exp(-t * 180) * 0.6
    y += np.sin(2 * np.pi * 3100 * t) * np.exp(-t * 90) * 0.25
    y += np.sin(2 * np.pi * 900 * t) * np.exp(-t * 60) * 0.2
    return y * strength


def chime():
    d = 1.4; t = tvec(d); y = np.zeros_like(t)
    for t0, f in ((0.0, 1318.5), (0.11, 1760.0)):
        tt = np.clip(t - t0, 0, None); on = (t >= t0)
        for h, a in ((1, 1), (2.76, 0.25), (5.4, 0.08)):
            y += on * a * np.sin(2 * np.pi * f * h * tt) * np.exp(-tt * (5 + h * 2))
    return y * 0.35


def vibrate(d=0.42):
    t = tvec(d)
    y = np.sin(2 * np.pi * 168 * t) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 26 * t)))
    y = filt(y + 0.3 * noise(d), 'low', 600) * adsr(len(t), 0.01, 0.05, 0.9, 0.05)
    return y * 0.35


def rustle(d, bright=3500, amt=1.0, seed=0):
    g = np.random.default_rng(seed)
    t = tvec(d)
    env = np.convolve(np.abs(g.standard_normal(len(t))), np.ones(int(0.05 * SR)) / (0.05 * SR), 'same')
    env = env ** 2 * adsr(len(t), d * 0.3, 0.0, 1.0, d * 0.4)
    y = filt(g.standard_normal(len(t)), 'band', [300, bright]) * env
    return y / (np.abs(y).max() + 1e-9) * 0.25 * amt


def click(f=2200, d=0.03, amt=0.3):
    t = tvec(d)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 300) + filt(noise(d), 'high', 3000) * np.exp(-t * 500) * 0.4) * amt


def knock(f=180, d=0.25, amt=0.5):
    t = tvec(d)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 35) + np.sin(2 * np.pi * f * 2.3 * t) * np.exp(-t * 60) * 0.5
    y += filt(noise(d), 'band', [800, 4000]) * np.exp(-t * 120) * 0.5
    return y * amt


def heartbeat(amt=1.0):
    d = 0.5; t = tvec(d); y = np.zeros_like(t)
    for t0, a in ((0.0, 1.0), (0.17, 0.7)):
        tt = np.clip(t - t0, 0, None); on = t >= t0
        f = 55 * np.exp(-tt * 6) + 38
        y += on * a * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 18)
    y = np.tanh(y * 2.2)
    return filt(y, 'low', 180) * amt


def boom(amt=1.0, d=1.8):
    t = tvec(d)
    f = 70 * np.exp(-t * 3) + 28
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    y += filt(noise(d), 'low', 900) * np.exp(-t * 6) * 0.5
    return np.tanh(y * 1.5) * amt


def whoosh_rev(d=1.3, amt=0.5):
    t = tvec(d)
    y = filt(noise(d), 'band', [400, 5000]) * (t / d) ** 3
    return y * amt


def breath(d, inhale=True, amt=0.5, seed=3):
    g = np.random.default_rng(seed)
    t = tvec(d)
    x = g.standard_normal(len(t))
    y = filt(x, 'band', [600, 2400] if inhale else [350, 1600])
    y += 0.5 * filt(x, 'band', [2400, 5200])
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** (0.6 if inhale else 1.4)
    if inhale:
        env *= np.clip(t / (0.08), 0, 1)
    return y * env * amt


def power_down(amt=0.4):
    d = 0.9; t = tvec(d)
    f = 900 * np.exp(-t * 4) + 60
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3)
    y += np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * np.exp(-t * 4) * 0.3
    return y * amt


def creak(d=0.6, amt=0.25):
    t = tvec(d)
    f = 900 + 400 * np.sin(2 * np.pi * 1.7 * t)
    y = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) * (0.5 + 0.5 * np.sin(2 * np.pi * 23 * t)) ** 4
    return filt(y, 'band', [700, 3000]) * adsr(len(t), 0.1, 0.1, 0.8, 0.2) * amt


def distort(x, drive=2.5, crush=10000):
    y = np.tanh(x * drive) / np.tanh(drive)
    step = max(1, int(SR / crush))
    y = np.repeat(y[::step], step, axis=0)[:len(x)]
    return y


# ======================================================================= build
def build():
    os.makedirs(OUT, exist_ok=True)
    music, amb, sfx, fear, vo = buf(), buf(), buf(), buf(), buf()

    # ---------------- ambience: room tone + distant city + fan + clock
    room = filt(pink(DUR), 'low', 900) * 0.010
    city = filt(noise(DUR), 'low', 140) * 0.02 + filt(pink(DUR), 'band', [200, 1200]) * 0.004
    t = np.arange(N) / SR
    fan = filt(noise(DUR), 'band', [150, 1200]) * (0.55 + 0.45 * np.sin(2 * np.pi * 1.65 * t) ** 2) * 0.006
    fan += np.sin(2 * np.pi * 100 * t) * 0.0015
    ambm = room + city + fan
    # fear section: bedroom ambience drops out
    g = np.ones(N)
    a0, a1 = int(fs(421) * SR), int(fs(517) * SR)
    g[a0 - 2400:a0] = np.linspace(1, 0, 2400); g[a0:a1] = 0
    fanboost = np.ones(N); s5c = int(fs(595) * SR); fanboost[s5c:] = 1.8
    amb += np.stack([ambm * g * fanboost, np.roll(ambm, 1300) * g * fanboost], 1)
    for k in range(int(DUR)):                              # slow clock ticking
        tt = k + 0.35
        if fs(421) - 0.2 < tt < fs(517):
            continue
        lvl = 0.55
        if tt < fs(97) or fs(561) <= tt < fs(595):
            lvl = 1.0
        if tt > fs(T.FADE_OUT[1]):
            lvl *= max(0, 1 - (tt - fs(T.FADE_OUT[1])) / 2)
        place(amb, tick(lvl), tt, 0.10, -0.35)

    # ---------------- piano score (D minor, sparse)
    chords = [(0.15, ['D3', 'A3', 'E4', 'F4']), (4.15, ['A#2', 'F3', 'A3', 'D4']),
              (8.15, ['G2', 'D3', 'A3', 'A#3']), (12.15, ['A2', 'E3', 'A3', 'D4'])]
    for i, (t0, notes) in enumerate(chords):
        v = 0.42 if i < 3 else 0.32
        place(music, piano(notes[0], 3.9, v * 0.9), t0, 1.0, -0.2)
        for j, (dt, n) in enumerate(zip((0.55, 1.15, 1.9, 2.7), notes[1:] + [notes[1]])):
            place(music, piano(n, 2.5, v * 0.7), t0 + dt, 1.0, -0.1 + 0.15 * j)
    for t0, n, v in ((1.95, 'A4', 0.36), (3.0, 'G4', 0.28), (6.05, 'F4', 0.34), (9.9, 'E4', 0.3),
                     (11.2, 'D4', 0.25), (13.8, 'C#4', 0.22)):
        place(music, piano(n, 2.2, v), t0, 1.0, 0.2)
    # shot 5 / title
    place(music, piano('A5', 3.0, 0.22), fs(528), 1.0, 0.25)
    place(music, piano('D2', 4.0, 0.25), fs(566), 1.0, -0.2)
    place(music, piano('F4', 2.5, 0.18), fs(585), 1.0, 0.1)
    tt = fs(T.SHOTS[-1][1]) + 0.1
    for j, n in enumerate(['D3', 'A3', 'E4', 'F4', 'A4']):
        place(music, piano(n, 4.2, 0.3), tt + j * 0.09, 1.0, -0.3 + 0.15 * j)
    place(music, piano('D5', 3.4, 0.27), tt + 1.25, 1.0, 0.15)       # the emotional note
    music = reverb(music, 3.2, 0.42, seed=2)

    # tension drone (shot 3 onwards) with a creeping semitone
    d0, d1 = fs(217), fs(421)
    td = tvec(d1 - d0 + 1.0)
    x = np.zeros(len(td))
    for f, a in ((36.71, 1.0), (73.4, 0.5), (110.0, 0.25), (77.8, 0.0)):
        aa = a if f != 77.8 else 0.22 * np.clip((td - 3.0) / 3.0, 0, 1)
        x += aa * signal.sawtooth(2 * np.pi * f * td + rng.uniform(0, 6))
    cut = 140 + 520 * np.clip(td / (d1 - d0), 0, 1) ** 1.5
    y = np.zeros_like(x); zi = None
    blk = 2400
    for i in range(0, len(x), blk):          # time-varying low-pass
        sos_ = sos('low', float(cut[i]))
        seg, zi = signal.sosfilt(sos_, x[i:i + blk], zi=zi if zi is not None else signal.sosfilt_zi(sos_) * 0)
        y[i:i + blk] = seg
    y *= np.clip(td / 2.5, 0, 1) * np.clip((d1 - d0 + 0.6 - td) / 0.6, 0, 1) * 0.07
    place(music, reverb(y, 2.0, 0.3, seed=4), d0)

    # ---------------- phone & foley
    place(sfx, chime(), fs(T.PHONE_ON), 0.55, -0.4)
    place(sfx, vibrate(), fs(T.PHONE_ON), 0.6, -0.4); place(sfx, vibrate(0.3), fs(T.PHONE_ON) + 0.55, 0.5, -0.4)
    place(sfx, rustle(1.1, 3000, 0.9, 1), fs(116), 0.8, -0.3)
    place(sfx, rustle(0.6, 2500, 0.6, 2), fs(140), 0.7, -0.2)
    place(sfx, click(2600, 0.03, 0.22), fs(T.PHONE_UNLOCK), 1, -0.1)
    place(sfx, filt(noise(0.25), 'band', [1500, 6000]) * adsr(int(0.25 * SR), 0.05, 0.05, 0.6, 0.15) * 0.05, fs(T.PHONE_UNLOCK), 1, -0.1)
    for s0, s1 in (T.SCROLL_1, T.SCROLL_2):
        place(sfx, filt(noise(fs(s1) - fs(s0)), 'band', [2000, 7000]) * adsr(int((fs(s1) - fs(s0)) * SR), 0.05, 0.1, 0.5, 0.2) * 0.035, fs(s0), 1, -0.1)
        place(sfx, click(3200, 0.02, 0.08), fs(s0), 1, -0.1)
    # distant notification pings that dissolve into the drone (shot 3)
    for k, (tt, gl, lp) in enumerate(((9.6, 0.25, 6000), (10.5, 0.18, 3500), (11.3, 0.12, 2000), (12.1, 0.08, 1200))):
        c = filt(chime() * (1.0 if k % 2 else 0.8), 'low', lp)
        place(sfx, reverb(c, 2.5, 0.6, seed=5 + k), tt, gl, 0.5 - k * 0.3)
    place(sfx, click(1800, 0.04, 0.3), fs(T.PHONE_LOCK), 1, -0.2)
    place(sfx, rustle(0.9, 2800, 0.7, 3), fs(372), 0.7, -0.4)
    place(sfx, knock(210, 0.25, 0.32), fs(T.PUTDOWN), 1, -0.55)
    place(sfx, rustle(1.0, 3200, 1.0, 4), fs(398), 0.9, 0.2)

    # ---------------- fear sequence (distorted bus)
    place(fear, whoosh_rev(1.4, 0.35), fs(421) - 1.4)
    hits = [s[1] for s in T.SHOTS if s[3] == 'Office']
    for i, f in enumerate(hits):
        place(fear, boom(0.55 + 0.08 * i), fs(f))
        place(fear, filt(noise(0.35), 'band', [1500, 8000]) * np.exp(-tvec(0.35) * 9) * 0.25, fs(f), 1, 0.3 * (-1) ** i)
    hb_t = fs(373); bpm = 70
    while hb_t < fs(517) - 0.1:
        lvl = 0.35 if hb_t < fs(421) else 0.9
        place(fear, heartbeat(lvl), hb_t)
        hb_t += 60 / bpm
        bpm = min(bpm + 2.4, 112)
    hum = (np.sin(2 * np.pi * 120 * tvec(fs(517) - fs(421))) * 0.012 + filt(noise(fs(517) - fs(421)), 'band', [100, 400]) * 0.01)
    hum[int((fs(503) - fs(421)) * SR):] *= np.linspace(1, 0, len(hum) - int((fs(503) - fs(421)) * SR))
    place(fear, hum, fs(421))
    place(fear, power_down(0.35), fs(445))
    place(fear, click(1200, 0.05, 0.3), fs(450))
    place(fear, filt(noise(0.3), 'band', [2000, 7000]) * adsr(int(0.3 * SR), 0.1, 0.0, 1, 0.1) * 0.05, fs(458))
    place(fear, filt(noise(0.5), 'band', [3000, 9000]) * np.abs(np.sin(2 * np.pi * 14 * tvec(0.5))) * 0.06, fs(468))
    place(fear, knock(900, 0.12, 0.35), fs(478)); place(fear, knock(1100, 0.08, 0.15), fs(480))
    place(fear, creak(0.7, 0.18), fs(486))
    for r in range(6):
        place(fear, knock(90, 0.3, 0.35) + click(800, 0.03, 0.2)[:int(0.3 * SR)].sum() * 0, fs(503 + (5 - r) * 2 + 1), 1, -0.5 + 0.2 * r)
    fear = distort(reverb(fear, 1.6, 0.3, seed=6), 1.8, 14000) * 0.9
    # hard silence at the wake-up, then the gasp
    place(sfx, breath(0.55, True, 0.32, 7), fs(520))
    place(sfx, breath(1.7, False, 0.16, 8), fs(540))
    place(sfx, rustle(0.6, 2500, 0.6, 9), fs(523), 0.6, 0.3)

    # ---------------- voice-over
    meta = json.load(open(os.path.join(OUT, 'vo_lines.json')))
    duck = np.ones(N)
    for m in meta:
        sr, x = wavfile.read(os.path.join(OUT, m['file']))
        x = x.astype(np.float64)
        if x.dtype.kind == 'i' or np.abs(x).max() > 2:
            x = x / 32768.0
        x = signal.resample_poly(x, SR, sr)
        x = x / (np.abs(x).max() + 1e-9) * 0.5
        x = filt(x, 'high', 70)
        if m['voice'] == 'narrator':
            # warm, close: light low-shelf-ish boost + small room
            x = x + filt(x, 'low', 220) * 0.35
            st = reverb(x, 0.6, 0.10, seed=9, bright=5000)
            place(vo, st, m['start'], 1.0)
        else:
            # inner thought: narrower band, echo taps, larger reverb
            x = filt(x, 'band', [180, 6000])
            y = x.copy()
            for k, (dt, gg) in enumerate(((0.21, 0.45), (0.42, 0.28), (0.63, 0.16), (0.84, 0.09))):
                y = np.concatenate([y, np.zeros(int(0.9 * SR))]) if k == 0 else y
                i = int(dt * SR); y[i:i + len(x)] += x * gg
            st = reverb(y, 2.6, 0.45, seed=10, bright=4000)
            st[:, 0] *= 1.0; st[:, 1] = np.roll(st[:, 1], 300)
            place(vo, st, m['start'], 0.95)
        i0 = int((m['start'] - 0.15) * SR); i1 = int((m['start'] + m['dur'] + 0.3) * SR)
        duck[max(i0, 0):min(i1, N)] = 0.55
    duck = np.convolve(duck, np.ones(4800) / 4800, 'same')
    music *= duck[:, None]
    fear *= (0.35 + 0.65 * (duck[:, None] - 0.55) / 0.45)

    af = np.ones(N); a2 = int(27.0 * SR); af[a2:] = np.linspace(1, 0.15, N - a2)
    amb *= af[:, None]
    mix = music * 0.9 + amb * 1.0 + sfx * 1.0 + fear * 0.24 + vo * 1.15
    # silence slam at wake-up (21.5 s): everything except breath & room tone dips
    # master fade
    f0 = int(30.2 * SR); mix[f0:] *= np.linspace(1, 0, N - f0)[:, None]
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.89
    for name, x in (('stem_music', music), ('stem_ambience', amb), ('stem_sfx', sfx), ('stem_fear', fear), ('stem_vo', vo), ('scene01_mix', mix)):
        y = x / max(np.abs(x).max(), 1e-9) * 0.89 if name != 'scene01_mix' else x
        wavfile.write(os.path.join(OUT, name + '.wav'), SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    print('mix written', DUR, 's  peak', np.abs(mix).max())


if __name__ == '__main__':
    build()
