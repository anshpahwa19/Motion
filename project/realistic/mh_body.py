"""ARJUN (realistic) — body builder on the CC0 MakeHuman / MPFB2 base mesh.

Anatomy comes from MakeHuman's measured base mesh + morph targets (CC0,
https://github.com/makehumancommunity/mpfb2 -> src/mpfb/data). We blend
macro targets (adult male, ~28, average build, mixed ethnic base tuned to a
South Asian face), add feature tweaks and natural asymmetry, then create:
  * FACS-style expression shape keys (eye closure, brow inner-up, mouth ...)
  * the MPFB 'default' skeleton (163 bones) with its painted skin weights.

Units: Blender metres, Z up, character faces -Y (MPFB convention).
"""
import os, gzip, json
import numpy as np
import bpy
from mathutils import Vector

MH = os.environ.get('MH_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            '..', '..', 'third_party', 'mpfb2_data'))


def to_bl(P):
    P = np.asarray(P, np.float64)
    return np.c_[P[:, 0], -P[:, 2], P[:, 1]] * 0.1


def load_obj(path):
    V, VT, F, FT, G = [], [], [], [], []
    cur = None
    with open(path) as fh:
        for ln in fh:
            if ln.startswith('v '):
                V.append([float(x) for x in ln.split()[1:4]])
            elif ln.startswith('vt '):
                VT.append([float(x) for x in ln.split()[1:3]])
            elif ln.startswith('g '):
                cur = ln[2:].strip()
            elif ln.startswith('f '):
                vi, ti = [], []
                for p in ln.split()[1:]:
                    a = p.split('/')
                    vi.append(int(a[0]) - 1); ti.append(int(a[1]) - 1 if len(a) > 1 and a[1] else -1)
                F.append(vi); FT.append(ti); G.append(cur)
    return np.array(V), np.array(VT), F, FT, G


_tcache = {}


def target(rel):
    p = os.path.join(MH, 'targets', rel)
    if not p.endswith('.gz'):
        p += '.target.gz'
    if p in _tcache:
        return _tcache[p]
    if not os.path.exists(p):
        print('missing target', rel); return None
    rows = []
    with gzip.open(p, 'rt') as fh:
        for ln in fh:
            s = ln.split()
            if len(s) == 4 and not ln.startswith('#'):
                rows.append(s)
    if not rows:
        print('empty target', rel); _tcache[p] = None; return None
    a = np.array(rows, float)
    _tcache[p] = (a[:, 0].astype(int), a[:, 1:4])
    return _tcache[p]


def apply_targets(V, items):
    V = V.copy()
    for rel, w in items:
        if not w:
            continue
        t = target(rel)
        if t is None:
            continue
        idx, d = t
        V[idx] += d * w
    return V


ETHNIC = dict(caucasian=0.56, african=0.36, asian=0.08)   # tuned for a South Asian face

FEATURES = [
    ('nose/nose-width1-incr', 0.25), ('nose/nose-flaring-incr', 0.35), ('nose/nose-point-width-incr', 0.3),
    ('nose/nose-hump-incr', 0.15), ('nose/nose-volume-incr', 0.12), ('nose/nose-scale-depth-incr', 0.10),
    ('mouth/mouth-lowerlip-volume-incr', 0.45), ('mouth/mouth-upperlip-volume-incr', 0.3),
    ('mouth/mouth-angles-down', 0.12), ('mouth/mouth-scale-horiz-incr', 0.08),
    ('eyes/l-eye-bag-incr', 0.35), ('eyes/r-eye-bag-incr', 0.38),             # tired under-eyes
    ('eyes/l-eye-eyefold-down', 0.20), ('eyes/r-eye-eyefold-down', 0.22),
    ('eyebrows/eyebrows-trans-down', 0.25), ('eyebrows/eyebrows-angle-down', 0.10),
    ('chin/chin-width-incr', 0.15), ('chin/chin-prominent-incr', 0.10),
    ('cheek/l-cheek-bones-incr', 0.15), ('cheek/r-cheek-bones-incr', 0.12),
    ('head/head-square', 0.15), ('neck/neck-scale-depth-incr', 0.10),
]
ASYM = [('asym/asym-brown-1-l', 0.25), ('asym/asym-cheek-1-r', 0.2), ('asym/asym-ear-1-l', 0.3),
        ('asym/asym-eye-1-r', 0.18), ('asym/asym-mouth-1-l', 0.15), ('asym/asym-nose-1-r', 0.15),
        ('asym/asym-chin-1-l', 0.12), ('asym/asym-jaw-1-r', 0.12)]

EXPR_UNITS = ['eye-left-closure', 'eye-right-closure', 'eye-left-slit', 'eye-right-slit',
              'eye-left-opened-up', 'eye-right-opened-up',
              'eyebrows-left-inner-up', 'eyebrows-right-inner-up', 'eyebrows-left-down', 'eyebrows-right-down',
              'eyebrows-left-up', 'eyebrows-right-up', 'eyebrows-left-extern-up', 'eyebrows-right-extern-up',
              'mouth-depression', 'mouth-compression', 'mouth-open', 'mouth-parling', 'mouth-pursing',
              'mouth-corner-puller', 'mouth-depression-retraction', 'mouth-elevation', 'neck-platysma',
              'nose-left-dilatation', 'nose-right-dilatation', 'nose-compression']


def macro_items():
    items = [('macrodetails/universal-male-young-averagemuscle-averageweight', 1.0)]
    for eth, w in ETHNIC.items():
        items.append((f'macrodetails/{eth}-male-young', w))
    return items


def build_body(coll, name='ARJ_Body'):
    V0, VT, F, FT, G = load_obj(os.path.join(MH, '3dobjs', 'base.obj'))
    Vt = apply_targets(V0, macro_items() + FEATURES + ASYM)
    body_f = [i for i, g in enumerate(G) if g == 'body']
    used = np.unique(np.concatenate([F[i] for i in body_f]))
    remap = -np.ones(len(V0), int); remap[used] = np.arange(len(used))
    Vb = to_bl(Vt[used])
    me = bpy.data.meshes.new(name)
    faces = [remap[F[i]] for i in body_f]
    me.from_pydata(Vb.tolist(), [], [list(f) for f in faces])
    me.update()
    uv = me.uv_layers.new(name='UVMap')
    uvs = []
    for i in body_f:
        uvs.extend(VT[FT[i]].tolist())
    uv.data.foreach_set('uv', np.array(uvs, np.float32).ravel())
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    # expression shape keys (ethnic-weighted blend of the unit targets)
    ob.shape_key_add(name='Basis', from_mix=False)
    for unit in EXPR_UNITS:
        d = np.zeros_like(V0)
        for eth, w in ETHNIC.items():
            t = target(f'expression/units/{eth}/{unit}')
            if t is None:
                continue
            d[t[0]] += t[1] * w
        sk = ob.shape_key_add(name=unit, from_mix=False)
        sk.value = 0.0
        co = to_bl(Vt[used] + d[used])
        sk.data.foreach_set('co', co.astype(np.float32).ravel())
    # helper geometry we need later (all with targets applied)
    helpers = {}
    for hname in ('helper-l-eye', 'helper-r-eye', 'helper-hair', 'helper-upper-teeth', 'helper-lower-teeth',
                  'helper-tongue', 'helper-tights'):
        fi = [i for i, g in enumerate(G) if g == hname]
        if fi:
            vi = np.unique(np.concatenate([F[i] for i in fi]))
            hv = to_bl(Vt[vi])
            loc = {v: k for k, v in enumerate(vi)}
            helpers[hname] = (hv, [[loc[v] for v in F[i]] for i in fi])
    joints = {}
    for i, g in enumerate(G):
        if g and g.startswith('joint-'):
            joints.setdefault(g, set()).update(F[i])
    joints = {k: to_bl(Vt[sorted(v)]).mean(0) for k, v in joints.items()}
    return ob, dict(Vt=Vt, used=used, remap=remap, helpers=helpers, joints=joints)


def build_rig(coll, body, info, rigname='default'):
    rj = json.load(open(os.path.join(MH, 'rigs', 'standard', f'rig.{rigname}.json')))
    wj = json.load(open(os.path.join(MH, 'rigs', 'standard', f'weights.{rigname}.json')))['weights']
    Vt, joints = info['Vt'], info['joints']

    def pos(spec):
        s = spec['strategy']
        if s == 'CUBE':
            return Vector(joints[spec['cube_name']])
        if s == 'VERTEX':
            return Vector(to_bl(Vt[[spec['vertex_index']]])[0])
        return Vector(to_bl(Vt[spec['vertex_indices']]).mean(0))
    arm = bpy.data.armatures.new('ARJ_RigData'); rig = bpy.data.objects.new('ARJ_Rig', arm)
    coll.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bn, spec in rj.items():
        eb = arm.edit_bones.new(bn); eb.head = pos(spec['head']); eb.tail = pos(spec['tail'])
        if (eb.tail - eb.head).length < 1e-4:
            eb.tail = eb.head + Vector((0, 0, 0.01))
        eb.roll = spec.get('roll', 0.0)
    for bn, spec in rj.items():
        if spec.get('parent'):
            arm.edit_bones[bn].parent = arm.edit_bones[spec['parent']]
            arm.edit_bones[bn].use_connect = bool(spec.get('use_connect', False))
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    remap = info['remap']
    for bn, lst in wj.items():
        if not lst:
            continue
        a = np.array(lst)
        vi = remap[a[:, 0].astype(int)]; w = a[:, 1]
        ok = vi >= 0
        vg = body.vertex_groups.new(name=bn)
        for v, ww in zip(vi[ok], w[ok]):
            vg.add([int(v)], float(ww), 'REPLACE')
    m = body.modifiers.new('Armature', 'ARMATURE'); m.object = rig
    body.parent = rig
    return rig
