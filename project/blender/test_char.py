import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import bpy, numpy as np
import bl_util as U
import character as C
from mathutils import Vector, Quaternion
U.reset()
sc = bpy.context.scene
t = time.time()
o = C.build_arjun(sc.collection, hair=os.environ.get('HAIR', '1') == '1', lod=float(os.environ.get('LOD', 1)))
print('built', time.time() - t)
rig = o['rig']
# test pose: curl right fingers, blink half, look left
pb = rig.pose.bones
for n in ('index', 'middle', 'ring', 'pinky'):
    for i in range(1, 4):
        pb[f'f_{n}.{i:02d}.R'].rotation_quaternion = Quaternion((1, 0, 0), np.radians(35))
for s in 'LR':
    pb['lid_up.' + s].rotation_quaternion = Quaternion((1, 0, 0), np.radians(-8))
o['ctrl']['IK_hand.L'].location += Vector((-0.08, -0.25, 0.25))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); U.link(cam); sc.camera = cam
a = np.radians(float(sys.argv[-1]))
cam.location = (2.6 * np.sin(a), -2.6 * np.cos(a), 0.45); cam.data.lens = 50
U.look_at(cam, (0, 0, 0.3))
for loc, e in (((1.5, -2, 2), 400), ((-2, -1, 0.5), 120), ((0, 2, 2), 250)):
    L = bpy.data.objects.new('L', bpy.data.lights.new('L', 'AREA')); U.link(L)
    L.location = loc; L.data.energy = e; L.data.size = 1.5; U.look_at(L, (0, 0, 0.3))
sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.03, 0.03, 0.035)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'AgX'
sc.render.resolution_x = 800; sc.render.resolution_y = 800
sc.render.filepath = os.environ.get('OUT', '/tmp/p.png')
if os.environ.get('SAVE'): bpy.ops.wm.save_as_mainfile(filepath=os.environ['SAVE'])
bpy.ops.render.render(write_still=True)
