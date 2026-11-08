"""Character library: builds one character per run into source/characters/<name>.blend

    python build_characters.py -- arjun|rao|colleague_a|colleague_b [--lod 1.0]

Each library file has one collection 'CH_<name>' (rig + meshes + controls) that
scene builds append. Variants are parameter sets on the same procedural model.
"""
import sys, os, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
import bl_util as U
import char_head as H, char_face as CF, char_hair as CH, char_body as B
import character as C

CAST = {
    'arjun': dict(variant={}, skin='#875c46', hair={}, body={}, kw=dict(tee_color='#3d5862', pants_color='#30353d')),
    'rao': dict(variant={'age': 1.0, 'nose': 1.15, 'cheek': 1.0}, skin='#7e5640',
                mats={'HairMat': (0.45, 0.04, 0.95), 'BrowHair': (0.55, 0.05, 0.7), 'MoustacheMat': (0.45, 0.04, 0.9)},
                hair={'len': 0.72, 'recede': 0.024, 'melanin': 0.22, 'random': 0.35, 'cap': '#5d5853'},
                body={'belly': 1.13},
                kw=dict(tee_color='#bfae90', pants_color='#45464c', brow_melanin=0.45,
                        moustache=dict(melanin=0.42, random=0.45), glasses=True)),
    'colleague_a': dict(variant={'cheek': 1.0}, skin='#a27a5f', hair={'len': 0.7, 'melanin': 0.93},
                        body={}, kw=dict(tee_color='#7a3b3b', pants_color='#262a33', lod=0.6)),
    'colleague_b': dict(variant={'nose': 1.08}, skin='#6f4a37', hair={'len': 0.55, 'melanin': 0.98},
                        body={'belly': 1.05}, kw=dict(tee_color='#2e4f3d', pants_color='#3a3a3a', lod=0.6)),
}

name = sys.argv[sys.argv.index('--') + 1]
cfg = CAST[name]
H.VARIANT.update(cfg['variant']); CH.VARIANT.update(cfg['hair']); B.VARIANT.update(cfg['body'])
CF.SKIN = U.hex2lin(cfg['skin'])
U.reset()
coll = U.collection('CH_' + name)
kw = dict(cfg['kw']); lod = kw.pop('lod', 1.0)
objs = C.build_arjun(coll, hair=True, lod=lod, legs=True, prefix=name[:3].upper(), **kw)
# rename everything uniquely so several characters can share a scene
for ob in list(coll.all_objects):
    ob.name = ob.name.replace('ARJ_', name.upper() + '_') if name != 'arjun' else ob.name
for m in bpy.data.materials:
    if name != 'arjun' and m.name.startswith('ARJ_'):
        m.name = m.name.replace('ARJ_', name.upper() + '_')
for c in list(bpy.data.collections):
    if c is not coll and c.name in [x.name for x in bpy.context.scene.collection.children] and c.name != coll.name:
        pass
# hair colour overrides: (melanin, redness, random)
for key, (mel, red, rnd) in cfg.get('mats', {}).items():
    for m in bpy.data.materials:
        if m.name.endswith(key) and m.node_tree:
            hb = m.node_tree.nodes.get('Principled Hair BSDF')
            if hb:
                hb.inputs['Melanin'].default_value = mel; hb.inputs['Melanin Redness'].default_value = red
                hb.inputs['Random Color'].default_value = rnd
# office shoes material available on every character (scenes swap it in)
sh = U.simple_mat(name.upper() + '_Shoes', U.hex2lin('#1c1a19'), rough=0.35)
sh.use_fake_user = True
out = os.path.join(HERE, '..', '..', 'source', 'characters', name + '.blend')
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out), compress=True)
print('saved', out, len(coll.all_objects), 'objects')
