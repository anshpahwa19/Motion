"""ARJUN — body: arms + hands (skin) and home T-shirt, sculpted as SDF parts.
Body space: standing, origin at pelvis, facing -Y, +Z up, +X = character's left.
Each part maps to a rig bone; skin weights come from a soft-min over the
part distance fields, so joints blend exactly where the shapes blend."""
import numpy as np
from sdf import (ellipsoid, round_cone, sphere, round_box, smin, smax, capsule,
                 value_noise3, mesh_sdf)

HEAD_ORIGIN = np.array([0.0, 0.0, 0.672])      # head-local origin in body space

J = {
    'pelvis': (0, 0.0, 0.0), 'spine': (0, 0.005, 0.17), 'chest': (0, 0.012, 0.33),
    'neck': (0, 0.02, 0.50), 'head': (0, 0.018, 0.598), 'head_end': (0, 0.0, 0.80),
    'shoulder.R': (-0.168, 0.015, 0.468), 'elbow.R': (-0.214, 0.035, 0.188),
    'wrist.R': (-0.244, 0.002, -0.058),
}
for k in list(J):
    if k.endswith('.R'):
        x, y, z = J[k]; J[k[:-2] + '.L'] = (-x, y, z)
J = {k: np.array(v, float) for k, v in J.items()}

FINGERS = {   # knuckle (hand-local), segment lengths, base radius, spread deg
    'index': ((0.0, -0.031, -0.092), (0.042, 0.025, 0.021), 0.0090, -6),
    'middle': ((0.0, -0.010, -0.096), (0.046, 0.028, 0.022), 0.0093, -1),
    'ring': ((0.0, 0.011, -0.093), (0.043, 0.026, 0.021), 0.0088, 4),
    'pinky': ((0.0, 0.030, -0.086), (0.034, 0.020, 0.018), 0.0078, 9),
}
REST_FLEX = (12, 16, 9)
THUMB = [(0.010, -0.020, -0.018), (0.025, -0.046, -0.046), (0.033, -0.061, -0.070), (0.039, -0.069, -0.090)]
THUMB_R = (0.0125, 0.0108, 0.0094, 0.0083)


def hand_frame(side):
    """Rotation (3x3, columns = hand-local axes in body space) and origin."""
    e, w = J['elbow.' + side], J['wrist.' + side]
    zl = -(w - e) / np.linalg.norm(w - e)          # local +Z points back to elbow
    med = np.array([1.0, 0, 0]) if side == 'R' else np.array([-1.0, 0, 0])
    xl = med - zl * (med @ zl); xl /= np.linalg.norm(xl)
    yl = np.cross(zl, xl)
    if side == 'L':
        yl = -yl                                    # keep thumb forward (-Y)
    return np.stack([xl, yl, zl], 1), w


def finger_joints():
    """hand-local joint chains for the right hand (list of points per finger)."""
    out = {}
    for name, (k, segs, r, spread) in FINGERS.items():
        p = np.array(k, float); pts = [p.copy()]; c = 0
        sp = np.radians(spread)
        for L, fl in zip(segs, REST_FLEX):
            c += np.radians(fl)
            d = np.array([np.sin(c), np.sin(sp) * np.cos(c), -np.cos(c) * np.cos(sp)])
            p = p + d / np.linalg.norm(d) * L; pts.append(p.copy())
        out[name] = (np.array(pts), r)
    out['thumb'] = (np.array(THUMB, float), THUMB_R[0])
    return out


def hand_parts(Q):
    """Q: points in right-hand-local space. Returns dict part -> sdf."""
    parts = {}
    palm = round_box(Q, (0.0005, 0.0, -0.050), (0.0125, 0.041, 0.047), 0.0115)
    palm = smin(palm, ellipsoid(Q, (0.0105, -0.022, -0.040), (0.0115, 0.017, 0.025)), 0.008)
    palm = smin(palm, ellipsoid(Q, (0.0075, 0.026, -0.052), (0.0085, 0.012, 0.030)), 0.008)
    palm = smin(palm, ellipsoid(Q, (0.0, 0.0, -0.002), (0.0175, 0.029, 0.022)), 0.012)
    parts['hand'] = palm
    for name, (pts, r) in finger_joints().items():
        if name == 'thumb':
            radii = THUMB_R
        else:
            radii = (r, r * 0.93, r * 0.86, r * 0.78)
        for i in range(3):
            parts[f'f_{name}.{i + 1:02d}'] = round_cone(Q, pts[i], pts[i + 1], radii[i], radii[i + 1])
    return parts


def body_parts(P, side_list=('R', 'L')):
    parts = {}
    parts['chest'] = smin(ellipsoid(P, (0, 0.012, 0.37), (0.148, 0.092, 0.15)),
                          round_cone(P, J['neck'], J['chest'], 0.06, 0.07), 0.03)
    parts['spine'] = ellipsoid(P, (0, 0.004, 0.16), (0.14, 0.09, 0.16))
    for s in side_list:
        sh, el, wr = J['shoulder.' + s], J['elbow.' + s], J['wrist.' + s]
        ua = smin(round_cone(P, sh, el, 0.050, 0.039), sphere(P, sh + np.array([0, 0, 0.0]), 0.052), 0.03)
        fa = round_cone(P, el, wr + (wr - el) * 0.05, 0.040, 0.0265)
        fa = smin(fa, ellipsoid(P, el + (wr - el) * 0.28, (0.042, 0.039, 0.065)), 0.02)
        parts['upper_arm.' + s] = ua
        parts['forearm.' + s] = fa
        R, o = hand_frame(s)
        Q = (P - o) @ R
        if s == 'L':
            Q = Q.copy(); Q[:, 0] *= 1  # frame already mirrored via axes
        for k, v in hand_parts(Q).items():
            parts[k + '.' + s if k != 'hand' else 'hand.' + s] = v
    return parts


def combine(parts, k_default=0.012, hand_k=0.004):
    d = None
    for name, v in parts.items():
        k = hand_k if name.startswith('f_') else k_default
        d = v if d is None else smin(d, v, k)
    return d


def skin_sdf(P):
    return combine(body_parts(P))


SKIN_BBOX = ((-0.33, -0.16, -0.27), (0.33, 0.16, 0.56))


def tee_sdf(P):
    s = []
    torso = smin(ellipsoid(P, (0, 0.012, 0.35), (0.172, 0.106, 0.18)),
                 ellipsoid(P, (0, 0.006, 0.12), (0.150, 0.098, 0.19)), 0.06)
    for side in ('R', 'L'):
        sh, el = J['shoulder.' + side], J['elbow.' + side]
        torso = smin(torso, sphere(P, sh + np.array([0.012 * np.sign(sh[0]) * -1, 0, -0.004]), 0.056), 0.05)
        end = sh + (el - sh) * 0.48
        slv = round_cone(P, sh, end, 0.058, 0.055)
        ax = (el - sh) / np.linalg.norm(el - sh)
        cut = (P - end) @ ax          # >0 beyond the sleeve hem
        slv = smax(slv, cut, 0.002)
        torso = smin(torso, slv, 0.03)
    # wrinkles
    torso = torso + 0.0016 * value_noise3(P, 38, 2) + 0.0008 * value_noise3(P, 90, 3)
    outer = torso
    inner = torso + 0.0035
    shell = smax(outer, -inner, 0.0)
    # collar (round neck) and hem cut
    nb = J['neck']
    collar = np.hypot(P[:, 0] / 1.0, (P[:, 1] - 0.016) / 0.85) - 0.068
    collar = smax(collar, -(P[:, 2] - 0.44), 0.01)
    shell = smax(shell, -collar, 0.004)
    shell = smax(shell, -(P[:, 2] + 0.05), 0.0)
    return shell


TEE_BBOX = ((-0.30, -0.14, -0.06), (0.30, 0.15, 0.56))


def tee_parts(P):
    """Part fields used only for skin weights of the tee."""
    parts = {'spine': ellipsoid(P, (0, 0.006, 0.12), (0.158, 0.104, 0.17)),
             'chest': ellipsoid(P, (0, 0.012, 0.38), (0.150, 0.100, 0.15))}
    for side in ('R', 'L'):
        sh, el = J['shoulder.' + side], J['elbow.' + side]
        parts['upper_arm.' + side] = round_cone(P, sh + (el - sh) * 0.12, el, 0.05, 0.05)
    return parts


def soft_weights(parts, tau):
    names = list(parts)
    D = np.stack([parts[n] for n in names], 1)
    D = D - D.min(1, keepdims=True)
    W = np.exp(-D / tau)
    W[W < 0.02] = 0
    W /= W.sum(1, keepdims=True)
    return names, W
