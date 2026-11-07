"""Builds the complete, editable Scene 1 production file.

    python build_scene01.py [--lod 1.0] [--out ../../source/scene01_the_fear_never_sleeps.blend]

Produces a .blend with two scenes:
  'Bedroom' : character ARJUN (rigged), bedroom set, phone, all bedroom shots
  'Office'  : the fear-flash set and shots
Camera cuts are timeline markers bound to cameras (see config/scene01_timing.py).
"""
import sys, os, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import bpy
import numpy as np
import bl_util as U
import scene01_layout as LY
import scene01_anim as AN
import bedroom as BR
import props as PR
import render_settings as RS
import scene01_timing as T

ap = argparse.ArgumentParser()
ap.add_argument('--lod', type=float, default=1.0)
ap.add_argument('--out', default=os.path.join(HERE, '..', '..', 'source', 'scene01_the_fear_never_sleeps.blend'))
ap.add_argument('--no-office', action='store_true')
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])

t0 = time.time()
U.reset()
sc = bpy.context.scene
sc.name = 'Bedroom'
sc.frame_start, sc.frame_end = 1, T.SHOTS[-2][2]
sc.render.fps = T.FPS

# phone UI frames
ui_dir = os.path.abspath(os.path.join(HERE, '..', 'assets', 'phone_ui'))
if not os.path.exists(os.path.join(ui_dir, f'ui_{T.LAST_FRAME:04d}.png')):
    import subprocess
    subprocess.check_call([sys.executable if 'python' in sys.executable else 'python3',
                           os.path.join(HERE, '..', 'ui', 'phone_ui.py')])

objs, setobjs = LY.build(T.LAST_FRAME, lod=args.lod)
BR.setup_world(sc)
print('set+character', round(time.time() - t0))

screen_mat = PR.phone_screen_material(ui_dir, 'ui_0001.png', T.LAST_FRAME)
phone, screen, slight = PR.build_phone(U.collection('PROPS'), screen_mat)
phone.rotation_mode = 'QUATERNION'
objs['ctrl']['IK_hand.R'].rotation_mode = 'QUATERNION'
info = AN.animate(objs, setobjs, phone, slight, screen_mat)
cams = AN.cameras(objs, setobjs, phone, info)
print('animation', round(time.time() - t0))

RS.apply(sc, 'final')

if not args.no_office:
    import office
    office.build_office_scene(objs)
    bpy.context.window.scene = sc if bpy.context.window else None

out = os.path.abspath(args.out)
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=out, relative_remap=True, compress=True)
print('saved', out, round(time.time() - t0))
