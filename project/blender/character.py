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


def tee_material():
    m = U.new_mat('ARJ_Tee')
    N, L = U.nodes(m); p = U.principled(m)
    col = U.hex2lin('#3d5862')
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
def build_arjun(coll, hair=True, lod=1.0):
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
    U.vgroup_weights(head, 'head', wh); U.vgroup_weights(head, 'neck', wn); U.vgroup_weights(head, 'chest', wc)
    add_armature_mod(head, rig)
    objs['head'] = head
    skin = head.data.materials[0]
    # --- eyes, lids, lashes, brows (rigid, bone-parented)
    em, cm = CF.eye_materials()
    lashm = CF.hair_material('ARJ_Lash', 0.98, 0.2, 0.4)
    browm = CF.hair_material('ARJ_BrowHair', 0.95, 0.3, 0.35)
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
    tee = U.mesh_obj('ARJ_Tee', v, f, coll, mat=tee_material())
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
