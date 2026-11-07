"""Voice-over for Scene 1 with Kokoro-82M (ONNX, Apache-2.0 weights).

Narrator : blend of 'am_onyx' (deep) + 'am_michael' (warm), unhurried.
Inner    : 'am_liam' - younger, closer; echo/reverb added in the mix.

    python tts.py <kokoro-v1.0.onnx> <voices-v1.0.bin>
Writes project/assets/audio/vo_XX.wav (24 kHz mono) + vo_lines.json
"""
import sys, os, json
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import scene01_timing as T

OUT = os.path.join(HERE, '..', 'assets', 'audio')


def main(model, voices):
    os.makedirs(OUT, exist_ok=True)
    k = Kokoro(model, voices)
    narr = k.get_voice_style('am_onyx') * 0.62 + k.get_voice_style('am_michael') * 0.38
    inner = k.get_voice_style('am_liam') * 0.8 + k.get_voice_style('am_michael') * 0.2
    meta = []
    for i, (t0, text, who) in enumerate(T.VO):
        style, speed = (narr, 0.86) if who == 'narrator' else (inner, 0.9)
        audio, sr = k.create(text, voice=style, speed=speed, lang='en-us')
        audio = np.asarray(audio, np.float32)
        # trim leading/trailing silence
        thr = 0.01 * np.abs(audio).max()
        nz = np.nonzero(np.abs(audio) > thr)[0]
        audio = audio[max(nz[0] - int(0.03 * sr), 0): nz[-1] + int(0.12 * sr)]
        p = os.path.join(OUT, f'vo_{i:02d}.wav')
        sf.write(p, audio, sr)
        meta.append(dict(file=os.path.basename(p), start=t0, dur=len(audio) / sr, text=text, voice=who, sr=sr))
        print(f'{i} {who:9s} {len(audio) / sr:5.2f}s  @{t0:5.2f}  "{text}"')
    json.dump(meta, open(os.path.join(OUT, 'vo_lines.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:3])
