"""Procedural night city skyline texture (seen through the bedroom window)."""
import numpy as np
from PIL import Image, ImageFilter


def make_skyline(path, W=4096, Hh=1536, seed=4):
    rng = np.random.default_rng(seed)
    img = np.zeros((Hh, W, 3), np.float32)
    yy = np.linspace(0, 1, Hh)[:, None]
    # sky: deep navy -> hazy violet/orange glow near horizon (city light pollution)
    top = np.array([0.006, 0.010, 0.030]); mid = np.array([0.03, 0.035, 0.08]); hor = np.array([0.20, 0.11, 0.08])
    t = yy
    sky = top * (1 - t) ** 2 + mid * 2 * t * (1 - t) + hor * t ** 3
    img[:] = sky[:, None, :].reshape(Hh, 1, 3)
    horizon = int(Hh * 0.86)
    # moon
    mx, my, mr = int(W * 0.30), int(Hh * 0.16), 34
    Y, X = np.ogrid[:Hh, :W]
    d = np.sqrt((X - mx) ** 2 + (Y - my) ** 2)
    img += (np.exp(-(d / 260) ** 2) * 0.10)[..., None] * np.array([0.6, 0.7, 1.0])
    img[d < mr] = np.array([2.2, 2.3, 2.5])
    # building layers (far -> near)
    for layer, (n, hmin, hmax, dim, win_p) in enumerate(
            [(70, 0.05, 0.22, 0.25, 0.12), (45, 0.08, 0.32, 0.55, 0.16), (26, 0.12, 0.42, 1.0, 0.2)]):
        x = 0
        while x < W:
            bw = int(rng.uniform(60, 220) * (0.6 + 0.4 * layer))
            bh = int(Hh * rng.uniform(hmin, hmax))
            top_y = horizon - bh + int(layer * 40)
            base = np.array([0.010, 0.011, 0.018]) * (1 + 0.5 * layer)
            img[top_y:, x:x + bw] = base
            # windows
            wx, wy = rng.integers(10, 16), rng.integers(14, 22)
            for yy0 in range(top_y + 12, Hh - 4, wy):
                for xx0 in range(x + 6, x + bw - 8, wx):
                    if rng.random() < win_p:
                        warm = rng.random() < 0.7
                        c = np.array([1.0, 0.62, 0.28]) if warm else np.array([0.6, 0.75, 1.0])
                        c = c * rng.uniform(0.4, 1.4) * dim
                        img[yy0:yy0 + wy // 2, xx0:xx0 + wx // 2] = c
            if rng.random() < 0.35:   # aircraft warning light
                img[top_y - 6:top_y, x + bw // 2 - 3:x + bw // 2 + 3] = np.array([3.0, 0.2, 0.1])
            x += bw + int(rng.uniform(0, 40))
    # haze over lower part
    haze = np.clip((yy - 0.55) / 0.45, 0, 1)[..., None] * np.array([0.06, 0.045, 0.05])
    img = img + haze.reshape(Hh, 1, 3)
    # store as HDR-ish via EXR-less approach: PNG with gamma, strength boosted in shader
    srgb = np.clip(img / 2.5, 0, 1) ** (1 / 2.2)
    Image.fromarray((srgb * 255).astype(np.uint8)).save(path)
