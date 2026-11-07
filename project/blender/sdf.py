"""Tiny numpy signed-distance-field toolkit used to sculpt organic shapes
(head, hands, body, pillow...) procedurally, then mesh them with marching cubes.

All functions take P: (N,3) float array and return (N,) distances (metres).
"""
import numpy as np


def _v(x):
    return np.asarray(x, dtype=np.float64)


def sphere(P, c, r):
    return np.linalg.norm(P - _v(c), axis=1) - r


def ellipsoid(P, c, r, R=None):
    """IQ's ellipsoid approximation. R: optional 3x3 rotation (world->local)."""
    q = P - _v(c)
    if R is not None:
        q = q @ _v(R).T
    r = _v(r)
    k0 = np.linalg.norm(q / r, axis=1)
    k1 = np.linalg.norm(q / (r * r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def round_cone(P, a, b, ra, rb):
    """Capsule from a (radius ra) to b (radius rb)."""
    a = _v(a); b = _v(b)
    ba = b - a
    l2 = ba @ ba
    rr = ra - rb
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = P - a
    y = pa @ ba
    z = y - l2
    xv = pa * l2 - np.outer(y, ba)
    x2 = np.einsum('ij,ij->i', xv, xv)
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    out = np.empty(len(P))
    m1 = np.sign(z) * a2 * z2 > k
    m2 = np.sign(y) * a2 * y2 < k
    out[:] = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - ra
    out[m1] = np.sqrt(x2[m1] + z2[m1]) * il2 - rb
    out[m2 & ~m1] = np.sqrt(x2[m2 & ~m1] + y2[m2 & ~m1]) * il2 - ra
    return out


def capsule(P, a, b, r):
    return round_cone(P, a, b, r, r + 1e-6)


def round_box(P, c, half, r, R=None):
    q = P - _v(c)
    if R is not None:
        q = q @ _v(R).T
    q = np.abs(q) - (_v(half) - r)
    return (np.linalg.norm(np.maximum(q, 0), axis=1)
            + np.minimum(np.max(q, axis=1), 0) - r)


def cyl_z(P, c, r, h):
    q = P - _v(c)
    d = np.stack([np.hypot(q[:, 0], q[:, 1]) - r, np.abs(q[:, 2]) - h], 1)
    return np.minimum(np.max(d, 1), 0) + np.linalg.norm(np.maximum(d, 0), axis=1)


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def ssub(a, b, k):
    """a minus b, smooth."""
    return smax(a, -b, k)


def rot(axis, deg):
    """3x3 rotation matrix (world->local when used as R in primitives = inverse)."""
    t = np.radians(deg)
    c, s = np.cos(t), np.sin(t)
    if axis == 'x':
        M = [[1, 0, 0], [0, c, -s], [0, s, c]]
    elif axis == 'y':
        M = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    else:
        M = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    return _v(M)


def value_noise3(P, scale, seed=0):
    """Cheap smooth 3D value noise in [-1,1]."""
    rng = np.random.default_rng(seed)
    perm = rng.random(4096) * 2 - 1
    q = P * scale
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)

    def h(ix, iy, iz):
        return perm[(ix * 73856093 ^ iy * 19349663 ^ iz * 83492791) & 4095]
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = ((f[:, 0] if dx else 1 - f[:, 0]) *
                     (f[:, 1] if dy else 1 - f[:, 1]) *
                     (f[:, 2] if dz else 1 - f[:, 2]))
                out = out + w * h(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz)
    return out


def mesh_sdf(fn, lo, hi, voxel, chunk=2_000_000):
    """Marching-cubes mesh of fn's zero level set inside box [lo,hi]."""
    from skimage.measure import marching_cubes
    lo = _v(lo); hi = _v(hi)
    n = np.ceil((hi - lo) / voxel).astype(int) + 1
    xs = [np.linspace(lo[i], lo[i] + (n[i] - 1) * voxel, n[i]) for i in range(3)]
    G = np.stack(np.meshgrid(*xs, indexing='ij'), -1).reshape(-1, 3)
    vals = np.empty(len(G))
    for s in range(0, len(G), chunk):
        vals[s:s + chunk] = fn(G[s:s + chunk])
    vol = vals.reshape(n)
    verts, faces, _, _ = marching_cubes(vol, 0.0, spacing=(voxel,) * 3)
    verts += lo
    # marching_cubes winding gives inward normals for "negative inside"; flip.
    faces = faces[:, ::-1]
    return verts, faces


def sdf_normal(fn, P, e=1e-4):
    d = np.zeros((len(P), 3))
    for i in range(3):
        o = np.zeros(3); o[i] = e
        d[:, i] = fn(P + o) - fn(P - o)
    return d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
