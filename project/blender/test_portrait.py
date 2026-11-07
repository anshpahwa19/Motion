import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import bpy, numpy as np
import bl_util as U
from sdf import mesh_sdf
import char_head as H
from mathutils import Vector

U.reset()
sc = bpy.context.scene
t = time.time()
v, f = mesh_sdf(H.head_sdf, *H.BBOX, 0.0016)
print('mesh', len(v), time.time() - t)
skin = U.simple_mat('clay', (0.6, 0.45, 0.38), rough=0.5)
head = U.mesh_obj('Head', v, f, mat=skin)
for E in (H.EYE_L, H.EYE_RT):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=H.EYE_R, location=E, segments=48, ring_count=24)
    bpy.ops.object.shade_smooth()
    bpy.context.object.data.materials.append(U.simple_mat('eye', (0.9, 0.9, 0.9), rough=0.1))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
U.link(cam); sc.camera = cam
ang = float(sys.argv[-1]) if sys.argv[-1].lstrip('-').isdigit() else 30
a = np.radians(ang)
cam.location = (0.95 * np.sin(a), -0.95 * np.cos(a), 0.02)
cam.data.lens = 85
U.look_at(cam, (0, 0, -0.03))
for loc, e in (((0.5, -0.6, 0.5), 40), ((-0.6, -0.3, 0.1), 10), ((0, 0.6, 0.4), 25)):
    L = bpy.data.objects.new('L', bpy.data.lights.new('L', 'AREA')); U.link(L)
    L.location = loc; L.data.energy = e; L.data.size = 0.5; U.look_at(L, (0, 0, 0))
sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.05, 0.05, 0.06)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x = 800; sc.render.resolution_y = 800
sc.render.filepath = os.environ.get('OUT', '/tmp/p.png')
bpy.ops.render.render(write_still=True)
