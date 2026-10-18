"""Add the light / dark studio setups to a .blend as separate Scenes.

    python mb_scenes.py -- <in.blend> <out.blend>

The vehicle collection is linked (not copied) into each studio scene, so the
model stays single-source. Lamp glow differs per scene through a scene custom
property ("mb_glow") read by the lens materials with an Attribute node.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector as V  # noqa: E402

import mb_studio as ST  # noqa: E402

VEH = 'GIT_Veh_Minibus'
SHOT = 'hero_fl'
LENS = {  # material: (glow colour, use "glow" (white headlights) or "glow - 1" (off in the light scene))
    'M_Minibus_Lens_White': ((1.0, 0.95, 0.82), 'scale'),
    'M_Minibus_Lens_Clear': ((1.0, 0.95, 0.85), 'minus1'),
    'M_Minibus_Lens_Red': ((1.0, 0.08, 0.04), 'minus1'),
    'M_Minibus_Lens_Orange': ((1.0, 0.45, 0.05), 'minus1'),
}


def per_scene_glow():
    """Emission strength = f(scene['mb_glow']) so each scene can light the lamps differently."""
    for name, (col, mode) in LENS.items():
        m = bpy.data.materials.get(name)
        if not m:
            continue
        nt = m.node_tree
        b = nt.nodes['Principled BSDF']
        b.inputs['Emission Color'].default_value = (*col, 1)
        at = nt.nodes.new('ShaderNodeAttribute')
        at.attribute_type = 'VIEW_LAYER'          # looks up view layer -> scene -> world -> camera properties
        at.attribute_name = 'mb_glow'
        at.location = (-600, -400)
        mth = nt.nodes.new('ShaderNodeMath')
        mth.location = (-380, -400)
        if mode == 'scale':
            mth.operation = 'MULTIPLY'
            mth.inputs[1].default_value = 2.0
        else:
            mth.operation = 'SUBTRACT'
            mth.inputs[1].default_value = 1.0
            mth.use_clamp = True
            mx = nt.nodes.new('ShaderNodeMath')
            mx.operation = 'MULTIPLY'
            mx.inputs[1].default_value = 1.2
            mx.location = (-200, -400)
            nt.links.new(mth.outputs[0], mx.inputs[0])
            nt.links.new(at.outputs['Fac'], mth.inputs[0])
            nt.links.new(mx.outputs[0], b.inputs['Emission Strength'])
            continue
        nt.links.new(at.outputs['Fac'], mth.inputs[0])
        nt.links.new(mth.outputs[0], b.inputs['Emission Strength'])


def link(scene, ob):
    scene.collection.objects.link(ob)
    return ob


def build_scene(look_name):
    look = ST.LOOKS[look_name]
    sc = bpy.data.scenes.new('Studio_' + look_name.capitalize())
    sc['mb_glow'] = look['glow']
    sc.collection.children.link(bpy.data.collections[VEH])
    # world
    w = bpy.data.worlds.new('Studio_World_' + look_name)
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*look['world'], 1)
    bg.inputs[1].default_value = look['world_strength']
    sc.world = w
    # build backdrop + lights with the studio helpers, then move them into this scene
    before = set(bpy.data.objects)
    cyc = ST.cyclorama(look)
    rig, extras = ST.light_rig(look)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        o.name = '%s_%s' % (o.name, look_name.capitalize())
        link(sc, o)
    # camera on the hero angle, rig + backdrop turned to match it
    pos, tgt, lens = (V(v) if i < 2 else v for i, v in enumerate(ST.SHOTS[SHOT]))
    cd = bpy.data.cameras.new('Studio_Cam_' + look_name)
    cd.lens = lens
    cd.clip_end = 1000
    cam = link(sc, bpy.data.objects.new('Studio_Cam_' + look_name.capitalize(), cd))
    cam.location = pos
    cam.rotation_euler = (tgt - pos).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    d = pos - tgt
    theta = math.atan2(d.x, -d.y)
    cyc.rotation_euler = (0, 0, theta)
    c, s = math.cos(theta), math.sin(theta)
    for o in rig:
        rel = o.location - ST.TARGET
        o.location = ST.TARGET + V((rel.x * c - rel.y * s, rel.x * s + rel.y * c, rel.z))
        o.rotation_euler = (ST.TARGET - o.location).to_track_quat('-Z', 'Y').to_euler()
    # render settings
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 96
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 100
    vs = sc.view_settings
    vs.view_transform = 'AgX'
    for look_try in ('AgX - Medium High Contrast', 'AgX - Base Contrast', 'None'):
        try:
            vs.look = look_try
            break
        except TypeError:
            continue
    vs.exposure = look['exposure']
    sc.render.filepath = '//renders/studio/minibus_v05_studio_%s_' % look_name
    return sc


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    src, out = args[0], args[1]
    bpy.ops.wm.open_mainfile(filepath=src)
    base = bpy.context.window.scene if bpy.context.window else bpy.data.scenes[0]
    base['mb_glow'] = 1.0                # modelling scene keeps the normal (subtle) headlight glow
    per_scene_glow()
    for look in ('light', 'dark'):
        build_scene(look)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print('SCENES', [s.name for s in bpy.data.scenes])
    print('SAVED', out)


if __name__ == '__main__':
    main()
