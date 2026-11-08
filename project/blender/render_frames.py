"""Render frames of Scene 1 from the production .blend.

    python render_frames.py -- <file.blend> <out_dir> <Bedroom|Office> <first> <last>
           [--quality final|check|preview] [--res PCT] [--spp N] [--frames a,b,c] [--skip-existing]

Uses the shot table (config/scene01_timing.py) to pick the camera for every
frame, so it works with bpy-as-a-module (no window / active-scene switching).
"""
import bpy, sys, os, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'config'))
import scene01_timing as T
import render_settings as RS

argv = sys.argv[sys.argv.index('--') + 1:]
ap = argparse.ArgumentParser()
ap.add_argument('blend'); ap.add_argument('out'); ap.add_argument('scene')
ap.add_argument('first', type=int); ap.add_argument('last', type=int)
ap.add_argument('--quality', default='final'); ap.add_argument('--res', type=int, default=0)
ap.add_argument('--spp', type=int, default=0); ap.add_argument('--frames', default='')
ap.add_argument('--skip-existing', action='store_true'); ap.add_argument('--no-mblur', action='store_true')
a = ap.parse_args(argv)

bpy.ops.wm.open_mainfile(filepath=a.blend)
sc = bpy.data.scenes[a.scene]
for other in list(bpy.data.scenes):
    if other != sc:
        bpy.data.scenes.remove(other)
RS.apply(sc, a.quality)
if a.res:
    sc.render.resolution_percentage = a.res
if a.spp:
    sc.cycles.samples = a.spp
if a.no_mblur:
    sc.render.use_motion_blur = False
os.makedirs(a.out, exist_ok=True)
cams = {s[0]: s[4] for s in T.SHOTS}
frames = [int(x) for x in a.frames.split(',')] if a.frames else range(a.first, a.last + 1)
for f in frames:
    path = os.path.join(a.out, f'f{f:04d}.png')
    if a.skip_existing and os.path.exists(path):
        continue
    if a.scene in ('Bedroom', 'Office'):
        shot = next((s for s in T.SHOTS if s[1] <= f <= s[2]), None)
        if shot and shot[4] and shot[4] in bpy.data.objects:
            sc.camera = bpy.data.objects[shot[4]]
    else:
        mk = [m for m in sc.timeline_markers if m.frame <= f and m.camera]
        if mk:
            sc.camera = max(mk, key=lambda m: m.frame).camera
    sc.frame_set(f)
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f'RENDERED {a.scene} {f} {time.time() - t:.1f}s', flush=True)
