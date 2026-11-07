"""SCENE SET — Arjun's bedroom (modern middle-class Indian apartment, night).

World axes: +Y towards the headboard, +X = character's left (wardrobe wall),
-X = character's right (bedside table + window wall). Floor z=0. Metres.
"""
import bpy, os, bmesh
import numpy as np
from mathutils import Vector, Matrix
import bl_util as U
from sdf import (round_box, ellipsoid, smin, smax, value_noise3, mesh_sdf,
                 capsule, round_cone, sphere)

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, '..', 'assets', 'textures')

ROOM = dict(x0=-1.9, x1=1.9, y0=-1.9, y1=1.85, h=2.95)
MATTRESS_TOP = 0.55
BED = dict(x0=-0.78, x1=0.78, y0=-0.42, y1=1.78)
WIN = dict(y0=-0.10, y1=1.10, z0=0.95, z1=2.15)       # on the x0 wall
TABLE = dict(x0=-1.24, x1=-0.83, y0=1.18, y1=1.64, h=0.58)
CLOCK_POS = Vector((-1.05, 1.47, TABLE['h']))


# ----------------------------------------------------------- materials
def mat_wall():
    m = U.new_mat('SET_Wall'); N, L = U.nodes(m); p = U.principled(m)
    p.inputs['Base Color'].default_value = (*U.hex2lin('#c9cdb8'), 1)
    p.inputs['Roughness'].default_value = 0.9
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 40; nz.inputs['Detail'].default_value = 8
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    b = N.new('ShaderNodeBump'); b.inputs['Strength'].default_value = 0.05
    L.new(nz.outputs['Fac'], b.inputs['Height']); L.new(b.outputs['Normal'], p.inputs['Normal'])
    return m


def mat_floor():
    m = U.new_mat('SET_FloorTile'); N, L = U.nodes(m); p = U.principled(m)
    tc = N.new('ShaderNodeTexCoord')
    br = N.new('ShaderNodeTexBrick'); br.offset = 0.0
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Brick Width'].default_value = 0.6; br.inputs['Row Height'].default_value = 0.6
    br.inputs['Mortar Size'].default_value = 0.003
    br.inputs['Color1'].default_value = (*U.hex2lin('#cdbfa8'), 1)
    br.inputs['Color2'].default_value = (*U.hex2lin('#c4b59c'), 1)
    br.inputs['Mortar'].default_value = (*U.hex2lin('#8c8070'), 1)
    L.new(tc.outputs['Object'], br.inputs['Vector'])
    L.new(br.outputs['Color'], p.inputs['Base Color'])
    rr = N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.6; rr.inputs['To Max'].default_value = 0.16
    L.new(br.outputs['Fac'], rr.inputs['Value'])
    L.new(rr.outputs['Result'], p.inputs['Roughness'])
    return m


def mat_wood(name='SET_Wood', col='#5a3a24', scale=6):
    m = U.new_mat(name); N, L = U.nodes(m); p = U.principled(m)
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1, 1, 12)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    w = N.new('ShaderNodeTexWave'); w.inputs['Scale'].default_value = scale
    w.inputs['Distortion'].default_value = 6; w.inputs['Detail'].default_value = 4
    L.new(mp.outputs['Vector'], w.inputs['Vector'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    c = np.array(U.hex2lin(col))
    mix.inputs['A'].default_value = (*c, 1); mix.inputs['B'].default_value = (*(c * 0.6), 1)
    L.new(w.outputs['Fac'], mix.inputs['Factor']); L.new(mix.outputs['Result'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.45
    p.inputs['Coat Weight'].default_value = 0.3
    return m


def mat_sheet():
    """Soft indigo-striped cotton bedsheet."""
    m = U.new_mat('SET_Bedsheet'); N, L = U.nodes(m); p = U.principled(m)
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    w1 = N.new('ShaderNodeTexWave'); w1.wave_type = 'BANDS'; w1.bands_direction = 'X'
    w1.inputs['Scale'].default_value = 7; w1.wave_profile = 'SIN'
    L.new(tc.outputs['Object'], w1.inputs['Vector'])
    w2 = N.new('ShaderNodeTexWave'); w2.wave_type = 'BANDS'; w2.bands_direction = 'X'
    w2.inputs['Scale'].default_value = 28
    L.new(tc.outputs['Object'], w2.inputs['Vector'])
    r1 = N.new('ShaderNodeValToRGB'); e = r1.color_ramp.elements
    e[0].position = 0.80; e[0].color = (*U.hex2lin('#d9d3c2'), 1)
    e[1].position = 0.86; e[1].color = (*U.hex2lin('#3b4f86'), 1)
    L.new(w1.outputs['Fac'], r1.inputs['Fac'])
    r2 = N.new('ShaderNodeMath'); r2.operation = 'GREATER_THAN'; r2.inputs[1].default_value = 0.93
    L.new(w2.outputs['Fac'], r2.inputs[0])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    L.new(r2.outputs[0], mix.inputs['Factor']); L.new(r1.outputs['Color'], mix.inputs['A'])
    mix.inputs['B'].default_value = (*U.hex2lin('#9aa6c4'), 1)
    L.new(mix.outputs['Result'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.9
    p.inputs['Sheen Weight'].default_value = 0.5
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 400
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    b = N.new('ShaderNodeBump'); b.inputs['Strength'].default_value = 0.08
    L.new(nz.outputs['Fac'], b.inputs['Height']); L.new(b.outputs['Normal'], p.inputs['Normal'])
    return m


def mat_cotton(name, col, rough=0.9):
    m = U.simple_mat(name, U.hex2lin(col), rough=rough)
    p = U.principled(m); p.inputs['Sheen Weight'].default_value = 0.4
    return m


def mat_curtain():
    m = U.new_mat('SET_Curtain'); N, L = U.nodes(m); p = U.principled(m)
    p.inputs['Base Color'].default_value = (*U.hex2lin('#b9a98a'), 1)
    p.inputs['Roughness'].default_value = 0.8
    p.inputs['Transmission Weight'].default_value = 0.0
    p.inputs['Subsurface Weight'].default_value = 0.0
    # thin translucent cloth: mix diffuse with translucent
    out = N.get('Material Output')
    tr = N.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = (*U.hex2lin('#d8b98a'), 1)
    mx = N.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.45
    L.new(p.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], out.inputs[0])
    return m


def mat_glass():
    m = U.new_mat('SET_Glass'); nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.02
    lp = nt.nodes.new('ShaderNodeLightPath')
    mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.12
    mx2 = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
    nt.links.new(lp.outputs['Is Shadow Ray'], mx2.inputs[0])
    nt.links.new(mx.outputs[0], mx2.inputs[1]); nt.links.new(tr.outputs[0], mx2.inputs[2])
    nt.links.new(mx2.outputs[0], o.inputs[0])
    return m


# ----------------------------------------------------------- geometry helpers
def box(name, x0, x1, y0, y1, z0, z1, mat, coll, bevel=0.0, segs=3):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = (x0 + x1) / 2 + v.co.x * (x1 - x0)
        v.co.y = (y0 + y1) / 2 + v.co.y * (y1 - y0)
        v.co.z = (z0 + z1) / 2 + v.co.z * (z1 - z0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); U.link(ob, coll)
    me.materials.append(mat)
    if bevel > 0:
        b = ob.modifiers.new('bevel', 'BEVEL'); b.width = bevel; b.segments = segs
        b.limit_method = 'NONE'
        me.shade_smooth()
        ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
    return ob


def cylinder(name, r, depth, loc, mat, coll, verts=32, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r, depth=depth)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); U.link(ob, coll)
    ob.location = loc; ob.rotation_euler = rot
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = abs(p.normal.z) < 0.5
    return ob


def grid(name, nx, ny, sx, sy, coll, mat=None):
    xs = np.linspace(-sx / 2, sx / 2, nx); ys = np.linspace(-sy / 2, sy / 2, ny)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    V = np.c_[X.ravel(), Y.ravel(), np.zeros(X.size)]
    F = [[i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1]
         for i in range(nx - 1) for j in range(ny - 1)]
    ob = U.mesh_obj(name, V, F, coll, mat=mat)
    me = ob.data
    uv = me.uv_layers.new(name='UVMap')
    lv = np.array([l.vertex_index for l in me.loops])
    uvs = np.c_[(V[lv, 0] / sx + 0.5), (V[lv, 1] / sy + 0.5)]
    uv.data.foreach_set('uv', uvs.astype(np.float32).ravel())
    return ob, X, Y


def set_grid_z(ob, Z):
    V = U.mesh_verts(ob); V[:, 2] = Z.ravel()
    ob.data.vertices.foreach_set('co', V.astype(np.float32).ravel()); ob.data.update()


def set_grid_verts(ob, V):
    ob.data.vertices.foreach_set('co', np.asarray(V, np.float32).ravel()); ob.data.update()


# ----------------------------------------------------------- room shell
def build_shell(coll):
    R = ROOM
    wall = mat_wall()
    floor, _, _ = grid('SET_Floor', 2, 2, R['x1'] - R['x0'], R['y1'] - R['y0'], coll, mat_floor())
    floor.location = ((R['x0'] + R['x1']) / 2, (R['y0'] + R['y1']) / 2, 0)
    ceil = box('SET_Ceiling', R['x0'], R['x1'], R['y0'], R['y1'], R['h'], R['h'] + 0.1, wall, coll)
    box('SET_WallBack', R['x0'], R['x1'], R['y1'], R['y1'] + 0.1, 0, R['h'], wall, coll)
    box('SET_WallFront', R['x0'], R['x1'], R['y0'] - 0.1, R['y0'], 0, R['h'], wall, coll)
    box('SET_WallRight', R['x1'], R['x1'] + 0.1, R['y0'], R['y1'], 0, R['h'], wall, coll)
    # window wall (x0) with an opening
    W = WIN; x0 = R['x0']
    box('SET_WallWin_a', x0 - 0.12, x0, R['y0'], W['y0'], 0, R['h'], wall, coll)
    box('SET_WallWin_b', x0 - 0.12, x0, W['y1'], R['y1'], 0, R['h'], wall, coll)
    box('SET_WallWin_c', x0 - 0.12, x0, W['y0'], W['y1'], 0, W['z0'], wall, coll)
    box('SET_WallWin_d', x0 - 0.12, x0, W['y0'], W['y1'], W['z1'], R['h'], wall, coll)
    # skirting
    sk = U.simple_mat('SET_Skirting', U.hex2lin('#8a7d6a'), rough=0.3)
    box('SET_Skirt_back', R['x0'], R['x1'], R['y1'] - 0.012, R['y1'], 0, 0.08, sk, coll)
    box('SET_Skirt_right', R['x1'] - 0.012, R['x1'], R['y0'], R['y1'], 0, 0.08, sk, coll)
    box('SET_Skirt_left', R['x0'], R['x0'] + 0.012, R['y0'], R['y1'], 0, 0.08, sk, coll)
    return wall


def build_window(coll):
    W = WIN; x0 = ROOM['x0']
    frame = U.simple_mat('SET_WinFrame', U.hex2lin('#d8d6d0'), rough=0.35, metal=0.2)
    iron = U.simple_mat('SET_Iron', U.hex2lin('#1c1d20'), rough=0.45, metal=0.7)
    t = 0.05
    box('SET_WinF_top', x0 - 0.1, x0 + 0.02, W['y0'], W['y1'], W['z1'] - t, W['z1'], frame, coll)
    box('SET_WinF_bot', x0 - 0.1, x0 + 0.05, W['y0'] - 0.03, W['y1'] + 0.03, W['z0'], W['z0'] + t, frame, coll)
    box('SET_WinF_l', x0 - 0.1, x0 + 0.02, W['y0'], W['y0'] + t, W['z0'], W['z1'], frame, coll)
    box('SET_WinF_r', x0 - 0.1, x0 + 0.02, W['y1'] - t, W['y1'], W['z0'], W['z1'], frame, coll)
    box('SET_WinF_mid', x0 - 0.09, x0 - 0.05, (W['y0'] + W['y1']) / 2 - 0.02, (W['y0'] + W['y1']) / 2 + 0.02, W['z0'], W['z1'], frame, coll)
    # one sliding pane is open (slid behind the other) -> breeze comes in
    glass = mat_glass()
    ym = (W['y0'] + W['y1']) / 2
    box('SET_WinGlass', x0 - 0.075, x0 - 0.07, ym, W['y1'] - t, W['z0'] + t, W['z1'] - t, glass, coll)
    # iron grill: vertical bars + two rails (very typical)
    n = 11
    for i in range(n):
        y = W['y0'] + 0.06 + i * (W['y1'] - W['y0'] - 0.12) / (n - 1)
        cylinder(f'SET_Grill_v{i}', 0.006, W['z1'] - W['z0'] - 0.08, (x0 - 0.035, y, (W['z0'] + W['z1']) / 2), iron, coll, 10)
    for z in (W['z0'] + 0.35, W['z1'] - 0.35):
        box(f'SET_Grill_h{z:.2f}', x0 - 0.045, x0 - 0.025, W['y0'] + 0.03, W['y1'] - 0.03, z - 0.008, z + 0.008, iron, coll)
    # curtain rod + curtains
    rod = U.simple_mat('SET_Rod', U.hex2lin('#6b5a44'), rough=0.3, metal=0.8)
    cylinder('SET_CurtainRod', 0.012, W['y1'] - W['y0'] + 0.7, (x0 + 0.08, ym, W['z1'] + 0.18), rod, coll, 16, rot=(np.radians(90), 0, 0))
    cm = mat_curtain()
    curt = []
    for side, (ya, yb) in (('a', (W['y0'] - 0.35, W['y0'] + 0.15)), ('b', (W['y1'] - 0.25, W['y1'] + 0.35))):
        width = yb - ya
        nx, ny = 70, 60
        ob, X, Y = grid('SET_Curtain_' + side, nx, ny, width, W['z1'] + 0.18 - 0.55, coll, cm)
        u = (X + width / 2) / width
        v = (Y - Y.min()) / (Y.max() - Y.min())       # 0 bottom .. 1 top
        pleat = 0.035 * np.sin(u * np.pi * 2 * 6) * (0.7 + 0.3 * v)
        V = np.c_[pleat.ravel(), (ya + width / 2 + X).ravel(), (0.55 + (Y - Y.min())).ravel()]
        set_grid_verts(ob, V)
        ob.location = (x0 + 0.11, 0, 0)
        ob.data.shade_smooth()
        vg = ob.vertex_groups.new(name='flutter')
        w = (1 - v.ravel()) ** 1.5
        for val in np.unique(np.round(w, 2)):
            vg.add(np.nonzero(np.round(w, 2) == val)[0].tolist(), float(val), 'REPLACE')
        so = ob.modifiers.new('solid', 'SOLIDIFY'); so.thickness = 0.003
        curt.append(ob)
    return curt


def animate_curtains(curtains, frames):
    """Gentle breeze: displace driven by a slowly drifting texture."""
    tex = bpy.data.textures.new('SET_Breeze', 'CLOUDS'); tex.noise_scale = 0.6
    drift = bpy.data.objects.new('SET_BreezeDrift', None); U.link(drift)
    drift.location = (0, 0, 0); drift.keyframe_insert('location', frame=0)
    drift.location = (0.0, 0.5, 0.35); drift.keyframe_insert('location', frame=frames)
    for fc in drift.animation_data.action.fcurves if hasattr(drift.animation_data.action, 'fcurves') else []:
        for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    for ob in curtains:
        d = ob.modifiers.new('breeze', 'DISPLACE'); d.texture = tex
        d.texture_coords = 'OBJECT'; d.texture_coords_object = drift
        d.vertex_group = 'flutter'; d.strength = 0.07; d.mid_level = 0.5
        d.direction = 'X'
        ob.modifiers.move(len(ob.modifiers) - 1, 0)


def build_skyline(coll):
    import skyline
    path = os.path.join(TEX, 'city_skyline.png')
    if not os.path.exists(path):
        skyline.make_skyline(path)
    m = U.new_mat('SET_Skyline'); nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Strength'].default_value = 1.6
    im = nt.nodes.new('ShaderNodeTexImage'); im.image = bpy.data.images.load(path, check_existing=True)
    nt.links.new(im.outputs['Color'], e.inputs['Color']); nt.links.new(e.outputs[0], o.inputs[0])
    ob, _, _ = grid('SET_Skyline', 2, 2, 40, 15, coll, m)
    ob.rotation_euler = (np.radians(90), 0, np.radians(90))
    ob.location = (-16, 0.5, 1.2)
    ob.visible_shadow = False
    return ob


# ----------------------------------------------------------- furniture
def build_bed(coll):
    B = BED
    wood = mat_wood('SET_BedWood', '#4a2e1c')
    box('SET_BedFrame', B['x0'] - 0.04, B['x1'] + 0.04, B['y0'] - 0.04, B['y1'], 0.12, 0.36, wood, coll, 0.01)
    box('SET_Headboard', B['x0'] - 0.06, B['x1'] + 0.06, B['y1'], B['y1'] + 0.06, 0.1, 1.15, wood, coll, 0.015)
    for x in (B['x0'], B['x1'] - 0.06):
        for y in (B['y0'] - 0.04, B['y1'] - 0.06):
            box('SET_BedLeg', x, x + 0.06, y, y + 0.06, 0, 0.14, wood, coll, 0.005)
    fn = lambda P: round_box(P, ((B['x0'] + B['x1']) / 2, (B['y0'] + B['y1']) / 2, 0.455),
                             ((B['x1'] - B['x0']) / 2, (B['y1'] - B['y0']) / 2, 0.095), 0.05)
    v, f = mesh_sdf(fn, (B['x0'] - 0.02, B['y0'] - 0.02, 0.34), (B['x1'] + 0.02, B['y1'] + 0.02, 0.57), 0.02)
    mt = U.mesh_obj('SET_Mattress', v, f, coll, mat=mat_cotton('SET_MattressCover', '#d8d2c4'))
    return mt


def pillow_sdf(c, half, dent=None):
    def fn(P):
        q = P - np.asarray(c)
        # puffy pillow: rounded box squashed at the edges
        edge = np.clip(1 - (np.abs(q[:, 0]) / half[0]) ** 4 - (np.abs(q[:, 1]) / half[1]) ** 4, 0, 1)
        thick = half[2] * (0.35 + 0.65 * np.sqrt(edge))
        d = np.maximum(np.maximum(np.abs(q[:, 0]) - half[0], np.abs(q[:, 1]) - half[1]), np.abs(q[:, 2]) - thick)
        d = d + 0.003 * value_noise3(P, 30, 9)
        if dent is not None:
            d = smax(d, -ellipsoid(P, dent[0], dent[1]), 0.03)
        return d
    return fn


def build_pillows(coll, head_dent):
    m = mat_cotton('SET_PillowCover', '#e4e0d6', 0.85)
    out = []
    for name, cx, dent in (('SET_Pillow_A', -0.30, head_dent), ('SET_Pillow_B', 0.38, None)):
        c = (cx, 1.48, MATTRESS_TOP + 0.075)
        half = (0.34, 0.22, 0.085)
        fn = pillow_sdf(c, half, dent)
        v, f = mesh_sdf(fn, (cx - 0.37, 1.23, MATTRESS_TOP - 0.03), (cx + 0.37, 1.73, MATTRESS_TOP + 0.18), 0.008)
        ob = U.mesh_obj(name, v, f, coll, mat=m)
        U.smooth_mesh(ob, 3, 0.5)
        out.append(ob)
    return out


def build_blanket(coll, body_top_fn, edge_y=0.84):
    """Heightfield drape over mattress + hidden legs/hips, with a turned-down edge."""
    from scipy.ndimage import gaussian_filter
    B = BED
    nx, ny = 150, 200
    x0, x1 = B['x0'] - 0.13, B['x1'] + 0.13
    y0, y1 = B['y0'] - 0.13, edge_y
    xs = np.linspace(x0, x1, nx); ys = np.linspace(y0, y1, ny)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    top = np.full(X.shape, MATTRESS_TOP + 0.012)
    body = body_top_fn(X, Y)
    Z = np.maximum(top, body + 0.012)
    # drape over the mattress edges
    dx = np.maximum(B['x0'] - X, X - B['x1']); dx = np.maximum(dx, 0)
    dy = np.maximum(B['y0'] - Y, 0)
    dd = np.sqrt(dx ** 2 + dy ** 2)
    Z = gaussian_filter(Z, 3.5)
    Z = Z - np.where(dd > 0, np.minimum(dd * 9.0, 0.40), 0)
    Z = gaussian_filter(Z, 1.0)
    rng = np.random.default_rng(3)
    P = np.c_[X.ravel(), Y.ravel(), np.zeros(X.size)]
    wr = (0.007 * value_noise3(P * np.array([1, 3, 1]), 9, 1) + 0.004 * value_noise3(P, 22, 2)).reshape(X.shape)
    Z = Z + wr * (Z > MATTRESS_TOP + 0.005)
    # drape: push hanging part outward slightly
    Xo = X + np.sign(X) * np.where(dx > 0, 0.012 * np.minimum(dd * 8, 1), 0)
    ob, _, _ = grid('SET_Blanket', nx, ny, x1 - x0, y1 - y0, coll, mat_sheet())
    set_grid_verts(ob, np.c_[Xo.ravel(), Y.ravel(), Z.ravel()])
    ob.data.shade_smooth()
    so = ob.modifiers.new('solid', 'SOLIDIFY'); so.thickness = 0.006
    # turned-down fold at the edge
    fy = np.linspace(edge_y - 0.16, edge_y, 12)
    FX, FY = np.meshgrid(xs, fy, indexing='ij')
    zi = np.array([np.interp(fy, ys, Z[i]) for i in range(nx)])
    fold, _, _ = grid('SET_BlanketFold', nx, 12, x1 - x0, 0.16, coll, bpy.data.materials['SET_Bedsheet'])
    FZ = zi + 0.008 + 0.004 * np.sin(FY * 60)
    set_grid_verts(fold, np.c_[FX.ravel(), FY.ravel(), FZ.ravel()])
    fold.data.shade_smooth()
    so = fold.modifiers.new('solid', 'SOLIDIFY'); so.thickness = 0.008
    return ob, fold


def build_table(coll):
    T = TABLE
    wood = mat_wood('SET_TableWood', '#6b4a30')
    box('SET_Table', T['x0'], T['x1'], T['y0'], T['y1'], 0.08, T['h'], wood, coll, 0.008)
    box('SET_TableDrawer', T['x1'] - 0.001, T['x1'] + 0.004, T['y0'] + 0.03, T['y1'] - 0.03, 0.38, 0.52, wood, coll, 0.003)
    brass = U.simple_mat('SET_Brass', U.hex2lin('#b08d57'), rough=0.3, metal=1)
    cylinder('SET_Knob', 0.01, 0.02, (T['x1'] + 0.012, (T['y0'] + T['y1']) / 2, 0.45), brass, coll, 16, rot=(0, np.radians(90), 0))
    # steel water bottle
    steel = U.simple_mat('SET_Steel', (0.6, 0.6, 0.62), rough=0.25, metal=1)
    cylinder('SET_Bottle', 0.035, 0.24, (-1.16, 1.24, T['h'] + 0.12), steel, coll, 32)
    cylinder('SET_BottleCap', 0.022, 0.03, (-1.16, 1.24, T['h'] + 0.255), U.simple_mat('SET_Cap', (0.02, 0.02, 0.02), 0.4), coll, 24)
    # books
    for i, (c, th) in enumerate((('#7a2e2a', 0.03), ('#284a6b', 0.025), ('#c9b48a', 0.02))):
        z = T['h'] + sum(t for _, t in (('', 0.03), ('', 0.025), ('', 0.02))[:i])
        b = box(f'SET_Book{i}', -1.22, -1.05, 1.48, 1.62, z, z + th, U.simple_mat(f'SET_BookM{i}', U.hex2lin(c), 0.6), coll, 0.002)
        b.rotation_euler.z = np.radians(4 * (i - 1))
    return


def build_clock(coll, text='2:17'):
    body = U.simple_mat('SET_ClockBody', (0.012, 0.012, 0.014), rough=0.25)
    face = U.simple_mat('SET_ClockFace', (0.002, 0.002, 0.002), rough=0.05, coat=1.0)
    c = CLOCK_POS
    ob = box('SET_Clock', -0.07, 0.07, -0.03, 0.03, 0, 0.06, body, coll, 0.008)
    ob.location = c
    fc = box('SET_ClockScreen', -0.062, 0.062, -0.0305, -0.029, 0.007, 0.053, face, coll)
    fc.parent = ob
    bpy.ops.object.text_add()
    t = bpy.context.object; t.name = 'SET_ClockDigits'
    for col in t.users_collection: col.objects.unlink(t)
    U.link(t, coll)
    t.data.body = text
    fnt = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
    if os.path.exists(fnt):
        t.data.font = bpy.data.fonts.load(fnt, check_existing=True)
    t.data.size = 0.04; t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'
    t.data.extrude = 0.0005
    t.data.materials.append(U.emission_mat('SET_ClockLED', (1.0, 0.16, 0.05), 18))
    t.parent = ob
    t.location = (0, -0.0315, 0.030); t.rotation_euler = (np.radians(90), 0, 0)
    # clock faces the bed (rotate towards +x / -y)
    ob.rotation_euler = (0, 0, np.radians(70))
    glow = bpy.data.objects.new('SET_ClockGlow', bpy.data.lights.new('SET_ClockGlow', 'POINT'))
    U.link(glow, coll); glow.parent = ob; glow.location = (0, -0.06, 0.03)
    glow.data.energy = 0.25; glow.data.color = (1, 0.2, 0.08); glow.data.shadow_soft_size = 0.02
    return ob


def build_fan(coll, frames):
    m = U.simple_mat('SET_FanWhite', U.hex2lin('#8d8a84'), rough=0.4)
    mb = U.simple_mat('SET_FanBlade', U.hex2lin('#4a4038'), rough=0.5)
    h = ROOM['h']
    cx, cy = 0.0, 0.55
    cylinder('SET_FanCanopy', 0.06, 0.04, (cx, cy, h - 0.02), m, coll, 32)
    cylinder('SET_FanRod', 0.012, 0.32, (cx, cy, h - 0.2), m, coll, 12)
    hub = cylinder('SET_FanHub', 0.11, 0.09, (cx, cy, h - 0.40), m, coll, 48)
    rot = bpy.data.objects.new('SET_FanRotor', None); U.link(rot, coll)
    rot.location = (cx, cy, h - 0.43)
    for i in range(3):
        b = box(f'SET_FanBlade{i}', 0.12, 0.62, -0.055, 0.055, -0.004, 0.004, mb, coll, 0.003)
        b.parent = rot; b.rotation_euler = (np.radians(8), 0, np.radians(120 * i))
        b.data.polygons.foreach_set('use_smooth', [False] * len(b.data.polygons))
    cylinder('SET_FanCap', 0.07, 0.03, (cx, cy, h - 0.46), m, coll, 32).parent = None
    # slow spin (~0.55 rev/s) - linear keys
    rot.rotation_euler = (0, 0, 0); rot.keyframe_insert('rotation_euler', index=2, frame=0)
    rot.rotation_euler = (0, 0, -2 * np.pi * 0.55 * frames / 24); rot.keyframe_insert('rotation_euler', index=2, frame=frames)
    return rot


def build_wardrobe(coll):
    x1 = ROOM['x1']
    wood = mat_wood('SET_WardrobeWood', '#7a5638', 4)
    box('SET_Wardrobe', x1 - 0.58, x1 - 0.005, 0.2, 1.35, 0.0, 2.05, wood, coll, 0.01)
    box('SET_WardrobeSplit', x1 - 0.585, x1 - 0.58, 0.77, 0.78, 0.05, 2.0, U.simple_mat('SET_Dark', (0.02, 0.015, 0.01), 0.5), coll)
    brass = bpy.data.materials['SET_Brass']
    for y in (0.74, 0.81):
        cylinder('SET_WHandle', 0.008, 0.18, (x1 - 0.6, y, 1.05), brass, coll, 12)
    # mirror strip
    mir = U.simple_mat('SET_Mirror', (0.9, 0.9, 0.9), rough=0.02, metal=1)
    box('SET_WMirror', x1 - 0.584, x1 - 0.581, 0.3, 0.7, 0.6, 1.8, mir, coll)


def build_chair(coll):
    wood = mat_wood('SET_ChairWood', '#3d2a1c')
    x, y = 1.05, -1.25
    box('SET_ChairSeat', x - 0.22, x + 0.22, y - 0.22, y + 0.22, 0.44, 0.48, wood, coll, 0.01)
    for dx in (-0.2, 0.17):
        for dy in (-0.2, 0.17):
            box('SET_ChairLeg', x + dx, x + dx + 0.03, y + dy, y + dy + 0.03, 0, 0.44, wood, coll)
    box('SET_ChairBack', x - 0.22, x + 0.22, y - 0.23, y - 0.2, 0.48, 0.95, wood, coll, 0.01)
    # backpack (laptop bag) leaning on chair + clothes on backrest
    fn = lambda P: smin(round_box(P, (x + 0.02, y + 0.05, 0.66), (0.15, 0.08, 0.2), 0.06),
                        round_box(P, (x + 0.02, y + 0.13, 0.6), (0.11, 0.03, 0.1), 0.03), 0.03)
    v, f = mesh_sdf(fn, (x - 0.2, y - 0.1, 0.4), (x + 0.22, y + 0.22, 0.9), 0.01)
    U.mesh_obj('SET_Backpack', v, f, coll, mat=U.simple_mat('SET_BagFabric', U.hex2lin('#2c3036'), 0.7))
    fn2 = lambda P: smin(round_box(P, (x, y - 0.21, 0.93), (0.24, 0.035, 0.03), 0.025),
                         round_box(P, (x - 0.1, y - 0.21, 0.78), (0.09, 0.03, 0.15), 0.02), 0.03) + 0.004 * value_noise3(P, 60, 1)
    v, f = mesh_sdf(fn2, (x - 0.3, y - 0.3, 0.6), (x + 0.3, y - 0.1, 1.0), 0.008)
    U.mesh_obj('SET_ClothOnChair', v, f, coll, mat=mat_cotton('SET_Shirt', '#8a6d5a'))


def build_wall_details(coll):
    R = ROOM
    # switchboard with tiny red indicator (by the bed, back wall)
    sw = U.simple_mat('SET_Switch', U.hex2lin('#e8e6e0'), rough=0.3)
    box('SET_Switchboard', -1.35, -1.05, R['y1'] - 0.02, R['y1'], 0.95, 1.07, sw, coll, 0.004)
    led = U.emission_mat('SET_SwitchLED', (1, 0.05, 0.02), 30)
    box('SET_SwitchLEDb', -1.12, -1.11, R['y1'] - 0.023, R['y1'] - 0.02, 1.04, 1.05, led, coll)
    # wall calendar
    from PIL import Image, ImageDraw, ImageFont
    p = os.path.join(TEX, 'calendar.png')
    if not os.path.exists(p):
        im = Image.new('RGB', (300, 420), (236, 232, 222)); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 300, 200], fill=(70, 110, 140))
        f = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Bold.otf', 34)
        d.text((150, 230), 'NOVEMBER', fill=(160, 40, 40), font=f, anchor='mm')
        fs = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Regular.otf', 18)
        for i in range(30):
            d.text((30 + (i % 7) * 40, 270 + (i // 7) * 30), str(i + 1), fill=(40, 40, 40), font=fs)
        im.save(p)
    m = U.new_mat('SET_Calendar'); N, L = U.nodes(m); pr = U.principled(m)
    im = N.new('ShaderNodeTexImage'); im.image = bpy.data.images.load(p, check_existing=True)
    L.new(im.outputs['Color'], pr.inputs['Base Color']); pr.inputs['Roughness'].default_value = 0.6
    cal, _, _ = grid('SET_Calendar', 2, 2, 0.3, 0.42, coll, m)
    cal.rotation_euler = (np.radians(90), 0, np.radians(-90)); cal.location = (R['x1'] - 0.01, -0.6, 1.55)
    # framed photo above headboard
    fr = mat_wood('SET_FrameWood', '#2a1d14')
    box('SET_PhotoFrame', 0.18, 0.62, R['y1'] - 0.03, R['y1'], 1.45, 1.75, fr, coll, 0.005)
    art = U.simple_mat('SET_PhotoArt', U.hex2lin('#8a6a4a'), 0.7)
    box('SET_PhotoArt', 0.21, 0.59, R['y1'] - 0.031, R['y1'] - 0.03, 1.48, 1.72, art, coll)
    # tube light (off) on the right wall
    tl = U.simple_mat('SET_Tube', (0.85, 0.85, 0.85), 0.2)
    cylinder('SET_TubeLight', 0.014, 1.2, (R['x1'] - 0.04, -0.2, 2.35), tl, coll, 16, rot=(np.radians(90), 0, 0))
    # rug
    rug, _, _ = grid('SET_Rug', 2, 2, 0.7, 1.3, coll, mat_cotton('SET_RugMat', '#6b3b33'))
    rug.location = (1.12, 0.65, 0.004)
    # charging cable on table edge (simple curve)
    cu = bpy.data.curves.new('SET_Cable', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0025
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(2)
    for bp, co in zip(sp.bezier_points, ((-1.2, 1.63, 0.3), (-0.95, 1.6, TABLE['h'] + 0.005), (-0.86, 1.62, TABLE['h'] + 0.005))):
        bp.co = co; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    cob = bpy.data.objects.new('SET_Cable', cu); U.link(cob, coll)
    cu.materials.append(U.simple_mat('SET_CableMat', (0.85, 0.85, 0.85), 0.4))


def build_lights(coll):
    out = {}
    W = WIN
    # moonlight through the window (casts grill shadows across the bed)
    sun = bpy.data.objects.new('LGT_Moon', bpy.data.lights.new('LGT_Moon', 'SUN')); U.link(sun, coll)
    sun.data.energy = 4.5; sun.data.color = (0.55, 0.68, 1.0); sun.data.angle = np.radians(1.2)
    d = Vector((1.6, 0.92, -0.74)).normalized()
    sun.rotation_euler = (-d).to_track_quat('Z', 'Y').to_euler()
    # Spot through window to tightly control the moon patch
    out['moon'] = sun
    # city glow outside window (warm, soft)
    city = bpy.data.objects.new('LGT_CityGlow', bpy.data.lights.new('LGT_CityGlow', 'AREA')); U.link(city, coll)
    city.data.shape = 'RECTANGLE'; city.data.size = 1.3; city.data.size_y = 1.2
    city.data.energy = 3.5; city.data.color = (1.0, 0.62, 0.38)
    city.location = (ROOM['x0'] - 0.6, (W['y0'] + W['y1']) / 2, (W['z0'] + W['z1']) / 2 - 0.2)
    city.rotation_euler = (0, np.radians(-90), 0)
    out['city'] = city
    # cool moon-bounce fill from the window side (keeps faces readable)
    fill = bpy.data.objects.new('LGT_MoonFill', bpy.data.lights.new('LGT_MoonFill', 'AREA')); U.link(fill, coll)
    fill.data.shape = 'RECTANGLE'; fill.data.size = 1.2; fill.data.size_y = 1.1
    fill.data.energy = 6; fill.data.color = (0.5, 0.62, 1.0)
    fill.location = (ROOM['x0'] + 0.15, (W['y0'] + W['y1']) / 2, (W['z0'] + W['z1']) / 2)
    fill.rotation_euler = (0, np.radians(-90), 0)
    fill.visible_camera = False
    out['fill'] = fill
    # faint ceiling bounce
    amb = bpy.data.objects.new('LGT_Ambient', bpy.data.lights.new('LGT_Ambient', 'AREA')); U.link(amb, coll)
    amb.data.size = 2.5; amb.data.energy = 3; amb.data.color = (0.45, 0.55, 0.9)
    amb.location = (0.3, 0.4, ROOM['h'] - 0.05)
    amb.visible_camera = False
    out['ambient'] = amb
    return out


def setup_world(scene):
    w = bpy.data.worlds.new('WLD_Night'); scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.004, 0.006, 0.014, 1); bg.inputs['Strength'].default_value = 1.0


def build_bedroom(coll, frames, body_top_fn, head_dent):
    build_shell(coll)
    curt = build_window(coll)
    animate_curtains(curt, frames)
    build_skyline(coll)
    build_bed(coll)
    pillows = build_pillows(coll, head_dent)
    blanket = build_blanket(coll, body_top_fn)
    build_table(coll)
    clock = build_clock(coll)
    fan = build_fan(coll, frames)
    build_wardrobe(coll)
    build_chair(coll)
    build_wall_details(coll)
    lights = build_lights(coll)
    return dict(clock=clock, fan=fan, lights=lights, pillows=pillows, blanket=blanket, curtains=curt)
