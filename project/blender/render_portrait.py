"""Renders Arjun's ID-card photo from the production file (frame 1 pose)."""
import bpy, sys, os
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0]); out = a[1]
sc = bpy.data.scenes['Bedroom']; sc.frame_set(1)
for m in list(sc.timeline_markers): sc.timeline_markers.remove(m)
rig = bpy.data.objects['ARJ_Rig']
import scene01_anim as AN
e, up, fwd, left = AN.face_frame(rig, 1)
cam = bpy.data.objects.new('PORTRAIT', bpy.data.cameras.new('PORTRAIT')); sc.collection.objects.link(cam)
loc = e + fwd * 0.62 + up * 0.0
z = (loc - e).normalized(); x = up.cross(z).normalized(); y = z.cross(x)
cam.matrix_world = Matrix.LocRotScale(loc, Matrix((x, y, z)).transposed().to_quaternion(), None)
cam.data.lens = 85; sc.camera = cam
cam.location = cam.location - up * 0.02
L = bpy.data.objects.new('PL', bpy.data.lights.new('PL', 'AREA')); sc.collection.objects.link(L)
L.data.size = 0.6; L.data.energy = 25; L.data.color = (1, 0.97, 0.92)
L.location = e + fwd * 0.5 + left * 0.25 + up * 0.2
L.rotation_euler = (e - L.location).to_track_quat('-Z', 'Y').to_euler()
for n in ('LGT_Moon',):
    bpy.data.objects[n].hide_render = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 600, 740, 100
sc.cycles.samples = 24; sc.render.use_motion_blur = False
sc.render.filepath = out
bpy.ops.render.render(write_still=True, scene='Bedroom')
