"""Scene 1 post: grade, optical effects, fear-flash treatment, fades, titles.

    python composite.py <render_dir> <out_dir> [--first 1 --last 744]

render_dir holds f####.png from Cycles (bedroom + office frames). Output is the
final picture sequence (1920x1080). Grain + temporal denoise are applied by
ffmpeg at encode time (see encode.sh).
"""
import os, sys, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import scene01_timing as T

W, H = 1920, 1080
FD = '/usr/share/fonts/opentype/inter/'


def shot_of(f):
    return next((s for s in T.SHOTS if s[1] <= f <= s[2]), None)


def smooth(t):
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)


def to_f(im):
    return np.asarray(im.convert('RGB'), np.float32) / 255.0


def to_im(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def blur(a, r):
    r = float(np.mean(r))
    if r <= 0:
        return a
    im = to_im(a)
    return to_f(im.filter(ImageFilter.GaussianBlur(r)))


_grid = {}


def radial(h, w):
    if (h, w) not in _grid:
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        nx = (x - w / 2) / (w / 2); ny = (y - h / 2) / (h / 2)
        _grid[(h, w)] = (np.sqrt(nx * nx * 1.0 + ny * ny * 0.8), nx, ny)
    return _grid[(h, w)]


def bloom(a, thr=0.72, r=None, amt=0.35):
    h, w = a.shape[:2]
    r = r or w / 90
    lum = a.max(2, keepdims=True)
    hi = a * np.clip((lum - thr) / (1 - thr), 0, 1)
    small = to_im(hi).resize((w // 4, h // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 4))
    b = to_f(small.resize((w, h), Image.BILINEAR))
    return a + b * amt


def chroma(a, amt):
    if amt <= 0:
        return a
    h, w = a.shape[:2]
    out = a.copy()
    s = 1 + amt
    for c, k in ((0, s), (2, 1 / s)):
        im = Image.fromarray((np.clip(a[..., c], 0, 1) * 255).astype(np.uint8))
        nw, nh = int(w * k), int(h * k)
        im = im.resize((nw, nh), Image.BILINEAR)
        l, t = (nw - w) // 2, (nh - h) // 2
        if k >= 1:
            im = im.crop((l, t, l + w, t + h))
        else:
            pad = Image.new('L', (w, h)); pad.paste(im, (-l, -t)); im = pad
        out[..., c] = np.asarray(im, np.float32) / 255
    return out


def grade_night(a):
    # gentle teal shadows / warm highlights, lifted blacks, a touch of contrast
    lum = (a @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    shadow = np.clip(1 - lum * 2.2, 0, 1)
    a = a + shadow * np.array([-0.004, 0.004, 0.014], np.float32)
    a = a * np.array([1.0, 0.995, 1.02], np.float32)
    a = 0.012 + a * 0.985
    a = np.clip(a, 0, 1)
    a = a + (a - a ** 2) * 0.06 * (a - 0.35)     # mild S-curve
    return a


def grade_fear(a, f, shot):
    lum = (a @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    a = lum * 0.82 + a * 0.18                         # near-monochrome
    a = a * np.array([0.86, 0.97, 1.12], np.float32)  # cold
    a = np.clip((a - 0.06) * 1.35, 0, 1)              # crushed, contrasty
    k = f - shot[1]; n = shot[2] - shot[1]
    flash = np.exp(-k / 1.2) * 0.9                     # white flash at each cut
    a = a + flash
    a = a * (1 - 0.6 * smooth((k - (n - 3)) / 3))      # dip at the end of each flash
    return a


def vignette(a, strength=0.35, power=2.2):
    h, w = a.shape[:2]
    r, _, _ = radial(h, w)
    v = 1 - strength * np.clip(r / 1.25, 0, 1) ** power
    return a * v[..., None]


def shake(a, f, amp):
    if amp <= 0:
        return a
    g = np.random.default_rng(f)
    dx, dy = (g.standard_normal(2) * amp).astype(int)
    return np.roll(np.roll(a, dy, 0), dx, 1)


def edge_blur(a, amount):
    """Blur outside the centre (attention narrowing)."""
    amount = float(np.mean(amount))
    if amount <= 0:
        return a
    h, w = a.shape[:2]
    r, _, _ = radial(h, w)
    m = np.clip((r - 0.25) / 0.7, 0, 1)[..., None] * amount
    return a * (1 - m) + blur(a, w / 160 * (0.5 + amount)) * m


# --------------------------------------------------------------- titles
def title_frame(f):
    s0 = T.SHOTS[-1][1]; k = f - s0
    im = Image.new('RGB', (W, H), (0, 0, 0))
    t_in = smooth(k / 26); sub_in = smooth((k - 36) / 22)
    out = smooth((T.LAST_FRAME - f) / 14)
    title = 'THE LAST LOGIN'
    ft = ImageFont.truetype(FD + 'Inter-Light.otf', 104)
    track = 26
    d = ImageDraw.Draw(im)
    widths = [d.textlength(ch, font=ft) for ch in title]
    total = sum(widths) + track * (len(title) - 1)
    layer = Image.new('L', (W, H), 0); dl = ImageDraw.Draw(layer)
    x = (W - total) / 2; y = H / 2 - 70
    for ch, wd in zip(title, widths):
        dl.text((x, y), ch, font=ft, fill=255, anchor='lm'); x += wd + track
    # login-field underline draws out, cursor blinks after the title
    lw = total * smooth((k - 10) / 30)
    dl.rectangle([(W - lw) / 2, y + 78, (W + lw) / 2, y + 80], fill=110)
    if k > 20 and (k // 12) % 2 == 0 and k < T.LAST_FRAME - s0 - 12:
        cx = (W + total) / 2 + 22
        dl.rectangle([cx, y - 46, cx + 5, y + 46], fill=200)
    glow = layer.filter(ImageFilter.GaussianBlur(14))
    a = np.asarray(layer, np.float32) / 255 * t_in + np.asarray(glow, np.float32) / 255 * 0.45 * t_in
    col = np.array([0.93, 0.95, 1.0], np.float32)
    img = a[..., None] * col
    sub = 'Sometimes, the biggest battle happens inside your own mind.'
    fs_ = ImageFont.truetype(FD + 'Inter-Regular.otf', 40)
    sl = Image.new('L', (W, H), 0); ds = ImageDraw.Draw(sl)
    ds.text((W / 2, y + 150), sub, font=fs_, fill=255, anchor='mm')
    img = img + (np.asarray(sl, np.float32) / 255 * sub_in * 0.78)[..., None] * np.array([0.82, 0.85, 0.9], np.float32)
    return np.clip(img * out, 0, 1)


# --------------------------------------------------------------- main
def process(f, src):
    sh = shot_of(f)
    if sh and sh[3] == 'Post':
        return title_frame(f)
    p = os.path.join(src, f'f{f:04d}.png')
    if not os.path.exists(p):
        return np.zeros((H, W, 3), np.float32)
    im = Image.open(p).convert('RGB')
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    a = to_f(im)
    name = sh[0]
    if sh[3] == 'Office':
        a = grade_fear(a, f, sh)
        a = chroma(a, 0.006)
        a = edge_blur(a, 0.7)
        a = vignette(a, 0.6, 1.8)
        a = shake(a, f, 6)
        return np.clip(a, 0, 1)
    a = grade_night(a)
    a = bloom(a, 0.70, amt=0.30 if not name.startswith('S2b') and not name.startswith('S3b') else 0.12)
    a = chroma(a, 0.0012)
    vs = 0.38
    if name == 'S3c_eyes':                       # world darkens + blurs around his eyes
        k = (f - sh[1]) / (sh[2] - sh[1])
        a = edge_blur(a, 0.25 + 0.6 * smooth(k))
        vs = 0.45 + 0.4 * smooth(k)
    if 412 <= f <= 420:                          # sink into the fear
        a = a * (1 - smooth((f - 412) / 8))
    if name == 'S5a_wake' and f < sh[1] + 3:     # jolt on waking
        a = shake(a, f, 4)
    a = vignette(a, vs)
    f0, f1 = T.FADE_OUT
    if f >= f0:
        a = a * (1 - smooth((f - f0) / (f1 - f0)))
    if f <= 8:
        a = a * smooth(f / 8)
    return np.clip(a, 0, 1)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--first', type=int, default=1); ap.add_argument('--last', type=int, default=T.LAST_FRAME)
    a = ap.parse_args()
    os.makedirs(a.dst, exist_ok=True)
    for f in range(a.first, a.last + 1):
        to_im(process(f, a.src)).save(os.path.join(a.dst, f'f{f:04d}.png'), compress_level=1)
        if f % 50 == 0:
            print('post', f, flush=True)
