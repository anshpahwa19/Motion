"""Append library characters into a scene and pose them (shared by Scenes 2-6)."""
import os
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.abspath(os.path.join(HERE, '..', '..', 'source', 'characters'))


class Actor:
    def __init__(self, name, coll):
        self.name = name; self.coll = coll
        self.objs = {o.name: o for o in coll.all_objects if isinstance(o, bpy.types.Object)}
        self.rig = next(o for o in coll.all_objects if o.type == 'ARMATURE')
        self.pb = self.rig.pose.bones
        self.ik = {s: self.find('IK_hand.' + s) for s in 'LR'}
        self.pole = {s: self.find('Pole_elbow.' + s) for s in 'LR'}
        self.head = next(o for o in coll.all_objects if o.type == 'MESH' and o.name.endswith('_Head'))
        self.tee = next((o for o in coll.all_objects if o.name.endswith('_Tee')), None)
        self.pants = next((o for o in coll.all_objects if o.name.endswith('_Pants')), None)
        self.feet = next((o for o in coll.all_objects if o.name.endswith('_Feet')), None)
        self.eyes = [o for o in coll.all_objects if '_Eye.' in o.name and o.type == 'MESH']
        for o in (self.ik['L'], self.ik['R']):
            o.rotation_mode = 'QUATERNION'

    def find(self, prefix):
        return next(o for o in self.coll.all_objects if o.name.startswith(prefix))

    def place(self, loc, rot_z=0.0, rot=None):
        self.rig.location = loc
        self.rig.rotation_euler = rot if rot is not None else Euler((0, 0, np.radians(rot_z)))

    def eyes_world(self):
        bpy.context.view_layer.update()
        return sum((e.matrix_world.translation for e in self.eyes), Vector()) / len(self.eyes)

    def tee_color(self, hexcol):
        import bl_util as U
        m = self.tee.data.materials[0]
        mix = next(n for n in m.node_tree.nodes if n.type == 'MIX')
        c = np.array(U.hex2lin(hexcol))
        mix.inputs['A'].default_value = (*c, 1); mix.inputs['B'].default_value = (*(c * 0.72), 1)

    def pants_color(self, hexcol):
        import bl_util as U
        m = self.pants.data.materials[0]
        mix = next(n for n in m.node_tree.nodes if n.type == 'MIX')
        c = np.array(U.hex2lin(hexcol))
        mix.inputs['A'].default_value = (*c, 1); mix.inputs['B'].default_value = (*(c * 0.75), 1)

    def shape(self, name, value, frame=None):
        kb = self.head.data.shape_keys.key_blocks[name]
        kb.value = value
        if frame is not None:
            kb.keyframe_insert('value', frame=frame)


def append(name, scene=None):
    path = os.path.join(LIB, name + '.blend')
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = ['CH_' + name]
    coll = dst.collections[0]
    (scene or bpy.context.scene).collection.children.link(coll)
    return Actor(name, coll)


def q(axis, deg):
    return Quaternion(Vector(axis), np.radians(deg))


def key_q(pb, f, quat):
    pb.rotation_quaternion = quat; pb.keyframe_insert('rotation_quaternion', frame=f)


def hand_matrix(pos, fingers_dir, palm_normal):
    y = Vector(fingers_dir).normalized()
    z = Vector(palm_normal); z = (z - y * z.dot(y)).normalized()
    x = y.cross(z)
    M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = Vector(pos)
    return M


def key_ik(actor, side, f, pos, fingers, palm):
    ik = actor.ik[side]
    ik.matrix_basis = hand_matrix(pos, fingers, palm)
    ik.keyframe_insert('location', frame=f); ik.keyframe_insert('rotation_quaternion', frame=f)


CURL = {
    'relax': (14, 18, 8), 'type': (22, 30, 14), 'open': (3, 5, 2), 'point': None, 'fist': (70, 90, 60), 'hold': (30, 60, 30),
}


def key_fingers(actor, side, f, pose='relax', thumb=(0, 6, 6), point=False):
    for fn in ('index', 'middle', 'ring', 'pinky'):
        c = CURL[pose] if not (point and fn == 'index') else (2, 4, 2)
        if point and fn != 'index':
            c = (70, 90, 50)
        for i in range(3):
            key_q(actor.pb[f'f_{fn}.{i + 1:02d}.{side}'], f, q((1, 0, 0), c[i] + (5 if fn == 'pinky' else 0)))
    for i in range(3):
        key_q(actor.pb[f'f_thumb.{i + 1:02d}.{side}'], f, q((1, 0, 0), thumb[i]))


def seat(actor, f=1, lean=6, knee=88, hip=86, spread=7):
    """Seated pose on a chair (pelvis at rig origin)."""
    pb = actor.pb
    for s, sg in (('L', 1), ('R', -1)):
        key_q(pb['thigh.' + s], f, q((1, 0, 0), hip) @ q((0, 0, 1), -sg * spread))
        key_q(pb['shin.' + s], f, q((1, 0, 0), -knee))
        key_q(pb['foot.' + s], f, q((1, 0, 0), 4))
    key_q(pb['spine'], f, q((1, 0, 0), lean * 0.5))
    key_q(pb['chest'], f, q((1, 0, 0), lean * 0.5))


def breathe(actor, f0, f1, period=4.2, amp=0.05):
    br = actor.pb['breath']; ph = 0.0; f = f0
    while f <= f1:
        br.scale = Vector((1, 1 + amp * (0.5 - 0.5 * np.cos(ph)), 1)); br.keyframe_insert('scale', frame=f)
        f += 6; ph += 2 * np.pi * 6 / (period * 24)


def blinks(actor, f0, f1, rest=-7, every=(70, 130), seed=0):
    rng = np.random.default_rng(seed)
    pb = actor.pb
    def lids(f, up, lo):
        for s in 'LR':
            key_q(pb['lid_up.' + s], f, q((1, 0, 0), up)); key_q(pb['lid_lo.' + s], f, q((1, 0, 0), lo))
    lids(f0, rest, 0)
    f = f0 + int(rng.integers(20, 60))
    while f < f1 - 10:
        lids(f - 1, rest, 0); lids(f + 3, -44, 7); lids(f + 8, rest, 0)
        f += int(rng.integers(*every))
    lids(f1, rest, 0)


def key_head(actor, f, yaw=0, nod=0, roll=0):
    key_q(actor.pb['neck'], f, Euler((np.radians(nod * 0.4), np.radians(yaw * 0.4), np.radians(roll * 0.4))).to_quaternion())
    key_q(actor.pb['head'], f, Euler((np.radians(nod * 0.6), np.radians(yaw * 0.6), np.radians(roll * 0.6))).to_quaternion())


def key_eyes(actor, f, up=0, left=0):
    for s in 'LR':
        key_q(actor.pb['eye.' + s], f, Euler((np.radians(up), 0, np.radians(left))).to_quaternion())


def key_brows(actor, f, worry=0.0, raise_=0.0):
    for s, sg in (('L', -1), ('R', 1)):
        key_q(actor.pb['brow.' + s], f, q((0, 1, 0), sg * 9 * worry))
        actor.pb['brow.' + s].location = Vector((0, 0.0012 * raise_ + 0.0007 * worry, 0))
        actor.pb['brow.' + s].keyframe_insert('location', frame=f)
