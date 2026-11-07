"""Scene 1 layout: character placement + lying rest pose + set build."""
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler
import bl_util as U
import character as C
import char_body as B
import bedroom as BR

RIG_LOC = Vector((-0.30, 0.70, 0.655))
RIG_ROT = Euler((np.radians(-90), 0, 0))


def body_to_world(p):
    M = Matrix.Translation(RIG_LOC) @ RIG_ROT.to_matrix().to_4x4()
    return M @ Vector(p)


def q(axis, deg):
    return Quaternion(Vector(axis), np.radians(deg))


def hand_matrix(pos, fingers_dir, palm_normal):
    """IK target basis (rig/body space): bone Y = fingers, bone Z = palm normal."""
    y = Vector(fingers_dir).normalized()
    z = Vector(palm_normal); z = (z - y * z.dot(y)).normalized()
    x = y.cross(z)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = Vector(pos)
    return M


REST_POSE = {
    'chest': q((1, 0, 0), 6), 'neck': q((1, 0, 0), 16), 'head': q((1, 0, 0), 10),
}
LEFT_HAND_ON_BELLY = dict(pos=(0.05, -0.125, 0.20), fingers=(-0.85, -0.1, -0.35), palm=(0, 1, 0.1))


def pose_rest(rig, ctrl):
    pb = rig.pose.bones
    for n, qq in REST_POSE.items():
        pb[n].rotation_quaternion = qq
    ik = ctrl['IK_hand.L']
    ik.matrix_basis = hand_matrix(LEFT_HAND_ON_BELLY['pos'], LEFT_HAND_ON_BELLY['fingers'], LEFT_HAND_ON_BELLY['palm'])
    ctrl['Pole_elbow.L'].location = Vector((0.45, 0.05, 0.25))
    # right arm relaxed beside body, slightly away
    R = ctrl['IK_hand.R']
    R.matrix_basis = hand_matrix((-0.27, 0.065, -0.03), (-0.05, 0.1, -1), (1, 0, 0))
    ctrl['Pole_elbow.R'].location = Vector((-0.5, 0.2, 0.2))
    # relaxed finger curl
    for s in 'LR':
        for f in ('index', 'middle', 'ring', 'pinky'):
            for i, a in enumerate((14, 18, 8)):
                pb[f'f_{f}.{i + 1:02d}.{s}'].rotation_quaternion = q((1, 0, 0), a + (6 if f == 'pinky' else 0))


def body_top_fn(X, Y):
    """Top surface (world z) of the hidden legs/hips/belly under the blanket."""
    segs = [  # body-space capsules (a, b, ra, rb)
        ((0.09, 0.03, -0.02), (0.11, 0.035, -0.46), 0.08, 0.058),
        ((0.11, 0.035, -0.46), (0.12, 0.04, -0.86), 0.055, 0.042),
        ((-0.09, 0.03, -0.02), (-0.13, 0.035, -0.46), 0.08, 0.058),
        ((-0.13, 0.035, -0.46), (-0.16, 0.04, -0.86), 0.055, 0.042),
        ((0.0, 0.01, 0.0), (0.0, 0.0, 0.26), 0.125, 0.12),
        ((0.12, 0.04, -0.89), (0.13, -0.07, -0.92), 0.035, 0.028),   # feet up
        ((-0.16, 0.04, -0.89), (-0.17, -0.07, -0.92), 0.035, 0.028),
    ]
    Z = np.full(X.shape, -1.0)
    P2 = np.stack([X, Y], -1)
    for a, b, ra, rb in segs:
        A = np.array(body_to_world(a)); Bv = np.array(body_to_world(b))
        ab = Bv[:2] - A[:2]; L2 = max(ab @ ab, 1e-9)
        t = np.clip(((P2 - A[:2]) @ ab) / L2, 0, 1)
        C2 = A[:2] + t[..., None] * ab
        cz = A[2] + t * (Bv[2] - A[2])
        r = ra + t * (rb - ra)
        d2 = ((P2 - C2) ** 2).sum(-1)
        Z = np.maximum(Z, np.where(d2 < r * r, cz + np.sqrt(np.maximum(r * r - d2, 0)), -1))
    return Z


def build(frames, lod=1.0, hair=True):
    sc = bpy.context.scene
    cc = U.collection('CH_Arjun'); sc_set = U.collection('SET_Bedroom')
    objs = C.build_arjun(cc, hair=hair, lod=lod)
    rig = objs['rig']
    rig.location = RIG_LOC; rig.rotation_euler = RIG_ROT
    pose_rest(rig, objs['ctrl'])
    bpy.context.view_layer.update()
    # back of the skull -> pillow dent
    hb = rig.matrix_world @ rig.pose.bones['head'].matrix
    occ = hb @ Vector((0, 0.07, 0.10))      # bone space: y along bone (up the head), z = forward
    occ = rig.matrix_world @ rig.pose.bones['head'].head
    head_c = rig.matrix_world @ (rig.pose.bones['head'].matrix @ Vector((0, 0.08, 0.0)))
    dent = ((head_c.x, head_c.y, head_c.z - 0.02), (0.13, 0.15, 0.10))
    set_objs = BR.build_bedroom(sc_set, frames, body_top_fn, dent)
    return objs, set_objs
