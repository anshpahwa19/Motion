"""Full-film sound: Scene 1 mix + new score, ambiences, foley and dialogue for
Scenes 2-6 and the end cards. Writes project/assets/audio/film_mix.wav"""
import os, sys, json
import numpy as np
from scipy import signal
from scipy.io import wavfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import sound as SN
import film_timing as FT
from sound import SR, piano, reverb, chime, tick, heartbeat, rustle, click, knock, breath, boom, filt, noise, pink, adsr, tvec, power_down, creak, whoosh_rev

DUR = FT.total_frames() / FT.FPS
N = int(DUR * SR) + SR
OUT = os.path.join(HERE, '..', 'assets', 'audio')
rng = np.random.default_rng(21)
at = FT.at


def buf():
    return np.zeros((N, 2))


def place(dst, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.stack([x * l * 1.414, x * r * 1.414], 1)
    if i >= N:
        return
    j = min(N, i + len(x)); dst[i:j] += x[:j - i] * gain


def seg_env(t0, t1, fin=1.0, fout=1.0):
    e = np.zeros(N); a, b = int(t0 * SR), int(t1 * SR)
    e[a:b] = 1
    fi, fo = int(fin * SR), int(fout * SR)
    e[a:a + fi] *= np.linspace(0, 1, fi); e[b - fo:b] *= np.linspace(1, 0, fo)
    return e


def chord(dst, t, notes, dur, vel, spread=0.08, pan=0.0):
    for j, n in enumerate(notes):
        place(dst, piano(n, dur, vel), t + j * spread, 1.0, pan - 0.2 + 0.12 * j)


def arp(dst, t0, t1, notes, step, vel, pan=0.0):
    t = t0; k = 0
    while t < t1:
        place(dst, piano(notes[k % len(notes)], step * 2.2, vel * (0.85 + 0.3 * rng.random())), t, 1.0, pan + 0.3 * np.sin(k))
        t += step; k += 1


def build():
    music, amb, sfx, vo = buf(), buf(), buf(), buf()
    # ---------------- Scene 1: the original mix
    sr, s1 = wavfile.read(os.path.join(OUT, 'scene01_mix.wav')); s1 = s1.astype(np.float64) / 32768
    s1end = at('2a_morning_wide')
    k = int(s1end * SR); s1 = s1[:k].copy(); f = int(0.8 * SR); s1[-f:] *= np.linspace(1, 0, f)[:, None]
    place(sfx, s1, 0.0, 1.0)
    # ---------------- Scene 2: morning
    t2, t2o, t3 = at('2a_morning_wide'), at('2d_office_est'), at('3a_prompt_ots')
    birds = np.zeros(int((t2o - t2) * SR))
    for _ in range(26):
        tt = rng.uniform(0, len(birds) / SR - 0.4); d = rng.uniform(0.06, 0.18); tv = tvec(d)
        f0 = rng.uniform(2800, 4800); ch = np.sin(2 * np.pi * np.cumsum(f0 + 900 * np.sin(2 * np.pi * rng.uniform(8, 20) * tv)) / SR) * np.sin(np.pi * tv / d)
        i = int(tt * SR); birds[i:i + len(ch)] += ch * rng.uniform(0.02, 0.05)
    city = filt(noise(t2o - t2), 'low', 400) * 0.02 + filt(pink(t2o - t2), 'band', [300, 2000]) * 0.004
    place(amb, reverb(birds + city, 1.0, 0.3, seed=31), t2)
    ring = np.zeros(int(4.2 * SR))
    for k_ in range(10):     # digital alarm melody
        for j, fr in enumerate((1568, 1975, 2349)):
            tv = tvec(0.09); n_ = np.sin(2 * np.pi * fr * tv) * np.exp(-tv * 20) * 0.25
            i = int((k_ * 0.42 + j * 0.1) * SR); ring[i:i + len(n_)] += n_
    place(sfx, filt(ring, 'low', 6000), t2 + 0.2, 0.55, -0.5)
    place(sfx, click(1500, 0.04, 0.3), at('2b_alarm_cu', 2.6), 1, -0.4)
    place(sfx, breath(1.6, False, 0.14, 41), at('2b_alarm_cu', 0.6))
    place(sfx, rustle(1.0, 2600, 0.8, 42), at('2c_bed_edge', 0.0), 0.7)
    chord(music, t2 + 0.2, ['A2', 'E3', 'C4', 'E4'], 5.0, 0.26)
    for t, n_, v in ((t2 + 2.2, 'G4', 0.2), (t2 + 4.4, 'E4', 0.2), (t2 + 6.8, 'F4', 0.18), (t2 + 8.6, 'E4', 0.18)):
        place(music, piano(n_, 2.4, v), t, 1.0, 0.2)
    chord(music, t2o + 0.1, ['F2', 'C3', 'A3', 'E4'], 5.0, 0.22)
    chord(music, t2o + 5.0, ['D2', 'A2', 'F3', 'C4'], 5.0, 0.2)
    chord(music, t2o + 9.5, ['E2', 'B2', 'G3', 'D4'], 4.0, 0.18)
    # office room tone for scenes 2b-5
    tO, t6 = at('2d_office_est'), at('6a_night_wide')
    L = t6 - tO
    murmur = filt(noise(L), 'band', [250, 1100]) * (0.6 + 0.4 * np.abs(filt(noise(L), 'low', 3))) * 0.012
    hum = filt(noise(L), 'low', 180) * 0.012 + np.sin(2 * np.pi * 120 * tvec(L)) * 0.0015
    oamb = murmur + hum
    for _ in range(int(L * 1.3)):   # distant keyboards
        tt = rng.uniform(0, L - 0.5); burst = np.zeros(int(0.5 * SR))
        for c in range(rng.integers(3, 9)):
            cl = click(rng.uniform(1800, 3200), 0.02, 0.03); i = int(rng.uniform(0, 0.45) * SR); burst[i:i + len(cl)] += cl
        i = int(tt * SR); oamb[i:i + len(burst)] += filt(burst, 'low', 3500) * 0.5
    place(amb, np.stack([oamb, np.roll(oamb, 900)], 1), tO)
    place(sfx, click(900, 0.06, 0.25) + knock(300, 0.06, 0.1)[:int(0.06 * SR)], at('2e_desk_side', 1.2), 1, -0.3)   # lid
    # ---------------- Scene 3: the machine (tense pulse)
    t3, t3e = at('3a_prompt_ots'), at('4a_test_wide')
    pulse_notes = ['D3', 'A3', 'D4', 'F4', 'A4', 'F4', 'D4', 'A3']
    arp(music, t3 + 1.0, t3e - 1.5, pulse_notes, 0.25, 0.14, 0.1)
    chord(music, t3, ['D2', 'A2', 'D3'], 7.0, 0.28)
    chord(music, t3 + 8.0, ['A#1', 'F2', 'A#2'], 7.0, 0.28)
    chord(music, t3 + 16.0, ['G1', 'D2', 'G2'], 7.0, 0.3)
    chord(music, t3 + 23.0, ['A1', 'E2', 'A2'], 6.0, 0.3)
    for k_ in range(int((t3e - t3) / 1.0)):   # clock-like tick (the machine never stops)
        place(sfx, tick(0.5), t3 + k_ * 0.5, 0.06, 0.3)
    for tt in np.arange(at('3a_prompt_ots', 0.2), at('3a_prompt_ots', 3.8), 0.11):   # his typing
        place(sfx, click(rng.uniform(2200, 3400), 0.02, 0.09), tt + rng.uniform(0, 0.04), 1, -0.2)
    gs, ge = at('3b_ai_generate'), at('3b_ai_generate', 6.0)
    for k_, tt in enumerate(np.linspace(gs + 0.2, ge - 0.4, 24)):   # each generated screen: a digital blip
        tv = tvec(0.16); fr = 900 + 60 * k_
        place(sfx, np.sin(2 * np.pi * fr * tv) * np.exp(-tv * 24) * 0.12 + np.sin(2 * np.pi * fr * 2 * tv) * np.exp(-tv * 30) * 0.05, tt, 1, np.sin(k_))
    sw = filt(noise(ge - gs), 'band', [2000, 8000]) * np.linspace(0.0, 0.05, int((ge - gs) * SR)); place(sfx, sw, gs)
    place(sfx, chime() * 0.7, at('3d_ai_result', 0.3), 0.5)
    place(sfx, heartbeat(0.25), at('3f_doubt', 0.5)); place(sfx, heartbeat(0.25), at('3f_doubt', 1.4)); place(sfx, heartbeat(0.22), at('3f_doubt', 2.3))
    # ---------------- Scene 4: the human factor (tender)
    t4, t5 = at('4a_test_wide'), at('5a_sketch')
    chord(music, t4 + 0.3, ['F2', 'C3', 'A3', 'C4'], 6.0, 0.24)
    chord(music, at('4d_arjun_realises', 0.0), ['D2', 'A2', 'F3', 'A3'], 6.0, 0.24)
    chord(music, at('4e_two_shot', 0.5), ['A#1', 'F2', 'D3', 'A3'], 6.0, 0.24)
    chord(music, at('4g_arjun_thinks', 0.0), ['C2', 'G2', 'E3', 'G3'], 6.0, 0.26)
    for t, n_, v in ((at('4d_arjun_realises', 1.0), 'A4', 0.2), (at('4d_arjun_realises', 2.6), 'C5', 0.18), (at('4e_two_shot', 1.5), 'D5', 0.2),
                     (at('4e_two_shot', 3.2), 'C5', 0.18), (at('4g_arjun_thinks', 0.8), 'E5', 0.2), (at('4g_arjun_thinks', 2.4), 'G4', 0.18)):
        place(music, piano(n_, 2.6, v), t, 1.0, 0.25)
    for tt in np.arange(at('4e_two_shot', 3.9), at('4e_two_shot', 5.4), 0.09):   # pen on paper
        place(sfx, filt(noise(0.08), 'band', [2500, 7000]) * np.exp(-tvec(0.08) * 20) * 0.05, tt)
    for tt in np.arange(at('4f_notebook', 0.2), at('4f_notebook', 4.2), 0.1):
        place(sfx, filt(noise(0.09), 'band', [2500, 7000]) * np.exp(-tvec(0.09) * 18) * 0.06, tt)
    for k_ in range(3):
        place(sfx, click(1400, 0.02, 0.05), at('4b_bank_app', 1.0 + k_ * 0.9), 1, 0.1)
    # ---------------- Scene 5: a different way forward (uplifting, major)
    prog = [(['F2', 'C3', 'A3', 'C4'], 'F4'), (['C2', 'G2', 'E3', 'G3'], 'E4'), (['D2', 'A2', 'F3', 'A3'], 'D4'), (['A#1', 'F2', 'D3', 'F3'], 'F4')]
    tt = t5 + 0.2; k_ = 0
    while tt < t6 - 2.0:
        ch, mel = prog[k_ % 4]
        chord(music, tt, ch, 3.4, 0.24 + 0.02 * min(k_, 6))
        arp(music, tt + 0.5, tt + 3.6, [ch[1], ch[2], ch[3], mel], 0.375, 0.12 + 0.01 * min(k_, 6), -0.1)
        tt += 3.6; k_ += 1
    for t, n_ in ((at('5c_face_engaged', 0.5), 'A4'), (at('5c_face_engaged', 2.0), 'C5'), (at('5e_rao_success', 0.6), 'F5'), (at('5e_rao_success', 2.4), 'E5'),
                  (at('5f_golden_wide', 0.4), 'C5'), (at('5f_golden_wide', 2.0), 'A4')):
        place(music, piano(n_, 3.0, 0.24), t, 1.0, 0.25)
    for tt in np.arange(at('5c_face_engaged', 0.2), at('5c_face_engaged', 4.3), 0.12):
        place(sfx, click(rng.uniform(2200, 3400), 0.02, 0.08), tt + rng.uniform(0, 0.05), 1, -0.2)
    place(sfx, chime(), at('5d_result_test', 1.9), 0.4)
    place(sfx, creak(0.6, 0.08), at('5f_golden_wide', 2.2), 1, 0.2)
    for tt in np.arange(at('5a_sketch', 0.1), at('5a_sketch', 4.8), 0.09):
        place(sfx, filt(noise(0.08), 'band', [2000, 6000]) * np.exp(-tvec(0.08) * 22) * 0.045, tt)
    # ---------------- Scene 6: tomorrow is another day (calm)
    tE = at('E1_card')
    room = filt(pink(tE - t6), 'low', 800) * 0.009 + filt(noise(tE - t6), 'low', 140) * 0.012
    place(amb, np.stack([room, np.roll(room, 1100)], 1), t6)
    for k_ in range(int(tE - t6)):
        place(amb, tick(0.5), t6 + k_ + 0.3, 0.07, -0.35)
    chord(music, t6 + 0.3, ['F2', 'C3', 'A3', 'E4'], 7.0, 0.22)
    chord(music, at('6c_lamp_off', 0.0), ['D2', 'A2', 'F3', 'C4'], 7.0, 0.2)
    chord(music, at('6d_peace_cu', 0.5), ['A#1', 'F2', 'D3', 'A3'], 7.0, 0.18)
    chord(music, at('6e_overhead', 0.2), ['F2', 'C3', 'A3', 'C4'], 6.0, 0.18)
    place(sfx, knock(220, 0.25, 0.3), at('6b_phone_down', (97 + 110 - 97) / 24 - 0.0 + 4.5), 1, -0.5)
    place(sfx, click(1700, 0.04, 0.35), at('6c_lamp_off', (279 - 229) / 24), 1, -0.6)
    place(sfx, breath(2.2, False, 0.1, 51), at('6d_peace_cu', 1.0))
    # ---------------- End cards
    theme = [('F4', 0.0), ('A4', 0.9), ('C5', 1.8), ('D5', 3.0), ('C5', 4.4), ('A4', 6.0), ('G4', 7.4), ('F4', 9.0), ('E4', 10.6), ('F4', 12.0)]
    chord(music, tE + 0.1, ['F2', 'C3', 'A3'], 5.5, 0.26); chord(music, tE + 6.0, ['D2', 'A2', 'F3'], 5.0, 0.26)
    chord(music, tE + 11.0, ['A#1', 'F2', 'D3'], 5.5, 0.27); chord(music, at('E4_title', 0.0), ['F1', 'C2', 'A2', 'F3', 'C4', 'A4'], 4.6, 0.32)
    for n_, dt in theme:
        place(music, piano(n_, 2.8, 0.23), tE + 0.6 + dt, 1.0, 0.2)
    place(music, piano('F5', 4.0, 0.25), at('E4_title', 0.8), 1.0, 0.2)
    music = reverb(music, 3.0, 0.4, seed=33)
    # ---------------- voices
    meta = json.load(open(os.path.join(OUT, 'film_vo', 'lines.json')))
    duck = np.ones(N)
    for m in meta:
        sr_, x = wavfile.read(os.path.join(OUT, 'film_vo', m['file'])); x = x.astype(np.float64)
        if np.abs(x).max() > 2: x = x / 32768.0
        x = signal.resample_poly(x, SR, sr_); x = x / (np.abs(x).max() + 1e-9) * 0.5
        x = filt(x, 'high', 70)
        if m['voice'] == 'narrator':
            x = x + filt(x, 'low', 220) * 0.35
            place(vo, reverb(x, 0.6, 0.1, seed=9, bright=5000), m['start'], 1.0)
        else:   # in-scene dialogue: room reverb, slightly lower, panned to his side
            place(vo, reverb(filt(x, 'band', [120, 7000]), 0.9, 0.22, seed=12), m['start'], 0.85, -0.25)
        i0, i1 = int((m['start'] - 0.15) * SR), int((m['start'] + m['dur'] + 0.3) * SR)
        duck[max(i0, 0):min(i1, N)] = 0.55
    duck = np.convolve(duck, np.ones(4800) / 4800, 'same')
    s1n = int(s1end * SR)
    duck[:s1n] = 1.0
    music *= duck[:, None]; amb *= (0.6 + 0.4 * duck)[:, None]
    mix = music * 0.85 + amb + sfx + vo * 1.15
    fo = int((DUR - 1.2) * SR); mix[fo:] *= np.linspace(1, 0, N - fo)[:, None]
    mix = mix[:int(DUR * SR)]
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.89
    wavfile.write(os.path.join(OUT, 'film_mix.wav'), SR, (mix * 32767).astype(np.int16))
    print('film mix', DUR, 's')


if __name__ == '__main__':
    build()
