"""Textures for the office fear-flash set: Arjun's ID card, his laptop screen
(design tool with his wireframes) and sticky-note sketches."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, '..', 'assets', 'textures')
FD = '/usr/share/fonts/opentype/inter/'
F = lambda w, s: ImageFont.truetype(FD + {'b': 'Inter-Bold.otf', 'sb': 'Inter-SemiBold.otf', 'm': 'Inter-Medium.otf',
                                          'r': 'Inter-Regular.otf', 'xb': 'Inter-ExtraBold.otf'}[w], s)


def id_card(portrait=None):
    W, H = 640, 1010
    im = Image.new('RGB', (W, H), (248, 248, 250)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 230], fill=(24, 32, 62))
    d.ellipse([40, 60, 120, 140], fill=(90, 200, 255))
    d.ellipse([62, 82, 98, 118], fill=(24, 32, 62))
    d.text((140, 70), 'NOVA', font=F('xb', 58), fill=(255, 255, 255))
    d.text((142, 136), 'DIGITAL STUDIO', font=F('sb', 26), fill=(150, 200, 255))
    d.rounded_rectangle([W / 2 - 60, 22, W / 2 + 60, 44], 10, fill=(10, 14, 30))   # lanyard slot
    px0, py0, px1, py1 = 170, 270, 470, 640
    if portrait and os.path.exists(portrait):
        p = Image.open(portrait).convert('RGB')
        r = max((px1 - px0) / p.width, (py1 - py0) / p.height)
        p = p.resize((int(p.width * r), int(p.height * r)))
        p = p.crop(((p.width - (px1 - px0)) // 2, (p.height - (py1 - py0)) // 2,
                    (p.width - (px1 - px0)) // 2 + px1 - px0, (p.height - (py1 - py0)) // 2 + py1 - py0))
        im.paste(p, (px0, py0))
    else:
        d.rectangle([px0, py0, px1, py1], fill=(200, 205, 215))
        d.ellipse([px0 + 90, py0 + 60, px1 - 90, py0 + 180], fill=(120, 90, 70))
        d.rounded_rectangle([px0 + 50, py0 + 200, px1 - 50, py1 + 40], 60, fill=(60, 85, 95))
    d.rectangle([px0, py0, px1, py1], outline=(24, 32, 62), width=4)
    d.text((W / 2, 700), 'ARJUN MEHTA', font=F('xb', 52), fill=(20, 22, 30), anchor='mm')
    d.text((W / 2, 760), 'UX Designer', font=F('m', 36), fill=(60, 70, 90), anchor='mm')
    d.text((W / 2, 808), 'EMP ID  NDS-20417', font=F('r', 26), fill=(110, 115, 130), anchor='mm')
    x = 120
    import random
    random.seed(7)
    while x < W - 120:
        w = random.choice([3, 3, 5, 7]); d.rectangle([x, 860, x + w, 960], fill=(20, 20, 26)); x += w + random.choice([3, 4, 6])
    im.save(os.path.join(TEX, 'id_card.png'))


def laptop_screen():
    W, H = 1600, 1000
    im = Image.new('RGB', (W, H), (30, 30, 34)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 48], fill=(44, 44, 50))
    for i, t in enumerate(['File', 'Edit', 'View', 'Prototype']):
        d.text((80 + i * 110, 12), t, font=F('m', 22), fill=(200, 200, 210))
    d.rectangle([0, 48, 260, H], fill=(38, 38, 44))
    d.text((20, 70), 'Layers', font=F('sb', 22), fill=(230, 230, 235))
    for i, t in enumerate(['Onboarding / 01', 'Onboarding / 02', 'Home', 'Checkout', 'Profile', 'Empty state', 'Error toast']):
        d.text((30, 115 + i * 38), '▢  ' + t, font=F('r', 20), fill=(170, 170, 185))
    d.rectangle([W - 280, 48, W, H], fill=(38, 38, 44))
    d.text((W - 260, 70), 'Design', font=F('sb', 22), fill=(230, 230, 235))
    for i in range(8):
        d.rounded_rectangle([W - 260, 120 + i * 60, W - 20, 160 + i * 60], 6, fill=(52, 52, 60))
    d.rectangle([260, 48, W - 280, H], fill=(52, 52, 58))
    # artboards: phone wireframes + user-journey sticky notes
    for k in range(4):
        x0 = 310 + k * 255; y0 = 110
        d.text((x0, y0 - 30), ['Welcome', 'Sign up', 'Home', 'Checkout'][k], font=F('m', 18), fill=(200, 200, 210))
        d.rounded_rectangle([x0, y0, x0 + 220, y0 + 440], 22, fill=(250, 250, 252))
        d.rounded_rectangle([x0 + 20, y0 + 40, x0 + 200, y0 + 170], 10, fill=(220, 225, 240))
        for j in range(4):
            d.rounded_rectangle([x0 + 20, y0 + 195 + j * 42, x0 + 200 - (j * 30) % 90, y0 + 220 + j * 42], 6, fill=(205, 208, 220))
        d.rounded_rectangle([x0 + 30, y0 + 380, x0 + 190, y0 + 418], 18, fill=(88, 101, 242))
        if k < 3:
            d.line([(x0 + 222, y0 + 220), (x0 + 252, y0 + 220)], fill=(120, 160, 255), width=3)
    cols = [(255, 222, 120), (255, 180, 190), (170, 230, 200), (180, 210, 255)]
    notes = ['Why do users drop here?', 'Interview: Priya, 34', 'Empathy map', 'Test with real users']
    for k in range(4):
        x0 = 330 + k * 250; y0 = 640
        d.rectangle([x0, y0, x0 + 200, y0 + 160], fill=cols[k])
        lines = notes[k].split(' ')
        txt = ''; yy = y0 + 20
        for w in lines:
            if d.textlength(txt + ' ' + w, font=F('m', 22)) > 170:
                d.text((x0 + 14, yy), txt.strip(), font=F('m', 22), fill=(50, 40, 30)); yy += 30; txt = w
            else:
                txt += ' ' + w
        d.text((x0 + 14, yy), txt.strip(), font=F('m', 22), fill=(50, 40, 30))
    im.save(os.path.join(TEX, 'laptop_screen.png'))


def sticky(i):
    im = Image.new('RGB', (300, 300), [(255, 222, 120), (255, 180, 190), (170, 230, 200)][i]); d = ImageDraw.Draw(im)
    if i == 0:
        d.rectangle([60, 50, 160, 240], outline=(40, 40, 60), width=5); d.line([(70, 90), (150, 90)], fill=(40, 40, 60), width=4)
        d.rectangle([180, 50, 260, 140], outline=(40, 40, 60), width=5); d.line([(160, 140), (180, 100)], fill=(40, 40, 60), width=4)
    elif i == 1:
        d.text((150, 120), 'USER\nFIRST', font=F('b', 52), fill=(60, 30, 40), anchor='mm', align='center')
    else:
        for k in range(4):
            d.ellipse([40 + k * 60, 140, 80 + k * 60, 180], outline=(30, 60, 50), width=5)
            if k < 3: d.line([(80 + k * 60, 160), (100 + k * 60, 160)], fill=(30, 60, 50), width=4)
    im.save(os.path.join(TEX, f'sticky_{i}.png'))


def main(portrait=None):
    os.makedirs(TEX, exist_ok=True)
    id_card(portrait); laptop_screen()
    for i in range(3):
        sticky(i)


if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(TEX, 'arjun_portrait.png'))
