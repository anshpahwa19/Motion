"""Scenes 2b-5 — the office day file (one timeline, see config/film_timing.OFFICE)."""
import sys, os, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'config')); sys.path.insert(0, os.path.join(HERE, '..', 'ui'))
import bpy, numpy as np
from mathutils import Vector, Euler, Matrix, Quaternion
import bl_util as U, cast, office_day as OD, scene01_anim as AN, render_settings as RS
import film_timing as FT, film_screens as FS
from cast import key_q, q

NF = FT.OFFICE[-1][2]
SH = {n: (a, b) for n, a, b, c in FT.OFFICE}
ASSETS = os.path.abspath(os.path.join(HERE, '..', 'assets', 'film_ui'))
rng = np.random.default_rng(12)


# ------------------------------------------------------------ screen sequences
def gen_screens():
    md = os.path.join(ASSETS, 'monitor'); pd = os.path.join(ASSETS, 'rao_phone')
    if os.path.exists(os.path.join(md, f'f{NF:04d}.jpg')) and os.path.exists(os.path.join(pd, f'f{NF:04d}.jpg')):
        return md, pd
    os.makedirs(md, exist_ok=True); os.makedirs(pd, exist_ok=True)
    from PIL import Image
    W, H = 960, 560
    design = Image.open(os.path.join(HERE, '..', 'assets', 'textures', 'laptop_screen.png')).convert('RGB').resize((W, H))
    design.save(os.path.join(md, 'static_design.jpg'), quality=88)
    FS.draw_ai_result(1.0, W, H).save(os.path.join(md, 'static_ai.jpg'), quality=88)
    def seg(a, b):
        return a <= f <= b
    a3, b3 = SH['3a_prompt_ots']; c3, d3 = SH['3c_face_monitor']; e5, f5 = SH['5a_sketch']; g5, h5 = SH['5c_face_engaged']
    for f in range(1, NF + 1):
        p = os.path.join(md, f'f{f:04d}.jpg')
        if seg(a3, b3):
            FS.draw_ai_prompt((f - a3) / (b3 - a3), W, H).save(p, quality=85)
        elif seg(c3, d3):
            FS.draw_ai_generate((f - c3) / (d3 - c3), W, H).save(p, quality=85)
        elif seg(d3 + 1, SH['3f_doubt'][1]):
            os.link(os.path.join(md, 'static_ai.jpg'), p) if not os.path.exists(p) else None
        elif seg(e5, e5 + 50):
            FS.draw_cocreate(0.25 * (f - e5) / 50, W, H).save(p, quality=85)
        elif seg(e5 + 51, h5):
            FS.draw_cocreate(0.25 + 0.75 * (f - e5 - 51) / (h5 - e5 - 51), W, H).save(p, quality=85)
        else:
            if not os.path.exists(p):
                os.link(os.path.join(md, 'static_design.jpg'), p)
    bad = FS.draw_bank_app(0.0).resize((540, 1152)); bad.save(os.path.join(pd, 'bad.jpg'), quality=88)
    a5, b5 = SH['5e_rao_success']
    for f in range(1, NF + 1):
        p = os.path.join(pd, f'f{f:04d}.jpg')
        if a5 <= f <= b5:
            FS.draw_bank_app((f - a5) / (b5 - a5), good=True).resize((540, 1152)).save(p, quality=85)
        elif not os.path.exists(p):
            os.link(os.path.join(pd, 'bad.jpg'), p)
    return md, pd


md, pd = gen_screens()
U.reset(); sc = bpy.context.scene; sc.name = 'OfficeDay'
sc.frame_start, sc.frame_end = 1, NF
w = bpy.data.worlds.new('WLD_OfficeDay'); sc.world = w; w.use_nodes = True
setc = U.collection('SET_OfficeDay')
O = OD.build_office_day(setc, md, pd, NF)

# ------------------------------------------------------------ cast
ARJ = cast.append('arjun'); RAO = cast.append('rao'); CA = cast.append('colleague_a'); CB = cast.append('colleague_b')
ARJ.tee_color('#28385a'); ARJ.pants_color('#34465f')
for a in (ARJ, RAO, CA, CB):
    sh = next((m for m in bpy.data.materials if m.name.endswith('_Shoes')), None)
    if sh and a.feet:
        a.feet.data.materials[0] = sh

DESK = Vector((0.0, -0.64, 0.62)); MEETA = Vector((OD.MEET.x + 0.05, OD.MEET.y - 0.60, 0.62))
RAOP = Vector((OD.MEET.x - 0.58, OD.MEET.y - 0.05, 0.62))


def keyrig(a, f, loc, rz):
    a.rig.location = loc; a.rig.rotation_euler = Euler((0, 0, np.radians(rz)))
    a.rig.keyframe_insert('location', frame=f); a.rig.keyframe_insert('rotation_euler', frame=f)


def constant(obj):
    for fc in AN.all_fcurves(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT'


def show(a, f, on):
    for o in list(a.objs.values()):
        if not isinstance(o, bpy.types.Object):
            continue
        o.hide_render = not on; o.keyframe_insert('hide_render', frame=f)


# where Arjun is per shot
desk_shots = ['2d_office_est', '2e_desk_side', '2f_present_absent', '3a_prompt_ots', '3c_face_monitor', '3e_office_wide', '3f_doubt',
              '5a_sketch', '5c_face_engaged', '5f_golden_wide']
meet_shots = ['4a_test_wide', '4c_rao_cu', '4d_arjun_realises', '4e_two_shot', '4g_arjun_thinks', '5e_rao_success']
for n in desk_shots:
    keyrig(ARJ, SH[n][0], DESK, 180)
for n in meet_shots:
    keyrig(ARJ, SH[n][0], MEETA, 180)
constant(ARJ.rig)
keyrig(RAO, 1, RAOP, 90); constant(RAO.rig)
show(RAO, 1, False)
for n in meet_shots:
    show(RAO, SH[n][0], True)
for n in desk_shots:
    if SH[n][0] > 1:
        show(RAO, SH[n][0], False)
for a in (RAO,):
    for o in list(a.objs.values()):
        if isinstance(o, bpy.types.Object):
            constant(o)
keyrig(CA, 1, Vector((1.6, -0.64, 0.62)), 180); keyrig(CB, 1, Vector((0.0, 0.96, 0.62)), 180)
for a in (ARJ, RAO, CA, CB):
    cast.seat(a, 1)
    cast.breathe(a, 1, NF, 4.0 + rng.uniform(-0.4, 0.4), 0.04)
    cast.blinks(a, 1, NF, rest=-6 if a is not ARJ else -8, seed=int(rng.integers(100)))

# ------------------------------------------------------------ typing helpers (rig space: body faces -Y)
KB = {'R': Vector((-0.10, -0.47, 0.15)), 'L': Vector((0.10, -0.47, 0.15))}


def hands_on_keys(a, f0, f1, type_=True, seed=0):
    g = np.random.default_rng(seed)
    for s in 'LR':
        p = KB[s]
        cast.key_ik(a, s, f0, p, (0.08 * (1 if s == 'R' else -1), -1, -0.25), (0, 0.1, -1))
        cast.key_ik(a, s, f1, p, (0.08 * (1 if s == 'R' else -1), -1, -0.25), (0, 0.1, -1))
        a.pole[s].location = Vector((0.45 * (1 if s == 'L' else -1), 0.1, -0.1)); a.pole[s].keyframe_insert('location', frame=f0)
        if type_:
            for f in range(f0, f1, 3):
                for fn in ('index', 'middle', 'ring', 'pinky'):
                    c = np.array([18, 26, 12]) + g.uniform(-10, 14, 3) * (g.random() < 0.45)
                    for i in range(3):
                        key_q(a.pb[f'f_{fn}.{i + 1:02d}.{s}'], f, q((1, 0, 0), c[i]))
        else:
            cast.key_fingers(a, s, f0, 'type'); cast.key_fingers(a, s, f1, 'type')


hands_on_keys(CA, 1, NF, True, 3); hands_on_keys(CB, 1, NF, True, 4)
for a, s in ((CA, 5), (CB, 6)):
    for f in range(1, NF, 60):
        cast.key_head(a, f, rng.uniform(-6, 6), rng.uniform(4, 10), rng.uniform(-2, 2))
        cast.key_eyes(a, f, -6, rng.uniform(-6, 6))

pb = ARJ.pb
# ============================================================ SCENE 2 (office part)
a2, b2 = SH['2d_office_est']
hands_on_keys(ARJ, a2, b2, False)
cast.key_head(ARJ, a2, 0, 12); cast.key_eyes(ARJ, a2, -10, 0); cast.key_brows(ARJ, a2, 0.6)
ARJ.shape('frown', 0.35, a2)
# 2e: opens the laptop, stares, foot taps, looks to the window
a, b = SH['2e_desk_side']
lid = O['lid']
def world_to_rig(a_, p):
    return a_.rig.matrix_world.inverted() @ p
for f, ang in ((1, 88), (a + 8, 88), (a + 30, -8)):
    lid.rotation_euler = (np.radians(ang), 0, 0); lid.keyframe_insert('rotation_euler', frame=f)
sc.frame_set(a); bpy.context.view_layer.update()
piv = Vector((-0.40, -0.04, OD.DESK_H + 0.015))
for f, ang in ((a + 2, 88), (a + 8, 88), (a + 30, -8)):
    tipw = piv + 0.22 * Vector((0, -np.sin(np.radians(ang)), np.cos(np.radians(ang))))
    cast.key_ik(ARJ, 'L', f, world_to_rig(ARJ, tipw + Vector((0.0, -0.02, 0.01))), (0, -0.3, 1), (0, -1, 0.2))
cast.key_fingers(ARJ, 'L', a + 2, 'open'); cast.key_fingers(ARJ, 'L', a + 30, 'relax')
cast.key_ik(ARJ, 'L', a + 46, KB['L'], (-0.08, -1, -0.25), (0, 0.1, -1))
cast.key_head(ARJ, a, 0, 10); cast.key_head(ARJ, a + 40, 0, 14); cast.key_head(ARJ, a + 90, -28, 4); cast.key_head(ARJ, b, -32, 3)
cast.key_eyes(ARJ, a + 40, -14, 0); cast.key_eyes(ARJ, a + 86, -2, -22); cast.key_eyes(ARJ, b, -2, -18)
for f in range(a + 40, b, 6):   # anxious foot tap
    key_q(pb['foot.R'], f, q((1, 0, 0), 4 + (12 if (f // 6) % 2 else 0)))
# 2f: present but absent — close-up, unfocused, slow blink
a, b = SH['2f_present_absent']
cast.key_head(ARJ, a, 0, 9); cast.key_head(ARJ, b, 2, 10); cast.key_eyes(ARJ, a, -8, 3); cast.key_eyes(ARJ, b, -9, 4)
cast.key_brows(ARJ, a, 0.75); ARJ.shape('frown', 0.4, a)
hands_on_keys(ARJ, a, b, False)

# ============================================================ SCENE 3
a, b = SH['3a_prompt_ots']
hands_on_keys(ARJ, a, b, True, 7)
cast.key_head(ARJ, a, 0, 6); cast.key_eyes(ARJ, a, 2, 0)
a, b = SH['3c_face_monitor']
hands_on_keys(ARJ, a, b, False)
cast.key_head(ARJ, a, 0, 4); cast.key_head(ARJ, b, 0, 1)
cast.key_brows(ARJ, a, 0.3, 0.5); cast.key_brows(ARJ, a + 50, 0.8, 1.2); cast.key_brows(ARJ, b, 1.0, 0.6)
for s in 'LR':
    key_q(pb['lid_up.' + s], a, q((1, 0, 0), -8)); key_q(pb['lid_up.' + s], a + 50, q((1, 0, 0), 2)); key_q(pb['lid_up.' + s], b - 4, q((1, 0, 0), 0))
ARJ.shape('frown', 0.2, a); ARJ.shape('frown', 0.55, b)
for f in range(a, b, 5):   # eyes scanning the cascade of screens
    cast.key_eyes(ARJ, f, 3 + rng.uniform(-3, 3), rng.uniform(-10, 10))
mon = O['monitor_light']
for f in range(a, b, 4):
    mon.data.energy = 3.0 + 1.5 * rng.random(); mon.data.keyframe_insert('energy', frame=f)
a, b = SH['3e_office_wide']
hands_on_keys(ARJ, a, b, False); cast.key_head(ARJ, a, 0, 3); cast.key_eyes(ARJ, a, 2, 0)
a, b = SH['3f_doubt']
hands_on_keys(ARJ, a, a + 40, False)
cast.key_head(ARJ, a, 0, 3); cast.key_head(ARJ, a + 50, 14, 6); cast.key_head(ARJ, b, 16, 8)
cast.key_eyes(ARJ, a, 2, 0); cast.key_eyes(ARJ, a + 46, 4, 18); cast.key_eyes(ARJ, b, 2, 16)
sticky_rig = world_to_rig(ARJ, O['sticky'] + Vector((0.01, -0.03, 0)))
cast.key_ik(ARJ, 'L', a + 60, sticky_rig + Vector((0, -0.04, -0.06)), (0.2, -1, 0.4), (0, 1, 0))
cast.key_ik(ARJ, 'L', a + 80, sticky_rig, (0.1, -0.6, 0.8), (0, 1, 0)); cast.key_ik(ARJ, 'L', b, sticky_rig, (0.1, -0.6, 0.8), (0, 1, 0))
cast.key_fingers(ARJ, 'L', a + 60, 'relax'); cast.key_fingers(ARJ, 'L', a + 78, 'relax', point=True)
cast.key_brows(ARJ, a, 0.9); cast.key_brows(ARJ, b, 1.1, -0.2); ARJ.shape('frown', 0.6, b)

# ============================================================ SCENE 4 — usability test
TBL = Vector((OD.MEET.x, OD.MEET.y, 0.745))
a4 = SH['4a_test_wide'][0]
keyrig(RAO, a4, RAOP, 90); bpy.context.view_layer.update()
phone = O['rao_phone']
# phone in Rao's right hand, screen to his face
ph_rig = AN.phone_mat((-0.04, -0.33, 0.24), (0, 0.55, 0.83), (0.0, -0.6, 0.6))
GB = AN.grip_B()
RAO.ik['R'].matrix_basis = ph_rig @ GB
for f in (1, NF):
    RAO.ik['R'].keyframe_insert('location', frame=f); RAO.ik['R'].keyframe_insert('rotation_quaternion', frame=f)
cast.key_fingers(RAO, 'R', 1, 'hold')
phone.parent = RAO.rig; phone.matrix_parent_inverse = Matrix.Identity(4); phone.matrix_basis = ph_rig
RAO.pole['R'].location = Vector((-0.45, 0.1, -0.1)); RAO.pole['L'].location = Vector((0.45, 0.1, -0.1))
cast.key_ik(RAO, 'L', 1, Vector((0.12, -0.30, 0.10)), (-0.4, -1, 0.1), (-0.3, 0, -1))
cast.key_fingers(RAO, 'L', 1, 'relax')
rp = RAO.pb
cast.key_head(RAO, a4, 0, 22); cast.key_eyes(RAO, a4, -18, 0); cast.key_brows(RAO, a4, 0.4)
# Arjun with notebook & pen
pen = O['pen']
pen.parent = ARJ.rig; pen.parent_type = 'BONE'; pen.parent_bone = 'hand.R'
pen.location = (0.012, 0.03, -0.012); pen.rotation_euler = (np.radians(70), 0, np.radians(15))
pen.hide_render = True; pen.keyframe_insert('hide_render', frame=1)
for n in meet_shots + ['5a_sketch']:
    pen.hide_render = False; pen.keyframe_insert('hide_render', frame=SH[n][0])
for n in ['5c_face_engaged', '5f_golden_wide']:
    pen.hide_render = True; pen.keyframe_insert('hide_render', frame=SH[n][0])
NB = world_to_rig(ARJ, TBL + Vector((0.05, -0.31, 0.02))) if False else None
def arjun_meet_hands(f, write=False):
    keyrig(ARJ, f, MEETA, 180); bpy.context.view_layer.update()
    nbw = TBL + Vector((0.05, -0.31, 0.03))
    cast.key_ik(ARJ, 'R', f, world_to_rig(ARJ, nbw + Vector((-0.04, 0.0, 0.0))), (0.3, -1, -0.3), (0, 0.2, -1))
    cast.key_ik(ARJ, 'L', f, world_to_rig(ARJ, nbw + Vector((0.12, 0.02, 0.0))), (-0.4, -1, -0.2), (0, 0.2, -1))
    cast.key_fingers(ARJ, 'R', f, 'hold'); cast.key_fingers(ARJ, 'L', f, 'relax')
a, b = SH['4a_test_wide']
arjun_meet_hands(a); cast.key_head(ARJ, a, 40, 14); cast.key_eyes(ARJ, a, -6, 10); cast.key_brows(ARJ, a, 0.5)
ARJ.shape('frown', 0.15, a)
# 4c: Rao confused, squints, tilts, speaks
a, b = SH['4c_rao_cu']
cast.key_head(RAO, a, 0, 22, 0); cast.key_head(RAO, a + 30, 4, 26, 8); cast.key_head(RAO, a + 70, -3, 18, -4); cast.key_head(RAO, b, 6, 14, 6)
cast.key_brows(RAO, a, 0.6, 0.2); cast.key_brows(RAO, a + 40, 1.0, 0.0); cast.key_brows(RAO, b, 0.8, 0.6)
for s in 'LR':
    key_q(rp['lid_up.' + s], a, q((1, 0, 0), -6)); key_q(rp['lid_up.' + s], a + 30, q((1, 0, 0), -16)); key_q(rp['lid_up.' + s], b, q((1, 0, 0), -10))
    key_q(rp['lid_lo.' + s], a + 30, q((1, 0, 0), 5)); key_q(rp['lid_lo.' + s], b, q((1, 0, 0), 2))
RAO.shape('frown', 0.3, a); RAO.shape('frown', 0.55, a + 40)
RAO.shape('jaw_open', 0, a + 44)
for f in range(a + 46, b - 6, 3):   # speech
    v = max(0, rng.normal(0.55, 0.3)) if ((f - a) % 20) < 15 else 0.05
    RAO.shape('jaw_open', min(v, 1.0), f); RAO.shape('lips_part', min(v, 1.0), f)
RAO.shape('jaw_open', 0, b); RAO.shape('lips_part', 0, b)
cast.key_eyes(RAO, a + 60, -8, 14)        # glances up at Arjun
cast.key_eyes(RAO, b, -16, 0)
# 4d: Arjun realises
a, b = SH['4d_arjun_realises']
arjun_meet_hands(a)
cast.key_head(ARJ, a, 46, 10); cast.key_head(ARJ, b, 42, 6)
cast.key_eyes(ARJ, a, -4, 12); cast.key_eyes(ARJ, a + 50, 0, 10)
cast.key_brows(ARJ, a, 0.6, 0.0); cast.key_brows(ARJ, a + 45, 0.2, 1.4); cast.key_brows(ARJ, b, 0.0, 0.6)
ARJ.shape('frown', 0.2, a); ARJ.shape('frown', 0.0, a + 50); ARJ.shape('smile', 0.0, a + 50); ARJ.shape('smile', 0.25, b)
for s in 'LR':
    key_q(pb['lid_up.' + s], a + 40, q((1, 0, 0), -7)); key_q(pb['lid_up.' + s], a + 52, q((1, 0, 0), 0)); key_q(pb['lid_up.' + s], b, q((1, 0, 0), -4))
cast.key_head(ARJ, a + 70, 44, 12); cast.key_head(ARJ, a + 82, 44, 4)   # small nod
# 4e: leans in, points, Rao nods & smiles, Arjun writes
a, b = SH['4e_two_shot']
arjun_meet_hands(a)
key_q(pb['spine'], a, q((1, 0, 0), 3)); key_q(pb['spine'], a + 20, q((1, 0, 0), 12)); key_q(pb['spine'], a + 70, q((1, 0, 0), 12)); key_q(pb['spine'], a + 90, q((1, 0, 0), 5))
sc.frame_set(a + 30); bpy.context.view_layer.update()
phw = phone.matrix_world.translation.copy()
cast.key_ik(ARJ, 'L', a + 30, world_to_rig(ARJ, phw + Vector((0.06, -0.02, 0.05))), (-0.7, -0.4, -0.3), (0, 0, -1))
cast.key_ik(ARJ, 'L', a + 64, world_to_rig(ARJ, phw + Vector((0.06, -0.02, 0.05))), (-0.7, -0.4, -0.3), (0, 0, -1))
cast.key_fingers(ARJ, 'L', a + 24, 'relax', point=True); cast.key_fingers(ARJ, 'L', a + 66, 'relax')
arjun_meet_hands(a + 90)
for f in range(a + 92, b, 4):   # writing
    nbw = TBL + Vector((0.05 + 0.03 * np.sin(f * 0.7), -0.31 + 0.01 * np.cos(f * 1.3), 0.03))
    cast.key_ik(ARJ, 'R', f, world_to_rig(ARJ, nbw + Vector((-0.04, 0.0, 0.0))), (0.3, -1, -0.3), (0, 0.2, -1))
cast.key_head(ARJ, a, 40, 10); cast.key_head(ARJ, a + 30, 44, 18); cast.key_head(ARJ, a + 92, 10, 30); cast.key_head(ARJ, b, 8, 30)
cast.key_eyes(ARJ, a + 92, -16, 0)
ARJ.shape('smile', 0.3, a); ARJ.shape('smile', 0.45, a + 60)
cast.key_head(RAO, a, 4, 20); cast.key_head(RAO, a + 40, 2, 26); cast.key_head(RAO, a + 52, 2, 16); cast.key_head(RAO, a + 64, 2, 26); cast.key_head(RAO, a + 76, 0, 18)
RAO.shape('frown', 0.5, a); RAO.shape('frown', 0.0, a + 50); RAO.shape('smile', 0.0, a + 44); RAO.shape('smile', 0.7, a + 70)
cast.key_brows(RAO, a + 40, 0.2, 0.8)
# 4g: Arjun looks up from the notebook, thoughtful
a, b = SH['4g_arjun_thinks']
arjun_meet_hands(a)
cast.key_head(ARJ, a, 8, 28); cast.key_head(ARJ, a + 40, 4, 6); cast.key_head(ARJ, b, 2, 2)
cast.key_eyes(ARJ, a, -16, 0); cast.key_eyes(ARJ, a + 38, 4, 6); cast.key_eyes(ARJ, b, 6, 10)
cast.key_brows(ARJ, a, 0.2, 0.3); cast.key_brows(ARJ, b, 0.0, 0.9)
ARJ.shape('smile', 0.2, a); ARJ.shape('smile', 0.45, b)

# ============================================================ SCENE 5
a, b = SH['5a_sketch']
keyrig(ARJ, a, DESK, 180); bpy.context.view_layer.update()
pw = Vector((0.13, -0.33, OD.DESK_H + 0.025))
for f in range(a, b, 3):
    p = pw + Vector((0.05 * np.sin(f * 0.37), 0.025 * np.sin(f * 0.81), 0))
    cast.key_ik(ARJ, 'R', f, world_to_rig(ARJ, p + Vector((-0.04, 0, 0))), (0.3, -1, -0.3), (0, 0.2, -1))
cast.key_ik(ARJ, 'L', a, world_to_rig(ARJ, pw + Vector((0.18, 0.02, 0))), (-0.4, -1, -0.2), (0, 0.2, -1))
cast.key_fingers(ARJ, 'R', a, 'hold'); cast.key_fingers(ARJ, 'L', a, 'relax')
cast.key_head(ARJ, a, 6, 26); cast.key_head(ARJ, a + 70, 4, 20); cast.key_head(ARJ, a + 90, 0, 6); cast.key_head(ARJ, b, 0, 4)
cast.key_eyes(ARJ, a, -18, -4); cast.key_eyes(ARJ, a + 88, 2, 0)
cast.key_brows(ARJ, a, 0.1, 0.2); ARJ.shape('frown', 0.0, a); ARJ.shape('smile', 0.15, a); ARJ.shape('smile', 0.35, b)
a, b = SH['5c_face_engaged']
hands_on_keys(ARJ, a, b, True, 9)
cast.key_head(ARJ, a, 0, 4); cast.key_head(ARJ, a + 50, 0, 2); cast.key_head(ARJ, a + 62, 0, 7); cast.key_head(ARJ, a + 74, 0, 2)
for f in range(a, b, 6):
    cast.key_eyes(ARJ, f, 2 + rng.uniform(-2, 2), rng.uniform(-8, 8))
cast.key_brows(ARJ, a, 0.0, 0.5); ARJ.shape('smile', 0.3, a); ARJ.shape('smile', 0.6, b)
a, b = SH['5e_rao_success']
arjun_meet_hands(a)
cast.key_head(ARJ, a, 42, 12); cast.key_head(ARJ, b, 36, 8); ARJ.shape('smile', 0.6, a); ARJ.shape('smile', 0.85, b - 20)
cast.key_head(RAO, a, 0, 22); cast.key_head(RAO, a + 60, 0, 22); cast.key_head(RAO, a + 80, 16, 6); cast.key_head(RAO, b, 20, 4)
cast.key_eyes(RAO, a, -18, 0); cast.key_eyes(RAO, a + 78, -2, 20)
RAO.shape('frown', 0.0, a); RAO.shape('smile', 0.2, a); RAO.shape('smile', 0.95, a + 70)
cast.key_brows(RAO, a, 0.0, 0.5); cast.key_brows(RAO, a + 70, 0.0, 1.2)
cast.key_ik(RAO, 'L', a + 70, Vector((0.12, -0.30, 0.10)), (-0.4, -1, 0.1), (-0.3, 0, -1))
cast.key_ik(RAO, 'L', a + 84, Vector((0.16, -0.30, 0.34)), (0, 0, 1), (-1, 0, 0))   # thumbs up
cast.key_ik(RAO, 'L', b, Vector((0.16, -0.30, 0.36)), (0, 0, 1), (-1, 0, 0))
cast.key_fingers(RAO, 'L', a + 74, 'relax'); cast.key_fingers(RAO, 'L', a + 84, 'fist', thumb=(-30, -10, 0))
a, b = SH['5f_golden_wide']
hands_on_keys(ARJ, a, a + 30, False)
cast.key_ik(ARJ, 'R', a + 60, Vector((-0.05, -0.10, 0.38)), (0.2, 0.6, 0.6), (0, 1, 0)); cast.key_ik(ARJ, 'L', a + 60, Vector((0.05, -0.10, 0.38)), (-0.2, 0.6, 0.6), (0, 1, 0))
key_q(pb['spine'], a, q((1, 0, 0), 3)); key_q(pb['spine'], a + 60, q((1, 0, 0), -10)); key_q(pb['chest'], a + 60, q((1, 0, 0), -6))
cast.key_head(ARJ, a, 0, 4); cast.key_head(ARJ, a + 60, 0, -14); ARJ.shape('smile', 0.5, a); ARJ.shape('smile', 0.7, b)
cast.key_eyes(ARJ, a + 60, 10, 0)
for n in desk_shots + meet_shots:   # reset pose bits that must not drift between shots
    pass

# ------------------------------------------------------------ light per scene
for n, tod in (('2d_office_est', 'morning'), ('3a_prompt_ots', 'midday'), ('4a_test_wide', 'soft'), ('5a_sketch', 'golden'), ('5e_rao_success', 'soft'), ('5f_golden_wide', 'golden')):
    OD.key_tod(O, w, SH[n][0], tod)
pan = bpy.data.materials['OFF_PanelDay'].node_tree.nodes['Emission']
for n, v in (('2d_office_est', 3.0), ('3a_prompt_ots', 2.6), ('4a_test_wide', 2.4), ('5a_sketch', 0.7), ('5e_rao_success', 2.0), ('5f_golden_wide', 0.5)):
    pan.inputs['Strength'].default_value = v; pan.inputs['Strength'].keyframe_insert('default_value', frame=SH[n][0])
for o in (O['sun'], O['sun'].data, O['skyfill'].data, w.node_tree, bpy.data.materials['OFF_PanelDay'].node_tree):
    constant(o)

fl = bpy.data.objects.new('LGT_MeetFill', bpy.data.lights.new('LGT_MeetFill', 'AREA')); U.link(fl, setc)
fl.data.size = 1.2; fl.data.energy = 45; fl.data.color = (1.0, 0.93, 0.85); fl.visible_camera = False
fl.location = (OD.MEET.x - 0.3, OD.MEET.y + 1.3, 1.5); U.look_at(fl, (OD.MEET.x, OD.MEET.y - 0.5, 1.2))
# ------------------------------------------------------------ cameras
cams = {}
def eyes(a_, f):
    sc.frame_set(f); return a_.eyes_world()
def cam(name, lens, fstop, keys, focus_fn=None):
    c, t = AN.make_cam(name, lens, fstop)
    for f, loc, look in keys:
        AN.key_cam(c, t, f, Vector(loc), Vector(look), lens, (Vector(loc) - Vector(focus_fn(f) if focus_fn else look)).length)
    cams[name] = c
    return c
S_ = SH
f0, f1 = S_['2d_office_est']; e = eyes(ARJ, f0)
cam('CAM_2d', 26, 5.6, [(f0, (3.6, -4.3, 1.75), (0.0, -0.3, 1.0)), (f1, (3.1, -3.7, 1.65), (0.0, -0.3, 1.0))])
f0, f1 = S_['2e_desk_side']; e = eyes(ARJ, f0 + 40)
cam('CAM_2e', 34, 3.2, [(f0, (0.95, -1.35, 1.32), e + Vector((-0.1, 0.2, -0.22))), (f1, (0.85, -1.22, 1.30), e + Vector((-0.05, 0.12, -0.12)))], lambda f: eyes(ARJ, f))
f0, f1 = S_['2f_present_absent']; e = eyes(ARJ, f0)
cam('CAM_2f', 70, 2.4, [(f0, e + Vector((-0.42, 0.40, 0.02)), e), (f1, e + Vector((-0.36, 0.34, 0.02)), e)])
f0, f1 = S_['3a_prompt_ots']
cam('CAM_3a', 40, 4.0, [(f0, (-0.34, -1.10, 1.46), (0, 0.217, 1.06)), (f1, (-0.28, -0.95, 1.42), (0, 0.217, 1.08))], lambda f: Vector((0, 0.217, 1.08)))
f0, f1 = S_['3c_face_monitor']; e = eyes(ARJ, f0)
cam('CAM_3c', 65, 2.4, [(f0, e + Vector((0.22, 0.48, -0.02)), e), (f1, e + Vector((0.16, 0.36, -0.01)), e)])
f0, f1 = S_['3e_office_wide']
cam('CAM_3e', 22, 6.0, [(f0, (-3.4, -3.2, 2.35), (0.2, 0.2, 0.9)), (f1, (-4.6, -4.3, 2.6), (0.2, 0.2, 0.9))])
f0, f1 = S_['3f_doubt']; e = eyes(ARJ, f0)
cam('CAM_3f', 60, 2.0, [(f0, e + Vector((0.55, 0.15, 0.05)), e), (f0 + 60, e + Vector((0.55, 0.17, 0.02)), e + Vector((-0.12, 0.35, -0.10))),
                         (f1, e + Vector((0.50, 0.20, 0.0)), e + Vector((-0.2, 0.6, -0.22)))],
    lambda f: eyes(ARJ, f) if f < f0 + 50 else O['sticky'])
M = OD.MEET
f0, f1 = S_['4a_test_wide']
cam('CAM_4a', 30, 4.0, [(f0, (M.x + 1.6, M.y + 1.5, 1.5), (M.x - 0.2, M.y - 0.3, 0.95)), (f1, (M.x + 1.4, M.y + 1.3, 1.45), (M.x - 0.2, M.y - 0.3, 0.95))])
f0, f1 = S_['4c_rao_cu']; e = eyes(RAO, f0)
cam('CAM_4c', 75, 2.4, [(f0, e + Vector((0.75, -0.22, 0.02)), e + Vector((0, 0, -0.02))), (f1, e + Vector((0.66, -0.20, 0.02)), e + Vector((0, 0, -0.02)))], lambda f: eyes(RAO, f))
f0, f1 = S_['4d_arjun_realises']; e = eyes(ARJ, f0)
cam('CAM_4d', 75, 2.4, [(f0, e + Vector((-0.42, 0.62, 0.03)), e), (f1, e + Vector((-0.36, 0.53, 0.03)), e)], lambda f: eyes(ARJ, f))
f0, f1 = S_['4e_two_shot']; e1 = eyes(ARJ, f0); e2 = eyes(RAO, f0); mid = (e1 + e2) / 2
cam('CAM_4e', 34, 3.2, [(f0, mid + Vector((0.95, 1.05, 0.05)), mid + Vector((0, 0, -0.18))), (f1, mid + Vector((0.85, 0.92, 0.05)), mid + Vector((0, 0, -0.2)))])
f0, f1 = S_['4g_arjun_thinks']; e = eyes(ARJ, f0 + 40)
cam('CAM_4g', 70, 2.2, [(f0, e + Vector((-0.20, 0.70, 0.04)), e), (f1, e + Vector((-0.17, 0.60, 0.04)), e)], lambda f: eyes(ARJ, f))
f0, f1 = S_['5a_sketch']; e = eyes(ARJ, f0)
cam('CAM_5a', 35, 3.2, [(f0, (0.92, -0.18, 1.30), e + Vector((0.05, 0.05, -0.22))), (f1, (0.84, -0.16, 1.28), e + Vector((0, 0.0, -0.12)))], lambda f: eyes(ARJ, f))
f0, f1 = S_['5c_face_engaged']; e = eyes(ARJ, f0)
cam('CAM_5c', 65, 2.4, [(f0, e + Vector((-0.20, 0.48, 0.0)), e), (f1, e + Vector((-0.15, 0.37, 0.0)), e)])
f0, f1 = S_['5e_rao_success']; e1 = eyes(ARJ, f0); e2 = eyes(RAO, f0); mid = (e1 + e2) / 2
cam('CAM_5e', 40, 2.8, [(f0, mid + Vector((0.95, 0.85, 0.0)), mid + Vector((-0.1, 0, -0.12))), (f1, mid + Vector((0.8, 0.72, 0.0)), mid + Vector((-0.1, 0, -0.1)))], lambda f: eyes(RAO, f))
f0, f1 = S_['5f_golden_wide']
cam('CAM_5f', 26, 5.0, [(f0, (-2.2, -2.8, 1.55), (0, -0.4, 1.05)), (f1, (-2.7, -3.4, 1.7), (0, -0.4, 1.05))])
for c in ('CAM_2e', 'CAM_2f', 'CAM_3c', 'CAM_4c', 'CAM_4d', 'CAM_4g', 'CAM_5c'):
    AN.handheld(cams[c], 0.0015, 45, hash(c) % 10)
for n, a_, b_, c in FT.OFFICE:
    mk = sc.timeline_markers.new(n, frame=a_); mk.camera = cams[c]
sc.camera = cams['CAM_2d']
RS.apply(sc, 'final')
out = os.path.abspath(os.path.join(HERE, '..', '..', 'source', 'scenes02-05_office_day.blend'))
bpy.ops.wm.save_as_mainfile(filepath=out, relative_remap=True, compress=True)
print('saved', out)
