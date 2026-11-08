"""ARJUN — dark, slightly messy hair: SDF scalp cap + groomed, clumped
Cycles strand curves (Principled Hair BSDF). Head-local space."""
import numpy as np
import bl_util as U
import char_head as H
import char_face as CF
from sdf import mesh_sdf, sdf_normal, smax, value_noise3

CROWN = np.array([0.0, 0.045, 0.088])
VARIANT = {}   # {'len': 0.8, 'recede': 0.02, 'melanin': 0.2, 'random': 0.3}


def hairline(P):
    """>0 where the scalp grows hair."""
    a = np.arctan2(P[:, 0], -P[:, 1])      # 0 = front, +-pi = back
    aa = np.abs(a)
    rec = VARIANT.get('recede', 0.0)
    z_front = 0.060 + rec - 0.010 * (aa / 0.55) ** 2 + rec * 0.6 * np.clip(aa / 0.6, 0, 1)
    z_temple = np.interp(aa, [0.55, 0.95, 1.12, 1.28, 1.45, 1.95, 2.4, np.pi],
                         [0.050, 0.044, 0.020, -0.012, 0.030, 0.022, -0.035, -0.062])
    zl = np.where(aa < 0.55, z_front, z_temple)
    return P[:, 2] - zl


def cap_sdf(P):
    head = H.head_sdf(P, socket=False, neck=True)
    thick = 0.0055 + 0.0035 * np.clip(P[:, 2] / 0.09, 0, 1) + 0.0015 * value_noise3(P, 90, 5)
    d = head - thick
    return smax(d, -hairline(P) * 0.6, 0.004)


def build_cap(coll, mat):
    v, f = mesh_sdf(cap_sdf, (-0.1, -0.12, -0.11), (0.1, 0.12, 0.14), 0.0018)
    ob = U.mesh_obj('ARJ_HairCap', v, f, coll, mat=mat)
    U.smooth_mesh(ob, 2, 0.5)
    return ob


def sample_surface(v, f, n, rng):
    tri = v[f]
    area = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1) / 2
    idx = rng.choice(len(f), n, p=area / area.sum())
    r1 = np.sqrt(rng.random(n)); r2 = rng.random(n)
    t = tri[idx]
    return t[:, 0] * (1 - r1)[:, None] + t[:, 1] * (r1 * (1 - r2))[:, None] + t[:, 2] * (r1 * r2)[:, None]


def comb_dir(P, rng_jit=None):
    a = np.arctan2(P[:, 0], -P[:, 1]); aa = np.abs(a)
    rad = P - CROWN; rad[:, 2] = 0
    rad /= np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-6)
    top = np.clip((P[:, 2] - 0.035) / 0.03, 0, 1)
    front = np.clip(1 - aa / 1.3, 0, 1)
    v_top = rad * 0.6 + np.array([-0.55, -1.0, 0.05]) * front[:, None] * 0.9
    v_side = np.array([0, 0.35, -1.0]) + np.c_[np.sign(P[:, 0]) * 0.1, np.zeros(len(P)), np.zeros(len(P))]
    v = v_top * top[:, None] + v_side * (1 - top[:, None])
    return v


def lengths(P, rng):
    a = np.abs(np.arctan2(P[:, 0], -P[:, 1]))
    top = np.clip((P[:, 2] - 0.03) / 0.04, 0, 1)
    front = np.clip(1 - a / 1.4, 0, 1)
    L = 0.020 + top * (0.030 + 0.022 * front)
    return L * VARIANT.get('len', 1.0) * rng.uniform(0.85, 1.12, len(P))


def grow(roots, fn, rng, nseg=9, jitter=None, lift=None):
    n = len(roots)
    L = lengths(roots, rng)
    d = comb_dir(roots)
    if jitter is not None:
        d = d + jitter
    pts = [roots.copy()]
    p = roots.copy()
    for k in range(nseg):
        nrm = sdf_normal(fn, p)
        t = d - nrm * np.einsum('ij,ij->i', d, nrm)[:, None]
        t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
        out = (0.55 if k == 0 else 0.12) * nrm
        if lift is not None:
            out = out + lift[:, None] * nrm * (1 - k / nseg)
        step = t + out
        step /= np.linalg.norm(step, axis=1, keepdims=True)
        p = p + step * (L / nseg)[:, None]
        dd = fn(p)
        floor = 0.0012 + 0.0004 * k
        push = np.maximum(floor - dd, 0)
        p = p + sdf_normal(fn, p) * push[:, None]
        # gravity on long front strands
        p[:, 2] -= 0.0006 * k * np.clip((p[:, 2] - 0.02) / 0.05, 0, 1) * (L > 0.05)
        pts.append(p.copy())
    return np.stack(pts, 1)   # (n, nseg+1, 3)


def build_hair(coll, n_guides=520, n_children=22000, seed=21):
    rng = np.random.default_rng(seed)
    capm = U.simple_mat('ARJ_HairCapMat', U.hex2lin(VARIANT.get('cap', '#120c09')), rough=0.55)
    cap = build_cap(coll, capm)
    v = U.mesh_verts(cap)
    f = np.array([p.vertices[:] for p in cap.data.polygons])
    fn = cap_sdf
    groots = sample_surface(v, f, n_guides, rng)
    jit = rng.normal(0, 0.2, (n_guides, 3))
    lift = np.clip(rng.normal(0.06, 0.12, n_guides), 0, 0.4)
    G = grow(groots, fn, rng, jitter=jit, lift=lift)
    croots = sample_surface(v, f, n_children, rng)
    # nearest guide
    d2 = ((croots[:, None, :] - groots[None, :, :]) ** 2).sum(-1)
    gi = np.argmin(d2, 1)
    Gs = G[gi]                                     # (n, k, 3)
    rel = Gs - Gs[:, :1]
    nseg = G.shape[1]
    tt = np.linspace(0, 1, nseg)[None, :, None]
    clump = rng.uniform(0.6, 0.92, n_children)[:, None, None]
    child = croots[:, None, :] + rel
    child = child * (1 - clump * tt ** 1.3) + Gs * (clump * tt ** 1.3)
    child += rng.normal(0, 0.0005, child.shape) * tt
    # frizz / flyaways
    fly = rng.random(n_children) < 0.012
    child[fly] += rng.normal(0, 0.003, (fly.sum(), nseg, 3)) * tt[0] ** 2
    for k in range(1, nseg):
        p = child[:, k]
        dd = fn(p)
        push = np.maximum(0.0010 - dd, 0)
        child[:, k] = p + sdf_normal(fn, p) * push[:, None]
    strands = list(child) + list(G)
    hm = CF.hair_material('ARJ_HairMat', melanin=VARIANT.get('melanin', 0.975), redness=0.2, rough=0.44, coat=0.0)
    if VARIANT.get('random'):
        hm.node_tree.nodes['Principled Hair BSDF'].inputs['Random Color'].default_value = VARIANT['random']
    rr = rng.uniform(0.00009, 0.00014, len(strands))
    hair = CF.hair_curves_obj('ARJ_Hair', strands, rr, 0.00002, coll, hm)
    return cap, hair
