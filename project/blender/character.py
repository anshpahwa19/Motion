"""ARJUN — full character assembly: meshes, armature, skin weights, controls.

build_arjun(coll) -> dict with 'rig' (armature object), 'ctrl' (IK empties),
and mesh objects. The rig is built standing (body space, see char_body); place
it in a scene by transforming the armature object.

Rig controls (pose bones unless noted):
  head / neck / chest / spine      : FK rotation (quaternion)
  eye.L / eye.R                    : gaze  (X = up/down, Z = left/right)
  lid_up.* / lid_lo.*              : blink (X rot; upper closes with -X)
  brow.*                           : brow tilt/raise (Y rot + location)
  f_<finger>.0n.*                  : curl  (X rot, + = flex)
  IK_hand.R/L (empty)              : wrist location + hand orientation
  Pole_elbow.R/L (empty)           : elbow direction
"""
import bpy, os
import numpy as np
from mathutils import Vector, Matrix
import bl_util as U
import char_head as H
import char_face as CF
import char_hair as CH
import char_body as B
from sdf import mesh_sdf

E0 = B.HEAD_ORIGIN
HS = 1.06          # stylised head scale


def scale_data(ob, s=HS):
    """Bake a uniform scale (about the object origin) into mesh/curve data
    and scale the object's local offset (head-local -> scaled head-local)."""
    d = ob.data
    if ob.type == 'MESH':
        a = np.empty(len(d.vertices) * 3, np.float32); d.vertices.foreach_get('co', a)
        d.vertices.foreach_set('co', a * s); d.update()
    elif ob.type == 'CURVES':
        a = np.empty(len(d.points) * 3, np.float32); d.position_data.foreach_get('vector', a)
        d.position_data.foreach_set('vector', a * s)
        r = d.attributes['radius']; b = np.empty(len(d.points), np.float32)
        r.data.foreach_get('value', b); r.data.foreach_set('value', b * s)
    ob.location = ob.location * s
    for ch in ob.children:
        scale_data(ch, s)
        ch.location = ch.location / s * s


def tee_material(color='#3d5862'):
    m = U.new_mat('ARJ_Tee')
    N, L = U.nodes(m); p = U.principled(m)
    col = U.hex2lin(color)
    tc = N.new('ShaderNodeTexCoord')
    wave = N.new('ShaderNodeTexWave'); wave.inputs['Scale'].default_value = 900
    wave.inputs['Distortion'].default_value = 2; wave.bands_direction = 'DIAGONAL'
    L.new(tc.outputs['Object'], wave.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (*col, 1)
    mix.inputs['B'].default_value = (*(np.array(col) * 0.72), 1)
    L.new(nz.outputs['Fac'], mix.inputs['Factor'])
    L.new(mix.outputs['Result'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.85
    p.inputs['Sheen Weight'].default_value = 0.6
    p.inputs['Sheen Roughness'].default_value = 0.4
    p.inputs['Sheen Tint'].default_value = (0.7, 0.8, 0.85, 1)
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.15
    bump.inputs['Distance'].default_value = 0.0005
    L.new(wave.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], p.inputs['Normal'])
    return m


def body_skin_maps(V):
    col = np.tile(np.array(CF.SKIN), (len(V), 1))
    # slightly darker knuckles / redder palms & fingertips
    return np.c_[col, np.ones(len(V))]


# ----------------------------------------------------------------- rig
def bone_specs():
    """name -> (head, tail, parent, z_axis_hint)"""
    fwd = np.array([0, -1.0, 0]); up = np.array([0, 0, 1.0])
    S = {}
    S['pelvis'] = (B.J['pelvis'], B.J['spine'], None, fwd)
    S['spine'] = (B.J['spine'], B.J['chest'], 'pelvis', fwd)
    S['chest'] = (B.J['chest'], B.J['neck'], 'spine', fwd)
    S['neck'] = (B.J['neck'], B.J['head'], 'chest', fwd)
    S['head'] = (B.J['head'], B.J['head_end'], 'neck', fwd)
    S['breath'] = (np.array([0, 0.09, 0.36]), np.array([0, -0.02, 0.36]), 'spine', up)
    for s in 'LR':
        S['upper_arm.' + s] = (B.J['shoulder.' + s], B.J['elbow.' + s], 'chest', fwd)
        S['forearm.' + s] = (B.J['elbow.' + s], B.J['wrist.' + s], 'upper_arm.' + s, fwd)
        R, o = B.hand_frame(s)
        palm_n = R[:, 0]
        to_b = lambda q: o + R @ np.asarray(q)
        S['hand.' + s] = (o, to_b((0, -0.010, -0.090)), 'forearm.' + s, palm_n)
        for name, (pts, r) in B.finger_joints().items():
            par = 'hand.' + s
            for i in range(3):
                bn = f'f_{name}.{i + 1:02d}.{s}'
                S[bn] = (to_b(pts[i]), to_b(pts[i + 1]), par, palm_n)
                par = bn
        E = E0 + HS * (H.EYE_L if s == 'L' else H.EYE_RT)
        for bn in ('eye', 'lid_up', 'lid_lo'):
            S[f'{bn}.{s}'] = (E, E + np.array([0, -0.02, 0]), 'head', up)
        sx = 1 if s == 'L' else -1
        piv = E0 + HS * np.array([0.056 * sx, -0.066, 0.020])
        S['brow.' + s] = (piv, piv + np.array([0, -0.015, 0]), 'head', up)
        S['thigh.' + s] = (B.J['hip.' + s], B.J['knee.' + s], 'pelvis', fwd)
        S['shin.' + s] = (B.J['knee.' + s], B.J['ankle.' + s], 'thigh.' + s, fwd)
        S['foot.' + s] = (B.J['ankle.' + s], B.J['toe.' + s], 'shin.' + s, up)
    return S


def build_rig(coll):
    arm = bpy.data.armatures.new('ARJ_RigData')
    rig = bpy.data.objects.new('ARJ_Rig', arm)
    U.link(rig, coll)
    arm.display_type = 'STICK'
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    specs = bone_specs()
    for name, (h, t, par, z) in specs.items():
        eb = arm.edit_bones.new(name)
        eb.head = Vector(h); eb.tail = Vector(t)
        eb.align_roll(Vector(z))
        eb.use_deform = not (name.startswith(('eye', 'lid', 'brow')))
    for name, (h, t, par, z) in specs.items():
        if par:
            eb = arm.edit_bones[name]; eb.parent = arm.edit_bones[par]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return rig


def bone_parent(ob, rig, bone):
    bpy.context.view_layer.update()
    mw = ob.matrix_world.copy()
    ob.parent = rig; ob.parent_type = 'BONE'; ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = mw


def add_armature_mod(ob, rig):
    m = ob.modifiers.new('Armature', 'ARMATURE'); m.object = rig
    ob.parent = rig


# ----------------------------------------------------------------- build
def mouth_shape_keys(head):
    """Analytic facial shapes on the (scaled) head mesh: smile, frown, jaw_open, sneer-free."""
    me = head.data
    V = U.mesh_verts(head) / HS                          # head-local
    if not me.shape_keys:
        head.shape_key_add(name='Basis', from_mix=False)
    def g(c, r):
        q = (V - np.array(c)) / np.array(r); return np.exp(-np.einsum('ij,ij->i', q, q))
    M = V.copy(); M[:, 0] = np.abs(M[:, 0])
    sx = np.sign(V[:, 0])
    def gm(c, r):
        q = (M - np.array(c)) / np.array(r); return np.exp(-np.einsum('ij,ij->i', q, q))
    front = np.clip((-V[:, 1] - 0.03) / 0.03, 0, 1)
    shapes = {}
    w = gm((0.022, -0.078, -0.061), (0.011, 0.02, 0.009)) * front
    ck = gm((0.035, -0.062, -0.035), (0.016, 0.03, 0.014)) * front
    shapes['smile'] = np.c_[sx * 0.0022 * w, 0.0018 * w + 0.0008 * ck, 0.0030 * w + 0.0014 * ck]
    shapes['frown'] = np.c_[sx * -0.0008 * w, 0.0004 * w, -0.0026 * w]
    jaw = np.clip((-0.0615 - V[:, 2]) / 0.006, 0, 1) * np.clip((0.03 - V[:, 1]) / 0.04, 0, 1) * np.clip((V[:, 2] + 0.16) / 0.04, 0, 1)
    ang = np.radians(7) * jaw
    piv = np.array([0, 0.012, -0.035])
    q = V - piv
    ny = q[:, 1] * np.cos(ang) + q[:, 2] * np.sin(ang)
    nz = -q[:, 1] * np.sin(ang) + q[:, 2] * np.cos(ang)
    shapes['jaw_open'] = np.c_[np.zeros(len(V)), ny + piv[1] - V[:, 1], nz + piv[2] - V[:, 2]]
    lipup = g((0, -0.085, -0.057), (0.016, 0.015, 0.004)) * front
    shapes['lips_part'] = np.c_[np.zeros(len(V)), np.zeros(len(V)), 0.0012 * lipup]
    for name, d in shapes.items():
        sk = head.shape_key_add(name=name, from_mix=False)
        sk.data.foreach_set('co', ((V + d) * HS).astype(np.float32).ravel())
        sk.value = 0.0


def build_lower_body(coll, rig, objs, skin, lod=1.0, pants_color='#2f3540', feet_mat=None):
    v, f = mesh_sdf(B.pants_sdf, *B.PANTS_BBOX, 0.0024 / lod)
    pm = U.new_mat(f'{PREFIX}_Pants'); p = U.principled(pm)
    N, L = U.nodes(pm)
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 300
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    c = np.array(U.hex2lin(pants_color)); mx.inputs['A'].default_value = (*c, 1); mx.inputs['B'].default_value = (*(c * 0.75), 1)
    L.new(nz.outputs['Fac'], mx.inputs['Factor']); L.new(mx.outputs['Result'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.85; p.inputs['Sheen Weight'].default_value = 0.4
    pants = U.mesh_obj(f'{PREFIX}_Pants', v, f, coll, mat=pm)
    U.smooth_mesh(pants, 1, 0.4)
    V = U.mesh_verts(pants)
    names, W = B.soft_weights(B.leg_parts(V), 0.016)
    for i, n in enumerate(names):
        U.vgroup_weights(pants, n, W[:, i])
    add_armature_mod(pants, rig)
    v, f = mesh_sdf(B.feet_sdf, *B.FEET_BBOX, 0.0022 / lod)
    feet = U.mesh_obj(f'{PREFIX}_Feet', v, f, coll, mat=feet_mat or skin)
    V = U.mesh_verts(feet)
    names, W = B.soft_weights(B.feet_parts(V), 0.012)
    for i, n in enumerate(names):
        U.vgroup_weights(feet, n, W[:, i])
    if feet_mat is None:
        col = body_skin_maps(V); U.set_color_attr(feet, 'skin_col', col); U.set_float_attr(feet, 'stubble', np.zeros(len(V)))
    add_armature_mod(feet, rig)
    objs['pants'] = pants; objs['feet'] = feet


PREFIX = 'ARJ'


def build_moustache(coll, head_parent_fn, melanin=0.9, random=0.3, seed=31):
    """Groomed moustache strands (head-local, then scaled + bone-parented by caller)."""
    import char_head as H
    rng = np.random.default_rng(seed)
    fn = lambda P: H.head_sdf(P, socket=False, neck=False)
    n = 2600
    x = rng.uniform(-0.025, 0.025, n); z = -0.0535 + rng.normal(0, 0.0028, n) + 0.006 * (np.abs(x) / 0.025) ** 2
    P = np.c_[x, np.full(n, -0.12), z]
    for _ in range(40):
        d = fn(P); P[:, 1] += np.maximum(d, 0) * 0.9
    from char_face import surface_project, hair_curves_obj, hair_material
    P = surface_project(fn, P, 0.0002)
    strands = []
    for i in range(n):
        dirw = np.array([np.sign(x[i]) * 0.35 * abs(x[i]) / 0.025, -0.25, -1.0]) + rng.normal(0, 0.15, 3)
        L = rng.uniform(0.004, 0.0085)
        pts = [P[i]]; p = P[i].copy()
        for k in range(4):
            from sdf import sdf_normal
            nrm = sdf_normal(fn, p[None])[0]
            t = dirw - nrm * (dirw @ nrm); t /= np.linalg.norm(t)
            p = p + t * L / 4 + nrm * 0.0004 * (k == 0); pts.append(p.copy())
        strands.append(np.array(pts))
    m = hair_material(f'{PREFIX}_MoustacheMat', melanin, 0.15, 0.4)
    m.node_tree.nodes['Principled Hair BSDF'].inputs['Random Color'].default_value = random
    return hair_curves_obj(f'{PREFIX}_Moustache', strands, 0.00009, 0.00002, coll, m)


def build_glasses(coll):
    """Thin metal reading glasses in head-local space."""
    import char_head as H
    metal = U.simple_mat(f'{PREFIX}_GlassesMetal', U.hex2lin('#3a3530'), rough=0.3, metal=0.9)
    lens = U.new_mat(f'{PREFIX}_GlassesLens'); nt = lens.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.02
    mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.08
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs[0])
    objs = []
    yfr = H.EYE_L[1] - H.EYE_R if False else H.EYE_L[1] - 0.030
    for sx in (1, -1):
        cx = H.EYE_L[0] * sx; cz = -0.002
        cu = bpy.data.curves.new(f'{PREFIX}_Rim', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0009
        sp = cu.splines.new('POLY'); n = 40; sp.points.add(n - 1)
        for i in range(n):
            a = 2 * np.pi * i / n
            sp.points[i].co = (cx + 0.0215 * np.cos(a), yfr - 0.002 * np.cos(a) ** 2, cz + 0.0150 * np.sin(a) - 0.002 * (np.sin(a) < 0), 1)
        sp.use_cyclic_u = True
        rim = bpy.data.objects.new(f'{PREFIX}_GlassRim', cu); coll.objects.link(rim); cu.materials.append(metal)
        V = [(cx + 0.0205 * np.cos(2 * np.pi * i / 32), yfr, cz + 0.0142 * np.sin(2 * np.pi * i / 32)) for i in range(32)]
        ln = U.mesh_obj(f'{PREFIX}_GlassLens', V + [(cx, yfr - 0.0015, cz)], [[i, (i + 1) % 32, 32] for i in range(32)], coll, mat=lens)
        objs += [rim, ln]
        # temple arm
        cu2 = bpy.data.curves.new(f'{PREFIX}_Temple', 'CURVE'); cu2.dimensions = '3D'; cu2.bevel_depth = 0.0010
        sp2 = cu2.splines.new('POLY'); sp2.points.add(2)
        for i, co in enumerate(((cx + 0.0215 * sx, yfr, cz + 0.004), (0.071 * sx, -0.02, 0.006), (0.077 * sx, 0.03, -0.012))):
            sp2.points[i].co = (*co, 1)
        tm = bpy.data.objects.new(f'{PREFIX}_GlassTemple', cu2); coll.objects.link(tm); cu2.materials.append(metal); objs.append(tm)
    cu3 = bpy.data.curves.new(f'{PREFIX}_Bridge', 'CURVE'); cu3.dimensions = '3D'; cu3.bevel_depth = 0.0009
    sp3 = cu3.splines.new('BEZIER'); sp3.bezier_points.add(1)
    for bp, co in zip(sp3.bezier_points, ((-H.EYE_L[0] + 0.0215, yfr, 0.003), (H.EYE_L[0] - 0.0215, yfr, 0.003))):
        bp.co = co; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    sp3.bezier_points[0].handle_right = (0, yfr - 0.004, 0.008); sp3.bezier_points[1].handle_left = (0, yfr - 0.004, 0.008)
    br = bpy.data.objects.new(f'{PREFIX}_GlassBridge', cu3); coll.objects.link(br); cu3.materials.append(metal); objs.append(br)
    return objs


def build_arjun(coll, hair=True, lod=1.0, legs=False, tee_color='#3d5862', pants_color='#2f3540',
                brow_melanin=0.95, moustache=None, glasses=False, prefix='ARJ'):
    global PREFIX
    PREFIX = prefix
    objs = {}
    rig = build_rig(coll)
    objs['rig'] = rig
    # --- head (skinned head/neck/chest)
    head = CF.build_head(coll, voxel=0.0013 / lod)
    V = U.mesh_verts(head)
    z = V[:, 2]
    wh = np.clip((z + 0.135) / 0.06, 0, 1); wh = wh * wh * (3 - 2 * wh)
    wn = (1 - wh) * np.clip((z + 0.20) / 0.05, 0, 1)
    wc = 1 - wh - wn
    scale_data(head); head.location = E0
    mouth_shape_keys(head)
    U.vgroup_weights(head, 'head', wh); U.vgroup_weights(head, 'neck', wn); U.vgroup_weights(head, 'chest', wc)
    add_armature_mod(head, rig)
    objs['head'] = head
    skin = head.data.materials[0]
    # --- eyes, lids, lashes, brows (rigid, bone-parented)
    em, cm = CF.eye_materials()
    lashm = CF.hair_material('ARJ_Lash', 0.98, 0.2, 0.4)
    browm = CF.hair_material('ARJ_BrowHair', brow_melanin, 0.3, 0.35)
    for s in 'LR':
        eye = CF.build_eye(coll, s, em, cm)
        scale_data(eye)
        eye.location = Vector(E0) + eye.location
        bone_parent(eye, rig, 'eye.' + s)
        for up in (True, False):
            lid, th, pe, R = CF.build_lid(coll, s, up, skin)
            CF.lashes(lid, th, pe, R, up, coll, lashm, (7 if up else 9) + (s == 'R'))
            scale_data(lid)
            lid.location = Vector(E0) + lid.location
            bone_parent(lid, rig, ('lid_up.' if up else 'lid_lo.') + s)
        brow = CF.build_brow(coll, s, browm, 11 if s == 'L' else 12)
        scale_data(brow)
        brow.location = Vector(E0)
        bone_parent(brow, rig, 'brow.' + s)
    if hair:
        cap, hr = CH.build_hair(coll, n_children=int(22000 * lod))
        for o in (cap, hr):
            scale_data(o)
            o.location = Vector(E0)
            bone_parent(o, rig, 'head')
        objs['hair'] = hr
    # --- body skin (arms + hands + upper chest)
    v, f = mesh_sdf(B.skin_sdf, *B.SKIN_BBOX, 0.0021 / lod)
    body = U.mesh_obj('ARJ_Body', v, f, coll, mat=skin)
    U.smooth_mesh(body, 2, 0.4)
    V = U.mesh_verts(body)
    names, W = B.soft_weights(B.body_parts(V), 0.0028)
    # arm/torso joints blend wider than fingers
    for i, n in enumerate(names):
        U.vgroup_weights(body, n, W[:, i])
    col = body_skin_maps(V)
    U.set_color_attr(body, 'skin_col', col)
    U.set_float_attr(body, 'stubble', np.zeros(len(V)))
    add_armature_mod(body, rig)
    objs['body'] = body
    # --- T-shirt
    v, f = mesh_sdf(B.tee_sdf, *B.TEE_BBOX, 0.0017 / lod)
    tee = U.mesh_obj('ARJ_Tee', v, f, coll, mat=tee_material(tee_color))
    U.smooth_mesh(tee, 1, 0.4)
    V = U.mesh_verts(tee)
    names, W = B.soft_weights(B.tee_parts(V), 0.012)
    br = np.clip((0.0 - V[:, 1]) / 0.06, 0, 1) * np.exp(-((V[:, 2] - 0.33) / 0.11) ** 2) * np.clip(1 - np.abs(V[:, 0]) / 0.17, 0, 1)
    W = W * (1 - 0.6 * br[:, None])
    for i, n in enumerate(names):
        U.vgroup_weights(tee, n, W[:, i])
    U.vgroup_weights(tee, 'breath', 0.6 * br)
    add_armature_mod(tee, rig)
    objs['tee'] = tee
    if legs:
        build_lower_body(coll, rig, objs, skin, lod, pants_color)
    if moustache:
        mo = build_moustache(coll, None, **moustache)
        scale_data(mo); mo.location = Vector(E0) + mo.location
        bone_parent(mo, rig, 'head'); objs['moustache'] = mo
    if glasses:
        for g in build_glasses(coll):
            if g.type == 'MESH':
                scale_data(g)
            else:
                g.scale = (HS, HS, HS); g.location = g.location * HS
            g.location = Vector(E0) + g.location
            bone_parent(g, rig, 'head')
    # --- IK controls
    ctrl = {}
    for s in 'LR':
        pb = rig.pose.bones['hand.' + s]
        ik = bpy.data.objects.new('IK_hand.' + s, None); U.link(ik, coll)
        ik.empty_display_type = 'CUBE'; ik.empty_display_size = 0.03
        ik.parent = rig
        ik.matrix_world = rig.matrix_world @ pb.bone.matrix_local
        pole = bpy.data.objects.new('Pole_elbow.' + s, None); U.link(pole, coll)
        pole.empty_display_size = 0.03; pole.parent = rig
        pole.location = Vector(B.J['elbow.' + s]) + Vector((0.12 * (1 if s == 'L' else -1), 0.25, 0))
        c = rig.pose.bones['forearm.' + s].constraints.new('IK')
        c.target = ik; c.pole_target = pole; c.chain_count = 2
        c.pole_angle = np.radians(-90)
        c2 = pb.constraints.new('COPY_ROTATION'); c2.target = ik
        ctrl['IK_hand.' + s] = ik; ctrl['Pole_elbow.' + s] = pole
    objs['ctrl'] = ctrl
    return objs
