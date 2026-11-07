import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import bpy, numpy as np
import bl_util as U
import char_face as CF
import char_head as H

U.reset()
sc = bpy.context.scene
coll = sc.collection
t = time.time()
head = CF.build_head(coll)
print('head', time.time() - t)
em, cm = CF.eye_materials()
skin = head.data.materials[0]
lashm = CF.hair_material('ARJ_Lash', 0.98, 0.2, 0.4)
browm = CF.hair_material('ARJ_BrowHair', 0.95, 0.3, 0.35)
for side in 'LR':
    CF.build_eye(coll, side, em, cm)
    for up in (True, False):
        lid, th, pe, R = CF.build_lid(coll, side, up, skin)
        lid.rotation_euler.x = np.radians(float(os.environ.get('LIDROT', -7))) if up else 0
        CF.lashes(lid, th, pe, R, up, coll, lashm, 7 if up else 9)
    CF.build_brow(coll, side, browm, 11 if side == 'L' else 12)
print('face', time.time() - t)
import char_hair as CH
CH.build_hair(coll)
print('hair', time.time() - t)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
U.link(cam); sc.camera = cam
ang = float(sys.argv[-1])
a = np.radians(ang)
dist = float(os.environ.get('DIST', 0.95))
cam.location = (dist * np.sin(a), -dist * np.cos(a), 0.02)
cam.data.lens = 100
U.look_at(cam, (0, -0.02, float(os.environ.get('TZ', -0.03))))
for loc, e, c in (((0.5, -0.6, 0.5), 40, (1, 0.95, 0.9)), ((-0.6, -0.3, 0.1), 12, (0.8, 0.9, 1)), ((0, 0.6, 0.4), 25, (1, 1, 1))):
    L = bpy.data.objects.new('L', bpy.data.lights.new('L', 'AREA')); U.link(L)
    L.location = loc; L.data.energy = e; L.data.size = 0.5; L.data.color = c; U.look_at(L, (0, 0, 0))
sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.03, 0.03, 0.035)
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('SPP', 32)); sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'AgX'
sc.render.resolution_x = 800; sc.render.resolution_y = 800
sc.render.filepath = os.environ.get('OUT', '/tmp/p.png')
if os.environ.get('SAVE'): bpy.ops.wm.save_as_mainfile(filepath=os.environ['SAVE'])
bpy.ops.render.render(write_still=True)
