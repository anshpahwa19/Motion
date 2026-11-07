"""Generates the phone-screen image sequence for Scene 1 (one PNG per frame).

Lock screen with notification -> unlock -> news feed that scrolls through the
three headlines. Text is rendered with Inter, large enough to stay readable in
the screen-insert shots. Output: project/assets/phone_ui/ui_####.png
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import scene01_timing as T

W, H = 1080, 2304
OUT = os.path.join(HERE, '..', 'assets', 'phone_ui')
FD = '/usr/share/fonts/opentype/inter/'


def font(w, s):
    return ImageFont.truetype(FD + {'b': 'Inter-Bold.otf', 'sb': 'Inter-SemiBold.otf', 'm': 'Inter-Medium.otf',
                                    'r': 'Inter-Regular.otf', 'l': 'Inter-Light.otf', 'xb': 'Inter-ExtraBold.otf',
                                    'th': 'Inter-Thin.otf'}[w], s)


def ease(t):
    t = min(max(t, 0), 1); return t * t * (3 - 2 * t)


def ease_out(t):
    t = min(max(t, 0), 1); return 1 - (1 - t) ** 3


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ''
    for w_ in words:
        test = (cur + ' ' + w_).strip()
        if d.textlength(test, font=f) <= width:
            cur = test
        else:
            lines.append(cur); cur = w_
    lines.append(cur)
    return lines


def rounded(d, box, r, fill):
    d.rounded_rectangle(box, r, fill=fill)


def wallpaper():
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    a = np.array([16, 22, 48]); b = np.array([60, 36, 82]); c = np.array([10, 12, 24])
    g = a * (1 - y) + b * y * (1 - y) * 2.2 + c * y
    blob = np.exp(-(((x - 0.75) / 0.35) ** 2 + ((y - 0.3) / 0.22) ** 2))[..., None] * np.array([40, 30, 70])
    img = np.clip(g[..., None].repeat(1, 1).reshape(H, 1, 3) + blob, 0, 255)
    img = np.broadcast_to(img, (H, W, 3)).astype(np.uint8)
    return Image.fromarray(img)


def status_bar(d, light=True):
    col = (235, 238, 245) if light else (30, 30, 34)
    d.text((70, 52), '2:17', font=font('sb', 40), fill=col)
    # signal / wifi / battery
    x = W - 250
    for i in range(4):
        h = 12 + i * 8; d.rounded_rectangle([x + i * 16, 88 - h, x + i * 16 + 10, 88], 3, fill=col)
    d.rounded_rectangle([W - 150, 58, W - 80, 92], 8, outline=col, width=3)
    d.rounded_rectangle([W - 145, 63, W - 112, 87], 5, fill=col)   # ~45% battery
    d.rectangle([W - 78, 68, W - 72, 82], fill=col)


def lock_screen(t_on, notif_t):
    img = wallpaper(); d = ImageDraw.Draw(img)
    status_bar(d)
    d.text((W / 2, 300), 'Saturday, 8 November', font=font('m', 46), fill=(225, 228, 240), anchor='mm')
    d.text((W / 2, 520), '2:17', font=font('l', 300), fill=(240, 242, 250), anchor='mm')
    # notification card slides in
    k = ease_out(notif_t)
    y0 = int(760 - (1 - k) * 120)
    card = Image.new('RGBA', (W - 100, 300), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, W - 100, 300], 44, fill=(38, 40, 58, int(235 * k)))
    cd.rounded_rectangle([40, 40, 110, 110], 18, fill=(230, 72, 60, int(255 * k)))
    cd.text((75, 75), 'T', font=font('xb', 46), fill=(255, 255, 255, int(255 * k)), anchor='mm')
    cd.text((135, 52), 'TechPulse', font=font('sb', 36), fill=(235, 236, 245, int(255 * k)))
    cd.text((W - 140, 52), 'now', font=font('r', 32), fill=(170, 172, 190, int(255 * k)), anchor='ra')
    lines = wrap(cd, T.HEADLINES[0][0], font('sb', 50), W - 180)
    for i, ln in enumerate(lines[:3]):
        cd.text((40, 140 + i * 64), ln, font=font('sb', 50), fill=(250, 250, 255, int(255 * k)))
    img.paste(card, (50, y0), card)
    d.rounded_rectangle([W / 2 - 140, H - 50, W / 2 + 140, H - 38], 6, fill=(230, 230, 240))
    return img


def thumb_art(i, w, h):
    """Small generated illustration per story (no stock imagery)."""
    rng = np.random.default_rng(10 + i)
    im = Image.new('RGB', (w, h)); d = ImageDraw.Draw(im)
    pal = [((32, 44, 92), (120, 90, 255), (60, 220, 255)),
           ((50, 36, 30), (240, 150, 60), (255, 220, 160)),
           ((24, 24, 30), (230, 70, 90), (255, 255, 255))][i]
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(pal[0][c] * (1 - t) + pal[1][c] * t * 0.6) for c in range(3)))
    if i == 0:   # AI generating a website: wireframe browser with sparkles
        d.rounded_rectangle([80, 60, w - 80, h - 60], 24, outline=pal[2], width=6)
        d.line([(80, 120), (w - 80, 120)], fill=pal[2], width=5)
        for k in range(3): d.ellipse([105 + k * 34, 82, 125 + k * 34, 102], fill=pal[2])
        for k in range(4):
            yy = 160 + k * 70
            d.rounded_rectangle([120, yy, 120 + int(rng.uniform(250, 600)), yy + 36], 10, fill=pal[1])
        for k in range(14):
            x, y = rng.uniform(w * 0.55, w - 100), rng.uniform(140, h - 100); s = rng.uniform(6, 18)
            d.polygon([(x, y - s * 2), (x + s * .5, y - s * .5), (x + s * 2, y), (x + s * .5, y + s * .5),
                       (x, y + s * 2), (x - s * .5, y + s * .5), (x - s * 2, y), (x - s * .5, y - s * .5)], fill=pal[2])
    elif i == 1:  # org chart with a faded node
        pts = [(w / 2, 110), (w / 4, 250), (w / 2, 250), (3 * w / 4, 250), (w / 6, 390), (w / 3, 390), (2 * w / 3, 390), (5 * w / 6, 390)]
        for a, b in ((0, 1), (0, 2), (0, 3), (1, 4), (1, 5), (3, 6), (3, 7)):
            d.line([pts[a], pts[b]], fill=pal[2], width=5)
        for k, (x, y) in enumerate(pts):
            c = (90, 80, 70) if k == 5 else pal[2]
            d.ellipse([x - 34, y - 34, x + 34, y + 34], fill=c)
    else:        # person silhouette vs. chip
        d.ellipse([w * 0.22 - 60, 120, w * 0.22 + 60, 240], fill=(200, 200, 210))
        d.rounded_rectangle([w * 0.22 - 110, 250, w * 0.22 + 110, h - 40], 60, fill=(200, 200, 210))
        cx, cy = w * 0.72, h / 2
        d.rounded_rectangle([cx - 120, cy - 120, cx + 120, cy + 120], 24, fill=pal[1])
        for k in range(-3, 4):
            for (x1, y1, x2, y2) in ((cx + k * 30, cy - 120, cx + k * 30, cy - 160), (cx + k * 30, cy + 120, cx + k * 30, cy + 160),
                                     (cx - 120, cy + k * 30, cx - 160, cy + k * 30), (cx + 120, cy + k * 30, cx + 160, cy + k * 30)):
                d.line([(x1, y1), (x2, y2)], fill=pal[1], width=8)
        d.text((cx, cy), 'AI', font=font('xb', 110), fill=(255, 255, 255), anchor='mm')
        d.text((w * 0.47, cy), 'vs', font=font('b', 70), fill=pal[2], anchor='mm')
    return im


CARD_H = 1180


def feed_canvas():
    """Tall canvas with header + 3 big story cards (+ a teaser below)."""
    total = 300 + CARD_H * 3 + 900
    img = Image.new('RGB', (W, total), (246, 246, 249)); d = ImageDraw.Draw(img)
    d.text((60, 150), 'Pulse', font=font('xb', 76), fill=(20, 20, 28))
    d.text((W - 60, 168), 'For you', font=font('m', 40), fill=(120, 120, 135), anchor='ra')
    for i, (head, src, ago) in enumerate(T.HEADLINES):
        y = 300 + i * CARD_H
        d.rounded_rectangle([40, y, W - 40, y + CARD_H - 60], 46, fill=(255, 255, 255))
        art = thumb_art(i, W - 80, 520)
        mask = Image.new('L', art.size, 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, art.width, art.height + 60], 46, fill=255)
        img.paste(art, (40, y), mask)
        d.rounded_rectangle([90, y + 570, 150, y + 630], 14, fill=[(230, 72, 60), (40, 110, 200), (20, 20, 20)][i])
        d.text((120, y + 600), ['T', 'B', 'D'][i], font=font('xb', 34), fill=(255, 255, 255), anchor='mm')
        d.text((170, y + 600), f'{src}  ·  {ago}', font=font('sb', 36), fill=(110, 110, 125), anchor='lm')
        fs = 82 if i == 2 else 74
        lines = wrap(d, head, font('b', fs), W - 180)
        for k, ln in enumerate(lines):
            d.text((90, y + 670 + k * int(fs * 1.18)), ln, font=font('b', fs), fill=(16, 16, 22))
        d.text((90, y + CARD_H - 140), ['2.4k likes   ·   318 comments', '1.1k likes   ·   204 comments', '9.8k likes   ·   2.1k comments'][i], font=font('m', 34), fill=(140, 140, 150))
    y = 300 + 3 * CARD_H
    d.rounded_rectangle([40, y, W - 40, y + 800], 46, fill=(255, 255, 255))
    d.text((90, y + 80), 'More stories', font=font('b', 52), fill=(30, 30, 38))
    for k in range(4):
        d.rounded_rectangle([90, y + 190 + k * 140, W - 90, y + 290 + k * 140], 20, fill=(236, 236, 241))
    return img


def feed_frame(canvas, scroll_px, focus_card=None, focus_amt=0.0):
    view = canvas.crop((0, int(scroll_px), W, int(scroll_px) + H)).copy()
    d = ImageDraw.Draw(view)
    # top bar overlay
    d.rectangle([0, 0, W, 130], fill=(246, 246, 249))
    status_bar(d, light=False)
    if focus_card is not None and focus_amt > 0:
        # dim everything except the focused card (attention narrowing)
        y = 300 + focus_card * CARD_H - scroll_px
        ov = Image.new('RGBA', view.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        a = int(110 * focus_amt)
        od.rectangle([0, 130, W, max(130, y)], fill=(10, 10, 20, a))
        od.rectangle([0, y + CARD_H - 60, W, H], fill=(10, 10, 20, a))
        view = Image.alpha_composite(view.convert('RGBA'), ov).convert('RGB')
        d = ImageDraw.Draw(view)
    d.rounded_rectangle([W / 2 - 140, H - 50, W / 2 + 140, H - 38], 6, fill=(30, 30, 30))
    return view


def scroll_for(card):
    return 300 + card * CARD_H - 300


def main(first=1, last=T.LAST_FRAME):
    os.makedirs(OUT, exist_ok=True)
    black = Image.new('RGB', (W, H), (0, 0, 0))
    canvas = feed_canvas()
    s0 = 0
    for f in range(first, last + 1):
        if f < T.PHONE_ON or f >= T.PHONE_LOCK:
            img = black
        elif f < T.PHONE_UNLOCK:
            img = lock_screen(ease((f - T.PHONE_ON) / 4), (f - T.PHONE_ON - 2) / 8)
            b = ease((f - T.PHONE_ON) / 3)       # wake brightness ramp
            img = Image.blend(black, img, b)
        else:
            u = (f - T.PHONE_UNLOCK) / 8
            if f < T.SCROLL_1[0]:
                sc = scroll_for(0) - 40
            elif f < T.SCROLL_2[0]:
                sc = scroll_for(0) - 40 + (scroll_for(1) - scroll_for(0)) * ease_out((f - T.SCROLL_1[0]) / (T.SCROLL_1[1] - T.SCROLL_1[0]))
            else:
                sc = scroll_for(1) - 40 + (scroll_for(2) - scroll_for(1) + 60) * ease_out((f - T.SCROLL_2[0]) / (T.SCROLL_2[1] - T.SCROLL_2[0]))
            sc = max(sc, 0)
            focus = None; fa = 0
            if f >= T.SCROLL_2[1] + 6:
                focus, fa = 2, ease((f - T.SCROLL_2[1] - 6) / 30)
            img = feed_frame(canvas, sc, focus, fa)
            if u < 1:   # unlock: lock screen slides up, feed fades in
                ls = lock_screen(1, 1)
                k = ease(u)
                comp = img.copy()
                comp.paste(ls.crop((0, int(H * k), W, H)), (0, 0))
                img = Image.blend(comp, img, k * 0.6)
        img.save(os.path.join(OUT, f'ui_{f:04d}.png'), optimize=False, compress_level=3)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(*(int(x) for x in a)) if a else main()
