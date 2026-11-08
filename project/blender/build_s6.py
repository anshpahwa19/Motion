"""Scene 6 — Tomorrow Is Another Day (bedroom, calm night). Shots in config/film_timing.S6."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import bpy, numpy as np
from mathutils import Vector, Euler, Matrix
import bl_util as U, bedroom as BR, scene01_layout as LY, scene01_anim as AN, props as PR, cast, render_settings as RS
import film_timing as FT
from cast import key_q, q

SH = {n: (a, b) for n, a, b, c in FT.S6}
NF = FT.S6[-1][2]
U.reset(); sc = bpy.context.scene; sc.name = 'S6Night'; sc.frame_start, sc.frame_end = 1, NF
A = cast.append('arjun'); rig = A.rig; pb = A.pb
ctrl = {'IK_hand.L': A.ik['L'], 'IK_hand.R': A.ik['R'], 'Pole_elbow.L': A.pole['L'], 'Pole_elbow.R': A.pole['R']}
rig.location = LY.RIG_LOC; rig.rotation_euler = LY.RIG_ROT
LY.pose_rest(rig, ctrl); bpy.context.view_layer.update()
for o in (A.pants, A.feet):
    o.hide_render = True
head_c = rig.matrix_world @ (rig.pose.bones['head'].matrix @ Vector((0, 0.08, 0.0)))
setc = U.collection('SET_Bedroom')
S = BR.build_bedroom(setc, NF + 20, LY.body_top_fn, ((head_c.x, head_c.y, head_c.z - 0.02), (0.13, 0.15, 0.10)), clock='11:08')
BR.setup_world(sc)
bpy.data.objects['SET_Bottle'].hide_render = True; bpy.data.objects['SET_BottleCap'].hide_render = True
# bedside lamp
lc = U.collection('PROPS')
brass = bpy.data.materials['SET_Brass']
BR.cylinder('PRP_LampBase', 0.06, 0.02, (-1.13, 1.27, BR.TABLE['h'] + 0.01), brass, lc, 32)
BR.cylinder('PRP_LampStem', 0.008, 0.26, (-1.13, 1.27, BR.TABLE['h'] + 0.15), brass, lc, 12)
shade_m = U.new_mat('PRP_LampShade'); p = U.principled(shade_m)
p.inputs['Base Color'].default_value = (*U.hex2lin('#e8d9b8'), 1); p.inputs['Roughness'].default_value = 0.8
emn = shade_m.node_tree.nodes; out = emn['Material Output']
tr = emn.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = (1.0, 0.8, 0.5, 1)
em = emn.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (1.0, 0.72, 0.4, 1); em.inputs['Strength'].default_value = 2.6
mx = emn.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.5
add = emn.new('ShaderNodeAddShader')
shade_m.node_tree.links.new(p.outputs[0], mx.inputs[1]); shade_m.node_tree.links.new(tr.outputs[0], mx.inputs[2])
shade_m.node_tree.links.new(mx.outputs[0], add.inputs[0]); shade_m.node_tree.links.new(em.outputs[0], add.inputs[1])
shade_m.node_tree.links.new(add.outputs[0], out.inputs[0])
bm = __import__('bmesh').new(); __import__('bmesh').ops.create_cone(bm, cap_ends=False, segments=48, radius1=0.11, radius2=0.07, depth=0.16)
me = bpy.data.meshes.new('PRP_LampShade'); bm.to_mesh(me); bm.free(); me.materials.append(shade_m)
shade = bpy.data.objects.new('PRP_LampShade', me); lc.objects.link(shade); shade.location = (-1.13, 1.27, BR.TABLE['h'] + 0.31)
shade.modifiers.new('s', 'SOLIDIFY').thickness = 0.002
lamp = bpy.data.objects.new('LGT_Lamp', bpy.data.lights.new('LGT_Lamp', 'POINT')); lc.objects.link(lamp)
lamp.location = (-1.13, 1.27, BR.TABLE['h'] + 0.29); lamp.data.color = (1.0, 0.70, 0.42); lamp.data.shadow_soft_size = 0.05
OFF = SH['6c_lamp_off'][0] + 50
for f, e, emv in ((1, 26, 2.6), (OFF - 1, 26, 2.6), (OFF, 0, 0.0)):
    lamp.data.energy = e; lamp.data.keyframe_insert('energy', frame=f)
    em.inputs['Strength'].default_value = emv; em.inputs['Strength'].keyframe_insert('default_value', frame=f)
L = S['lights']
L['moon'].data.energy = 3.4      # calmer, softer moon
for f, v in ((1, 2.0), (OFF - 1, 2.0), (OFF, 6.0)):
    L['fill'].data.energy = v; L['fill'].data.keyframe_insert('energy', frame=f)
# phone: calm headline
from PIL import Image, ImageDraw, ImageFont
FD = '/usr/share/fonts/opentype/inter/'
ui = os.path.join(HERE, '..', 'assets', 'textures', 'phone_s6.png')
im = Image.new('RGB', (1080, 2304), (246, 246, 249)); d = ImageDraw.Draw(im)
d.text((60, 150), 'Pulse', font=ImageFont.truetype(FD + 'Inter-ExtraBold.otf', 76), fill=(20, 20, 28))
d.rounded_rectangle([40, 300, 1040, 1300], 46, fill=(255, 255, 255))
d.text((90, 380), 'TechPulse · 5m', font=ImageFont.truetype(FD + 'Inter-SemiBold.otf', 36), fill=(110, 110, 125))
for i, ln in enumerate(['AI design tools', 'just got better.', 'Again.']):
    d.text((90, 460 + i * 96), ln, font=ImageFont.truetype(FD + 'Inter-Bold.otf', 80), fill=(16, 16, 22))
d.rounded_rectangle([40, 1350, 1040, 1700], 46, fill=(255, 255, 255))
d.text((90, 1430), 'Calendar · Tomorrow', font=ImageFont.truetype(FD + 'Inter-SemiBold.otf', 36), fill=(110, 110, 125))
d.text((90, 1500), '10:00  Test v2 with Mr. Rao', font=ImageFont.truetype(FD + 'Inter-Bold.otf', 58), fill=(16, 130, 90))
im.save(ui)
m = U.new_mat('PRP_PhoneScreen'); nt = m.node_tree; nt.nodes.clear()
o = nt.nodes.new('ShaderNodeOutputMaterial'); sem = nt.nodes.new('ShaderNodeEmission')
it = nt.nodes.new('ShaderNodeTexImage'); it.image = bpy.data.images.load(ui)
nt.links.new(it.outputs['Color'], sem.inputs['Color']); nt.links.new(sem.outputs[0], o.inputs[0])
phone, scr, slight = PR.build_phone(lc, m)
phone.rotation_mode = 'QUATERNION'; A.ik['R'].rotation_mode = 'QUATERNION'
LOCK = SH['6b_phone_down'][0] + 70
for f, v, l in ((1, 1.0, 2.2), (LOCK - 1, 1.0, 2.2), (LOCK, 0.0, 0.0)):
    sem.inputs['Strength'].default_value = v; sem.inputs['Strength'].keyframe_insert('default_value', frame=f)
    slight.data.energy = l; slight.data.keyframe_insert('energy', frame=f)
# phone path: held above face -> lowered -> table (face down) ; IK follows the phone
RW = rig.matrix_world.copy(); RWi = RW.inverted()
sc.frame_set(1); eyes = AN.eyes_world(rig)
P_hold = AN.phone_mat((-0.37, 1.13, 1.02), eyes - Vector((-0.37, 1.13, 1.02)), (0.12, 1, 0.35))
P_low = AN.phone_mat((-0.45, 1.05, 0.86), eyes - Vector((-0.45, 1.05, 0.86)) + Vector((0, 0, -0.1)), (0.1, 1, 0.2))
P_table = AN.phone_mat((-0.92, 1.36, BR.TABLE['h'] + 0.0042), (0, 0, -1), (0.15, 1, 0))     # face down
P_hover = Matrix.Translation((0.02, 0, 0.05)) @ P_table
GB, GD = AN.grip_B(), AN.grip_D()
b0 = SH['6b_phone_down'][0]
keys = [(1, P_hold, 1.0), (b0 + 20, P_hold, 1.0), (b0 + 72, P_low, 0.8), (b0 + 100, P_hover, 0.05), (b0 + 110, P_table, 0.0), (NF, P_table, 0.0)]
def at(f):
    for (fa, Ma, ga), (fb, Mb, gb) in zip(keys[:-1], keys[1:]):
        if fa <= f <= fb:
            t = AN.ease((f - fa) / max(fb - fa, 1)); return AN.mlerp(Ma, Mb, t), ga + (gb - ga) * t
    return keys[-1][1], keys[-1][2]
R_chest = LY.hand_matrix((-0.10, -0.115, 0.27), (0.8, -0.1, 0.45), (0, 1, 0.15))
prev = [None, None]; rel = b0 + 110
lampsw = Vector((-1.10, 1.30, BR.TABLE['h'] + 0.05))
for f in range(1, NF + 1):
    M, g = at(f)
    phone.matrix_world = M
    qq = phone.rotation_quaternion.copy()
    if prev[0] is not None and qq.dot(prev[0]) < 0: qq.negate(); phone.rotation_quaternion = qq
    prev[0] = qq.copy(); phone.keyframe_insert('location', frame=f); phone.keyframe_insert('rotation_quaternion', frame=f)
    if f <= rel:
        H = RWi @ (M @ AN.mlerp(GD, GB, g))
    elif f <= OFF - 22:
        H = AN.mlerp(RWi @ (P_hover @ GD), R_chest, AN.ease((f - rel) / 25))
    elif f <= OFF:   # reach the lamp switch
        sw = RWi @ Matrix.LocRotScale(lampsw, (P_hover @ GD).to_quaternion(), None)
        H = AN.mlerp(R_chest, sw, AN.ease((f - (OFF - 22)) / 22))
    else:
        sw = RWi @ Matrix.LocRotScale(lampsw, (P_hover @ GD).to_quaternion(), None)
        H = AN.mlerp(sw, R_chest, AN.ease((f - OFF) / 30))
    A.ik['R'].matrix_basis = H
    qq = A.ik['R'].rotation_quaternion.copy()
    if prev[1] is not None and qq.dot(prev[1]) < 0: qq.negate(); A.ik['R'].rotation_quaternion = qq
    prev[1] = qq.copy(); A.ik['R'].keyframe_insert('location', frame=f); A.ik['R'].keyframe_insert('rotation_quaternion', frame=f)
AN.set_interp(phone, 'LINEAR'); AN.set_interp(A.ik['R'], 'LINEAR')
cast.key_fingers(A, 'R', 1, 'hold'); cast.key_fingers(A, 'R', rel - 8, 'hold'); cast.key_fingers(A, 'R', rel + 6, 'open')
cast.key_fingers(A, 'R', OFF - 4, 'relax', point=True); cast.key_fingers(A, 'R', OFF + 20, 'relax')
cast.key_fingers(A, 'L', 1, 'relax')
# face: calm reading, gentle smile, lets go, sleeps
for f, yaw, nod in ((1, -5, 11), (b0 + 60, -6, 10), (b0 + 100, -24, 3), (OFF - 10, -22, 2), (OFF + 30, 0, 0), (NF, 2, 0)):
    AN.key_head(pb, f, yaw, nod)
for f, up, lf in ((1, -19, -3), (b0 + 60, -19, -2), (b0 + 96, -10, -20), (OFF, -6, -18), (OFF + 30, 8, 0)):
    cast.key_eyes(A, f, up, lf)
cast.key_brows(A, 1, 0.1, 0.3); cast.key_brows(A, b0 + 20, 0.0, 0.8); cast.key_brows(A, NF, 0.0, 0.0)
A.shape('smile', 0.0, 1); A.shape('smile', 0.35, b0 + 40); A.shape('smile', 0.2, OFF + 40); A.shape('smile', 0.3, NF)
d0, d1 = SH['6d_peace_cu']
cast.blinks(A, 1, d0 + 20, rest=-7, every=(70, 110), seed=8)
for s in 'LR':
    key_q(pb['lid_up.' + s], d0 + 30, q((1, 0, 0), -10)); key_q(pb['lid_up.' + s], d0 + 70, q((1, 0, 0), -46))
    key_q(pb['lid_lo.' + s], d0 + 30, q((1, 0, 0), 0)); key_q(pb['lid_lo.' + s], d0 + 70, q((1, 0, 0), 9))
    key_q(pb['lid_up.' + s], NF, q((1, 0, 0), -46)); key_q(pb['lid_lo.' + s], NF, q((1, 0, 0), 9))
cast.breathe(A, 1, NF, 5.2, 0.05)
# cameras
cams = {}
c, t = AN.make_cam('CAM_6a', 26, 4.0)
AN.key_cam(c, t, 1, (1.30, -1.20, 1.70), (-0.42, 1.0, 0.75), 26, 3.2); AN.key_cam(c, t, 96, (1.05, -0.75, 1.55), (-0.42, 1.02, 0.76), 27, 2.8)
cams['CAM_6a'] = c
c, t = AN.make_cam('CAM_6b', 34, 2.8)
sc.frame_set(b0 + 40); e = AN.eyes_world(rig)
AN.key_cam(c, t, b0, (0.55, 1.02, 1.30), (-0.50, 1.30, 0.80), 34, (Vector((0.55, 1.02, 1.30)) - e).length)
AN.key_cam(c, t, SH['6b_phone_down'][1], (0.45, 1.10, 1.22), (-0.55, 1.32, 0.76), 36, (Vector((0.45, 1.10, 1.22)) - e).length)
cams['CAM_6b'] = c
c, t = AN.make_cam('CAM_6c', 30, 3.2)
c0, c1 = SH['6c_lamp_off']
AN.key_cam(c, t, c0, (0.2, 0.55, 1.45), (-0.85, 1.35, 0.75), 30, 1.6); AN.key_cam(c, t, c1, (0.15, 0.62, 1.42), (-0.80, 1.36, 0.74), 31, 1.55)
cams['CAM_6c'] = c
c = AN.plain_cam('CAM_6d', 70, 2.8)
e0, up0, fwd0, left0 = AN.face_frame(rig, d0)
p0 = e0 + fwd0 * 0.42 + left0 * 0.18 + up0 * 0.06
AN.aim_cam(c, list(range(d0, d1 + 1, 6)) + [d1], lambda f, e, up, fwd, left: p0 + (e0 - p0) * 0.12 * (f - d0) / (d1 - d0), rig)
cams['CAM_6d'] = c
c = bpy.data.objects.new('CAM_6e', bpy.data.cameras.new('CAM_6e')); U.link(c, U.collection('CAMERAS'))
c.data.dof.use_dof = True; c.data.dof.aperture_fstop = 3.5; c.location = (-0.42, 1.16, 2.86); c.rotation_euler = (0, 0, np.radians(8))
sc.frame_set(SH['6e_overhead'][0]); c.data.dof.focus_distance = 2.86 - AN.eyes_world(rig).z
c.data.lens = 36; c.data.keyframe_insert('lens', frame=SH['6e_overhead'][0]); c.data.lens = 20; c.data.keyframe_insert('lens', frame=NF)
cams['CAM_6e'] = c
for n, a, b, cn in FT.S6:
    mk = sc.timeline_markers.new(n, frame=a); mk.camera = cams[cn]
sc.camera = cams['CAM_6a']
RS.apply(sc, 'final')
outp = os.path.abspath(os.path.join(HERE, '..', '..', 'source', 'scene06_tomorrow.blend'))
bpy.ops.wm.save_as_mainfile(filepath=outp, relative_remap=True, compress=True)
print('saved', outp)
