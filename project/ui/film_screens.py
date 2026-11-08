"""Screen graphics for Scenes 2-6: the AI design tool, the banking app used in
the usability test, Arjun's notebook, the co-creation flow and the results.

Each screen is a function draw_<name>(t, W, H) -> PIL image (t = 0..1 progress).
They feed both the full-frame inserts (1920x1080) and the 3D monitors/phones.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FD = '/usr/share/fonts/opentype/inter/'
OUT = os.path.join(HERE, '..', 'assets', 'film_ui')


def F(w, s):
    return ImageFont.truetype(FD + {'b': 'Inter-Bold.otf', 'sb': 'Inter-SemiBold.otf', 'm': 'Inter-Medium.otf', 'r': 'Inter-Regular.otf',
                                    'l': 'Inter-Light.otf', 'xb': 'Inter-ExtraBold.otf', 'i': 'Inter-Italic.otf'}[w], int(s))


def ease(t):
    t = min(max(t, 0), 1); return t * t * (3 - 2 * t)


PROMPT = 'Design a complete mobile banking app: onboarding, home, send money, history.'
ACC = (124, 92, 255)


def app_chrome(W, H, title='Genie AI · Design', dark=True):
    bg = (22, 23, 28) if dark else (245, 245, 248)
    im = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(im); s = W / 1920
    d.rectangle([0, 0, W, 64 * s], fill=(32, 33, 40))
    d.ellipse([24 * s, 22 * s, 44 * s, 42 * s], fill=ACC)
    d.text((60 * s, 32 * s), title, font=F('sb', 26 * s), fill=(230, 230, 240), anchor='lm')
    return im, d, s


def mini_screen(d, x, y, w, h, kind, s, seed=0, polish=1.0):
    rng = np.random.default_rng(seed)
    d.rounded_rectangle([x, y, x + w, y + h], 14 * s, fill=(250, 250, 252))
    cols = [(88, 101, 242), (16, 163, 127), (240, 112, 60), (220, 60, 110)]
    c = cols[seed % 4]
    d.rectangle([x, y, x + w, y + h * 0.22], fill=tuple(int(cc * polish + 230 * (1 - polish)) for cc in c))
    for k in range(5):
        yy = y + h * (0.28 + k * 0.12)
        d.rounded_rectangle([x + w * 0.08, yy, x + w * (0.5 + 0.4 * rng.random()), yy + h * 0.06], 6 * s, fill=(222, 224, 232))
    d.rounded_rectangle([x + w * 0.1, y + h * 0.86, x + w * 0.9, y + h * 0.95], 10 * s, fill=tuple(int(cc * polish + 210 * (1 - polish)) for cc in c))


def draw_ai_prompt(t, W=1920, H=1080):
    im, d, s = app_chrome(W, H)
    d.text((W / 2, 300 * s), 'What should we design today?', font=F('l', 64 * s), fill=(235, 235, 245), anchor='mm')
    n = int(len(PROMPT) * ease(t * 1.05))
    d.rounded_rectangle([260 * s, 420 * s, W - 260 * s, 600 * s], 28 * s, fill=(36, 37, 46), outline=(70, 70, 90), width=2)
    txt = PROMPT[:n] + ('|' if int(t * 40) % 2 == 0 else '')
    lines = [txt[:60], txt[60:]]
    for i, ln in enumerate(lines):
        d.text((300 * s, 470 * s + i * 56 * s), ln, font=F('r', 40 * s), fill=(230, 230, 240))
    d.rounded_rectangle([W - 470 * s, 620 * s, W - 260 * s, 690 * s], 35 * s, fill=ACC)
    d.text((W - 365 * s, 655 * s), 'Generate', font=F('sb', 30 * s), fill=(255, 255, 255), anchor='mm')
    return im


def draw_ai_generate(t, W=1920, H=1080):
    im, d, s = app_chrome(W, H)
    d.text((60 * s, 110 * s), PROMPT, font=F('r', 26 * s), fill=(160, 160, 180))
    n = int(24 * ease(t * 1.15))
    secs = 9.8 * min(t * 1.15, 1)
    d.text((W - 60 * s, 110 * s), f'Generating… {n}/24 screens · {secs:4.1f}s' if n < 24 else 'Done · 24 screens · 9.8 s',
           font=F('sb', 26 * s), fill=ACC if n < 24 else (16, 190, 140), anchor='ra')
    cw, ch = 205 * s, 400 * s
    for k in range(24):
        col, row = k % 8, k // 8
        x = 70 * s + col * (cw + 25 * s); y = 170 * s + row * (ch * 0.68 + 20 * s)
        if k < n:
            mini_screen(d, x, y, cw, ch * 0.62, 'x', s, k, 1.0)
        elif k == n:
            d.rounded_rectangle([x, y, x + cw, y + ch * 0.62], 14 * s, outline=ACC, width=3)
            sh = (t * 30) % 1
            d.rectangle([x, y + ch * 0.62 * sh, x + cw, y + ch * 0.62 * sh + 4 * s], fill=ACC)
        else:
            d.rounded_rectangle([x, y, x + cw, y + ch * 0.62], 14 * s, outline=(55, 55, 70), width=2)
    pw = (W - 120 * s) * min(t * 1.15, 1)
    d.rectangle([60 * s, H - 40 * s, 60 * s + pw, H - 30 * s], fill=ACC)
    return im


def draw_ai_result(t, W=1920, H=1080):
    im, d, s = app_chrome(W, H)
    for k in range(3):
        x = 140 * s + k * 560 * s
        mini_screen(d, x, 170 * s, 420 * s, 760 * s, 'x', s, k + 2, 1.0)
    pop = ease(t * 2)
    for i, (txt, col) in enumerate((('Prototype ready', (16, 190, 140)), ('Code exported · React', (124, 92, 255)), ('Design system generated', (240, 150, 60)))):
        y = 200 * s + i * 110 * s
        a = ease((t - i * 0.18) * 3)
        if a > 0:
            d.rounded_rectangle([W - 560 * s, y, W - 80 * s, y + 80 * s], 20 * s, fill=(36, 37, 46))
            d.ellipse([W - 540 * s, y + 25 * s, W - 510 * s, y + 55 * s], fill=col)
            d.text((W - 490 * s, y + 40 * s), txt, font=F('sb', 32 * s), fill=(235, 235, 245), anchor='lm')
    return im


def draw_bank_app(t, W=1080, H=2304, good=False):
    im = Image.new('RGB', (W, H), (247, 247, 250)); d = ImageDraw.Draw(im); s = W / 1080
    if not good:   # the AI-generated version: dense, tiny, icon-only
        d.rectangle([0, 0, W, 330 * s], fill=(88, 101, 242))
        d.text((60 * s, 150 * s), 'Hi, Ramesh', font=F('sb', 44 * s), fill=(255, 255, 255))
        d.text((60 * s, 215 * s), '₹ 48,250.00', font=F('b', 60 * s), fill=(255, 255, 255))
        icons = ['↗', '⇄', '◎', '▤', '⌂', '☰', '◈', '⊕', '✦', '⟳', '▣', '◐']
        for k in range(12):
            x = 70 * s + (k % 4) * 240 * s; y = 420 * s + (k // 4) * 220 * s
            d.rounded_rectangle([x, y, x + 150 * s, y + 150 * s], 36 * s, fill=(232, 234, 248))
            d.text((x + 75 * s, y + 75 * s), icons[k], font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', int(60 * s)), fill=(88, 101, 242), anchor='mm')
            d.text((x + 75 * s, y + 175 * s), ['Pay', 'Xfer', 'UPI', 'Stmt', 'Home', 'More', 'Inv', 'Add', 'Offers', 'Auto', 'Cards', 'Loans'][k],
                   font=F('r', 24 * s), fill=(120, 120, 135), anchor='mm')
        for k in range(5):
            y = 1150 * s + k * 160 * s
            d.rounded_rectangle([50 * s, y, W - 50 * s, y + 130 * s], 22 * s, fill=(255, 255, 255))
            d.text((90 * s, y + 45 * s), ['Swiggy', 'Electricity', 'Rahul S', 'Amazon', 'Petrol'][k], font=F('m', 30 * s), fill=(40, 40, 50))
            d.text((W - 90 * s, y + 45 * s), ['-₹320', '-₹1,840', '+₹2,000', '-₹999', '-₹600'][k], font=F('m', 30 * s), fill=(40, 40, 50), anchor='ra')
        if 0.3 < t:   # finger hovering, unsure
            fx = W * (0.25 + 0.4 * ease((t - 0.3) * 2) - 0.2 * ease((t - 0.7) * 3)); fy = 640 * s
            d.ellipse([fx - 70 * s, fy - 70 * s, fx + 70 * s, fy + 70 * s], fill=(200, 160, 140))
    else:          # redesigned with him
        d.text((70 * s, 160 * s), 'Namaste, Ramesh ji', font=F('sb', 64 * s), fill=(30, 30, 40))
        d.text((70 * s, 250 * s), 'Balance  ₹ 48,250', font=F('m', 52 * s), fill=(80, 80, 95))
        d.rounded_rectangle([60 * s, 400 * s, W - 60 * s, 760 * s], 50 * s, fill=(16, 150, 110))
        d.text((W / 2, 580 * s), 'Send money', font=F('b', 96 * s), fill=(255, 255, 255), anchor='mm')
        d.text((70 * s, 880 * s), 'Send to', font=F('sb', 52 * s), fill=(40, 40, 50))
        for k, nm in enumerate(['Sunita (wife)', 'Rahul (son)', 'Milkman Raju']):
            y = 980 * s + k * 260 * s
            d.rounded_rectangle([60 * s, y, W - 60 * s, y + 220 * s], 40 * s, fill=(255, 255, 255))
            d.ellipse([100 * s, y + 40 * s, 240 * s, y + 180 * s], fill=[(240, 180, 140), (150, 190, 230), (200, 220, 160)][k])
            d.text((280 * s, y + 110 * s), nm, font=F('m', 56 * s), fill=(30, 30, 40), anchor='lm')
        if t > 0.5:
            a = ease((t - 0.5) * 3)
            d.rounded_rectangle([60 * s, 1820 * s, W - 60 * s, 2080 * s], 50 * s, fill=(int(255 - 80 * a), 250, int(255 - 120 * a)))
            d.text((W / 2, 1950 * s), '✓  ₹500 sent to Sunita', font=F('b', 64 * s), fill=(20, 120, 80), anchor='mm')
    return im


def draw_bank_insert(t, W=1920, H=1080):
    bg = Image.new('RGB', (W, H), (18, 18, 22))
    ph = draw_bank_app(t).resize((440, 938))
    d = ImageDraw.Draw(bg)
    d.rounded_rectangle([W / 2 - 240, 60, W / 2 + 240, 1020], 60, fill=(10, 10, 12))
    bg.paste(ph, (int(W / 2 - 220), 72))
    # older hand / thumb hovering (soft shape)
    if t > 0.25:
        fx = W / 2 - 120 + 220 * ease((t - 0.25) * 2) - 160 * ease((t - 0.65) * 3); fy = 380 + 60 * math.sin(t * 9)
        lay = Image.new('L', (W, H), 0); ld = ImageDraw.Draw(lay)
        ld.ellipse([fx - 55, fy - 75, fx + 55, fy + 75], fill=255); ld.rectangle([fx - 55, fy, fx + 55, H], fill=255)
        lay = lay.filter(ImageFilter.GaussianBlur(10))
        skin = Image.new('RGB', (W, H), (150, 104, 80))
        bg = Image.composite(skin, bg, lay)
    return bg


def draw_notebook(t, W=1920, H=1080):
    im = Image.new('RGB', (W, H), (236, 230, 214)); d = ImageDraw.Draw(im)
    for y in range(120, H, 64):
        d.line([(0, y), (W, y)], fill=(190, 205, 225), width=2)
    d.line([(220, 0), (220, H)], fill=(230, 150, 150), width=3)
    lines = ['Usability test - Mr. Rao, 62', '', '- Text too small. Squints.', '- 12 icons = 12 questions',
             '- "Send money" should be ONE big button', '- Trusts faces & names, not icons', '- Confirm in words: "Rs 500 sent to Sunita"']
    total = sum(len(l) for l in lines); n = int(total * ease(t * 1.1)); c = 0
    fnt = ImageFont.truetype(FD + 'Inter-MediumItalic.otf', 52)
    for i, ln in enumerate(lines):
        if c >= n:
            break
        show = ln[:max(0, n - c)]; c += len(ln)
        d.text((270, 140 + i * 128 - 50), show, font=fnt, fill=(28, 40, 90) if i else (150, 30, 40))
    if t > 0.85:
        d.line([(520, 560 + 52), (650, 560 + 52)], fill=(150, 30, 40), width=5)
    return im.filter(ImageFilter.GaussianBlur(0.6))


COPROMPT = 'Users: 55+, low vision, first-time UPI. One task per screen. Big type. Show photo + name of who gets the money. Confirm in plain words.'


def draw_cocreate(t, W=1920, H=1080):
    im, d, s = app_chrome(W, H, 'Genie AI · Design — with research notes')
    # research notes panel
    d.rectangle([0, 64 * s, 520 * s, H], fill=(30, 31, 38))
    d.text((40 * s, 110 * s), 'From user research', font=F('sb', 30 * s), fill=(230, 230, 240))
    cols = [(255, 222, 120), (255, 180, 190), (170, 230, 200), (180, 210, 255)]
    notes = ['Mr. Rao squints at small text', 'Too many icons', 'Trusts faces & names', 'Wants confirmation in words']
    for k in range(4):
        y = 170 * s + k * 190 * s
        d.rectangle([40 * s, y, 480 * s, y + 160 * s], fill=cols[k])
        d.text((60 * s, y + 25 * s), notes[k], font=F('m', 28 * s), fill=(50, 40, 30))
    n = int(len(COPROMPT) * ease(t * 2.2))
    d.rounded_rectangle([570 * s, 110 * s, W - 60 * s, 260 * s], 24 * s, fill=(36, 37, 46))
    txt = COPROMPT[:n]
    cut = COPROMPT.rfind(' ', 0, 74)
    d.text((600 * s, 140 * s), txt[:cut], font=F('r', 30 * s), fill=(230, 230, 240))
    d.text((600 * s, 190 * s), txt[cut + 1:], font=F('r', 30 * s), fill=(230, 230, 240))
    if t > 0.45:   # options appear; he picks B and edits it
        for k in range(3):
            a = ease((t - 0.45 - k * 0.05) * 6)
            x = 600 * s + k * 420 * s
            col = (16, 150, 110)
            d.rounded_rectangle([x, 310 * s, x + 360 * s, 1000 * s], 30 * s, fill=(250, 250, 252), outline=ACC if (k == 1 and t > 0.7) else None, width=6)
            d.text((x + 30 * s, 360 * s), 'Namaste', font=F('sb', 34 * s), fill=(30, 30, 40))
            d.rounded_rectangle([x + 30 * s, 420 * s, x + 330 * s, 560 * s], 30 * s, fill=col if k != 2 else (88, 101, 242))
            d.text((x + 180 * s, 490 * s), 'Send money', font=F('b', 36 * s), fill=(255, 255, 255), anchor='mm')
            for j in range(3):
                y = 600 * s + j * 120 * s
                d.rounded_rectangle([x + 30 * s, y, x + 330 * s, y + 100 * s], 24 * s, fill=(238, 238, 244))
                d.ellipse([x + 45 * s, y + 20 * s, x + 105 * s, y + 80 * s], fill=(230, 180, 140))
            d.text((x + 180 * s, 1040 * s), f'Option {"ABC"[k]}', font=F('m', 28 * s), fill=(170, 170, 185), anchor='mm')
        if t > 0.75:
            cx = 600 * s + 420 * s + 260 * s + 40 * math.sin(t * 20); cy = 470 * s
            d.polygon([(cx, cy), (cx + 26 * s, cy + 60 * s), (cx + 8 * s, cy + 52 * s), (cx - 4 * s, cy + 80 * s)], fill=(255, 255, 255))
            d.rounded_rectangle([1520 * s, 300 * s, W - 70 * s, 380 * s], 18 * s, fill=(36, 37, 46))
            d.text((1540 * s, 340 * s), 'You: make the name larger', font=F('m', 26 * s), fill=(230, 230, 240), anchor='lm')
    return im


def draw_result_test(t, W=1920, H=1080):
    im = Image.new('RGB', (W, H), (20, 21, 26)); d = ImageDraw.Draw(im)
    d.text((W / 2, 60), 'Usability test · Mr. Rao, 62', font=F('sb', 40), fill=(230, 230, 240), anchor='mm')
    for k, (lab, good) in enumerate((('AI first draft', False), ('Designed with Mr. Rao', True))):
        x = 360 + k * 760
        ph = draw_bank_app(0.9 if good else 0.0, good=good).resize((380, 810))
        d.rounded_rectangle([x - 15, 170, x + 395, 995], 50, fill=(8, 8, 10)); im.paste(ph, (x, 178))
        d.text((x + 190, 1030), lab, font=F('m', 34), fill=(190, 190, 205), anchor='mm')
    a = ease((t - 0.25) * 3)
    if a > 0:
        d.rounded_rectangle([360 + 190 - 140, 120, 360 + 190 + 140, 160], 20, fill=(70, 30, 34))
        d.text((360 + 190, 140), 'Gave up after 3:40', font=F('sb', 28), fill=(255, 140, 140), anchor='mm')
    b = ease((t - 0.45) * 3)
    if b > 0:
        d.rounded_rectangle([1120 + 190 - 140, 120, 1120 + 190 + 140, 160], 20, fill=(20, 70, 50))
        d.text((1120 + 190, 140), 'Paid in 0:38', font=F('sb', 28), fill=(140, 255, 190), anchor='mm')
    return im


def write_sequence(name, fn, n, W, H, ext='png', **kw):
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
    for i in range(n):
        im = fn(i / max(n - 1, 1), W, H, **kw) if kw else fn(i / max(n - 1, 1), W, H)
        im.convert('RGB').save(os.path.join(d, f'f{i + 1:04d}.{ext}'), quality=90) if ext == 'jpg' else im.convert('RGB').save(os.path.join(d, f'f{i + 1:04d}.png'), compress_level=2)


if __name__ == '__main__':
    sys.path.insert(0, os.path.join(HERE, '..', 'config'))
    import film_timing as FT
    write_sequence('ai_generate', draw_ai_generate, FT.UI['ai_generate'], 1920, 1080)
    write_sequence('ai_result', draw_ai_result, FT.UI['ai_result'], 1920, 1080)
    write_sequence('bank_app', draw_bank_insert, FT.UI['bank_app'], 1920, 1080)
    write_sequence('notebook', draw_notebook, FT.UI['notebook'], 1920, 1080)
    write_sequence('cocreate', draw_cocreate, FT.UI['cocreate'], 1920, 1080)
    write_sequence('result_test', draw_result_test, FT.UI['result_test'], 1920, 1080)
    print('inserts done')
