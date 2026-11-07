import numpy as np


def vnoise(P, scale, seed=0):
    rng = np.random.default_rng(seed); perm = rng.random(4096) * 2 - 1
    q = P * scale; i = np.floor(q).astype(np.int64); f = q - i; f = f * f * (3 - 2 * f)
    h = lambda ix, iy, iz: perm[(ix * 73856093 ^ iy * 19349663 ^ iz * 83492791) & 4095]
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = ((f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2]))
                out = out + w * h(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz)
    return out
