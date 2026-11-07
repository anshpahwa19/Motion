"""ARJUN — face build: skin shading, eyes (iris/cornea), eyelid shells,
lashes, brows.  Everything is created in head-local space (see char_head)."""
import bpy, os
import numpy as np
from mathutils import Vector
import bl_util as U
import char_head as H
from sdf import mesh_sdf, sdf_normal

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, '..', 'assets', 'textures')
os.makedirs(TEX, exist_ok=True)

SKIN = U.hex2lin('#875c46')


def g(V, c, r):
    """Gaussian falloff around c with radii r (per axis)."""
    q = (V - np.asarray(c)) / np.asarray(r)
    return np.exp(-np.einsum('ij,ij->i', q, q))


def gm(V, c, r):  # mirrored in x
    W = V.copy(); W[:, 0] = np.abs(W[:, 0]); return g(W, c, r)


# ------------------------------------------------------------------ skin
def skin_maps(V):
    base = np.tile(np.array(SKIN), (len(V), 1))
    red = (gm(V, (0.045, -0.072, -0.030), (0.022, 0.03, 0.02)) * 0.8
           + g(V, (0, -0.104, -0.030), (0.012, 0.02, 0.012)) * 0.7
           + gm(V, (0.080, 0.012, -0.008), (0.012, 0.03, 0.03)) * 0.8)
    lips = (g(V, (0, -0.0835, -0.0562), (0.020, 0.012, 0.0062))
            + g(V, (0, -0.0818, -0.0664), (0.018, 0.012, 0.0074)))
    lips = np.clip(lips * 1.2, 0, 1)
    dark = gm(V, (0.0316, -0.082, -0.0160), (0.015, 0.02, 0.0060))
    lidtone = gm(V, (0.0316, -0.08, 0.0095), (0.018, 0.03, 0.006)) * 0.5
    col = base.copy()
    col = col * (1 - 0.25 * red[:, None]) + np.array([0.42, 0.13, 0.08]) * 0.25 * red[:, None]
    col = col * (1 - 0.45 * dark[:, None]) + np.array([0.12, 0.06, 0.07]) * 0.45 * dark[:, None]
    col = col * (1 - 0.3 * lidtone[:, None]) + np.array([0.18, 0.08, 0.06]) * 0.3 * lidtone[:, None]
    col = col * (1 - 0.75 * lips[:, None]) + np.array(U.hex2lin('#663630')) * 0.75 * lips[:, None]
    # stubble: jaw / chin / upper-lip / lower cheeks
    st = np.clip((-V[:, 2] - 0.032) / 0.02, 0, 1) * np.clip((-0.012 - V[:, 1]) / 0.03, 0, 1)
    st *= np.clip((V[:, 2] + 0.125) / 0.03, 0, 1)                # fade on neck
    st = np.maximum(st, g(V, (0, -0.082, -0.048), (0.024, 0.02, 0.006)))  # moustache zone
    st *= (1 - np.clip(lips * 1.6, 0, 1))
    st *= (1 - 0.8 * gm(V, (0.045, -0.07, -0.03), (0.016, 0.03, 0.012)))
    return np.c_[col, np.ones(len(V))], np.clip(st, 0, 1)


def skin_material():
    m = U.new_mat('ARJ_Skin')
    nt = m.node_tree; N, L = nt.nodes, nt.links
    p = U.principled(m)
    p.subsurface_method = 'RANDOM_WALK_SKIN'
    attr = N.new('ShaderNodeAttribute'); attr.attribute_name = 'skin_col'
    stb = N.new('ShaderNodeAttribute'); stb.attribute_name = 'stubble'
    tc = N.new('ShaderNodeTexCoord')
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2200; nz.inputs['Detail'].default_value = 1
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.56; ramp.color_ramp.elements[1].position = 0.66
    L.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    dots = N.new('ShaderNodeMath'); dots.operation = 'MULTIPLY'
    L.new(ramp.outputs['Color'], dots.inputs[0]); L.new(stb.outputs['Fac'], dots.inputs[1])
    shade = N.new('ShaderNodeMath'); shade.operation = 'MULTIPLY_ADD'
    L.new(stb.outputs['Fac'], shade.inputs[0]); shade.inputs[1].default_value = 0.22
    L.new(dots.outputs[0], shade.inputs[2])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MIX'
    L.new(shade.outputs[0], mix.inputs['Factor'])
    L.new(attr.outputs['Color'], mix.inputs['A'])
    mix.inputs['B'].default_value = (0.035, 0.028, 0.03, 1)
    L.new(mix.outputs['Result'], p.inputs['Base Color'])
    p.inputs['Subsurface Weight'].default_value = 0.6
    p.inputs['Subsurface Radius'].default_value = (1.0, 0.38, 0.22)
    p.inputs['Subsurface Scale'].default_value = 0.004
    p.inputs['Roughness'].default_value = 0.56
    p.inputs['Specular IOR Level'].default_value = 0.36
    # pores
    nz2 = N.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 2600
    L.new(tc.outputs['Object'], nz2.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.12
    bump.inputs['Distance'].default_value = 0.0002
    L.new(nz2.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], p.inputs['Normal'])
    return m


def build_head(coll, voxel=0.0013):
    v, f = mesh_sdf(H.head_sdf, *H.BBOX, voxel)
    ob = U.mesh_obj('ARJ_Head', v, f, coll, mat=skin_material())
    U.smooth_mesh(ob, 2, 0.4)
    V = U.mesh_verts(ob)
    col, st = skin_maps(V)
    U.set_color_attr(ob, 'skin_col', col)
    U.set_float_attr(ob, 'stubble', st)
    return ob


# ------------------------------------------------------------------ eyes
IRIS_A = 0.66   # iris half-angle (rad) - stylised / large
PUPIL_A = 0.25


def make_iris_texture(path, res=1024, seed=3):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:res, 0:res]
    u = (x + 0.5) / res * 2 - 1; v = (y + 0.5) / res * 2 - 1
    r = np.hypot(u, v); th = np.arctan2(v, u)
    ri, rp = np.sin(IRIS_A), np.sin(PUPIL_A)
    # sclera
    scl = np.array([0.86, 0.82, 0.78])
    img = np.ones((res, res, 3)) * scl
    edge = np.clip((r - 0.55) / 0.45, 0, 1)
    img = img * (1 - 0.25 * edge[..., None]) + np.array([0.75, 0.52, 0.48]) * 0.25 * edge[..., None]
    # veins
    for _ in range(26):
        a0 = rng.uniform(0, 2 * np.pi); w = rng.uniform(0.004, 0.009)
        wig = a0 + 0.08 * np.sin(r * rng.uniform(8, 20) + rng.uniform(0, 6))
        dth = np.angle(np.exp(1j * (th - wig)))
        m = np.exp(-(dth * r / w) ** 2) * np.clip((r - rng.uniform(0.62, 0.8)) / 0.2, 0, 1)
        img = img * (1 - 0.35 * m[..., None]) + np.array([0.62, 0.18, 0.16]) * 0.35 * m[..., None]
    # iris
    t = np.clip((r - rp) / (ri - rp), 0, 1)
    fib = np.zeros_like(r)
    for k, amp in ((60, 0.5), (140, 0.3), (23, 0.4)):
        ph = rng.uniform(0, 6.28, 3)
        fib += amp * np.sin(th * k + ph[0] + 3 * np.sin(t * 6 + ph[1]))
    fib = fib * 0.5 + 0.5
    dark = np.array([0.025, 0.012, 0.006]); mid = np.array([0.06, 0.027, 0.010]); amber = np.array([0.15, 0.07, 0.022])
    ic = dark + (mid - dark) * (0.4 + 0.6 * fib[..., None]) * np.clip(1.2 - t, 0, 1)[..., None]
    collar = np.exp(-((t - 0.28) / 0.1) ** 2)
    ic = ic + (amber - ic) * (0.55 * collar * (0.5 + 0.5 * fib))[..., None]
    limbal = np.clip((t - 0.82) / 0.18, 0, 1) ** 1.5
    ic = ic * (1 - 0.85 * limbal[..., None])
    inside = r < ri
    soft = np.clip((ri - r) / 0.012, 0, 1)
    img = img * (1 - soft[..., None]) + ic * soft[..., None]
    pup = np.clip((rp - r) / 0.01, 0, 1)
    img = img * (1 - pup[..., None]) + 0.004 * pup[..., None]
    from PIL import Image
    srgb = np.where(img <= 0.0031308, img * 12.92, 1.055 * np.power(np.clip(img, 0, 1), 1 / 2.4) - 0.055)
    Image.fromarray((np.clip(srgb, 0, 1) * 255).astype(np.uint8)[::-1]).save(path)
    return path


def eye_materials():
    path = os.path.join(TEX, 'arjun_iris.png')
    if not os.path.exists(path):
        make_iris_texture(path)
    m = U.new_mat('ARJ_Eye')
    N, L = U.nodes(m); p = U.principled(m)
    img = N.new('ShaderNodeTexImage'); img.image = bpy.data.images.load(path, check_existing=True)
    L.new(img.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.35
    p.inputs['Subsurface Weight'].default_value = 0.15
    p.inputs['Subsurface Radius'].default_value = (1, 0.5, 0.4)
    p.inputs['Subsurface Scale'].default_value = 0.001
    # cornea: transparent + sharp glossy (no refraction -> no noisy caustics)
    c = U.new_mat('ARJ_Cornea')
    nt = c.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.06
    fr = nt.nodes.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.45
    add = nt.nodes.new('ShaderNodeMixShader')
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MULTIPLY_ADD'
    nt.links.new(fr.outputs[0], mx.inputs[0]); mx.inputs[1].default_value = 0.45; mx.inputs[2].default_value = 0.025
    nt.links.new(mx.outputs[0], add.inputs[0])
    nt.links.new(tr.outputs[0], add.inputs[1]); nt.links.new(gl.outputs[0], add.inputs[2])
    nt.links.new(add.outputs[0], o.inputs[0])
    return m, c


def uv_sphere(R, nu=64, nv=40):
    th = np.linspace(0, np.pi, nv)
    ph = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    T, P = np.meshgrid(th, ph, indexing='ij')
    # pole axis = -Y (front)
    x = R * np.sin(T) * np.cos(P); z = R * np.sin(T) * np.sin(P); y = -R * np.cos(T)
    V = np.c_[x.ravel(), y.ravel(), z.ravel()]
    F = []
    for i in range(nv - 1):
        for j in range(nu):
            a = i * nu + j; b = i * nu + (j + 1) % nu
            F.append([a, b, b + nu, a + nu])
    return V, np.array(F)


def build_eye(coll, side, eye_mat, cornea_mat):
    E = H.EYE_L if side == 'L' else H.EYE_RT
    V, F = uv_sphere(H.EYE_R)
    ob = U.mesh_obj(f'ARJ_Eye.{side}', V, F, coll, mat=eye_mat)
    me = ob.data
    uv = me.uv_layers.new(name='UVMap')
    lv = np.array([l.vertex_index for l in me.loops])
    P = V[lv]
    xz = P[:, [0, 2]] / H.EYE_R
    back = P[:, 1] > 0
    xz[back] = xz[back] / np.maximum(np.linalg.norm(xz[back], axis=1, keepdims=True), 1e-6) * 0.99
    uvs = xz * 0.5 + 0.5
    uv.data.foreach_set('uv', uvs.astype(np.float32).ravel())
    ob.location = E
    # cornea bulge (spherical cap)
    Rc = H.EYE_R * 0.62
    off = H.EYE_R * np.cos(IRIS_A + 0.05) - np.sqrt(Rc ** 2 - (H.EYE_R * np.sin(IRIS_A + 0.05)) ** 2)
    Vc, Fc = uv_sphere(Rc, 48, 24)
    keep_rows = 12
    Vc = Vc[:keep_rows * 48]; Fc = Fc[: (keep_rows - 1) * 48]
    Vc[:, 1] -= off
    co = U.mesh_obj(f'ARJ_Cornea.{side}', Vc, Fc, coll, mat=cornea_mat)
    co.parent = ob
    return ob


# ------------------------------------------------------------------ lids
def lid_edge(theta, upper):
    th = np.abs(theta)
    if upper:
        return np.radians(96) - np.radians(35) * np.cos(np.clip(theta, -np.pi / 2, np.pi / 2)) ** 1.3
    return np.radians(97) - np.radians(30) * np.cos(np.clip(theta, -np.pi / 2, np.pi / 2)) ** 1.5


def lid_dir(phi, th, upper):
    s = 1 if upper else -1
    return np.stack([np.sin(phi) * np.sin(th), -np.sin(phi) * np.cos(th), s * np.cos(phi)], -1)


def build_lid(coll, side, upper, mat):
    R_out = H.EYE_R + (0.00072 if upper else 0.00060)
    R_in = H.EYE_R + (0.00022 if upper else 0.00014)
    nth, nph, nrim = 72, 22, 9
    th = np.linspace(-np.radians(118), np.radians(118), nth)
    rows = []   # list of (radius, phi-fraction-or-abs) per row
    pts = []
    tags = []
    pe = lid_edge(th, upper)
    for i in range(nph):            # outer surface pole -> edge
        f = i / (nph - 1)
        phi = pe * f
        pts.append(lid_dir(phi, th, upper) * R_out); tags.append(np.full(nth, f))
    h = (R_out - R_in) / 2; Rm = (R_out + R_in) / 2
    for k in range(1, nrim):        # rounded rim
        t = k / nrim
        rr = Rm + h * np.cos(np.pi * t)
        phi = pe + (h / Rm) * np.sin(np.pi * t) * 1.4
        pts.append(lid_dir(phi, th, upper) * rr); tags.append(np.full(nth, 1.0 + t))
    for i in range(nph - 1, -1, -1):  # inner surface edge -> pole
        f = i / (nph - 1)
        pts.append(lid_dir(pe * f, th, upper) * R_in); tags.append(np.full(nth, 2.0 + (1 - f)))
    P = np.concatenate(pts); T = np.concatenate(tags)
    nr = len(pts)
    F = [[r * nth + j, r * nth + j + 1, (r + 1) * nth + j + 1, (r + 1) * nth + j]
         for r in range(nr - 1) for j in range(nth - 1)]
    name = f"ARJ_Lid{'Up' if upper else 'Lo'}.{side}"
    ob = U.mesh_obj(name, P, F, coll, mat=mat)
    # tint: lash line darkening + crease + skin colour
    lash = np.clip((T - 0.93) / 0.07, 0, 1) * np.clip((2.35 - T) / 0.25, 0, 1)
    if not upper:
        lash *= 0.55
    crease = np.exp(-((T - 0.62) / 0.06) ** 2) * (0.6 if upper else 0.0)
    col = np.tile(np.array(SKIN) * np.array([0.82, 0.78, 0.8]), (len(P), 1))
    if not upper:
        col = col * 0.72 + np.array([0.10, 0.05, 0.06]) * 0.28    # tired under-eye
    col = col * (1 - 0.35 * crease[:, None])
    col = col * (1 - 0.9 * lash[:, None]) + np.array([0.02, 0.012, 0.01]) * 0.9 * lash[:, None]
    wet = np.clip((T - 1.5) / 0.4, 0, 1) * np.clip((2.2 - T) / 0.2, 0, 1)
    col = col * (1 - 0.6 * wet[:, None]) + np.array([0.55, 0.22, 0.2]) * 0.6 * wet[:, None]
    U.set_color_attr(ob, 'skin_col', np.c_[col, np.ones(len(P))])
    U.set_float_attr(ob, 'stubble', np.zeros(len(P)))
    E = H.EYE_L if side == 'L' else H.EYE_RT
    ob.location = E
    edge_pts = lid_dir(pe, th, upper) * R_out
    return ob, th, pe, R_out


# ------------------------------------------------------------- hair curves
def hair_curves_obj(name, strands, radius_root, radius_tip, coll, mat):
    """strands: list of (n_i,3) arrays."""
    hc = bpy.data.hair_curves.new(name)
    sizes = [len(s) for s in strands]
    hc.add_curves(sizes)
    pos = np.concatenate(strands).astype(np.float32)
    hc.position_data.foreach_set('vector', pos.ravel())
    rad = np.concatenate([np.linspace(1, 0, n) for n in sizes])
    if np.ndim(radius_root) == 0:
        rr = np.concatenate([np.full(n, radius_root) for n in sizes])
    else:
        rr = np.concatenate([np.full(n, r) for n, r in zip(sizes, radius_root)])
    radius = radius_tip + (rr - radius_tip) * rad ** 0.7
    ra = hc.attributes.get('radius') or hc.attributes.new('radius', 'FLOAT', 'POINT')
    ra.data.foreach_set('value', radius.astype(np.float32))
    ob = bpy.data.objects.new(name, hc)
    U.link(ob, coll)
    hc.materials.append(mat)
    return ob


def hair_material(name, melanin=0.92, redness=0.35, rough=0.32, coat=0.15):
    m = U.new_mat(name)
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    h = nt.nodes.new('ShaderNodeBsdfHairPrincipled')
    h.parametrization = 'MELANIN'
    h.inputs['Melanin'].default_value = melanin
    h.inputs['Melanin Redness'].default_value = redness
    h.inputs['Roughness'].default_value = rough
    h.inputs['Radial Roughness'].default_value = 0.4
    h.inputs['Coat'].default_value = coat
    nt.links.new(h.outputs[0], o.inputs[0])
    return m


def lashes(lid_ob, th, pe, R, upper, coll, mat, seed):
    rng = np.random.default_rng(seed)
    n = 70 if upper else 34
    tt = np.sort(rng.uniform(-np.radians(72), np.radians(80), n))
    side_sign = 1 if lid_ob.name.endswith('.L') else -1
    tt = tt * side_sign          # outer corner = +x for left eye
    strands = []
    for t in tt:
        phi = np.interp(t, th, pe) - 0.03
        root = lid_dir(phi, t, upper) * (R + 0.0002)
        nrm = root / np.linalg.norm(root)
        d2 = lid_dir(phi + 0.01, t, upper) * R
        tp = d2 - lid_dir(phi, t, upper) * R; tp /= np.linalg.norm(tp)
        frac = 1 - (abs(t) / np.radians(85)) ** 2
        outer = 0.5 + 0.5 * np.tanh((t * side_sign) * 3)
        L = (0.0062 if upper else 0.0028) * (0.55 + 0.45 * frac) * (0.85 + 0.3 * outer) * rng.uniform(0.85, 1.1)
        sweep = np.array([side_sign, 0, 0]) * (0.25 * outer)
        ts = np.linspace(0, 1, 6)
        up = -tp if upper else tp
        pts = [root + L * (nrm * (0.75 * s) + tp * (0.6 * s - 1.1 * s * s) * (1 if upper else 0.6)
                           + sweep * s) for s in ts]
        strands.append(np.array(pts))
    ob = hair_curves_obj(lid_ob.name.replace('Lid', 'Lash'), strands, 0.00011, 0.00002, coll, mat)
    ob.parent = lid_ob
    return ob


# ------------------------------------------------------------- brows
def surface_project(fn, P, offset=0.0, iters=4):
    for _ in range(iters):
        d = fn(P) - offset
        n = sdf_normal(fn, P)
        P = P - n * d[:, None]
    return P


def brow_strands(side, seed):
    rng = np.random.default_rng(seed)
    s = 1 if side == 'L' else -1
    fn = lambda P: H.head_sdf(P, socket=False, neck=False)
    n = 620
    u = rng.random(n) ** 0.85                 # 0 inner .. 1 outer
    x = 0.011 + u * 0.047
    zc = 0.0195 + 0.006 * np.sin(np.clip(u * 1.25, 0, 1) * np.pi * 0.85) - 0.004 * u
    thick = 0.0074 * (1 - u) + 0.0026 * u
    z = zc + (rng.random(n) - 0.5) * thick
    P = np.c_[x * s, np.full(n, -0.12), z]
    # ray-march along +y onto head surface
    for _ in range(40):
        d = fn(P); P[:, 1] += np.maximum(d, 0) * 0.9
    P = surface_project(fn, P, 0.0003)
    strands = []
    for i in range(n):
        ang = np.radians(80 - 75 * min(u[i] * 2.2, 1) - 15 * u[i])     # inner hairs point up
        dirw = np.array([np.cos(ang) * s, 0, np.sin(ang)])
        dirw += rng.normal(0, 0.15, 3)
        L = (0.0048 + 0.0025 * (1 - u[i])) * rng.uniform(0.7, 1.1)
        pts = [P[i]]
        p = P[i].copy()
        for k in range(4):
            nrm = sdf_normal(fn, p[None])[0]
            t = dirw - nrm * (dirw @ nrm); t /= np.linalg.norm(t)
            p = p + t * L / 4 + nrm * 0.00035 * (k == 0)
            pts.append(p.copy())
        strands.append(np.array(pts))
    return strands


def build_brow(coll, side, mat, seed):
    st = brow_strands(side, seed)
    ob = hair_curves_obj(f'ARJ_Brow.{side}', st, 0.00014, 0.00003, coll, mat)
    return ob
