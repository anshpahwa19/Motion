"""Narration + dialogue for the full film (Kokoro-82M)."""
import sys, os, json
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import film_timing as FT
OUT = os.path.join(HERE, '..', 'assets', 'audio', 'film_vo')


def main(model, voices):
    os.makedirs(OUT, exist_ok=True)
    k = Kokoro(model, voices)
    narr = k.get_voice_style('am_onyx') * 0.62 + k.get_voice_style('am_michael') * 0.38
    rao = k.get_voice_style('hm_omega') * 0.7 + k.get_voice_style('am_fenrir') * 0.3
    meta = []
    for i, (shot, dt, text, who) in enumerate(FT.FILM_VO):
        style, speed = (narr, 0.88) if who == 'narrator' else (rao, 0.82)
        audio, sr = k.create(text, voice=style, speed=speed, lang='en-us')
        a = np.asarray(audio, np.float32); thr = 0.01 * np.abs(a).max(); nz = np.nonzero(np.abs(a) > thr)[0]
        a = a[max(nz[0] - int(0.03 * sr), 0): nz[-1] + int(0.12 * sr)]
        p = os.path.join(OUT, f'vo_{i:02d}.wav'); sf.write(p, a, sr)
        t0 = FT.at(shot, dt)
        meta.append(dict(file=os.path.basename(p), start=t0, dur=len(a) / sr, text=text, voice=who, sr=sr, shot=shot))
        print(f'{i:2d} {who:8s} {t0:6.2f}s +{len(a) / sr:4.2f}s  [{shot}] {text}')
    json.dump(meta, open(os.path.join(OUT, 'lines.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:3])
