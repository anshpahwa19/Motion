import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import bpy, numpy as np
import bl_util as U
import scene01_layout as LY
import bedroom as BR
from mathutils import Vector
U.reset()
sc = bpy.context.scene
t = time.time()
objs, setobjs = LY.build(300, lod=float(os.environ.get('LOD', 0.6)), hair=os.environ.get('HAIR', '1') == '1')
BR.setup_world(sc)
print('built', time.time() - t)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); U.link(cam); sc.camera = cam
cam.location = Vector(eval(os.environ.get('CAMLOC', '(1.55,-1.45,1.75)')))
cam.data.lens = float(os.environ.get('LENS', 24))
U.look_at(cam, eval(os.environ.get('TGT', '(-0.4,0.95,0.75)')))
import render_settings as RS
RS.apply(sc, os.environ.get('Q', 'preview'))
sc.render.use_motion_blur = False
sc.view_settings.exposure = float(os.environ.get('EXPO', 0))
sc.render.filepath = os.environ.get('OUT', '/tmp/p.png')
if os.environ.get('SAVE'): bpy.ops.wm.save_as_mainfile(filepath=os.environ['SAVE'])
t = time.time(); bpy.ops.render.render(write_still=True); print('render', time.time() - t)
