"""Scene 2 (part 1) — Another Day, Another Fear: the morning bedroom.

Shots (file timeline): 2a 1-84 wide, 2b 85-168 alarm close-up, 2c 169-276 bed edge.
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import bpy, numpy as np
from mathutils import Vector, Euler, Matrix
import bl_util as U, bedroom as BR, scene01_layout as LY, scene01_anim as AN, props as PR, cast, render_settings as RS
import film_timing as FT

U.reset(); sc = bpy.context.scene; sc.name = 'S2Bed'
sc.frame_start, sc.frame_end = 1, 276
A = cast.append('arjun')
rig = A.rig
ctrl = {'IK_hand.L': A.ik['L'], 'IK_hand.R': A.ik['R'], 'Pole_elbow.L': A.pole['L'], 'Pole_elbow.R': A.pole['R']}
rig.location = LY.RIG_LOC; rig.rotation_euler = LY.RIG_ROT
LY.pose_rest(rig, ctrl)
bpy.context.view_layer.update()
head_c = rig.matrix_world @ (rig.pose.bones['head'].matrix @ Vector((0, 0.08, 0.0)))
dent = ((head_c.x, head_c.y, head_c.z - 0.02), (0.13, 0.15, 0.10))
setc = U.collection('SET_Bedroom')
S = BR.build_bedroom(setc, 300, LY.body_top_fn, dent, clock='7:30', day=True)
BR.setup_world(sc)
# second, thrown-back blanket for the sitting shot
blk2, fold2 = BR.build_blanket(setc, lambda X, Y: np.where((X > 0.0), BR.MATTRESS_TOP + 0.06 + 0.03 * np.sin(Y * 9), -1), edge_y=0.6)
for o in (blk2, fold2):
    o.name = o.name + '_Pushed'
blanket, fold = S['blanket']

def vis(objs, f, show):
    for o in objs:
        o.hide_render = not show; o.keyframe_insert('hide_render', frame=f)
        o.hide_viewport = not show; o.keyframe_insert('hide_viewport', frame=f)
vis([blk2, fold2, A.pants, A.feet], 1, False); vis([blanket, fold], 1, True)
vis([blk2, fold2, A.pants, A.feet], 169, True); vis([blanket, fold], 169, False)

# ---------------- morning light
L = S['lights']
sun = L['moon']; sun.data.color = (1.0, 0.80, 0.58); sun.data.energy = 3.6; sun.data.angle = np.radians(2)
d = Vector((1.5, 0.75, -0.55)).normalized(); sun.rotation_euler = (-d).to_track_quat('Z', 'Y').to_euler()
L['fill'].data.energy = 26; L['fill'].data.color = (0.78, 0.86, 1.0)
L['ambient'].data.energy = 12; L['ambient'].data.color = (0.95, 0.92, 0.88)
L['city'].data.energy = 0
sk = bpy.data.materials['SET_Skyline'].node_tree.nodes['Emission']; sk.inputs['Strength'].default_value = 2.2
bg = sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.05, 0.065, 0.09, 1)
bpy.data.materials['SET_ClockLED'].node_tree.nodes['Emission'].inputs['Strength'].default_value = 6
bpy.data.objects['SET_ClockGlow'].data.energy = 0.05

# ---------------- phone on the table: alarm ringing
from PIL import Image, ImageDraw, ImageFont
ui = os.path.join(HERE, '..', 'assets', 'textures', 'alarm_0730.png')
im = Image.new('RGB', (1080, 2304), (14, 16, 24)); dr = ImageDraw.Draw(im)
FD = '/usr/share/fonts/opentype/inter/'
dr.text((540, 300), 'Alarm', font=ImageFont.truetype(FD + 'Inter-Medium.otf', 64), fill=(200, 205, 220), anchor='mm')
dr.text((540, 620), '7:30', font=ImageFont.truetype(FD + 'Inter-Light.otf', 300), fill=(245, 245, 250), anchor='mm')
dr.text((540, 840), 'Office · Sprint review 10:00', font=ImageFont.truetype(FD + 'Inter-Regular.otf', 50), fill=(170, 175, 195), anchor='mm')
dr.rounded_rectangle([140, 1800, 940, 1960], 80, fill=(230, 80, 70)); dr.text((540, 1880), 'Stop', font=ImageFont.truetype(FD + 'Inter-SemiBold.otf', 64), fill=(255, 255, 255), anchor='mm')
dr.rounded_rectangle([140, 1580, 940, 1740], 80, fill=(60, 62, 75)); dr.text((540, 1660), 'Snooze', font=ImageFont.truetype(FD + 'Inter-SemiBold.otf', 64), fill=(230, 230, 240), anchor='mm')
im.save(ui)
m = U.new_mat('PRP_PhoneScreen'); nt = m.node_tree; nt.nodes.clear()
o = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); em.name = 'ScreenEmit'
it = nt.nodes.new('ShaderNodeTexImage'); it.image = bpy.data.images.load(ui)
nt.links.new(it.outputs['Color'], em.inputs['Color']); nt.links.new(em.outputs[0], o.inputs[0])
phone, scr, slight = PR.build_phone(U.collection('PROPS'), m)
phone.location = (-0.92, 1.30, BR.TABLE['h'] + 0.0042); phone.rotation_euler = (0, 0, np.radians(-8))
for f in range(1, 151, 6):        # pulsing ring
    v = 1.0 + 0.25 * np.sin(f * 0.8)
    em.inputs['Strength'].default_value = v; em.inputs['Strength'].keyframe_insert('default_value', frame=f)
    slight.data.energy = 0.8 * v; slight.data.keyframe_insert('energy', frame=f)
    phone.location.x = -0.92 + 0.0012 * np.sin(f * 2.1); phone.keyframe_insert('location', frame=f)
for f, v in ((150, 1.0), (152, 0.0)):
    em.inputs['Strength'].default_value = v; em.inputs['Strength'].keyframe_insert('default_value', frame=f)
    slight.data.energy = 0.8 * v; slight.data.keyframe_insert('energy', frame=f)

# ---------------- acting
pb = A.pb
cast.blinks(A, 1, 150, rest=-9, every=(55, 95), seed=2)
cast.breathe(A, 1, 168, 4.0, 0.05)
cast.key_brows(A, 1, 0.5, 0); cast.key_brows(A, 168, 0.7, 0)
cast.key_eyes(A, 1, 6, 0); cast.key_eyes(A, 60, 6, -2)
for f, yaw, nod in ((1, -2, 0), (100, -2, 0), (122, -30, 4), (150, -26, 4), (168, -10, 2)):
    AN.key_head(pb, f, yaw, nod)
cast.key_eyes(A, 102, -8, -20); cast.key_eyes(A, 150, -8, -14)
A.shape('frown', 0.3, 1); A.shape('frown', 0.45, 160)
# hold the lying pose on the left arm / poles until the cut
L0 = A.ik['L'].matrix_basis.copy()
for f in (1, 168):
    A.ik['L'].matrix_basis = L0; A.ik['L'].keyframe_insert('location', frame=f); A.ik['L'].keyframe_insert('rotation_quaternion', frame=f)
    for s_ in 'LR':
        A.pole[s_].keyframe_insert('location', frame=f)
cast.key_fingers(A, 'L', 1, 'relax'); cast.key_fingers(A, 'L', 168, 'relax')
# reach to stop the alarm
R0 = A.ik['R'].matrix_basis.copy()
RWi = rig.matrix_world.inverted()
tgt = RWi @ Matrix.Translation(phone.location + Vector((0.035, -0.02, 0.03)))
from mathutils import Quaternion
for f, M in ((1, R0), (120, R0), (140, Matrix.LocRotScale(tgt.translation, R0.to_quaternion(), None)), (150, Matrix.LocRotScale(tgt.translation, R0.to_quaternion(), None)),
             (166, R0), (168, R0)):
    A.ik['R'].matrix_basis = M; A.ik['R'].keyframe_insert('location', frame=f); A.ik['R'].keyframe_insert('rotation_quaternion', frame=f)
cast.key_fingers(A, 'R', 1, 'relax'); cast.key_fingers(A, 'R', 132, 'open'); cast.key_fingers(A, 'R', 146, 'relax', point=True); cast.key_fingers(A, 'R', 160, 'relax')
# ----- 2c: sitting on the bed edge, head bowed, then lifts towards the light
def keyrig(f, loc, rot):
    rig.location = loc; rig.rotation_euler = rot
    rig.keyframe_insert('location', frame=f); rig.keyframe_insert('rotation_euler', frame=f)
keyrig(1, LY.RIG_LOC, LY.RIG_ROT); keyrig(168, LY.RIG_LOC, LY.RIG_ROT)
keyrig(169, Vector((-0.66, 1.0, 0.61)), Euler((0, 0, np.radians(-90))))
keyrig(276, Vector((-0.66, 1.0, 0.61)), Euler((0, 0, np.radians(-90))))
for o in [rig]:
    for fc in AN.all_fcurves(o):
        if fc.data_path in ('location', 'rotation_euler'):
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
for n in ('thigh.L', 'thigh.R', 'shin.L', 'shin.R', 'foot.L', 'foot.R', 'spine', 'chest'):
    cast.key_q(pb[n], 168, cast.q((1, 0, 0), 0) if n not in ('chest',) else LY.REST_POSE['chest'])
cast.seat(A, 169, lean=0, knee=74, hip=74, spread=9)
cast.key_q(pb['spine'], 169, cast.q((1, 0, 0), 14)); cast.key_q(pb['chest'], 169, cast.q((1, 0, 0), 16))
cast.key_q(pb['spine'], 276, cast.q((1, 0, 0), 10)); cast.key_q(pb['chest'], 276, cast.q((1, 0, 0), 10))
for f, nod, yaw in ((169, 34, 4), (215, 32, 2), (240, 12, -2), (276, 6, -4)):
    cast.key_q(pb['neck'], f, Euler((np.radians(nod * 0.45), np.radians(yaw * 0.4), 0)).to_quaternion())
    cast.key_q(pb['head'], f, Euler((np.radians(nod * 0.55), np.radians(yaw * 0.6), 0)).to_quaternion())
for s, sx in (('L', 1), ('R', -1)):
    for f, z in ((169, 0.16), (215, 0.16), (245, 0.07), (276, 0.05)):
        cast.key_ik(A, s, f, (0.018 * sx, -0.40, z), (-0.25 * sx, -0.1, 1.0), (-sx, 0, 0))
    cast.key_fingers(A, s, 169, 'hold'); cast.key_fingers(A, s, 276, 'hold')
    A.pole[s].location = Vector((0.35 * sx, 0.1, 0.0)); A.pole[s].keyframe_insert('location', frame=169)
cast.key_eyes(A, 169, -18, 0); cast.key_eyes(A, 236, 0, 0); cast.key_eyes(A, 276, 2, -3)
cast.blinks(A, 169, 276, rest=-9, every=(40, 60), seed=4)
cast.key_brows(A, 169, 0.8, 0); cast.key_brows(A, 276, 0.6, 0.3)
cast.breathe(A, 169, 276, 3.6, 0.07)
A.shape('frown', 0.4, 169)

# ---------------- cameras
cams = {}
cam, tgt = AN.make_cam('CAM_2a', 24, 4.0)
AN.key_cam(cam, tgt, 1, (1.45, -1.55, 1.78), (-0.42, 0.95, 0.72), 24, 3.6)
AN.key_cam(cam, tgt, 84, (1.30, -1.30, 1.72), (-0.42, 0.98, 0.72), 25, 3.3)
cams['CAM_2a'] = cam
cam = AN.plain_cam('CAM_2b', 50, 2.8)
e0, up0, fwd0, left0 = AN.face_frame(rig, 100)
p0 = e0 + fwd0 * 0.55 + up0 * 0.10 - left0 * 0.14
AN.aim_cam(cam, list(range(85, 169, 4)) + [168], lambda f, e, up, fwd, left: p0 + (e0 - p0) * 0.08 * (f - 85) / 83, rig)
AN.handheld(cam, 0.001, 40, 3)
cams['CAM_2b'] = cam
cam, tgt = AN.make_cam('CAM_2c', 32, 2.8)
sc.frame_set(250); e = A.eyes_world()
AN.key_cam(cam, tgt, 169, (-1.78, 0.48, 1.02), e + Vector((0, 0, -0.22)), 32, (Vector((-1.78, 0.48, 1.02)) - e).length)
sc.frame_set(276); e2 = A.eyes_world()
AN.key_cam(cam, tgt, 276, (-1.70, 0.54, 1.04), e2 + Vector((0, 0, -0.16)), 35, (Vector((-1.70, 0.54, 1.04)) - e2).length)
AN.handheld(cam, 0.002, 50, 4)
cams['CAM_2c'] = cam
for n, a, b, c in FT.S2BED:
    mk = sc.timeline_markers.new(n, frame=a); mk.camera = cams[c]
sc.camera = cams['CAM_2a']
RS.apply(sc, 'final')
out = os.path.abspath(os.path.join(HERE, '..', '..', 'source', 'scene02a_morning_bedroom.blend'))
bpy.ops.wm.save_as_mainfile(filepath=out, relative_remap=True, compress=True)
print('saved', out)
