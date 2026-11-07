import sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'blender'))
import bpy, numpy as np
import bl_util as U
import mh_body as MB
from mathutils import Vector
U.reset(); sc = bpy.context.scene
t = time.time()
body, info = MB.build_body(sc.collection)
rig = MB.build_rig(sc.collection, body, info)
print('built', time.time() - t, len(body.data.vertices))
sd = body.modifiers.new('sub', 'SUBSURF'); sd.levels = 1; sd.render_levels = 2
body.data.materials.append(U.simple_mat('clay', (0.5, 0.42, 0.38), rough=0.6))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); U.link(cam); sc.camera = cam
mode = sys.argv[-1]
eye = (Vector(info['joints']['joint-l-eye']) + Vector(info['joints']['joint-r-eye'])) / 2
print('head joint', eye)
if mode == 'face':
    cam.location = eye + Vector((0.3, -0.85, 0.0)); cam.data.lens = 100; U.look_at(cam, eye + Vector((0, 0, -0.04)))
else:
    cam.location = (1.8, -4.5, 0.2); cam.data.lens = 50; U.look_at(cam, (0, 0, -0.05))
for loc, e in (((1.5, -2, 2), 300), ((-2, -1, 0.5), 80), ((0, 2, 2), 150)):
    L = bpy.data.objects.new('L', bpy.data.lights.new('L', 'AREA')); U.link(L)
    L.location = loc; L.data.energy = e; L.data.size = 1.5; U.look_at(L, (0, 0, 0.3))
sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.03, 0.03, 0.035)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'AgX'
sc.render.resolution_x = 700; sc.render.resolution_y = 800
sc.render.filepath = os.environ['OUT']
bpy.ops.render.render(write_still=True)
