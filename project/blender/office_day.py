"""SET — NOVA Digital Studio, daytime (Scenes 2-5). Reuses the fear-flash office
pieces (office.py) and adds daylight, side walls, live screens, a meeting
corner by the window and time-of-day lighting keys."""
import bpy, os
import numpy as np
from mathutils import Vector, Euler
import bl_util as U
import bedroom as BR
import office as OF

TEX = BR.TEX
DESK_H = OF.DESK_H
MEET = Vector((2.7, -3.3, 0.0))          # meeting-corner table centre


def seq_mat(name, folder, first_file, nframes, strength=1.0):
    m = U.new_mat(name); nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); em.name = 'Emit'
    em.inputs['Strength'].default_value = strength
    it = nt.nodes.new('ShaderNodeTexImage')
    img = bpy.data.images.load(os.path.join(folder, first_file)); img.source = 'SEQUENCE'
    it.image = img; it.image_user.frame_duration = nframes; it.image_user.frame_start = 1; it.image_user.use_auto_refresh = True
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.12; gl.inputs['Color'].default_value = (0.04, 0.04, 0.04, 1)
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(it.outputs['Color'], em.inputs['Color']); nt.links.new(em.outputs[0], add.inputs[0]); nt.links.new(gl.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], o.inputs[0])
    return m


def screen_plane(name, w, h, loc, rot, coll, mat):
    p = OF.plane(name, w, h, coll, mat); p.location = loc; p.rotation_euler = rot
    return p


def build_office_day(coll, monitor_dir, phone_dir, nframes):
    out = {}
    carpet = U.new_mat('OFF_Carpet'); N, L = U.nodes(carpet); p = U.principled(carpet)
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 300
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (*U.hex2lin('#56606c'), 1); mix.inputs['B'].default_value = (*U.hex2lin('#434b55'), 1)
    L.new(nz.outputs['Fac'], mix.inputs['Factor']); L.new(mix.outputs['Result'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.95
    BR.box('OFF_Floor', -8, 8, -6, 8, -0.05, 0, carpet, coll)
    BR.box('OFF_Ceiling', -8, 8, -6, 8, 2.9, 3.0, OF.om('OFF_Ceiling', U.hex2lin('#e2e3e4'), 0.9), coll)
    wall = OF.om('OFF_WallDay', U.hex2lin('#d5d7d2'), 0.9)
    BR.box('OFF_WallBack', -8, 8, 7.0, 7.1, 0, 2.9, wall, coll)
    BR.box('OFF_WallL', -8.1, -8.0, -6, 8, 0, 2.9, wall, coll)
    BR.box('OFF_WallR', 8.0, 8.1, -6, 8, 0, 2.9, wall, coll)
    accent = OF.om('OFF_Accent', U.hex2lin('#3d6b74'), 0.8)
    BR.box('OFF_AccentWall', -2.5, 2.5, 6.98, 7.0, 0.0, 2.9, accent, coll)
    # window wall with day city
    import skyline
    path = os.path.join(TEX, 'city_day.png')
    if not os.path.exists(path):
        skyline.make_skyline_day(path)
    sky = U.new_mat('OFF_CityDay'); nt = sky.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Strength'].default_value = 1.5
    im = nt.nodes.new('ShaderNodeTexImage'); im.image = bpy.data.images.load(path)
    nt.links.new(im.outputs['Color'], e.inputs['Color']); nt.links.new(e.outputs[0], o.inputs[0])
    sk = OF.plane('OFF_City', 70, 24, coll, sky); sk.rotation_euler = (np.radians(90), 0, 0); sk.location = (0, -32, 3.5)
    sk.visible_shadow = False
    out['sky_emit'] = e
    mull = OF.om('OFF_Mull', (0.08, 0.08, 0.09), 0.4)
    for i in range(-6, 7):
        BR.box(f'OFF_Mullion{i}', i * 1.2 - 0.03, i * 1.2 + 0.03, -5.0, -4.95, 0, 2.9, mull, coll)
    BR.box('OFF_Sill', -8, 8, -5.05, -4.9, 0, 0.35, mull, coll)
    BR.box('OFF_Header', -8, 8, -5.05, -4.9, 2.7, 2.9, mull, coll)
    # ceiling panels
    panel = U.emission_mat('OFF_PanelDay', (0.95, 0.97, 1.0), 3.0)
    for y in (-3.0, -1.2, 0.6, 2.4, 4.2, 6.0):
        for x in (-4.5, -1.5, 1.5, 4.5):
            BR.box(f'OFF_Panel_{x}_{y}', x - 0.6, x + 0.6, y - 0.3, y + 0.3, 2.88, 2.9, panel, coll)
    # desks (his = idx 2 at x=0, y=0)
    k = 0
    for y in (0.0, 1.6):
        for x in (-3.2, -1.6, 0.0, 1.6, 3.2):
            OF.build_desk(coll, x, y, mine=(x == 0 and y == 0), idx=k); k += 1
    chairs = {}
    for (x, y) in ((-3.2, 0), (-1.6, 0), (3.2, 0), (-3.2, 1.6), (-1.6, 1.6), (1.6, 1.6), (3.2, 1.6)):
        OF.build_chair(coll, (x + 0.05, y - 0.62, 0), np.radians(180 + np.random.default_rng(int(x * 7 + y * 3 + 40)).uniform(-25, 25)), f'OFF_Chair_{x}_{y}')
    chairs['arjun'] = OF.build_chair(coll, (0.0, -0.66, 0), np.radians(180), 'OFF_ChairArjun')
    chairs['colA'] = OF.build_chair(coll, (1.6, -0.66, 0), np.radians(180), 'OFF_ChairColA')
    chairs['colB'] = OF.build_chair(coll, (0.0, 0.94, 0), np.radians(180), 'OFF_ChairColB')
    # live screens: his monitor (sequence), colleagues' monitors (static AI UI)
    mon = seq_mat('OFF_MyMonitor', monitor_dir, 'f0001.jpg', nframes, 1.0)
    out['my_monitor'] = screen_plane('OFF_MyMonitorScreen', 0.57, 0.33, (0, 0.2165, DESK_H + 0.34), (np.radians(90), 0, 0), coll, mon)
    out['my_monitor_mat'] = mon
    stat = OF.img_mat('OFF_ColMonitor', os.path.join(monitor_dir, 'static_ai.jpg'), emit=1.0, rough=0.2)
    for (x, y) in ((1.6, 0), (0, 1.6), (-1.6, 0), (3.2, 1.6), (-1.6, 1.6)):
        screen_plane(f'OFF_ColScreen_{x}_{y}', 0.57, 0.33, (x, y + 0.2165, DESK_H + 0.34), (np.radians(90), 0, 0), coll, stat)
    # his keyboard, mouse, laptop, sketch paper, sticky notes
    kb = OF.om('OFF_Keys', U.hex2lin('#2a2c30'), 0.4)
    BR.box('OFF_Keyboard', -0.21, 0.21, -0.20, -0.06, DESK_H, DESK_H + 0.018, kb, coll, 0.004)
    BR.box('OFF_Mouse', 0.28, 0.34, -0.17, -0.07, DESK_H, DESK_H + 0.03, kb, coll, 0.012)
    alu = OF.om('OFF_Alu', (0.55, 0.56, 0.58), 0.3, 0.9)
    BR.box('OFF_LaptopBase', -0.56, -0.24, -0.28, -0.04, DESK_H, DESK_H + 0.015, alu, coll, 0.004)
    lid = bpy.data.objects.new('OFF_LaptopLidPivot', None); U.link(lid, coll); lid.location = (-0.40, -0.04, DESK_H + 0.015)
    lb = BR.box('OFF_LaptopLid', -0.16, 0.16, -0.005, 0.0, 0.0, 0.22, alu, coll, 0.003); lb.parent = lid
    lsm = OF.img_mat('OFF_LaptopScreenDay', os.path.join(TEX, 'laptop_screen.png'), emit=1.0, rough=0.15)
    ls = OF.plane('OFF_LaptopScreenP', 0.30, 0.19, coll, lsm); ls.parent = lid
    ls.rotation_euler = (np.radians(90), 0, np.radians(180)); ls.location = (0, -0.0062, 0.112)
    out['lid'] = lid
    paper = OF.om('OFF_Paper', U.hex2lin('#f2efe6'), 0.8)
    out['paper'] = BR.box('OFF_SketchPaper', 0.02, 0.24, -0.40, -0.25, DESK_H, DESK_H + 0.001, paper, coll)
    for i, (sx, sz, rot) in enumerate(((-0.33, 0.44, -6), (-0.33, 0.35, 4), (0.33, 0.42, -3))):
        sm = OF.img_mat(f'OFF_StickyD{i}', os.path.join(TEX, f'sticky_{i}.png'), rough=0.8)
        st = OF.plane(f'OFF_StickyDay{i}', 0.075, 0.075, coll, sm)
        st.rotation_euler = (np.radians(90), np.radians(rot), np.radians(180)); st.location = (sx, 0.214, DESK_H + sz)
    out['sticky'] = Vector((-0.33, 0.21, DESK_H + 0.44))
    BR.cylinder('OFF_Mug', 0.04, 0.095, (0.45, -0.02, DESK_H + 0.048), OF.om('OFF_MugM', U.hex2lin('#c7652f'), 0.3), coll, 24)
    # meeting corner
    wood = BR.mat_wood('OFF_TableWood', '#8a6a4a', 5)
    BR.cylinder('OFF_MeetTop', 0.48, 0.03, (MEET.x, MEET.y, 0.72), wood, coll, 64)
    BR.cylinder('OFF_MeetLeg', 0.04, 0.70, (MEET.x, MEET.y, 0.35), OF.om('OFF_DeskMetal', U.hex2lin('#3a3d42'), 0.3, 0.8), coll, 24)
    chairs['rao'] = OF.build_chair(coll, (MEET.x - 0.60, MEET.y - 0.05, 0), np.radians(90), 'OFF_ChairRao')
    chairs['arjun_meet'] = OF.build_chair(coll, (MEET.x + 0.05, MEET.y - 0.62, 0), np.radians(180), 'OFF_ChairArjunMeet')
    nb = OF.om('OFF_NotebookCover', U.hex2lin('#24384f'), 0.6)
    BR.box('OFF_MeetNotebook', MEET.x - 0.05, MEET.x + 0.16, MEET.y - 0.40, MEET.y - 0.22, 0.735, 0.745, nb, coll, 0.003)
    BR.box('OFF_MeetPage', MEET.x - 0.045, MEET.x + 0.155, MEET.y - 0.395, MEET.y - 0.225, 0.7451, 0.7455, paper, coll)
    BR.box('OFF_MeetLaptop', MEET.x + 0.15, MEET.x + 0.45, MEET.y + 0.05, MEET.y + 0.27, 0.735, 0.75, alu, coll, 0.004)
    pot = BR.cylinder('OFF_BigPot', 0.18, 0.4, (MEET.x + 0.9, MEET.y - 1.1, 0.2), OF.om('OFF_PotM', U.hex2lin('#b5653f'), 0.7), coll, 32)
    leaf = OF.om('OFF_Leaf', U.hex2lin('#3f6b3a'), 0.5)
    from sdf import capsule, smin, mesh_sdf
    c0 = np.array([MEET.x + 0.9, MEET.y - 1.1, 0.4])
    def plantfn(P):
        d = None
        rng = np.random.default_rng(3)
        for k in range(9):
            a = rng.uniform(0, 6.28); r = rng.uniform(0.15, 0.4); h = rng.uniform(0.6, 1.2)
            dd = capsule(P, c0, c0 + np.array([np.cos(a) * r, np.sin(a) * r, h]), 0.03)
            d = dd if d is None else smin(d, dd, 0.04)
        return d
    U.mesh_obj('OFF_BigPlant', *mesh_sdf(plantfn, c0 - 0.5, c0 + np.array([0.5, 0.5, 1.4]), 0.015), coll, mat=leaf)
    # props carried by actors
    pen = BR.cylinder('PRP_Pen', 0.0045, 0.14, (0, 0, 0), OF.om('PRP_PenM', U.hex2lin('#1d2a5c'), 0.3), coll, 12)
    out['pen'] = pen
    import props as PR
    pm = seq_mat('PRP_RaoPhoneScreen', phone_dir, 'f0001.jpg', nframes, 1.0)
    phone, scr, sl = PR.build_phone(coll, pm)
    sl.data.energy = 0.5
    out['rao_phone'] = phone
    # lights
    sun = bpy.data.objects.new('LGT_Sun', bpy.data.lights.new('LGT_Sun', 'SUN')); U.link(sun, coll)
    sun.data.angle = np.radians(1.5); out['sun'] = sun
    skyfill = bpy.data.objects.new('LGT_WindowSky', bpy.data.lights.new('LGT_WindowSky', 'AREA')); U.link(skyfill, coll)
    skyfill.data.shape = 'RECTANGLE'; skyfill.data.size = 14; skyfill.data.size_y = 2.4
    skyfill.location = (0, -4.8, 1.5); skyfill.rotation_euler = (np.radians(-90), 0, 0); skyfill.visible_camera = False
    out['skyfill'] = skyfill
    monl = bpy.data.objects.new('LGT_MyMonitor', bpy.data.lights.new('LGT_MyMonitor', 'AREA')); U.link(monl, coll)
    monl.data.shape = 'RECTANGLE'; monl.data.size = 0.55; monl.data.size_y = 0.32; monl.data.color = (0.85, 0.88, 1.0)
    monl.location = (0, 0.20, DESK_H + 0.34); monl.rotation_euler = (np.radians(90), 0, np.radians(180)); monl.visible_camera = False
    monl.data.energy = 3.0
    out['monitor_light'] = monl
    out['chairs'] = chairs
    return out


TOD = {  # time-of-day: sun colour, energy, direction (travel), sky fill energy/colour, world colour
    'morning': ((1.0, 0.88, 0.74), 3.0, (0.45, 1.0, -0.40), 90, (0.80, 0.88, 1.0), (0.10, 0.13, 0.18)),
    'midday': ((1.0, 0.97, 0.93), 3.2, (0.15, 1.0, -0.95), 80, (0.78, 0.86, 1.0), (0.10, 0.12, 0.16)),
    'soft': ((1.0, 0.93, 0.84), 2.6, (-0.25, 1.0, -0.70), 110, (0.92, 0.94, 1.0), (0.12, 0.13, 0.15)),
    'golden': ((1.0, 0.62, 0.34), 6.0, (-0.55, 1.0, -0.20), 40, (1.0, 0.72, 0.5), (0.10, 0.07, 0.05)),
}


def key_tod(o, world, f, name):
    col, en, d, se, sc_, wc = TOD[name]
    s = o['sun']; s.data.color = col; s.data.energy = en
    s.rotation_euler = (-Vector(d).normalized()).to_track_quat('Z', 'Y').to_euler()
    s.data.keyframe_insert('color', frame=f); s.data.keyframe_insert('energy', frame=f); s.keyframe_insert('rotation_euler', frame=f)
    k = o['skyfill']; k.data.energy = se; k.data.color = sc_
    k.data.keyframe_insert('energy', frame=f); k.data.keyframe_insert('color', frame=f)
    bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*wc, 1)
    bg.inputs['Color'].keyframe_insert('default_value', frame=f)
