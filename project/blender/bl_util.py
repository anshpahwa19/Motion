"""Blender helpers shared by all build scripts."""
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def collection(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in p.children]:
        p.children.link(c)
    return c


def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, coll=None, smooth=True, mat=None):
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, dtype=np.float32)
    faces = np.asarray(faces, dtype=np.int32)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.ravel())
    nf = len(faces)
    k = faces.shape[1]
    me.loops.add(nf * k)
    me.loops.foreach_set('vertex_index', faces.ravel())
    me.polygons.add(nf)
    me.polygons.foreach_set('loop_start', np.arange(0, nf * k, k, dtype=np.int32))
    me.update(calc_edges=True)
    me.validate()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    if mat:
        me.materials.append(mat)
    return ob


def mesh_verts(ob):
    n = len(ob.data.vertices)
    a = np.empty(n * 3, dtype=np.float32)
    ob.data.vertices.foreach_get('co', a)
    return a.reshape(-1, 3).astype(np.float64)


def set_color_attr(ob, name, cols):
    """cols: (N,4) per-vertex floats."""
    me = ob.data
    at = me.color_attributes.get(name) or me.color_attributes.new(name, 'FLOAT_COLOR', 'POINT')
    at.data.foreach_set('color', np.asarray(cols, dtype=np.float32).ravel())
    return at


def set_float_attr(ob, name, vals, domain='POINT'):
    me = ob.data
    at = me.attributes.get(name) or me.attributes.new(name, 'FLOAT', domain)
    at.data.foreach_set('value', np.asarray(vals, dtype=np.float32).ravel())


def smooth_mesh(ob, iters=2, factor=0.5):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for _ in range(iters):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=factor,
                              use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(ob.data)
    bm.free()


def decimate(ob, ratio):
    m = ob.modifiers.new('dec', 'DECIMATE')
    m.ratio = ratio
    apply_mods(ob)


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def vgroup_weights(ob, name, weights, thresh=1e-3):
    vg = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
    w = np.asarray(weights)
    for val in np.unique(np.round(w[w > thresh], 3)):
        idx = np.nonzero(np.abs(np.round(w, 3) - val) < 1e-9)[0].tolist()
        vg.add(idx, float(val), 'REPLACE')
    return vg


# ------------------------------------------------------------- materials
def new_mat(name):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m


def nodes(m):
    return m.node_tree.nodes, m.node_tree.links


def principled(m):
    return m.node_tree.nodes.get('Principled BSDF')


def simple_mat(name, color, rough=0.5, metal=0.0, spec=0.5, emit=None, emit_strength=0.0,
               coat=0.0, alpha=1.0, transmission=0.0, ior=1.45):
    m = new_mat(name)
    p = principled(m)
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['IOR'].default_value = ior
    p.inputs['Coat Weight'].default_value = coat
    p.inputs['Transmission Weight'].default_value = transmission
    p.inputs['Specular IOR Level'].default_value = spec
    if emit:
        p.inputs['Emission Color'].default_value = (*emit, 1)
        p.inputs['Emission Strength'].default_value = emit_strength
    if alpha < 1:
        p.inputs['Alpha'].default_value = alpha
    return m


def emission_mat(name, color, strength):
    m = new_mat(name)
    nt = m.node_tree
    nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*color, 1)
    e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def hex2lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def look_at(obj, target, roll=0.0):
    d = Vector(target) - obj.location
    q = d.to_track_quat('-Z', 'Y')
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = q.to_euler()
    if roll:
        obj.rotation_euler.rotate_axis('Z', np.radians(roll))
