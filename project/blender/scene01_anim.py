"""Scene 1 performance + cameras (bedroom shots).

All acting is keyed on rig controls defined in character.py. The phone's
world path is authored with keyframe 'poses' + easing, then baked per frame;
the right-hand IK target is derived from the phone every frame so the grip
never slips.
"""
import sys, os
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler
import bl_util as U
import scene01_layout as LY
import bedroom as BR
import character as C
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config'))
import scene01_timing as T

q = LY.q


def ease(t, kind='io'):
    t = min(max(t, 0.0), 1.0)
    if kind == 'io':
        return t * t * (3 - 2 * t)
    if kind == 'o':
        return 1 - (1 - t) ** 3
    if kind == 'i':
        return t ** 3
    return t


# --------------------------------------------------------------- key helpers
def kq(pb, f, quat):
    pb.rotation_quaternion = quat
    pb.keyframe_insert('rotation_quaternion', frame=f)


def kloc(pb, f, v):
    pb.location = v
    pb.keyframe_insert('location', frame=f)


def kscale(pb, f, v):
    pb.scale = v
    pb.keyframe_insert('scale', frame=f)


def eul(x=0, y=0, z=0):
    return Euler((np.radians(x), np.radians(y), np.radians(z))).to_quaternion()


def all_fcurves(idblock):
    ad = idblock.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, 'fcurves') and len(getattr(act, 'fcurves', [])):
        return list(act.fcurves)
    out = []
    for layer in getattr(act, 'layers', []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def set_interp(idblock, kind='LINEAR', path_contains=None):
    for fc in all_fcurves(idblock):
        if path_contains and path_contains not in fc.data_path:
            continue
        for kp in fc.keyframe_points:
            kp.interpolation = kind


# --------------------------------------------------------------- phone grips
def grip_B():
    """Hand bone matrix in phone space while holding it (portrait, right hand)."""
    y = Vector((-0.86, 0.51, 0.0)).normalized()
    z = Vector((0, 0, 1.0))
    x = y.cross(z)
    M = Matrix((x, y, z)).transposed().to_4x4()
    palm_c = Vector((0.034, -0.038, -0.0190))
    M.translation = palm_c - y * 0.052 - z * 0.002
    return M


def grip_D():
    return Matrix.Rotation(np.radians(-90), 4, 'Y') @ grip_B()


def mlerp(A, B, t):
    la, ra, _ = A.decompose(); lb, rb, _ = B.decompose()
    return Matrix.LocRotScale(la.lerp(lb, t), ra.slerp(rb, t), None)


def phone_mat(loc, screen_n, top):
    z = Vector(screen_n).normalized()
    y = Vector(top); y = (y - z * y.dot(z)).normalized()
    x = y.cross(z)
    M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = Vector(loc)
    return M


# --------------------------------------------------------------- finger poses
CURL = {
    'relax': {'index': (14, 18, 8), 'middle': (14, 18, 8), 'ring': (15, 19, 8), 'pinky': (20, 22, 10), 'thumb': (0, 6, 6)},
    'open': {'index': (2, 4, 2), 'middle': (2, 4, 2), 'ring': (3, 5, 3), 'pinky': (5, 6, 3), 'thumb': (-8, 0, 0)},
    'pinch': {'index': (35, 45, 25), 'middle': (40, 50, 25), 'ring': (45, 52, 25), 'pinky': (50, 55, 25), 'thumb': (10, 15, 15)},
    'hold': {'index': (4, 40, 34), 'middle': (5, 42, 34), 'ring': (7, 42, 32), 'pinky': (10, 40, 30), 'thumb': (16, 10, 12)},
    'chest': {'index': (8, 12, 6), 'middle': (8, 12, 6), 'ring': (10, 14, 6), 'pinky': (14, 16, 8), 'thumb': (0, 4, 4)},
}


def key_fingers(pb, side, f, pose, thumb_extra=(0, 0, 0)):
    P = CURL[pose]
    for fn in ('index', 'middle', 'ring', 'pinky', 'thumb'):
        for i in range(3):
            a = P[fn][i] + (thumb_extra[i] if fn == 'thumb' else 0)
            kq(pb[f'f_{fn}.{i + 1:02d}.{side}'], f, q((1, 0, 0), a))


# --------------------------------------------------------------- face helpers
LID_REST = -7           # tired: lowered upper lids
LID_CLOSED = -46
LOW_REST = 0
LOW_CLOSED = 9


def key_lids(pb, f, up, lo=None, sides='LR'):
    for s in sides:
        kq(pb['lid_up.' + s], f, q((1, 0, 0), up))
        if lo is not None:
            kq(pb['lid_lo.' + s], f, q((1, 0, 0), lo))


def blink(pb, f, base=LID_REST, dur=(3, 5)):
    key_lids(pb, f - 1, base, LOW_REST)
    key_lids(pb, f + dur[0], LID_CLOSED + 2, LOW_CLOSED - 2)
    key_lids(pb, f + dur[0] + dur[1], base, LOW_REST)


def key_eyes(pb, f, up=0, left=0):
    for s in 'LR':
        kq(pb['eye.' + s], f, eul(up, 0, left))


def key_brows(pb, f, worry=0.0, raise_=0.0):
    """worry: inner brows up/knit (0..1); raise_: both brows up (mm-ish)."""
    for s, sg in (('L', -1), ('R', 1)):
        kq(pb['brow.' + s], f, q((0, 1, 0), sg * 9 * worry))
        kloc(pb['brow.' + s], f, Vector((0, 0.0012 * raise_ + 0.0007 * worry, 0)))


def key_head(pb, f, yaw=0, nod=0, roll=0):
    """yaw + = towards his left (+X world). nod + = chin to chest."""
    base_n = LY.REST_POSE['neck']; base_h = LY.REST_POSE['head']
    kq(pb['neck'], f, base_n @ eul(nod * 0.4, yaw * 0.4, roll * 0.4))
    kq(pb['head'], f, base_h @ eul(nod * 0.6, yaw * 0.6, roll * 0.6))


# --------------------------------------------------------------- main
def animate(objs, setobjs, phone, screen_light, screen_mat):
    sc = bpy.context.scene
    rig = objs['rig']; pb = rig.pose.bones; ctrl = objs['ctrl']
    RW = rig.matrix_world.copy(); RWi = RW.inverted()

    # ---------------- breathing (whole timeline), anxious breathing gets faster
    br = pb['breath']
    f = 1; ph = 0.0
    while f <= 640:
        period = 4.6 * 24 if f < 260 else 3.4 * 24
        amp = 0.045 if f < 300 else 0.06
        if 520 <= f <= 560:
            period, amp = 40, 0.12        # the deep breath after waking
        kscale(br, f, Vector((1, 1 + amp * (0.5 - 0.5 * np.cos(ph)), 1)))
        f += 6; ph += 2 * np.pi * 6 / period
    kq(pb['chest'], 1, LY.REST_POSE['chest'])
    kq(pb['chest'], 522, LY.REST_POSE['chest'])
    kq(pb['chest'], 534, LY.REST_POSE['chest'] @ eul(-3, 0, 0))   # gasp lifts chest
    kq(pb['chest'], 560, LY.REST_POSE['chest'])

    # ---------------- head
    key_head(pb, 1, 0, 0)
    key_head(pb, 60, -2, 0, 1)                 # tiny settle while staring
    key_head(pb, 106, -2, 0, 1)
    key_head(pb, 121, -34, 3, -4)              # turns to the glowing phone
    key_head(pb, 140, -20, 6)
    key_head(pb, 152, -6, 10)                  # looks at the phone above him
    key_head(pb, 300, -5, 11)
    key_head(pb, 360, -5, 12)
    key_head(pb, 372, -14, 6)                  # follows the phone towards the table
    key_head(pb, 390, -26, 3)
    key_head(pb, 398, -22, 2)
    key_head(pb, 414, 36, 0, 5)                # turns away
    key_head(pb, 520, 37, 0, 5)
    key_head(pb, 524, 34, -1, 4)               # startle
    key_head(pb, 552, 4, 0, 0)                 # back to the ceiling
    key_head(pb, 640, 2, 0, 0)

    # ---------------- eyes (gaze)
    key_eyes(pb, 1, 4, 0)
    key_eyes(pb, 30, 4, 2); key_eyes(pb, 33, 3, -3); key_eyes(pb, 70, 3, -3); key_eyes(pb, 73, 5, 1)
    key_eyes(pb, 101, 5, 1); key_eyes(pb, 104, -6, -24)       # eyes flick to the light first
    key_eyes(pb, 118, -10, -12); key_eyes(pb, 132, -14, -6)
    key_eyes(pb, 150, -20, -4)
    # reading saccades (left->right sweeps, line drops)
    fr = 152; up0 = -18
    for i in range(16):
        key_eyes(pb, fr, up0 - (i % 4) * 1.2, -9); fr += 4
        key_eyes(pb, fr, up0 - (i % 4) * 1.2, 2); fr += 6
        if fr > 268:
            break
    key_eyes(pb, 285, -19, -3)                  # lands on headline 3
    key_eyes(pb, 300, -19, -3); key_eyes(pb, 330, -19.5, -3.5); key_eyes(pb, 360, -19, -3)
    key_eyes(pb, 368, -16, -8); key_eyes(pb, 384, -12, -22); key_eyes(pb, 398, -6, -10)
    key_eyes(pb, 408, 2, 14)
    key_eyes(pb, 518, 2, 14); key_eyes(pb, 521, 6, 4)          # snap open
    key_eyes(pb, 540, 8, 2); key_eyes(pb, 556, 10, 0); key_eyes(pb, 600, 10, -1); key_eyes(pb, 640, 10, 0)

    # ---------------- lids
    key_lids(pb, 1, LID_REST, LOW_REST)
    blink(pb, 44); blink(pb, 88)
    blink(pb, 103, LID_REST, (2, 4))             # light hits his eyes
    key_lids(pb, 126, LID_REST + 2, LOW_REST)
    blink(pb, 170); blink(pb, 232)
    key_lids(pb, 262, LID_REST - 2, LOW_REST + 1)
    key_lids(pb, 300, LID_REST - 4, LOW_REST + 1)     # heavy, tired lids
    blink(pb, 343, LID_REST - 4, (5, 8))              # one slow, heavy blink
    key_lids(pb, 360, LID_REST - 5, LOW_REST + 1.5)
    blink(pb, 378, LID_REST - 3)
    key_lids(pb, 406, LID_REST - 4, LOW_REST + 1)
    key_lids(pb, 416, LID_CLOSED, LOW_CLOSED)         # closes his eyes
    key_lids(pb, 518, LID_CLOSED, LOW_CLOSED)
    key_lids(pb, 521, LID_REST + 7, LOW_REST - 2)     # eyes snap open wide
    key_lids(pb, 548, LID_REST + 2, LOW_REST)
    key_lids(pb, 575, LID_REST - 1, LOW_REST)
    blink(pb, 588, LID_REST - 1, (4, 7))
    key_lids(pb, 640, LID_REST - 2, LOW_REST)

    # ---------------- brows (curiosity -> concern -> fear)
    key_brows(pb, 1, 0.25, 0)
    key_brows(pb, 100, 0.25, 0); key_brows(pb, 110, 0.1, 1.2)       # curiosity
    key_brows(pb, 200, 0.15, 1.0)
    key_brows(pb, 240, 0.35, 0.6)
    key_brows(pb, 264, 0.6, 0.2)
    key_brows(pb, 300, 0.75, 0.0); key_brows(pb, 360, 1.0, 0.0)      # concern
    key_brows(pb, 410, 0.9, 0.0); key_brows(pb, 418, 1.1, -0.6)      # squeeze
    key_brows(pb, 518, 1.1, -0.6); key_brows(pb, 521, 0.9, 2.0)      # startle
    key_brows(pb, 560, 0.7, 0.4); key_brows(pb, 640, 0.6, 0.2)

    # ---------------- left hand on belly: tiny finger tension
    key_fingers(pb, 'L', 1, 'relax')
    key_fingers(pb, 'L', 300, 'relax')
    key_fingers(pb, 'L', 340, 'pinch')        # anxious grip on the sheet/tee
    key_fingers(pb, 'L', 420, 'relax')
    key_fingers(pb, 'L', 518, 'relax'); key_fingers(pb, 'L', 526, 'pinch'); key_fingers(pb, 'L', 570, 'relax')

    # ---------------- phone path (world) and right-hand IK
    bpy.context.view_layer.update()
    P_bed = phone_mat((-0.66, 1.00, 0.561), (0, 0, 1), (0.25, 1, 0))
    # eyes position (world) at the reading pose -> phone faces them
    sc.frame_set(200)
    eyes = eyes_world(rig, sc)
    P_hold = phone_mat((-0.37, 1.13, 1.02), eyes - Vector((-0.37, 1.13, 1.02)), (0.12, 1, 0.35))
    P_hold2 = phone_mat((-0.365, 1.15, 1.00), eyes - Vector((-0.365, 1.15, 1.00)), (0.12, 1, 0.35))
    P_low = phone_mat((-0.45, 1.05, 0.86), eyes - Vector((-0.45, 1.05, 0.86)) + Vector((0, 0, -0.1)), (0.1, 1, 0.2))
    P_table = phone_mat((-0.90, 1.30, BR.TABLE['h'] + 0.0042), (0, 0, 1), (0.15, 1, 0))
    P_tab_hover = Matrix.Translation((0.02, 0, 0.05)) @ P_table
    GB, GD = grip_B(), grip_D()
    R_rest = ctrl['IK_hand.R'].matrix_basis.copy()                      # rig space
    R_chest = LY.hand_matrix((-0.10, -0.115, 0.27), (0.8, -0.1, 0.45), (0, 1, 0.15))
    R_reach = RWi @ (P_bed @ GD) @ Matrix.Translation((0, 0, 0))
    R_hover = RWi @ (Matrix.Translation((0, 0, 0.05)) @ P_bed @ GD)

    phone_keys = [  # (frame, matrix, grip_t (0=D,1=B))
        (1, P_bed, 0), (T.PICKUP, P_bed, 0),
        (T.PICKUP + 4, Matrix.Translation((0.03, 0.02, 0.06)) @ P_bed, 0.1),
        (148, P_hold, 1.0), (265, P_hold, 1.0), (285, P_hold2, 1.0), (361, P_hold2, 1.0),
        (372, P_low, 0.8), (386, P_tab_hover, 0.05), (T.PUTDOWN, P_table, 0.0), (640, P_table, 0.0),
    ]

    def phone_at(f):
        for (fa, Ma, ga), (fb, Mb, gb) in zip(phone_keys[:-1], phone_keys[1:]):
            if fa <= f <= fb:
                t = ease((f - fa) / max(fb - fa, 1))
                M = mlerp(Ma, Mb, t); g = ga + (gb - ga) * t
                return M, g
        return phone_keys[-1][1], phone_keys[-1][2]

    rng = np.random.default_rng(5)
    wob = rng.normal(0, 1, (6, 4))
    ik = ctrl['IK_hand.R']
    prev_q = [None, None]
    for f in range(1, 641):
        M, g = phone_at(f)
        if 150 <= f <= 365:   # hand-held drift (very small)
            tt = f / 24
            d = Vector([0.0025 * np.sin(tt * (0.7 + 0.3 * wob[i, 0]) + wob[i, 1]) for i in range(3)])
            r = Euler([np.radians(0.8 * np.sin(tt * (0.9 + 0.3 * wob[i + 3, 0]) + wob[i + 3, 1])) for i in range(3)])
            M = Matrix.Translation(d) @ M @ r.to_matrix().to_4x4()
        phone.matrix_world = M
        qq = phone.rotation_quaternion.copy()
        if prev_q[0] is not None and qq.dot(prev_q[0]) < 0:
            qq.negate(); phone.rotation_quaternion = qq
        prev_q[0] = qq.copy()
        phone.keyframe_insert('location', frame=f); phone.keyframe_insert('rotation_quaternion', frame=f)
        grip = mlerp(GD, GB, g)
        if f < 116:
            H = R_rest
        elif f < T.PICKUP - 6:
            H = mlerp(R_rest, R_hover, ease((f - 116) / (T.PICKUP - 6 - 116)))
        elif f < T.PICKUP:
            H = mlerp(R_hover, RWi @ (M @ grip), ease((f - (T.PICKUP - 6)) / 6))
        elif f <= T.PUTDOWN:
            H = RWi @ (M @ grip)
        elif f <= T.PUTDOWN + 5:
            H = mlerp(RWi @ (P_table @ GD), RWi @ (P_tab_hover @ GD), ease((f - T.PUTDOWN) / 5))
        else:
            H = mlerp(RWi @ (P_tab_hover @ GD), R_chest, ease((f - T.PUTDOWN - 5) / 22))
        ik.matrix_basis = H
        qq = ik.rotation_quaternion.copy()
        if prev_q[1] is not None and qq.dot(prev_q[1]) < 0:
            qq.negate(); ik.rotation_quaternion = qq
        prev_q[1] = qq.copy()
        ik.keyframe_insert('location', frame=f); ik.keyframe_insert('rotation_quaternion', frame=f)
    set_interp(phone, 'LINEAR'); set_interp(ik, 'LINEAR')
    ctrl['Pole_elbow.R'].location = Vector((-0.55, 0.30, 0.0))
    ctrl['Pole_elbow.R'].keyframe_insert('location', frame=1)
    ctrl['Pole_elbow.R'].location = Vector((-0.45, 0.35, 0.1)); ctrl['Pole_elbow.R'].keyframe_insert('location', frame=150)
    ctrl['Pole_elbow.R'].keyframe_insert('location', frame=365)
    ctrl['Pole_elbow.R'].location = Vector((-0.5, 0.2, 0.3)); ctrl['Pole_elbow.R'].keyframe_insert('location', frame=395)

    # right fingers
    key_fingers(pb, 'R', 1, 'relax'); key_fingers(pb, 'R', 116, 'relax')
    key_fingers(pb, 'R', 126, 'open'); key_fingers(pb, 'R', T.PICKUP, 'pinch')
    key_fingers(pb, 'R', 148, 'hold')
    # thumb scroll gestures (thumb.02/.03 extend then flex while the feed scrolls)
    def thumb_swipe(f0, f1):
        key_fingers(pb, 'R', f0 - 3, 'hold')
        key_fingers(pb, 'R', f0, 'hold', (6, -10, -14))
        key_fingers(pb, 'R', f1, 'hold', (14, 20, 26))
        key_fingers(pb, 'R', f1 + 4, 'hold', (8, 6, 6))
    thumb_swipe(T.PHONE_UNLOCK - 3, T.PHONE_UNLOCK + 4)
    thumb_swipe(*T.SCROLL_1)
    thumb_swipe(T.SCROLL_2[0], T.SCROLL_2[1] - 2)
    key_fingers(pb, 'R', 300, 'hold', (8, 6, 6))
    key_fingers(pb, 'R', 360, 'hold', (10, 8, 8))
    key_fingers(pb, 'R', 386, 'pinch'); key_fingers(pb, 'R', T.PUTDOWN + 1, 'pinch')
    key_fingers(pb, 'R', T.PUTDOWN + 6, 'open'); key_fingers(pb, 'R', T.PUTDOWN + 24, 'chest')

    # ---------------- phone screen + light
    em = screen_mat.node_tree.nodes['ScreenEmit']
    for f, e, l in ((1, 0, 0), (T.PHONE_ON - 1, 0, 0), (T.PHONE_ON + 3, 1.0, 2.0), (T.PHONE_UNLOCK, 1.0, 2.0),
                    (T.PHONE_UNLOCK + 8, 1.1, 3.0), (T.PHONE_LOCK - 1, 1.1, 3.0), (T.PHONE_LOCK, 0, 0)):
        em.inputs['Strength'].default_value = e; em.inputs['Strength'].keyframe_insert('default_value', frame=f)
        screen_light.data.energy = l; screen_light.data.keyframe_insert('energy', frame=f)
    set_interp(screen_mat.node_tree, 'LINEAR'); set_interp(screen_light.data, 'LINEAR')
    return dict(P_bed=P_bed, P_hold=P_hold, eyes=eyes)


def head_point(rig, local):
    """World position of a head-local (char_head) point at the current frame."""
    from char_body import J, HEAD_ORIGIN
    hs = C.HS
    x, y, z = local
    body_rest = Vector(HEAD_ORIGIN) + Vector((hs * x, hs * y, hs * z))
    pbh = rig.pose.bones['head']
    rest_inv = pbh.bone.matrix_local.inverted()
    return rig.matrix_world @ (pbh.matrix @ (rest_inv @ body_rest))


def eyes_world(rig, sc=None):
    bpy.context.view_layer.update()
    a = bpy.data.objects['ARJ_Eye.L'].matrix_world.translation
    b = bpy.data.objects['ARJ_Eye.R'].matrix_world.translation
    return (a + b) / 2


# --------------------------------------------------------------- cameras
def make_cam(name, lens, fstop=None, sensor=36):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name)); U.link(cam, U.collection('CAMERAS'))
    cam.data.lens = lens; cam.data.sensor_width = sensor
    cam.data.clip_start = 0.01
    if fstop:
        cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = fstop
        cam.data.dof.aperture_blades = 7
    tgt = bpy.data.objects.new(name + '_tgt', None); U.link(tgt, U.collection('CAMERAS'))
    c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    return cam, tgt


def key_cam(cam, tgt, f, loc, look, lens=None, focus=None):
    cam.location = loc; cam.keyframe_insert('location', frame=f)
    tgt.location = look; tgt.keyframe_insert('location', frame=f)
    if lens:
        cam.data.lens = lens; cam.data.keyframe_insert('lens', frame=f)
    if focus is not None:
        cam.data.dof.focus_distance = focus; cam.data.dof.keyframe_insert('focus_distance', frame=f)


def track_eyes(cam, tgt, f0, f1, at, step=4, offset=None, focus=True):
    """Re-key the aim target (and focus) on the eyes every `step` frames."""
    for f in list(range(f0, f1, step)) + [f1]:
        e = at(f)
        if offset is not None:
            e = e + offset
        tgt.location = e; tgt.keyframe_insert('location', frame=f)
        if focus:
            bpy.context.scene.frame_set(f)
            cam.data.dof.focus_distance = (cam.matrix_world.translation - e).length
            cam.data.dof.keyframe_insert('focus_distance', frame=f)


def face_frame(rig, f):
    sc = bpy.context.scene
    sc.frame_set(f); bpy.context.view_layer.update()
    e = eyes_world(rig)
    up = (head_point(rig, (0, -0.06, 0.07)) - head_point(rig, (0, -0.06, -0.07))).normalized()
    fwd = (head_point(rig, (0, -0.2, 0)) - head_point(rig, (0, 0, 0))).normalized()
    left = up.cross(fwd).normalized() * -1
    left = (head_point(rig, (0.1, 0, 0)) - head_point(rig, (-0.1, 0, 0))).normalized()
    return e, up, fwd, left


def aim_cam(cam, frames, pos_fn, rig, lens_fn=None):
    """Key camera transform so it looks at the eyes with the head's up axis
    as screen-up (keeps the eye line level although he is lying down)."""
    cam.rotation_mode = 'QUATERNION'
    prev = None
    for f in frames:
        e, up, fwd, left = face_frame(rig, f)
        loc = pos_fn(f, e, up, fwd, left)
        z = (loc - e).normalized()
        x = up.cross(z).normalized(); y = z.cross(x)
        qq = Matrix((x, y, z)).transposed().to_quaternion()
        if prev is not None and qq.dot(prev) < 0:
            qq.negate()
        prev = qq
        cam.location = loc; cam.rotation_quaternion = qq
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_quaternion', frame=f)
        cam.data.dof.focus_distance = (loc - e).length - 0.012
        cam.data.dof.keyframe_insert('focus_distance', frame=f)
        if lens_fn:
            cam.data.lens = lens_fn(f); cam.data.keyframe_insert('lens', frame=f)


def plain_cam(name, lens, fstop):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name)); U.link(cam, U.collection('CAMERAS'))
    cam.data.lens = lens; cam.data.clip_start = 0.01
    cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = fstop; cam.data.dof.aperture_blades = 7
    return cam


def handheld(cam, amp=0.004, scale=40, seed=0):
    for fc in all_fcurves(cam):
        if fc.data_path == 'location':
            m = fc.modifiers.new('NOISE'); m.strength = amp; m.scale = scale; m.phase = seed + fc.array_index * 7.3


def cameras(objs, setobjs, phone, info):
    sc = bpy.context.scene
    rig = objs['rig']
    cams = {}

    def at(f, local=None):
        sc.frame_set(f); bpy.context.view_layer.update()
        return eyes_world(rig) if local is None else head_point(rig, local)

    def eye(f, side):
        sc.frame_set(f); bpy.context.view_layer.update()
        return bpy.data.objects['ARJ_Eye.' + side].matrix_world.translation.copy()

    def dist(a, b):
        return (Vector(a) - Vector(b)).length

    # S1 — wide establishing, slow push in
    cam, tgt = make_cam('CAM_S1', 24, 4.0)
    face = at(48)
    key_cam(cam, tgt, 1, (1.45, -1.55, 1.78), (-0.42, 0.95, 0.72), 24, dist((1.45, -1.55, 1.78), face))
    key_cam(cam, tgt, 96, (1.08, -0.82, 1.58), (-0.40, 1.02, 0.74), 25, dist((1.08, -0.82, 1.58), face))
    for fc in all_fcurves(cam) + all_fcurves(tgt):
        for kp in fc.keyframe_points: kp.interpolation = 'SINE'
    cams['CAM_S1'] = cam

    # S2a — low angle across the bed from the window side, phone in foreground
    cam, tgt = make_cam('CAM_S2a', 30, 2.4)
    f1 = at(110)
    c0 = Vector((-1.06, 0.50, 0.80))
    key_cam(cam, tgt, 97, c0, f1 * 0.55 + Vector((-0.66, 1.0, 0.56)) * 0.45, 30, dist(c0, f1))
    f2 = at(150)
    c1 = Vector((-1.06, 0.55, 0.80))
    key_cam(cam, tgt, 150, c1, f2 * 0.8 + Vector((-0.37, 1.13, 1.02)) * 0.2, 30, dist(c1, f2))
    handheld(cam, 0.003, 50, 1)
    cams['CAM_S2a'] = cam

    # S2b / S3b — over-his-shoulder POV onto the screen
    sc.frame_set(200)
    ph = phone.matrix_world.copy()
    scr_c = ph @ Vector((0, 0, 0)); scr_n = (ph.to_3x3() @ Vector((0, 0, 1))).normalized()
    eyes = at(200)
    pov = eyes + (scr_c - eyes) * 0.12 + Vector((-0.07, 0.02, 0.025))
    cam, tgt = make_cam('CAM_S2b', 50, 5.0)
    key_cam(cam, tgt, 151, pov + Vector((0.01, 0.02, 0.01)), scr_c, 48, dist(pov, scr_c))
    key_cam(cam, tgt, 216, pov, scr_c + Vector((0, 0.005, 0)), 52, dist(pov, scr_c))
    handheld(cam, 0.0015, 30, 2)
    cams['CAM_S2b'] = cam
    cam, tgt = make_cam('CAM_S3b', 55, 6.3)
    key_cam(cam, tgt, 265, pov, scr_c + Vector((0, 0.008, 0)), 55, dist(pov, scr_c))
    key_cam(cam, tgt, 300, pov + (scr_c - pov) * 0.08, scr_c + Vector((0, 0.016, 0)), 66, dist(pov, scr_c) * 0.92)
    handheld(cam, 0.001, 30, 3)
    cams['CAM_S3b'] = cam

    # S3a — face close-up from beside the phone, lit by the screen
    cam, tgt = make_cam('CAM_S3a', 34, 2.4)
    e = at(240)
    sc.frame_set(240); pc = phone.matrix_world.translation.copy()
    c0 = pc + Vector((0.075, 0.035, 0.03)); c1 = pc + Vector((0.065, 0.045, 0.0)) + (e - pc) * 0.12
    key_cam(cam, tgt, 217, c0, e, 34, dist(c0, e))
    key_cam(cam, tgt, 264, c1, e, 38, dist(c1, e))
    track_eyes(cam, tgt, 217, 264, at)
    handheld(cam, 0.0015, 40, 4)
    cams['CAM_S3a'] = cam

    # S3c — extreme close-up of the eyes, slow push (face-relative, eye line level)
    cam = plain_cam('CAM_S3c', 70, 3.5)
    e0, up0, fwd0, left0 = face_frame(rig, 301)
    base = e0 + fwd0 * 0.36 + left0 * 0.12 + up0 * 0.08
    pend = e0 + fwd0 * 0.29 + left0 * 0.10 + up0 * 0.065
    aim_cam(cam, list(range(301, 361, 6)) + [360],
            lambda f, e, up, fwd, left: base.lerp(pend, (f - 301) / 59), rig,
            lambda f: 68 + 14 * (f - 301) / 59)
    handheld(cam, 0.0006, 50, 5)
    cams['CAM_S3c'] = cam

    # S4a — from the empty side of the bed: phone goes to the table, he turns to us
    cam, tgt = make_cam('CAM_S4a', 34, 2.8)
    f3 = at(380)
    key_cam(cam, tgt, 361, (0.55, 1.02, 1.30), (-0.52, 1.30, 0.78), 34, dist((0.55, 1.02, 1.30), f3))
    f4 = at(416)
    key_cam(cam, tgt, 420, (0.42, 1.12, 1.18), (-0.38, 1.33, 0.76), 38, dist((0.42, 1.12, 1.18), f4))
    handheld(cam, 0.002, 60, 6)
    cams['CAM_S4a'] = cam

    # S5a — close-up, eyes snap open (face turned towards +X / camera), he rolls back
    cam = plain_cam('CAM_S5a', 75, 2.8)
    e0, up0, fwd0, left0 = face_frame(rig, 518)
    p0 = e0 + fwd0 * 0.30 + up0 * 0.04 + left0 * 0.03
    aim_cam(cam, list(range(517, 561, 3)) + [560], lambda f, e, up, fwd, left: p0 + (fwd0 * 0.03 + up0 * 0.02) * (f - 517) / 43, rig)
    handheld(cam, 0.001, 35, 7)
    cams['CAM_S5a'] = cam

    # S5b — clock sharp in the foreground: still 2:17. He lies awake behind it.
    cam, tgt = make_cam('CAM_S5b', 45, 1.8)
    ck = BR.CLOCK_POS + Vector((0, 0, 0.03))
    e5 = at(575)
    c0 = Vector((-0.08, 1.02, 0.94)); c1 = Vector((-0.07, 1.05, 0.93))
    look0 = ck * 0.7 + e5 * 0.3; look1 = ck * 0.6 + e5 * 0.4
    key_cam(cam, tgt, 561, c0, look0, 45, dist(c0, ck))
    key_cam(cam, tgt, 576, c0 + (c1 - c0) * 0.45, look0 * 0.55 + look1 * 0.45, 45, dist(c0, ck))
    key_cam(cam, tgt, 588, c0 + (c1 - c0) * 0.8, look0 * 0.2 + look1 * 0.8, 46, dist(c1, e5))
    key_cam(cam, tgt, 594, c1, look1, 46, dist(c1, e5))
    cams['CAM_S5b'] = cam

    # S5c — top-down through the turning fan blades, pull back (zoom out)
    cam = bpy.data.objects.new('CAM_S5c', bpy.data.cameras.new('CAM_S5c')); U.link(cam, U.collection('CAMERAS'))
    cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 3.5; cam.data.clip_start = 0.01
    f5 = at(610)
    cam.location = (-0.42, 1.16, 2.86); cam.rotation_euler = (0, 0, np.radians(8))
    cam.data.dof.focus_distance = 2.86 - f5.z
    cam.data.lens = 38; cam.data.keyframe_insert('lens', frame=595)
    cam.data.lens = 22; cam.data.keyframe_insert('lens', frame=636)
    cam.keyframe_insert('rotation_euler', frame=595)
    cam.rotation_euler = (0, 0, np.radians(2)); cam.keyframe_insert('rotation_euler', frame=636)
    cams['CAM_S5c'] = cam

    # camera switching markers
    for name, first, last, scene, camname, _ in T.SHOTS:
        if scene == 'Bedroom' and camname in cams:
            m = sc.timeline_markers.new(name, frame=first); m.camera = cams[camname]
    sc.camera = cams['CAM_S1']
    return cams
