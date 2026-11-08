import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy, numpy as np
from mathutils import Vector
import bl_util as U, cast
U.reset(); sc = bpy.context.scene
a = cast.append(sys.argv[-1])
cast.seat(a, 1)
a.place((0, 0, 0.6))
cast.key_ik(a, 'R', 1, (-0.17, -0.30, 0.20), (0.2, -0.9, -0.2), (0, 0.2, -1))
cast.key_ik(a, 'L', 1, (0.17, -0.30, 0.20), (-0.2, -0.9, -0.2), (0, 0.2, -1))
a.shape('smile', 0.6)
bpy.context.view_layer.update()
e = a.eyes_world()
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); U.link(cam); sc.camera = cam
mode = os.environ.get('MODE', 'face')
if mode == 'face':
    cam.location = e + Vector((0.25, -0.75, 0.02)); cam.data.lens = 85; U.look_at(cam, e + Vector((0, 0, -0.04)))
else:
    cam.location = Vector((1.6, -2.6, 1.1)); cam.data.lens = 40; U.look_at(cam, (0, 0, 0.55))
for loc, en in (((1.2, -1.6, 2.0), 300), ((-1.8, -1.0, 1.0), 90), ((0, 1.8, 2.0), 200)):
    L = bpy.data.objects.new('L', bpy.data.lights.new('L', 'AREA')); U.link(L)
    L.location = loc; L.data.energy = en; L.data.size = 1.5; U.look_at(L, (0, 0, 0.8))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.05, 0.05, 0.06, 1)
import render_settings as RS
RS.apply(sc, 'check'); sc.render.resolution_percentage = 40; sc.cycles.samples = 16; sc.render.use_motion_blur = False
sc.render.filepath = os.environ['OUT']
bpy.ops.render.render(write_still=True)
