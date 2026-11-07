"""Look-dev test renders for realistic Arjun: close-up, medium, full body."""
import sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'blender'))
import bpy, numpy as np
from mathutils import Vector, Quaternion
import bl_util as U
import mh_body as MB, mh_look as ML

U.reset(); sc = bpy.context.scene; coll = sc.collection
t0 = time.time()
body, info = MB.build_body(coll)
rig = MB.build_rig(coll, body, info)
F = ML.Face(info)
ML.apply_skin(body, F)
sd = body.modifiers.new('Subdivision', 'SUBSURF'); sd.levels = 1; sd.render_levels = 2
ML.build_eyes(coll, F, rig); ML.build_mouth(coll, info, rig)
S = ML.Surface(body); rng = np.random.default_rng(3)
hair = os.environ.get('HAIR', '1') == '1'
ML.build_brows(coll, S, F, rng); ML.build_lashes(coll, S, F, rng)
if hair:
    ML.build_stubble(coll, S, F, rng)
    ML.build_scalp_hair(coll, S, F, rng, n_hair=int(os.environ.get('NHAIR', 90000)))
tee = ML.make_garment(body, 'ARJ_Tee', ML.tee_mask(info), 0.014, ML.cotton_mat('ARJ_TeeMat', '#3e5862'), 0.004)
pants = ML.make_garment(body, 'ARJ_Pyjama', ML.pants_mask(info), 0.016, ML.cotton_mat('ARJ_PyjamaMat', '#35383f', plaid='#5a5f6a'), 0.004)
j = info['joints']
ML.relax_arms(rig)
if os.environ.get('CLOTH', '1') == '1':
    shz = j['joint-l-shoulder'][2]; nk = j['joint-neck']
    ML.add_cloth(tee, body, lambda P: np.maximum(np.clip((P[:, 2] - 0.30) / 0.25, 0, 1) * 0.85 + np.clip((P[:, 2] - (shz - 0.03)) / 0.03, 0, 1),
                                                  (np.abs(P[:, 0]) > 0.17).astype(float)), (1, 45))
    ML.add_cloth(pants, body, lambda P: np.maximum(np.clip((P[:, 2] - (j['joint-pelvis'][2] + 0.0)) / 0.03, 0, 1), 0.55), (1, 45))
    sc.frame_start, sc.frame_end = 1, 45
    t1 = time.time(); ML.simulate(sc, 1, 45); print('cloth', round(time.time() - t1))
print('built', round(time.time() - t0, 1))
# expression: slight tired/worried
kb = body.data.shape_keys.key_blocks
for k, v in (('eyebrows-left-inner-up', 0.2), ('eyebrows-right-inner-up', 0.25)):
    kb[k].value = v
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); U.link(cam); sc.camera = cam
e = Vector(F.e); mode = sys.argv[-1]
cam.data.dof.use_dof = True
if mode == 'face':
    cam.location = e + Vector((0.16, -0.55, 0.01)); cam.data.lens = 85; tgt = e + Vector((0, 0, -0.035)); cam.data.dof.aperture_fstop = 2.8
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1100
elif mode == 'medium':
    cam.location = e + Vector((0.45, -1.35, -0.12)); cam.data.lens = 50; tgt = e + Vector((0, 0, -0.33)); cam.data.dof.aperture_fstop = 4
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1100
else:
    cam.location = Vector((1.3, -4.2, 0.2)); cam.data.lens = 50; tgt = Vector((0, 0, 0.05)); cam.data.dof.aperture_fstop = 8
    sc.render.resolution_x, sc.render.resolution_y = 700, 1100
U.look_at(cam, tgt); cam.data.dof.focus_distance = (cam.location - e).length
for loc, en, sz, col in (((-1.5, -1.1, 1.3), 300, 1.2, (1.0, 0.96, 0.92)), ((1.8, -1.4, 0.7), 18, 2.5, (0.8, 0.88, 1.0)),
                         ((0.9, 1.6, 1.5), 160, 0.8, (0.85, 0.92, 1.0))):
    L = bpy.data.objects.new('L', bpy.data.lights.new('L', 'AREA')); U.link(L)
    L.location = loc; L.data.energy = en; L.data.size = sz; L.data.color = col; U.look_at(L, (0, 0, 0.6))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.006, 0.02, 0.022, 1)
sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('SPP', 96)); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 8; sc.cycles.transparent_max_bounces = 32
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.render.filepath = os.environ['OUT']
if os.environ.get('SAVE'):
    bpy.ops.wm.save_as_mainfile(filepath=os.environ['SAVE'])
t = time.time(); bpy.ops.render.render(write_still=True); print('render', round(time.time() - t))
