"""FEAR FLASH SET — Arjun's empty office workspace (separate scene 'Office').

Shots F1–F5 (frames 421–516, see config). Cold, after-hours, desaturated.
"""
import bpy, os, sys
import numpy as np
from mathutils import Vector, Matrix, Euler
import bl_util as U
import bedroom as BR
from sdf import round_box, smin, capsule, cyl_z, mesh_sdf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config'))
import scene01_timing as T

TEX = BR.TEX
DESK_H = 0.74


def img_mat(name, path, emit=0.0, rough=0.5):
    m = U.new_mat(name); N, L = U.nodes(m); p = U.principled(m)
    im = N.new('ShaderNodeTexImage'); im.image = bpy.data.images.load(path, check_existing=True)
    L.new(im.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = rough
    if emit:
        L.new(im.outputs['Color'], p.inputs['Emission Color'])
        p.inputs['Emission Strength'].default_value = emit
    return m


def om(name, color, rough=0.5, metal=0.0):
    """get-or-create (shared by all desks/chairs)."""
    return bpy.data.materials.get(name) or U.simple_mat(name, color, rough=rough, metal=metal)


def plane(name, w, h, coll, mat):
    V = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    ob = U.mesh_obj(name, V, [[0, 1, 2, 3]], coll, smooth=False, mat=mat)
    uv = ob.data.uv_layers.new(name='UVMap')
    uv.data.foreach_set('uv', np.array([0, 0, 1, 0, 1, 1, 0, 1], np.float32))
    return ob


def build_chair(coll, loc, rot_z, name='OFF_Chair'):
    fab = om('OFF_ChairFabric', U.hex2lin('#2b2f36'), rough=0.8)
    plast = om('OFF_ChairPlastic', U.hex2lin('#16181b'), rough=0.35)
    root = bpy.data.objects.new(name, None); U.link(root, coll); root.location = loc
    spin = bpy.data.objects.new(name + '_Spin', None); U.link(spin, coll); spin.parent = root
    spin.rotation_euler.z = rot_z
    fn = lambda P: round_box(P, (0, 0, 0.47), (0.25, 0.24, 0.045), 0.035)
    seat = U.mesh_obj(name + '_Seat', *mesh_sdf(fn, (-0.3, -0.3, 0.4), (0.3, 0.3, 0.55), 0.012), coll, mat=fab)
    fn = lambda P: round_box(P, (0, 0.24, 0.83), (0.23, 0.035, 0.27), 0.04)
    back = U.mesh_obj(name + '_Back', *mesh_sdf(fn, (-0.3, 0.17, 0.5), (0.3, 0.31, 1.15), 0.012), coll, mat=fab)
    fn = lambda P: smin(capsule(P, (0, 0.2, 0.5), (0, 0.25, 0.6), 0.02), cyl_z(P, (0, 0, 0.3), 0.025, 0.15), 0.01)
    post = U.mesh_obj(name + '_Post', *mesh_sdf(fn, (-0.06, -0.06, 0.1), (0.06, 0.3, 0.65), 0.008), coll, mat=plast)
    for o in (seat, back, post):
        o.parent = spin
    base = None
    def basefn(P):
        d = cyl_z(P, (0, 0, 0.12), 0.04, 0.03)
        for k in range(5):
            a = 2 * np.pi * k / 5
            d = smin(d, capsule(P, (0, 0, 0.11), (0.3 * np.cos(a), 0.3 * np.sin(a), 0.07), 0.022), 0.02)
            d = smin(d, capsule(P, (0.3 * np.cos(a), 0.3 * np.sin(a), 0.035), (0.3 * np.cos(a) + 0.03, 0.3 * np.sin(a), 0.035), 0.03), 0.005)
        return d
    base = U.mesh_obj(name + '_Base', *mesh_sdf(basefn, (-0.36, -0.36, 0.0), (0.36, 0.36, 0.17), 0.01), coll, mat=plast)
    base.parent = root
    return root, spin


def build_desk(coll, x, y, mine=False, idx=0):
    top = om('OFF_DeskTop', U.hex2lin('#9c9890'), rough=0.45)
    metal = om('OFF_DeskMetal', U.hex2lin('#3a3d42'), rough=0.3, metal=0.8)
    BR.box(f'OFF_Desk{idx}', x - 0.75, x + 0.75, y - 0.38, y + 0.38, DESK_H - 0.03, DESK_H, top, coll, 0.004)
    for dx in (-0.7, 0.68):
        BR.box(f'OFF_DeskLeg{idx}', x + dx, x + dx + 0.03, y - 0.34, y + 0.34, 0, DESK_H - 0.03, metal, coll)
    pan = om('OFF_Partition', U.hex2lin('#4a5560'), rough=0.9)
    BR.box(f'OFF_Partition{idx}', x - 0.76, x + 0.76, y + 0.38, y + 0.42, 0, 1.25, pan, coll, 0.005)
    # monitor
    scr = bpy.data.materials.get('OFF_MonitorOff') or U.simple_mat('OFF_MonitorOff', (0.01, 0.01, 0.012), rough=0.1)
    BR.box(f'OFF_Monitor{idx}', x - 0.30, x + 0.30, y + 0.22, y + 0.25, DESK_H + 0.16, DESK_H + 0.52, metal, coll, 0.006)
    BR.box(f'OFF_MonScreen{idx}', x - 0.285, x + 0.285, y + 0.218, y + 0.221, DESK_H + 0.175, DESK_H + 0.505, scr, coll)
    BR.box(f'OFF_MonStand{idx}', x - 0.02, x + 0.02, y + 0.25, y + 0.28, DESK_H, DESK_H + 0.2, metal, coll)


def build_office_scene(char_objs=None):
    main = bpy.context.scene
    sc = bpy.data.scenes.new('Office')
    sc.frame_start, sc.frame_end = 421, 516
    import render_settings as RS
    coll = sc.collection
    oc = bpy.data.collections.new('SET_Office'); coll.children.link(oc)
    # textures
    portrait = os.path.join(TEX, 'arjun_portrait.png')
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ui'))
    import office_textures as OT
    if not os.path.exists(os.path.join(TEX, 'id_card.png')):
        OT.main(portrait)
    # room
    carpet = U.new_mat('OFF_Carpet'); N, L = U.nodes(carpet); p = U.principled(carpet)
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 300
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (*U.hex2lin('#3b4450'), 1); mix.inputs['B'].default_value = (*U.hex2lin('#2a313a'), 1)
    L.new(nz.outputs['Fac'], mix.inputs['Factor']); L.new(mix.outputs['Result'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.95
    BR.box('OFF_Floor', -8, 8, -6, 8, -0.05, 0, carpet, oc)
    ceil = U.simple_mat('OFF_Ceiling', U.hex2lin('#d0d2d4'), rough=0.9)
    BR.box('OFF_Ceiling', -8, 8, -6, 8, 2.9, 3.0, ceil, oc)
    wall = U.simple_mat('OFF_Wall', U.hex2lin('#9aa3ab'), rough=0.9)
    BR.box('OFF_WallBack', -8, 8, 7.0, 7.1, 0, 2.9, wall, oc)
    # window wall with night city
    glass = BR.mat_glass()
    sky = bpy.data.materials['SET_Skyline'] if 'SET_Skyline' in bpy.data.materials else None
    if sky:
        sk = plane('OFF_City', 60, 20, oc, sky); sk.rotation_euler = (np.radians(90), 0, 0); sk.location = (0, -30, 4)
    for i in range(-6, 7):
        BR.box(f'OFF_Mullion{i}', i * 1.2 - 0.03, i * 1.2 + 0.03, -5.0, -4.95, 0, 2.9, om('OFF_Mull', (0.05, 0.05, 0.06), 0.4), oc)
    # ceiling light panels (rows) — emissive, switched off row by row in F5
    rows = []
    for r, y in enumerate((-3.0, -1.2, 0.6, 2.4, 4.2, 6.0)):
        mats = U.emission_mat(f'OFF_Panel{r}', (0.82, 0.9, 1.0), 6.0)
        for x in (-4.5, -1.5, 1.5, 4.5):
            BR.box(f'OFF_Panel{r}_{x}', x - 0.6, x + 0.6, y - 0.3, y + 0.3, 2.88, 2.9, mats, oc)
        rows.append(mats)
    # desks: two rows facing each other; his desk is idx 0
    k = 0
    for y in (0.0, 1.6):
        for x in (-3.2, -1.6, 0.0, 1.6, 3.2):
            build_desk(oc, x, y, mine=(k == 0), idx=k); k += 1
    chairs = []
    for x in (-3.2, -1.6, 1.6, 3.2):
        build_chair(oc, (x, -0.55, 0), np.radians(np.random.default_rng(int(x * 10 + 50)).uniform(-30, 30)), f'OFF_ChairX{x}')
    my_root, my_spin = build_chair(oc, (0.05, -0.62, 0), np.radians(12), 'OFF_MyChair')
    # his laptop (open)
    alu = U.simple_mat('OFF_Alu', (0.55, 0.56, 0.58), rough=0.3, metal=1)
    BR.box('OFF_LaptopBase', -0.17, 0.17, -0.22, 0.02, DESK_H, DESK_H + 0.015, alu, oc, 0.004)
    lid = bpy.data.objects.new('OFF_LaptopLidPivot', None); U.link(lid, oc); lid.location = (0, 0.02, DESK_H + 0.015)
    lb = BR.box('OFF_LaptopLid', -0.17, 0.17, -0.005, 0.0, 0.0, 0.23, alu, oc, 0.003); lb.parent = lid
    lsm = img_mat('OFF_LaptopScreen', os.path.join(TEX, 'laptop_screen.png'), emit=1.4, rough=0.15)
    ls = plane('OFF_LaptopScreenP', 0.31, 0.195, oc, lsm); ls.parent = lid
    ls.rotation_euler = (np.radians(90), 0, 0); ls.location = (0, -0.0062, 0.118)
    lid.rotation_euler = (np.radians(-14), 0, 0)
    # sticky notes on his monitor, mug, notebook, plant
    for i in range(3):
        sm = img_mat(f'OFF_Sticky{i}', os.path.join(TEX, f'sticky_{i}.png'), rough=0.8)
        st = plane(f'OFF_StickyP{i}', 0.075, 0.075, oc, sm)
        st.rotation_euler = (np.radians(90), np.radians([-6, 4, -2][i]), 0)
        st.location = (-0.33 + i * 0.0 + (0.62 if i == 2 else 0) + (0.0 if i < 2 else 0), 0.214, DESK_H + 0.44 - i * 0.09 if i < 2 else DESK_H + 0.42)
    mug = BR.cylinder('OFF_Mug', 0.04, 0.095, (0.42, -0.08, DESK_H + 0.048), U.simple_mat('OFF_MugM', U.hex2lin('#d8d2c4'), 0.3), oc, 24)
    BR.box('OFF_Notebook', -0.55, -0.32, -0.25, -0.05, DESK_H, DESK_H + 0.012, U.simple_mat('OFF_NB', U.hex2lin('#2c3e50'), 0.6), oc, 0.002)
    pot = BR.cylinder('OFF_Pot', 0.06, 0.12, (0.62, 0.15, DESK_H + 0.06), U.simple_mat('OFF_PotM', U.hex2lin('#b5653f'), 0.7), oc, 24)
    leaf = U.simple_mat('OFF_Leaf', U.hex2lin('#3f6b3a'), 0.5)
    fn = lambda P: smin(smin(capsule(P, (0.62, 0.15, DESK_H + 0.12), (0.57, 0.12, DESK_H + 0.3), 0.03),
                             capsule(P, (0.62, 0.15, DESK_H + 0.12), (0.69, 0.19, DESK_H + 0.28), 0.028), 0.02),
                        capsule(P, (0.62, 0.15, DESK_H + 0.12), (0.63, 0.09, DESK_H + 0.33), 0.025), 0.02)
    U.mesh_obj('OFF_Plant', *mesh_sdf(fn, (0.5, 0.0, DESK_H + 0.08), (0.75, 0.25, DESK_H + 0.38), 0.008), oc, mat=leaf)
    # ID card with lanyard near the desk edge
    cardm = img_mat('OFF_IDCard', os.path.join(TEX, 'id_card.png'), rough=0.25)
    card_piv = bpy.data.objects.new('OFF_IDCardPivot', None); U.link(card_piv, oc)
    card = plane('OFF_IDCard', 0.054, 0.0856, oc, cardm)
    card.parent = card_piv
    so = card.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.0012
    lan = bpy.data.curves.new('OFF_Lanyard', 'CURVE'); lan.dimensions = '3D'
    lan.bevel_depth = 0.0; lan.extrude = 0.006
    sp = lan.splines.new('BEZIER'); sp.bezier_points.add(3)
    for i, bp in enumerate(sp.bezier_points):
        bp.co = (0, 0.045 + i * 0.07, 0); bp.handle_left_type = bp.handle_right_type = 'AUTO'
    lano = bpy.data.objects.new('OFF_Lanyard', lan); U.link(lano, oc); lano.parent = card_piv
    lan.materials.append(U.simple_mat('OFF_LanyardM', U.hex2lin('#b8262f'), 0.6))
    # card animation: rests at edge -> slides -> tips -> tumbles -> floor
    F3a, F3b = 457, 482
    keys = [
        (421, (0.55, -0.33, DESK_H + 0.0015), (0, 0, np.radians(18))),
        (458, (0.55, -0.33, DESK_H + 0.0015), (0, 0, np.radians(18))),
        (465, (0.56, -0.375, DESK_H + 0.0015), (0, 0, np.radians(14))),
        (468, (0.565, -0.40, DESK_H - 0.01), (np.radians(-40), 0, np.radians(10))),
        (472, (0.58, -0.43, DESK_H - 0.22), (np.radians(-140), np.radians(30), np.radians(30))),
        (476, (0.60, -0.46, 0.12), (np.radians(-250), np.radians(55), np.radians(60))),
        (478, (0.61, -0.47, 0.002), (np.radians(-360), np.radians(0), np.radians(75))),
        (480, (0.615, -0.475, 0.012), (np.radians(-352), np.radians(4), np.radians(77))),
        (482, (0.617, -0.476, 0.002), (np.radians(-360), 0, np.radians(78))),
        (516, (0.617, -0.476, 0.002), (np.radians(-360), 0, np.radians(78))),
    ]
    for f, l, r in keys:
        card_piv.location = l; card_piv.rotation_euler = r
        card_piv.keyframe_insert('location', frame=f); card_piv.keyframe_insert('rotation_euler', frame=f)
    # lanyard trailing shape keys (hand-keyed bezier points)
    lpts = {421: [(0, 0.045, 0), (0.0, 0.11, 0.0), (0.02, 0.17, 0.0), (0.06, 0.2, 0)],
            466: [(0, 0.045, 0), (0.0, 0.11, 0.0), (0.0, 0.17, 0.0), (0.02, 0.22, 0)],
            472: [(0, 0.045, 0), (0.01, 0.10, 0.03), (0.03, 0.15, 0.06), (0.04, 0.19, 0.1)],
            478: [(0, 0.045, 0), (0.0, 0.10, 0.0), (0.01, 0.16, 0.0), (0.04, 0.2, 0.0)]}
    for f, pts in lpts.items():
        for bp, co in zip(sp.bezier_points, pts):
            bp.co = co; bp.keyframe_insert('co', frame=f)
    # laptop screen dies in F2 (flicker -> black)
    p = U.principled(lsm)
    for f, v in ((421, 1.4), (445, 1.4), (446, 0.4), (447, 1.2), (448, 0.15), (450, 0.0), (516, 0.0)):
        p.inputs['Emission Strength'].default_value = v; p.inputs['Emission Strength'].keyframe_insert('default_value', frame=f)
    for f, v in ((421, (0.45, 0.45, 0.48)), (447, (0.45, 0.45, 0.48)), (450, (0.006, 0.006, 0.008)), (516, (0.006, 0.006, 0.008))):
        p.inputs['Base Color'].default_value = (*v, 1); p.inputs['Base Color'].keyframe_insert('default_value', frame=f)
    # empty chair drifts / spins slowly (someone just left... or never comes back)
    for f, a, x in ((421, 12, 0.05), (483, 12, 0.05), (498, -16, 0.11), (516, -24, 0.13)):
        my_spin.rotation_euler.z = np.radians(a); my_spin.keyframe_insert('rotation_euler', index=2, frame=f)
        my_root.location.x = x; my_root.keyframe_insert('location', index=0, frame=f)
    # ceiling rows switch off one by one in F5
    for r, m in enumerate(rows):
        e = m.node_tree.nodes['Emission']
        off = 516 - r * 2 if r < 6 else 516
        fo = 503 + (5 - r) * 2
        for f, v in ((421, 6.0), (fo, 6.0), (fo + 1, 0.6), (fo + 2, 0.0), (516, 0.0)):
            e.inputs['Strength'].default_value = v; e.inputs['Strength'].keyframe_insert('default_value', frame=f)
        if r == 0:
            pass
    # lights: cold key + city fill + practical over his desk
    key = bpy.data.objects.new('OFF_Key', bpy.data.lights.new('OFF_Key', 'AREA')); U.link(key, oc)
    key.data.size = 4; key.data.energy = 260; key.data.color = (0.8, 0.88, 1.0); key.location = (0, 0.2, 2.8)
    kfill = bpy.data.objects.new('OFF_CityFill', bpy.data.lights.new('OFF_CityFill', 'AREA')); U.link(kfill, oc)
    kfill.data.size = 6; kfill.data.energy = 120; kfill.data.color = (1.0, 0.6, 0.4)
    kfill.location = (0, -4.5, 1.5); kfill.rotation_euler = (np.radians(-90), 0, 0)
    for f, v in ((421, 260), (503, 260), (514, 30), (516, 15)):
        key.data.energy = v; key.data.keyframe_insert('energy', frame=f)
    w = bpy.data.worlds.new('WLD_Office'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.01, 0.012, 0.018, 1)
    # cameras
    cams = {}

    def cam(name, lens, fstop, keys, focus_obj=None):
        c = bpy.data.objects.new(name, bpy.data.cameras.new(name)); U.link(c, coll)
        t = bpy.data.objects.new(name + '_tgt', None); U.link(t, coll)
        cn = c.constraints.new('TRACK_TO'); cn.target = t; cn.track_axis = 'TRACK_NEGATIVE_Z'; cn.up_axis = 'UP_Y'
        c.data.lens = lens; c.data.dof.use_dof = True; c.data.dof.aperture_fstop = fstop; c.data.clip_start = 0.01
        if focus_obj is not None:
            c.data.dof.focus_object = focus_obj
        for f, loc, look in keys:
            c.location = loc; c.keyframe_insert('location', frame=f)
            t.location = look; t.keyframe_insert('location', frame=f)
        if focus_obj is None:
            c.data.dof.focus_distance = (Vector(keys[0][1]) - Vector(keys[0][2])).length
        cams[name] = c
        return c, t
    cam('CAM_F1', 35, 2.8, [(421, (1.3, -1.9, 1.45), (0.0, 0.0, 0.9)), (438, (1.05, -1.55, 1.35), (0.0, 0.0, 0.9))])
    cam('CAM_F2', 50, 2.2, [(439, (0.42, -0.50, 1.00), (0.0, 0.0, DESK_H + 0.12)), (456, (0.36, -0.42, 0.97), (0.0, 0.0, DESK_H + 0.12))])
    c3, t3 = cam('CAM_F3', 32, 2.8, [(457, (1.20, -0.95, 0.62), (0.57, -0.36, DESK_H - 0.02)),
                                    (468, (1.18, -0.96, 0.52), (0.58, -0.42, 0.42)),
                                    (482, (1.14, -0.98, 0.34), (0.61, -0.47, 0.03))], focus_obj=card_piv)
    cam('CAM_F4', 40, 2.5, [(483, (-0.9, -1.6, 0.95), (0.05, -0.6, 0.62)), (498, (-0.75, -1.45, 0.92), (0.06, -0.6, 0.62))])
    cam('CAM_F5', 24, 4.0, [(499, (0.4, -2.6, 1.7), (0.0, 0.4, 0.9)), (516, (0.5, -3.8, 2.0), (0.0, 0.5, 0.9))])
    for name, first, last, scn, camname, _ in T.SHOTS:
        if scn == 'Office':
            m = sc.timeline_markers.new(name, frame=first); m.camera = cams[camname]
    sc.camera = cams['CAM_F1']
    RS.apply(sc, 'final')
    return sc
