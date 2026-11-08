"""Assemble THE LAST LOGIN (full film) picture from the EDL.

    python film_edit.py <renders_root> <out_dir> [--draft]

renders_root contains s1/, s2bed/, office/, s6/ (Cycles frames f####.png).
Screen inserts come from project/assets/film_ui/<name>/, cards are drawn here.
Missing render frames become a labelled placeholder (useful for drafts).
"""
import os, sys, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import composite as C
import film_timing as FT

W, H = 1920, 1080
FD = '/usr/share/fonts/opentype/inter/'
UI = os.path.join(HERE, '..', 'assets', 'film_ui')
SCENE_OF = {}
for e in FT.EDL:
    n = e[0]
    SCENE_OF[n] = 1 if n == 'S1' else (int(n[0]) if n[0].isdigit() else 7)


def smooth(t):
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)


def placeholder(label):
    im = Image.new('RGB', (W, H), (18, 18, 22)); d = ImageDraw.Draw(im)
    d.text((W / 2, H / 2), f'[render pending] {label}', font=ImageFont.truetype(FD + 'Inter-Medium.otf', 40), fill=(120, 120, 130), anchor='mm')
    return C.to_f(im)


def load(path, label):
    if not os.path.exists(path):
        return placeholder(label)
    im = Image.open(path).convert('RGB')
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    return C.to_f(im)


def grade_new(a, scene, name):
    a = C.grade_night(a)
    a = C.bloom(a, 0.72, amt=0.22)
    a = C.chroma(a, 0.001)
    vs = 0.30 if scene in (2, 3, 4, 5) else 0.38
    if name.startswith('3f'):
        vs = 0.45
    return C.vignette(a, vs)


def insert_fx(a, k, n):
    # gentle push-in, like a camera on a screen; slight vignette
    s = 1.0 + 0.035 * (k / max(n - 1, 1))
    im = C.to_im(a); w2, h2 = int(W * s), int(H * s)
    im = im.resize((w2, h2), Image.BICUBIC).crop(((w2 - W) // 2, (h2 - H) // 2, (w2 - W) // 2 + W, (h2 - H) // 2 + H))
    return C.vignette(C.to_f(im), 0.35)


CARDS = {
    'grow': ['AI may change your job.', "But don't let the fear of it", 'take away your ability to grow.'],
    'create': ["DON'T COMPETE WITH AI.", 'LEARN TO CREATE WITH IT.'],
    'questions': ['Because technology can generate answers,', 'but meaningful questions still need people.'],
}


def card(name, k, n):
    if name == 'title':
        f = FT.offsets()['E4_title'] + k
        # reuse the Scene 1 title design, timed to this card
        import scene01_timing as T1
        kk = k + (T1.SHOTS[-1][1])
        return title_card(k, n)
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    lines = CARDS[name]
    big = name == 'create'
    fnt = ImageFont.truetype(FD + ('Inter-SemiBold.otf' if big else 'Inter-Light.otf'), 78 if big else 60)
    lh = 112 if big else 92
    y0 = H / 2 - lh * (len(lines) - 1) / 2
    a_in = smooth(k / 18); a_out = smooth((n - 1 - k) / 14)
    for i, ln in enumerate(lines):
        li = smooth((k - 10 - i * 14) / 16) if not big else smooth((k - 6 - i * 22) / 14)
        dd = ImageDraw.Draw(im)
        layer = Image.new('L', (W, H), 0); ImageDraw.Draw(layer).text((W / 2, y0 + i * lh), ln, font=fnt, fill=255, anchor='mm')
        im = Image.fromarray(np.maximum(np.asarray(im), (np.asarray(layer) * li).astype(np.uint8)))
    a = np.asarray(im, np.float32) / 255 * a_in * a_out
    glow = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12)), np.float32) / 255
    col = np.array([0.93, 0.95, 1.0]) if not big else np.array([1.0, 0.86, 0.62])
    return np.clip((a[..., None] + glow[..., None] * 0.35) * col, 0, 1)


def title_card(k, n):
    import scene01_timing as T1
    s0 = T1.SHOTS[-1][1]
    # map this card's k onto the S1 title animation, compressed to n frames
    kk = int(k * (T1.LAST_FRAME - s0) / max(n - 1, 1))
    return C.title_frame(s0 + kk)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('out')
    ap.add_argument('--first', type=int, default=1); ap.add_argument('--last', type=int, default=FT.total_frames())
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    offs = FT.offsets()
    order = [e[0] for e in FT.EDL]
    for idx, e in enumerate(FT.EDL):
        name, src, s0, s1, _ = e
        n = s1 - s0 + 1
        scene = SCENE_OF[name]
        nxt = FT.EDL[idx + 1] if idx + 1 < len(FT.EDL) else None
        prv = FT.EDL[idx - 1] if idx > 0 else None
        for k in range(n):
            g = offs[name] + k
            if g < a.first or g > a.last:
                continue
            if src == 's1':
                img = C.process(s0 + k, os.path.join(a.root, 's1'))
                if s0 + k > s1 - 16:          # dip to black before Scene 2
                    img = img * (1 - smooth((s0 + k - (s1 - 16)) / 16))
            elif src.startswith('ui:'):
                img = insert_fx(load(os.path.join(UI, src[3:], f'f{s0 + k:04d}.png'), name), k, n)
            elif src.startswith('card:'):
                img = card(src[5:], k, n)
            else:
                img = grade_new(load(os.path.join(a.root, src, f'f{s0 + k:04d}.png'), f'{name} f{s0 + k}'), scene, name)
            # scene transitions: fade in after black, fade out before a new scene
            if src != 's1' and not src.startswith('card:'):
                if prv and SCENE_OF[prv[0]] != scene and k < 14:
                    img = img * smooth(k / 14)
                if nxt and SCENE_OF[nxt[0]] != scene and (n - 1 - k) < 14:
                    img = img * smooth((n - 1 - k) / 14)
            C.to_im(np.clip(img, 0, 1)).save(os.path.join(a.out, f'f{g:05d}.png'), compress_level=1)
        print('edited', name, flush=True)


if __name__ == '__main__':
    main()
