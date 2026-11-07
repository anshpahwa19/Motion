"""Props: Arjun's smartphone (screen = image-sequence emission)."""
import bpy, os
import numpy as np
import bl_util as U
from sdf import round_box, mesh_sdf

PHONE = dict(w=0.0715, h=0.1525, t=0.0082)


def phone_screen_material(seq_dir, first_file, nframes, offset=0):
    m = U.new_mat('PRP_PhoneScreen'); nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    im = nt.nodes.new('ShaderNodeTexImage')
    img = bpy.data.images.load(os.path.join(seq_dir, first_file))
    img.source = 'SEQUENCE'
    im.image = img
    im.image_user.frame_duration = nframes
    im.image_user.frame_start = 1
    im.image_user.frame_offset = offset
    im.image_user.use_auto_refresh = True
    im.interpolation = 'Cubic'
    em = nt.nodes.new('ShaderNodeEmission'); em.name = 'ScreenEmit'
    em.inputs['Strength'].default_value = 1.0
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.08
    gl.inputs['Color'].default_value = (0.05, 0.05, 0.05, 1)
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(im.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs[0], add.inputs[0]); nt.links.new(gl.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], o.inputs[0])
    return m


def build_phone(coll, screen_mat):
    w, h, t = PHONE['w'], PHONE['h'], PHONE['t']
    fn = lambda P: round_box(P, (0, 0, 0), (w / 2, h / 2, t / 2), 0.0035)
    v, f = mesh_sdf(fn, (-w / 2 - 0.002, -h / 2 - 0.002, -t / 2 - 0.002), (w / 2 + 0.002, h / 2 + 0.002, t / 2 + 0.002), 0.0008)
    body = U.mesh_obj('PRP_Phone', v, f, coll,
                      mat=U.simple_mat('PRP_PhoneBody', U.hex2lin('#1d2227'), rough=0.25, metal=0.6))
    # screen plane (UV 0..1), slightly above the front face (+Z = screen side)
    sw, sh = w - 0.004, h - 0.004
    V = np.array([[-sw / 2, -sh / 2, 0], [sw / 2, -sh / 2, 0], [sw / 2, sh / 2, 0], [-sw / 2, sh / 2, 0]])
    scr = U.mesh_obj('PRP_PhoneScreen', V, [[0, 1, 2, 3]], coll, smooth=False, mat=screen_mat)
    uv = scr.data.uv_layers.new(name='UVMap')
    uv.data.foreach_set('uv', np.array([0, 0, 1, 0, 1, 1, 0, 1], np.float32))
    scr.parent = body; scr.location = (0, 0, t / 2 + 0.0002)
    # camera bump on back
    cam = U.mesh_obj('PRP_PhoneCam', *mesh_sdf(lambda P: round_box(P, (-0.018, 0.055, -t / 2 - 0.001), (0.014, 0.02, 0.0015), 0.004),
                                               (-0.035, 0.03, -t / 2 - 0.004), (0.0, 0.08, -t / 2 + 0.001), 0.0006),
                     coll, mat=bpy.data.materials['PRP_PhoneBody'])
    cam.parent = body
    # screen light (animated energy) - an area light just above the screen
    L = bpy.data.objects.new('LGT_PhoneScreen', bpy.data.lights.new('LGT_PhoneScreen', 'AREA')); U.link(L, coll)
    L.data.shape = 'RECTANGLE'; L.data.size = sw; L.data.size_y = sh
    L.data.color = (0.75, 0.85, 1.0); L.data.energy = 0.0
    L.parent = body; L.location = (0, 0, t / 2 + 0.003)
    L.rotation_euler = (np.pi, 0, 0)    # area lights emit along -Z -> flip to +Z (screen side)
    L.visible_camera = False
    return body, scr, L
