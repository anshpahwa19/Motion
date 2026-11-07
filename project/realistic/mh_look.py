"""ARJUN (realistic) — look development: skin, eyes, teeth, groomed strand hair
(scalp, brows, lashes, stubble) attached to the skin so it follows shape keys
and the rig ('Deform Curves on Surface'), and a cotton T-shirt.
"""
import os
import numpy as np
import bpy
from mathutils import Vector
from scipy.spatial import cKDTree
from sdf_noise import vnoise

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, '..', 'assets', 'textures')


def hex2lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def verts(ob):
    a = np.empty(len(ob.data.vertices) * 3, np.float32); ob.data.vertices.foreach_get('co', a)
    return a.reshape(-1, 3).astype(np.float64)


def vnormals(ob):
    a = np.empty(len(ob.data.vertices) * 3, np.float32); ob.data.vertices.foreach_get('normal', a)
    return a.reshape(-1, 3).astype(np.float64)


def gauss(P, c, r):
    q = (P - np.asarray(c)) / np.asarray(r); return np.exp(-np.einsum('ij,ij->i', q, q))


def mirror(P):
    Q = P.copy(); Q[:, 0] = np.abs(Q[:, 0]); return Q


class Face:
    """Facial landmark frame from rig joints (metres, body space)."""
    def __init__(self, info):
        j = info['joints']
        self.eL = np.array(j['joint-l-eye']); self.eR = np.array(j['joint-r-eye'])
        self.e = (self.eL + self.eR) / 2
        self.eye_r = 0.0121
        hv = info['helpers']['helper-l-eye'][0]
        self.eL = hv.mean(0); self.eR = info['helpers']['helper-r-eye'][0].mean(0)
        self.e = (self.eL + self.eR) / 2

    def local(self, P):
        return P - self.e      # x left, -y forward, z up (eye-line origin)


# ------------------------------------------------------------------ skin
def skin_maps(P, F):
    L = F.local(P); M = mirror(L)
    n = len(P)
    base = np.array(hex2lin('#7f5843'))
    col = np.tile(base, (n, 1))
    rng = np.random.default_rng(4)
    # large-scale melanin variation
    mel = vnoise(P, 18, 1) * 0.5 + vnoise(P, 55, 2) * 0.25
    col *= (1 + 0.09 * mel)[:, None]
    red = (gauss(M, (0.035, -0.045, -0.035), (0.025, 0.04, 0.025)) * 0.6 +          # cheeks
           gauss(L, (0, -0.075, -0.035), (0.012, 0.03, 0.02)) * 0.7 +              # nose tip
           gauss(M, (0.075, 0.025, -0.01), (0.012, 0.04, 0.035)) * 0.7)            # ears
    col = col * (1 - 0.18 * red[:, None]) + np.array([0.40, 0.12, 0.08]) * 0.18 * red[:, None]
    under = gauss(M, (0.030, -0.028, -0.016), (0.016, 0.03, 0.007))                # dark circles
    lid = gauss(M, (0.030, -0.03, 0.009), (0.017, 0.03, 0.008))                     # pigmented lids
    col = col * (1 - 0.32 * under[:, None]) + np.array([0.11, 0.06, 0.07]) * 0.32 * under[:, None]
    col = col * (1 - 0.22 * lid[:, None]) + np.array([0.13, 0.07, 0.055]) * 0.22 * lid[:, None]
    lips = np.clip(MASKS.get('lips', np.zeros(n)) * 1.2, 0, 1)
    lid = np.maximum(lid, MASKS.get('lids', np.zeros(n)) * 0.6)
    red = np.maximum(red, MASKS.get('ears', np.zeros(n)) * 0.5)
    mott = vnoise(P, 420, 7) * 0.5 + vnoise(P, 1100, 8) * 0.3
    col *= (1 + 0.07 * mott)[:, None]
    spots = np.clip((vnoise(P, 260, 9) - 0.78) * 6, 0, 1) * (1 - lips)
    col *= (1 - 0.18 * spots)[:, None]
    col = col * (1 - 0.5 * lips[:, None]) + np.array(hex2lin('#5e3530')) * 0.5 * lips[:, None]
    # beard shadow (stubble region)
    beard = beard_mask(L)
    col = col * (1 - 0.38 * beard[:, None]) + np.array([0.030, 0.032, 0.036]) * 0.38 * beard[:, None]
    # body: knuckles / elbows slightly darker, palms lighter handled by AO naturally
    rough = 0.48 - 0.10 * (gauss(L, (0, -0.07, 0.04), (0.04, 0.05, 0.03)) + gauss(L, (0, -0.08, -0.03), (0.012, 0.03, 0.03))) \
        + 0.08 * beard - 0.08 * lips
    pore = 0.55 + 0.45 * (gauss(M, (0.03, -0.05, -0.03), (0.03, 0.05, 0.03)) + gauss(L, (0, -0.075, -0.03), (0.015, 0.03, 0.02)))
    wrink = gauss(L, (0, -0.06, 0.06), (0.045, 0.05, 0.02))                         # forehead lines
    crow = gauss(M, (0.052, -0.02, 0.0), (0.008, 0.03, 0.01))
    return np.c_[col, np.ones(n)], np.clip(rough, 0.3, 0.7), np.clip(pore, 0, 1), wrink, crow, beard


def beard_mask(L):
    z, y, x = L[:, 2], L[:, 1], np.abs(L[:, 0])
    m = np.clip((-z - 0.050) / 0.015, 0, 1)                       # below cheekbones
    m *= np.clip((0.035 - y) / 0.03, 0, 1)                        # in front of ears/jaw angle
    m *= np.clip((z + 0.175) / 0.025, 0, 1)                       # fade down the neck
    m *= np.clip((0.075 - x) / 0.02, 0, 1)
    moust = np.exp(-((L[:, 0] / 0.024) ** 2 + ((z + 0.058) / 0.006) ** 2)) * (y < -0.05)
    m = np.maximum(m, moust)
    lips = np.exp(-((L[:, 0] / 0.022) ** 2 + ((z + 0.073) / 0.011) ** 2)) * (y < -0.05)
    m *= np.clip(1 - lips * 1.6, 0, 1)
    if 'lips_wide' in MASKS and len(MASKS['lips_wide']) == len(L):
        m *= np.clip(1 - MASKS['lips_wide'] * 2.2, 0, 1)
    cheek_top = np.exp(-(((x - 0.035) / 0.02) ** 2 + ((z + 0.04) / 0.012) ** 2))
    return np.clip(m * (1 - 0.7 * cheek_top), 0, 1)


def skin_material():
    m = bpy.data.materials.new('ARJ_Skin'); m.use_nodes = True
    nt = m.node_tree; N, Lk = nt.nodes, nt.links
    p = N['Principled BSDF']; p.subsurface_method = 'RANDOM_WALK_SKIN'
    a_col = N.new('ShaderNodeAttribute'); a_col.attribute_name = 'skin_col'
    a_r = N.new('ShaderNodeAttribute'); a_r.attribute_name = 'skin_rough'
    a_p = N.new('ShaderNodeAttribute'); a_p.attribute_name = 'skin_pore'
    a_w = N.new('ShaderNodeAttribute'); a_w.attribute_name = 'skin_wrinkle'
    a_c = N.new('ShaderNodeAttribute'); a_c.attribute_name = 'skin_crow'
    tc = N.new('ShaderNodeTexCoord')
    # pores: voronoi cells (~0.45 mm) + fine noise
    vor = N.new('ShaderNodeTexVoronoi'); vor.feature = 'SMOOTH_F1'; vor.inputs['Scale'].default_value = 1500
    vor.inputs['Randomness'].default_value = 1.0
    Lk.new(tc.outputs['Object'], vor.inputs['Vector'])
    fine = N.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 6000; fine.inputs['Detail'].default_value = 2
    Lk.new(tc.outputs['Object'], fine.inputs['Vector'])
    # micro-wrinkle crosshatch (stretched noise)
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (900, 900, 120)
    Lk.new(tc.outputs['Object'], mp.inputs['Vector'])
    cross = N.new('ShaderNodeTexNoise'); cross.inputs['Detail'].default_value = 3
    Lk.new(mp.outputs['Vector'], cross.inputs['Vector'])
    # forehead lines: horizontal waves
    mp2 = N.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (1, 1, 1)
    Lk.new(tc.outputs['Object'], mp2.inputs['Vector'])
    wav = N.new('ShaderNodeTexWave'); wav.bands_direction = 'Z'; wav.inputs['Scale'].default_value = 90
    wav.inputs['Distortion'].default_value = 3; wav.inputs['Detail'].default_value = 3
    Lk.new(mp2.outputs['Vector'], wav.inputs['Vector'])

    def math(op, a, b, v=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        Lk.new(a, n.inputs[0]) if not isinstance(a, float) else n.inputs[0].__setattr__('default_value', a)
        if isinstance(b, float):
            n.inputs[1].default_value = b
        else:
            Lk.new(b, n.inputs[1])
        return n.outputs[0]
    pores = math('MULTIPLY', vor.outputs['Distance'], a_p.outputs['Fac'])
    h = math('ADD', pores, math('MULTIPLY', fine.outputs['Fac'], 0.35))
    h = math('ADD', h, math('MULTIPLY', cross.outputs['Fac'], 0.25))
    h = math('ADD', h, math('MULTIPLY', math('MULTIPLY', wav.outputs['Fac'], a_w.outputs['Fac']), 0.6))
    a_l = N.new('ShaderNodeAttribute'); a_l.attribute_name = 'lips_m'
    lw = N.new('ShaderNodeTexWave'); lw.bands_direction = 'X'; lw.inputs['Scale'].default_value = 900
    lw.inputs['Distortion'].default_value = 4; lw.inputs['Detail'].default_value = 2
    Lk.new(tc.outputs['Object'], lw.inputs['Vector'])
    h = math('ADD', h, math('MULTIPLY', math('MULTIPLY', lw.outputs['Fac'], a_l.outputs['Fac']), 0.8))
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 1.0
    bump.inputs['Distance'].default_value = 0.0006
    Lk.new(h, bump.inputs['Height'])
    Lk.new(bump.outputs['Normal'], p.inputs['Normal'])
    # albedo: attribute colour, pores slightly darker
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    Lk.new(math('MULTIPLY', math('SUBTRACT', 1.0, vor.outputs['Distance']), 0.28), mix.inputs['Factor'])
    Lk.new(a_col.outputs['Color'], mix.inputs['A']); mix.inputs['B'].default_value = (0.7, 0.62, 0.6, 1)
    Lk.new(mix.outputs['Result'], p.inputs['Base Color'])
    # roughness: map + micro variation
    rr = math('ADD', a_r.outputs['Fac'], math('MULTIPLY', math('SUBTRACT', fine.outputs['Fac'], 0.5), 0.12))
    Lk.new(rr, p.inputs['Roughness'])
    p.inputs['Specular IOR Level'].default_value = 0.5
    p.inputs['IOR'].default_value = 1.4
    p.inputs['Subsurface Weight'].default_value = 0.6
    p.inputs['Subsurface Radius'].default_value = (1.0, 0.36, 0.17)
    p.inputs['Subsurface Scale'].default_value = 0.0025
    p.inputs['Subsurface Anisotropy'].default_value = 0.8
    p.inputs['Coat Weight'].default_value = 0.08; p.inputs['Coat Roughness'].default_value = 0.35
    return m


def vertex_uv(ob):
    me = ob.data
    uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv)
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    out = np.zeros((len(me.vertices), 2)); out[lv] = uv.reshape(-1, 2)
    return out


def uv_mask(ob, name, blur=0):
    from PIL import Image, ImageFilter
    import mh_body as MB
    im = Image.open(os.path.join(MB.MH, 'textures', name)).convert('L')
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(im, np.float32) / 255
    uv = vertex_uv(ob)
    x = np.clip((uv[:, 0] * (a.shape[1] - 1)).astype(int), 0, a.shape[1] - 1)
    y = np.clip(((1 - uv[:, 1]) * (a.shape[0] - 1)).astype(int), 0, a.shape[0] - 1)
    return a[y, x]


MASKS = {}


def apply_skin(body, F):
    P = verts(body)
    MASKS['lips'] = uv_mask(body, 'mpfb_lips.jpg', 2)
    MASKS['lips_wide'] = uv_mask(body, 'mpfb_lips.jpg', 10)
    MASKS['lids'] = uv_mask(body, 'mpfb_eyelids.jpg', 2)
    MASKS['ears'] = uv_mask(body, 'mpfb_ears.jpg', 4)
    col, rough, pore, wr, crow, beard = skin_maps(P, F)
    me = body.data
    a = me.color_attributes.new('skin_col', 'FLOAT_COLOR', 'POINT'); a.data.foreach_set('color', col.astype(np.float32).ravel())
    for nm, v in (('skin_rough', rough), ('skin_pore', pore * (1 - MASKS['lips'])), ('skin_wrinkle', wr), ('skin_crow', crow), ('beard', beard),
                  ('lips_m', MASKS['lips'])):
        at = me.attributes.new(nm, 'FLOAT', 'POINT'); at.data.foreach_set('value', v.astype(np.float32))
    me.materials.append(skin_material())
    return beard


# ------------------------------------------------------------------ eyes
def iris_texture(path, res=1024, seed=5):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:res, 0:res]
    u = (x + 0.5) / res * 2 - 1; v = (y + 0.5) / res * 2 - 1
    r = np.hypot(u, v); th = np.arctan2(v, u)
    IA, PA = 0.52, 0.19                          # realistic iris/pupil half-angles
    ri, rp = np.sin(IA), np.sin(PA)
    scl = np.array([0.80, 0.74, 0.66])            # slightly warm sclera
    img = np.ones((res, res, 3)) * scl
    edge = np.clip((r - 0.5) / 0.5, 0, 1)
    img = img * (1 - 0.35 * edge[..., None]) + np.array([0.62, 0.42, 0.36]) * 0.35 * edge[..., None]
    for _ in range(60):
        a0 = rng.uniform(0, 2 * np.pi); w = rng.uniform(0.002, 0.006)
        wig = a0 + 0.12 * np.sin(r * rng.uniform(10, 30) + rng.uniform(0, 6))
        dth = np.angle(np.exp(1j * (th - wig)))
        m = np.exp(-(dth * r / w) ** 2) * np.clip((r - rng.uniform(0.58, 0.85)) / 0.2, 0, 1)
        img = img * (1 - 0.45 * m[..., None]) + np.array([0.55, 0.12, 0.10]) * 0.45 * m[..., None]
    t = np.clip((r - rp) / (ri - rp), 0, 1)
    fib = np.zeros_like(r)
    for k, amp in ((90, 0.45), (200, 0.3), (37, 0.35), (13, 0.25)):
        ph = rng.uniform(0, 6.28, 2)
        fib += amp * np.sin(th * k + ph[0] + 2.5 * np.sin(t * 7 + ph[1]))
    fib = fib * 0.5 + 0.5
    crypt = np.clip(np.sin(th * 23 + 4 * t) * np.sin(t * 18) - 0.6, 0, 1)
    dark = np.array([0.018, 0.009, 0.005]); mid = np.array([0.045, 0.022, 0.009]); amber = np.array([0.12, 0.06, 0.022])
    ic = dark + (mid - dark) * (0.3 + 0.7 * fib[..., None])
    collar = np.exp(-((t - 0.3) / 0.09) ** 2)
    ic = ic + (amber - ic) * (0.45 * collar * (0.4 + 0.6 * fib))[..., None]
    ic = ic * (1 - 0.5 * crypt[..., None])
    limbal = np.clip((t - 0.8) / 0.2, 0, 1) ** 1.3
    ic = ic * (1 - 0.8 * limbal[..., None])
    soft = np.clip((ri - r) / 0.02, 0, 1)
    img = img * (1 - soft[..., None]) + ic * soft[..., None]
    pup = np.clip((rp - r) / 0.008, 0, 1)
    img = img * (1 - pup[..., None]) + 0.003 * pup[..., None]
    from PIL import Image
    srgb = np.where(img <= 0.0031308, img * 12.92, 1.055 * np.power(np.clip(img, 0, 1), 1 / 2.4) - 0.055)
    Image.fromarray((np.clip(srgb, 0, 1) * 255).astype(np.uint8)[::-1]).save(path)


def uv_sphere(R, nu=72, nv=48):
    th = np.linspace(0, np.pi, nv); ph = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    T, P = np.meshgrid(th, ph, indexing='ij')
    V = np.c_[(R * np.sin(T) * np.cos(P)).ravel(), (-R * np.cos(T)).ravel(), (R * np.sin(T) * np.sin(P)).ravel()]
    F = [[i * nu + j, i * nu + (j + 1) % nu, (i + 1) * nu + (j + 1) % nu, (i + 1) * nu + j] for i in range(nv - 1) for j in range(nu)]
    return V, F


def mesh_obj(name, V, F, coll, mat=None, smooth=True):
    me = bpy.data.meshes.new(name); me.from_pydata(np.asarray(V).tolist(), [], [list(f) for f in F]); me.update()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    if mat:
        me.materials.append(mat)
    return ob


def build_eyes(coll, F, rig):
    os.makedirs(TEX, exist_ok=True)
    path = os.path.join(TEX, 'arjun_iris_real.png')
    if not os.path.exists(path):
        iris_texture(path)
    m = bpy.data.materials.new('ARJ_EyeReal'); m.use_nodes = True
    N, Lk = m.node_tree.nodes, m.node_tree.links; p = N['Principled BSDF']
    im = N.new('ShaderNodeTexImage'); im.image = bpy.data.images.load(path)
    Lk.new(im.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.45; p.inputs['Specular IOR Level'].default_value = 0.2
    p.inputs['Subsurface Weight'].default_value = 0.3; p.inputs['Subsurface Radius'].default_value = (1, 0.5, 0.4)
    p.inputs['Subsurface Scale'].default_value = 0.0015
    c = bpy.data.materials.new('ARJ_CorneaReal'); c.use_nodes = True
    nt = c.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.01
    fr = nt.nodes.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.376
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fr.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], o.inputs[0])
    eyes = []
    R = F.eye_r
    for side, ctr in (('L', F.eL), ('R', F.eR)):
        V, Fc = uv_sphere(R)
        ob = mesh_obj(f'ARJ_EyeBall.{side}', V, Fc, coll, m)
        me = ob.data; uv = me.uv_layers.new(name='UVMap')
        lv = np.array([l.vertex_index for l in me.loops]); Pp = np.array(V)[lv]
        xz = Pp[:, [0, 2]] / R; back = Pp[:, 1] > 0
        xz[back] = xz[back] / np.maximum(np.linalg.norm(xz[back], axis=1, keepdims=True), 1e-6) * 0.99
        uv.data.foreach_set('uv', (xz * 0.5 + 0.5).astype(np.float32).ravel())
        # cornea: bulging cap
        Rc = R * 0.66; ang = 0.56
        off = R * np.cos(ang) - np.sqrt(Rc ** 2 - (R * np.sin(ang)) ** 2)
        Vc, Fcc = uv_sphere(Rc * 1.0, 64, 30); Vc = np.array(Vc)[:64 * 13]; Fcc = Fcc[:64 * 12]; Vc[:, 1] -= off
        co = mesh_obj(f'ARJ_Cornea.{side}', Vc, Fcc, coll, c); co.parent = ob
        # whole eye slightly bigger than the wet cornea; place
        ob.location = Vector(ctr) + Vector((0, -0.0008, 0))
        eyes.append(ob)
        if rig is not None:
            bpy.context.view_layer.update()
            mw = ob.matrix_world.copy()
            ob.parent = rig; ob.parent_type = 'BONE'; ob.parent_bone = 'eye.' + side
            bpy.context.view_layer.update(); ob.matrix_world = mw
    return eyes


def build_mouth(coll, info, rig):
    """Teeth + tongue from MakeHuman helper geometry (only seen when the mouth opens)."""
    out = []
    tm = bpy.data.materials.new('ARJ_Teeth'); tm.use_nodes = True
    p = tm.node_tree.nodes['Principled BSDF']; p.inputs['Base Color'].default_value = (0.72, 0.66, 0.56, 1)
    p.inputs['Roughness'].default_value = 0.25; p.inputs['Subsurface Weight'].default_value = 0.4
    gm = bpy.data.materials.new('ARJ_Gum'); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*hex2lin('#7a3a36'), 1)
    for h, mat in (('helper-upper-teeth', tm), ('helper-lower-teeth', tm), ('helper-tongue', gm)):
        if h in info['helpers']:
            V, Fh = info['helpers'][h]
            ob = mesh_obj('ARJ_' + h.replace('helper-', ''), V, Fh, coll, mat)
            sd = ob.modifiers.new('s', 'SUBSURF'); sd.levels = 1; sd.render_levels = 2
            if rig is not None:
                bpy.context.view_layer.update(); mw = ob.matrix_world.copy()
                bone = 'jaw' if ('lower' in h or 'tongue' in h) and 'jaw' in rig.data.bones else 'head'
                ob.parent = rig; ob.parent_type = 'BONE'; ob.parent_bone = bone
                bpy.context.view_layer.update(); ob.matrix_world = mw
            out.append(ob)
    return out


# ------------------------------------------------------------------ strands on the surface
class Surface:
    def __init__(self, ob):
        self.ob = ob
        me = ob.data
        me.calc_loop_triangles()
        nt = len(me.loop_triangles)
        tri_v = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('vertices', tri_v)
        tri_l = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('loops', tri_l)
        self.tv = tri_v.reshape(-1, 3); self.tl = tri_l.reshape(-1, 3)
        self.V = verts(ob); self.N = vnormals(ob)
        uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv)
        self.UV = uv.reshape(-1, 2)
        T = self.V[self.tv]
        self.area = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2
        self.cent = T.mean(1)
        # dense samples for distance queries
        self.kd = cKDTree(self.V)

    def sample(self, n, weight_fn, rng):
        w = self.area * np.clip(weight_fn(self.cent), 0, None)
        idx = rng.choice(len(w), n, p=w / w.sum())
        r1 = np.sqrt(rng.random(n)); r2 = rng.random(n)
        b = np.c_[1 - r1, r1 * (1 - r2), r1 * r2]
        P = np.einsum('ij,ijk->ik', b, self.V[self.tv[idx]])
        Nn = np.einsum('ij,ijk->ik', b, self.N[self.tv[idx]])
        Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
        UV = np.einsum('ij,ijk->ik', b, self.UV[self.tl[idx]])
        keep = np.clip(weight_fn(P), 0, 1) > rng.random(n) * 0.999   # per-point density shaping
        return P[keep], Nn[keep], UV[keep]

    def project(self, P, min_off):
        d, i = self.kd.query(P)
        n = self.N[i]; q = self.V[i]
        s = np.einsum('ij,ij->i', P - q, n)
        push = np.maximum(min_off - s, 0)
        return P + n * push[:, None], n


def curves_obj(name, strands, radii_root, radius_tip, coll, mat, surface=None, uvs=None):
    hc = bpy.data.hair_curves.new(name)
    sizes = [len(s) for s in strands]
    hc.add_curves(sizes)
    hc.position_data.foreach_set('vector', np.concatenate(strands).astype(np.float32).ravel())
    t = np.concatenate([np.linspace(0, 1, n) for n in sizes])
    rr = np.repeat(np.broadcast_to(np.asarray(radii_root, float), (len(sizes),)), sizes)
    rad = radius_tip + (rr - radius_tip) * (1 - t) ** 0.8
    ra = hc.attributes.get('radius') or hc.attributes.new('radius', 'FLOAT', 'POINT')
    ra.data.foreach_set('value', rad.astype(np.float32))
    ob = bpy.data.objects.new(name, hc); coll.objects.link(ob)
    hc.materials.append(mat)
    if surface is not None and uvs is not None:
        hc.surface = surface; hc.surface_uv_map = 'UVMap'
        at = hc.attributes.new('surface_uv_coordinate', 'FLOAT2', 'CURVE')
        at.data.foreach_set('vector', np.asarray(uvs, np.float32).ravel())
        ng = bpy.data.node_groups.new('DeformOnSurface', 'GeometryNodeTree')
        ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        gi = ng.nodes.new('NodeGroupInput'); go = ng.nodes.new('NodeGroupOutput')
        dn = ng.nodes.new('GeometryNodeDeformCurvesOnSurface')
        ng.links.new(gi.outputs[0], dn.inputs[0]); ng.links.new(dn.outputs[0], go.inputs[0])
        mod = ob.modifiers.new('Surface Deform', 'NODES'); mod.node_group = ng
        ob.parent = surface
    return ob


def hair_mat(name, melanin=0.97, red=0.25, rough=0.38, radial=0.45, random=0.15):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); h = nt.nodes.new('ShaderNodeBsdfHairPrincipled')
    h.parametrization = 'MELANIN'
    h.inputs['Melanin'].default_value = melanin; h.inputs['Melanin Redness'].default_value = red
    h.inputs['Roughness'].default_value = rough; h.inputs['Radial Roughness'].default_value = radial
    h.inputs['Random Color'].default_value = random; h.inputs['Random Roughness'].default_value = 0.2
    h.inputs['Coat'].default_value = 0.0
    nt.links.new(h.outputs[0], o.inputs[0])
    return m


def grow(S, roots, nrm, dirs, lengths, nseg, rng, min_off=0.0004, lift=0.0, gravity=0.0, curl=0.0):
    pts = [roots.copy()]; p = roots.copy(); d = dirs.copy()
    for k in range(nseg):
        _, i = S.kd.query(p); n = S.N[i]
        t = d - n * np.einsum('ij,ij->i', d, n)[:, None]
        t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
        lf = np.broadcast_to(np.asarray(lift, float), (len(p),))
        out = n * (lf * (1 - k / nseg) + (0.5 if k == 0 else 0.0))[:, None]
        step = t + out
        if curl:
            step += np.cross(n, t) * curl * np.sin(k * 0.9 + rng.uniform(0, 6, (len(p), 1)))
        step /= np.linalg.norm(step, axis=1, keepdims=True)
        p = p + step * (lengths / nseg)[:, None]
        p[:, 2] -= gravity * (k / nseg) * lengths
        p, _ = S.project(p, min_off * (1 + k * 0.6))
        pts.append(p.copy())
    return np.stack(pts, 1)


def build_brows(coll, S, F, rng):
    def region(P):
        L = F.local(P); x = np.abs(L[:, 0])
        u = np.clip((x - 0.010) / 0.050, 0, 1)
        zc = 0.020 + 0.009 * np.sin(np.clip(u * 1.2, 0, 1) * np.pi * 0.9) - 0.002 * u
        th = 0.0085 * (1 - u) + 0.0032 * u
        inside = np.exp(-((L[:, 2] - zc) / th) ** 4) * (x > 0.008) * (x < 0.062) * (L[:, 1] < -0.02)
        return inside * (1 - 0.6 * u)
    P, Nn, UV = S.sample(9000, region, rng)
    L = F.local(P); s = np.sign(L[:, 0]); u = np.clip((np.abs(L[:, 0]) - 0.010) / 0.05, 0, 1)
    ang = np.radians(75 - 70 * np.clip(u * 2.4, 0, 1) - 12 * u) + rng.normal(0, 0.18, len(P))
    d = np.c_[np.cos(ang) * s, np.zeros(len(P)), np.sin(ang)]
    Ls = (0.0045 + 0.0035 * (1 - u)) * rng.uniform(0.65, 1.15, len(P))
    st = grow(S, P, Nn, d, Ls, 4, rng, min_off=0.00025)
    return curves_obj('ARJ_Brows', list(st), rng.uniform(0.00005, 0.00008, len(P)), 0.00001, coll,
                      hair_mat('ARJ_BrowMat', 0.99, 0.12, 0.42), S.ob, UV)


def beard_mask_surface(S, F, Q):
    m = beard_mask(F.local(Q))
    if 'lips_wide' in MASKS:
        _, i = S.kd.query(Q)
        m = m * np.clip(1 - MASKS['lips_wide'][i] * 2.2, 0, 1)
    return m


def build_stubble(coll, S, F, rng):
    P, Nn, UV = S.sample(55000, lambda Q: beard_mask_surface(S, F, Q), rng)
    L = F.local(P)
    down = np.c_[np.zeros(len(P)), -0.25 * np.ones(len(P)), -np.ones(len(P))]
    d = down + rng.normal(0, 0.5, (len(P), 3)) + Nn * 1.2
    Ls = rng.gamma(2.5, 0.00035, len(P)) + 0.0003          # ~2-day stubble
    st = grow(S, P, Nn, d, Ls, 2, rng, min_off=0.0)
    return curves_obj('ARJ_Stubble', list(st), rng.uniform(0.000035, 0.00005, len(P)), 0.00002, coll,
                      hair_mat('ARJ_StubbleMat', 0.99, 0.1, 0.45, random=0.2), S.ob, UV)


def lid_margins(S, F, side):
    c = F.eL if side == 'L' else F.eR
    d = np.linalg.norm(S.V - c, axis=1)
    front = (S.V[:, 1] - c[1]) < -0.004
    cand = np.nonzero(front & (d < F.eye_r + 0.0022) & (d > F.eye_r - 0.004))[0]
    return cand


def build_lashes(coll, S, F, rng):
    strands, uvs = [], []
    for side in 'LR':
        c = F.eL if side == 'L' else F.eR
        cand = lid_margins(S, F, side)
        if len(cand) < 4:
            continue
        sgn = 1 if side == 'L' else -1
        for upper in (True, False):
            sel = cand[(S.V[cand, 2] > c[2]) == upper]
            if len(sel) < 3:
                continue
            # roots: interpolate along the margin (sorted by x)
            o = np.argsort(S.V[sel, 0]); sel = sel[o]
            Pm = S.V[sel]
            n = 90 if upper else 45
            tt = np.linspace(0.04, 0.96, n) + rng.normal(0, 0.004, n)
            xs = np.interp(tt, np.linspace(0, 1, len(Pm)), np.arange(len(Pm)))
            i0 = np.floor(xs).astype(int); fr = xs - i0; i1 = np.minimum(i0 + 1, len(Pm) - 1)
            R = Pm[i0] * (1 - fr)[:, None] + Pm[i1] * fr[:, None]
            # UV via nearest surface triangle centroid sample
            _, ii = cKDTree(S.cent).query(R)
            U = S.UV[S.tl[ii]].mean(1)
            outw = (R - c); outw /= np.linalg.norm(outw, axis=1, keepdims=True)
            up = np.array([0, 0, 1.0 if upper else -1.0])
            outer = np.clip((R[:, 0] - c[0]) * sgn / 0.014, -1, 1)
            L = (0.0085 if upper else 0.0042) * (0.55 + 0.45 * (1 - np.abs(np.linspace(-1, 1, n)) ** 2)) * (1 + 0.15 * outer)
            for k in range(n):
                r0 = R[k]
                pts = []
                for s in np.linspace(0, 1, 6):
                    pts.append(r0 + L[k] * (outw[k] * 0.8 * s + up * (0.25 * s + 0.55 * s * s) + np.array([sgn * 0.15 * outer[k] * s, 0, 0])))
                strands.append(np.array(pts)); uvs.append(U[k])
    return curves_obj('ARJ_Lashes', strands, 0.000075, 0.00001, coll, hair_mat('ARJ_LashMat', 0.99, 0.1, 0.35), S.ob, np.array(uvs))


def scalp_weight(P, F):
    L = F.local(P)
    a = np.arctan2(L[:, 0], -L[:, 1] - 0.02); aa = np.abs(a)
    zl = np.interp(aa, [0, 0.45, 0.85, 1.05, 1.22, 1.45, 1.75, 2.3, np.pi],
                   [0.072, 0.066, 0.058, 0.040, 0.004, 0.030, 0.024, -0.040, -0.075])
    return np.clip((L[:, 2] - zl) / 0.008, 0, 1)


def build_scalp_hair(coll, S, F, rng, n_guides=1500, n_hair=90000):
    w = lambda Q: scalp_weight(Q, F)
    G, Gn, GUV = S.sample(n_guides, w, rng)
    crown = F.e + np.array([0.012, 0.055, 0.105])
    L = F.local(G)
    rad = G - crown; rad[:, 2] = 0; rad /= np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-6)
    aa = np.abs(np.arctan2(L[:, 0], -L[:, 1]))
    top = np.clip((L[:, 2] - 0.045) / 0.035, 0, 1); front = np.clip(1 - aa / 1.2, 0, 1)
    d = (rad * (0.5 - 0.45 * front[:, None]) + np.array([-0.45, 0.75, 0.35]) * front[:, None]) * top[:, None] \
        + (np.array([0, 0.3, -1.0]) + np.c_[np.sign(L[:, 0]) * 0.15, 0 * aa, 0 * aa]) * (1 - top[:, None])
    d += rng.normal(0, 0.34, d.shape)
    Lg = (0.014 + top * (0.024 + 0.010 * front)) * rng.uniform(0.85, 1.15, len(G))
    lift = np.clip(rng.normal(0.4, 0.15, len(G)), 0.1, 0.8) * (0.4 + 0.6 * top) * (1 + 0.8 * front)
    GS = grow(S, G, Gn, d, Lg, 10, rng, min_off=0.0015, lift=lift, gravity=0.06)
    # children clumped around guides
    P, Pn, UV = S.sample(n_hair, w, rng)
    _, gi = cKDTree(G).query(P)
    rel = GS[gi] - GS[gi][:, :1]
    t = np.linspace(0, 1, GS.shape[1])[None, :, None]
    clump = rng.uniform(0.35, 0.8, len(P))[:, None, None]
    ch = P[:, None, :] + rel * rng.uniform(0.85, 1.08, len(P))[:, None, None]
    ch = ch * (1 - clump * t ** 1.5) + GS[gi] * clump * t ** 1.5
    ch += rng.normal(0, 0.0007, ch.shape) * t
    fly = rng.random(len(P)) < 0.02
    ch[fly] += rng.normal(0, 0.003, (fly.sum(), ch.shape[1], 3)) * t[0] ** 2
    for k in range(1, ch.shape[1]):
        ch[:, k], _ = S.project(ch[:, k], 0.0012 + 0.0006 * k)
    strands = list(ch) + list(GS)
    uvs = np.concatenate([UV, GUV])
    return curves_obj('ARJ_Hair', strands, rng.uniform(0.000035, 0.000055, len(strands)), 0.00001, coll,
                      hair_mat('ARJ_HairMat', 0.99, 0.12, 0.36, 0.5, 0.15), S.ob, uvs)


# ------------------------------------------------------------------ garments
def cotton_mat(name, col, plaid=None, rough=0.92):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, Lk = m.node_tree.nodes, m.node_tree.links; p = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    w1 = N.new('ShaderNodeTexWave'); w1.inputs['Scale'].default_value = 1400; w1.bands_direction = 'X'
    w2 = N.new('ShaderNodeTexWave'); w2.inputs['Scale'].default_value = 1400; w2.bands_direction = 'Z'
    for w in (w1, w2):
        Lk.new(tc.outputs['Object'], w.inputs['Vector'])
    fz = N.new('ShaderNodeTexNoise'); fz.inputs['Scale'].default_value = 90; fz.inputs['Detail'].default_value = 6
    Lk.new(tc.outputs['Object'], fz.inputs['Vector'])
    add = N.new('ShaderNodeMath'); add.operation = 'ADD'
    Lk.new(w1.outputs['Fac'], add.inputs[0]); Lk.new(w2.outputs['Fac'], add.inputs[1])
    b = N.new('ShaderNodeBump'); b.inputs['Strength'].default_value = 0.25; b.inputs['Distance'].default_value = 0.0003
    Lk.new(add.outputs[0], b.inputs['Height']); Lk.new(b.outputs['Normal'], p.inputs['Normal'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    c = np.array(hex2lin(col))
    mix.inputs['A'].default_value = (*c, 1); mix.inputs['B'].default_value = (*(c * 0.78), 1)
    Lk.new(fz.outputs['Fac'], mix.inputs['Factor'])
    out = mix.outputs['Result']
    if plaid:
        ch = N.new('ShaderNodeTexChecker'); ch.inputs['Scale'].default_value = 28
        ch.inputs['Color1'].default_value = (*hex2lin(plaid), 1); ch.inputs['Color2'].default_value = (*c, 1)
        Lk.new(tc.outputs['Object'], ch.inputs['Vector'])
        m2 = N.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.blend_type = 'MULTIPLY'; m2.inputs['Factor'].default_value = 0.6
        Lk.new(out, m2.inputs['A']); Lk.new(ch.outputs['Color'], m2.inputs['B']); out = m2.outputs['Result']
    Lk.new(out, p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = rough
    p.inputs['Sheen Weight'].default_value = 0.7; p.inputs['Sheen Roughness'].default_value = 0.35
    p.inputs['Sheen Tint'].default_value = (0.8, 0.85, 0.9, 1)
    p.inputs['Specular IOR Level'].default_value = 0.25
    return m


def make_garment(body, name, vmask_fn, offset, mat, fold_amp=0.004, fold_scale=(14, 14, 6), rng=None):
    import bmesh
    ob = body.copy(); ob.data = body.data.copy(); ob.name = name; ob.data.name = name
    body.users_collection[0].objects.link(ob)
    if ob.data.shape_keys:
        ob.shape_key_clear()
    for md in list(ob.modifiers):
        if md.type != 'ARMATURE':
            ob.modifiers.remove(md)
    ob.data.materials.clear(); ob.data.materials.append(mat)
    P = verts(ob); keep = vmask_fn(P)
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    dead = [f for f in bm.faces if not all(keep[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True, smooth=1.0)
    for _ in range(12):                      # straighten the cut hems / collar
        bnd = [v for v in bm.verts if v.is_boundary]
        new = {}
        for v in bnd:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2:
                new[v] = (nb[0].co + nb[1].co) / 2
        for v, co in new.items():
            v.co = v.co * 0.4 + co * 0.6
    bm.normal_update()
    for v in bm.verts:
        p = np.array(v.co[:])
        f = vnoise(p[None] * np.array(fold_scale) / 10, 10, 3)[0] * 0.7 + vnoise(p[None], 45, 4)[0] * 0.3
        v.co += v.normal * (offset + fold_amp * (0.5 + 0.5 * f))
    bm.to_mesh(ob.data); bm.free()
    ob.data.shade_smooth()
    so = ob.modifiers.new('Solidify', 'SOLIDIFY'); so.thickness = 0.0018; so.offset = 1
    sd = ob.modifiers.new('Subdivision', 'SUBSURF'); sd.levels = 1; sd.render_levels = 2
    return ob


def tee_mask(info):
    j = info['joints']
    shL, elL = j['joint-l-shoulder'], j['joint-l-elbow']
    shR, elR = j['joint-r-shoulder'], j['joint-r-elbow']
    nk = j['joint-neck']

    def seg(P, a, b, r, frac):
        b2 = a + (b - a) * frac; ab = b2 - a
        t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
        return np.linalg.norm(P - (a + t[:, None] * ab), axis=1) < r
    def fn(P):
        torso = (np.abs(P[:, 0]) < 0.21) & (P[:, 2] > 0.03) & (P[:, 2] < nk[2] - 0.01)
        neck = (P[:, 2] > nk[2] - 0.055) & (np.hypot(P[:, 0], (P[:, 1] - nk[1]) * 1.15) < 0.072)
        sleeves = seg(P, shL, elL, 0.075, 0.5) | seg(P, shR, elR, 0.075, 0.5)
        return (torso | sleeves) & ~neck
    return fn


def pants_mask(info):
    j = info['joints']
    return lambda P: (P[:, 2] < j['joint-pelvis'][2] + 0.06) & (P[:, 2] > j['joint-l-ankle'][2] + 0.035) & (np.abs(P[:, 0]) < 0.3)


# ------------------------------------------------------------------ posing + cloth
def aim_bone(rig, name, direction):
    """Rotate a pose bone so its axis points along `direction` (armature space)."""
    from mathutils import Matrix
    bpy.context.view_layer.update()
    pb = rig.pose.bones[name]
    cur = (pb.tail - pb.head).normalized()
    R = cur.rotation_difference(Vector(direction).normalized()).to_matrix().to_4x4()
    M = pb.matrix.copy(); head = M.translation.copy()
    M.translation = (0, 0, 0)
    M = R @ M; M.translation = head
    pb.matrix = M
    bpy.context.view_layer.update()


def relax_arms(rig):
    for s, sx in (('L', 1), ('R', -1)):
        aim_bone(rig, 'upperarm01.' + s, (0.06 * sx, 0.05, -1.0))
        aim_bone(rig, 'upperarm02.' + s, (0.06 * sx, 0.05, -1.0))
        aim_bone(rig, 'lowerarm01.' + s, (-0.02 * sx, -0.18, -1.0))
        aim_bone(rig, 'lowerarm02.' + s, (-0.02 * sx, -0.18, -1.0))


def add_cloth(garment, body, pin_fn, frames=(1, 60), quality=6):
    col = body.modifiers.get('Collision') or body.modifiers.new('Collision', 'COLLISION')
    body.collision.thickness_outer = 0.004; body.collision.cloth_friction = 8
    P = verts(garment)
    w = np.clip(pin_fn(P), 0, 1)
    vg = garment.vertex_groups.new(name='pin')
    for i, ww in enumerate(w):
        if ww > 0.01:
            vg.add([i], float(ww), 'REPLACE')
    cl = garment.modifiers.new('Cloth', 'CLOTH')
    # order: Armature -> Cloth -> Solidify -> Subdivision
    while garment.modifiers.find('Cloth') > 1:
        bpy.ops.object.modifier_move_up({'object': garment}, modifier='Cloth') if False else garment.modifiers.move(garment.modifiers.find('Cloth'), garment.modifiers.find('Cloth') - 1)
    s = cl.settings
    s.quality = quality; s.mass = 0.15; s.air_damping = 1.0
    s.tension_stiffness = 12; s.compression_stiffness = 12; s.shear_stiffness = 6; s.bending_stiffness = 0.4
    s.vertex_group_mass = 'pin'; s.pin_stiffness = 1.0
    cl.collision_settings.distance_min = 0.003; cl.collision_settings.use_self_collision = False
    cl.point_cache.frame_start, cl.point_cache.frame_end = frames
    return cl


def simulate(scene, f0, f1):
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
