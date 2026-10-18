"""Studio presentation renders of the minibus (light + dark looks).

Run headless (Blender 5.2 or the bpy module):
    python mb_studio.py -- <file.blend> <out_dir> <light|dark> [shot ...] [--preview]
    blender -b <file.blend> -P mb_studio.py -- <file.blend> <out_dir> dark hero_fl side

Shots: hero_fl, hero_rl, side, high_fr, detail. The .blend is never saved;
the backdrop, lights and camera are added in memory for the render only.
"""
import math
import sys

import bpy
from mathutils import Vector as V

TARGET = V((0.0, -0.6, 5.0))
SHOTS = {
    # name: (camera position, look-at, focal length mm)
    'hero_fl': ((27.0, -34.0, 6.5), (0.0, -1.2, 5.6), 55),
    'hero_rl': ((28.0, 29.0, 8.0), (0.0, 1.0, 5.8), 55),
    'side': ((58.0, -1.5, 6.2), (0.0, -0.4, 5.4), 85),
    'high_fr': ((-25.0, -28.0, 20.0), (0.0, -0.6, 4.8), 50),
    'detail': ((11.5, -17.5, 7.0), (2.4, -7.2, 5.4), 45),
}
LOOKS = {
    'light': dict(world=(0.85, 0.86, 0.9), world_strength=0.35, floor=(0.72, 0.72, 0.74), floor_rough=0.55,
                  key=(1.0, 0.97, 0.92, 13000), fill=(0.92, 0.95, 1.0, 3000), top=(1.0, 1.0, 1.0, 7000),
                  rim=(1.0, 1.0, 1.0, 6000), bulbs=False, glow=1.0, exposure=0.0),
    'dark': dict(world=(0.02, 0.022, 0.03), world_strength=0.5, floor=(0.03, 0.028, 0.027), floor_rough=0.38,
                 key=(1.0, 0.72, 0.42, 9000), fill=(0.55, 0.62, 0.8, 900), top=(1.0, 0.8, 0.55, 1500),
                 rim=(0.45, 0.62, 1.0, 14000), bulbs=True, glow=7.0, exposure=0.15),
}


def hide_scene_extras(sc):
    for c in bpy.data.collections:
        if c.name in ('MCP_Test', 'M3_Reference', 'M3_Ref_Colour', 'M3_Ref_Pencil', 'Minibus__Cutters'):
            c.hide_render = True
    for o in sc.objects:
        if o.type in ('LIGHT', 'CAMERA') or o.name.startswith(('CUT_', 'Danfo', 'GIT_TubeProfile', 'REF_')) \
                or (o.type == 'CURVE' and o.name.startswith('B')):
            o.hide_render = True


def make_material(name, color, rough, emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = strength
    return m


def cyclorama(look):
    """Seamless floor that curves up into a back wall (wall on +Y before rotation)."""
    prof = [(-60.0, 0.0), (18.0, 0.0)]
    r = 14.0
    for k in range(1, 13):
        a = math.pi / 2 * k / 12
        prof.append((18.0 + r * math.sin(a), r * (1 - math.cos(a))))
    prof.append((18.0 + r, 60.0))
    w = 70.0
    verts, faces = [], []
    for i, (y, z) in enumerate(prof):
        verts += [(-w, y, z), (w, y, z)]
        if i:
            a = 2 * (i - 1)
            faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new('Studio_Cyc')
    me.from_pydata(verts, [], faces)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(make_material('Studio_Floor', look['floor'], look['floor_rough']))
    ob = bpy.data.objects.new('Studio_Cyc', me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def area(name, pos, target, size, color_power, shape='RECTANGLE'):
    r, g, b, p = color_power
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = shape
    ld.size = size
    ld.size_y = size * 0.6
    ld.energy = p
    ld.color = (r, g, b)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = pos
    ob.rotation_euler = (V(target) - V(pos)).to_track_quat('-Z', 'Y').to_euler()
    return ob


def light_rig(look):
    """Rig authored for a camera on the -Y side looking toward +Y; rotated per shot."""
    rig = [area('Key', (-20, -18, 24), TARGET, 14, look['key']),
           area('Fill', (24, -12, 9), TARGET, 18, look['fill']),
           area('Top', (0, 0, 32), TARGET, 22, look['top']),
           area('Rim', (8, 26, 16), TARGET, 10, look['rim'])]
    extras = []
    if look['bulbs']:
        # warm workshop bulbs hanging over the roof, like the garage showcase
        bulb_mat = make_material('Studio_Bulb', (1, 0.8, 0.5), 0.3, (1.0, 0.62, 0.25), 40.0)
        for x, y in ((-6.0, -5.5), (5.5, 1.5), (-4.0, 8.0)):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(x, y, 17.2), segments=16, ring_count=8)
            s = bpy.context.active_object
            s.data.materials.append(bulb_mat)
            pl = bpy.data.lights.new('Bulb', 'POINT')
            pl.energy = 2600
            pl.color = (1.0, 0.62, 0.3)
            pl.shadow_soft_size = 0.35
            po = bpy.data.objects.new('Bulb', pl)
            bpy.context.scene.collection.objects.link(po)
            po.location = (x, y, 16.8)
            # cord up to the ceiling
            bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=14.0, location=(x, y, 24.5), vertices=6)
            extras.append(bpy.context.active_object)
    return rig, extras


def boost_glow(look):
    """Make the vehicle's lamps glow in the dark look (render-time only)."""
    g = look['glow']
    for name, col in (('M_Minibus_Lens_White', (1.0, 0.95, 0.82)), ('M_Minibus_Lens_Clear', (1.0, 0.95, 0.85)),
                      ('M_Minibus_Lens_Red', (1.0, 0.08, 0.04)), ('M_Minibus_Lens_Orange', (1.0, 0.45, 0.05))):
        m = bpy.data.materials.get(name)
        if not m:
            continue
        b = m.node_tree.nodes.get('Principled BSDF')
        b.inputs['Emission Color'].default_value = (*col, 1)
        base = 2.0 if 'White' in name else (0.0 if g <= 1.0 else 1.0)
        b.inputs['Emission Strength'].default_value = base * g if g > 1.0 else base


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    preview = '--preview' in args
    args = [a for a in args if a != '--preview']
    path, out_dir, look_name = args[0], args[1], args[2]
    shots = args[3:] or list(SHOTS)
    look = LOOKS[look_name]
    bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    hide_scene_extras(sc)
    w = bpy.data.worlds.new('Studio_World')
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*look['world'], 1)
    bg.inputs[1].default_value = look['world_strength']
    sc.world = w
    cyc = cyclorama(look)
    rig, extras = light_rig(look)
    boost_glow(look)
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 24 if preview else 96
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = (960, 540) if preview else (1920, 1080)
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    vs = sc.view_settings
    vs.view_transform = 'AgX'
    for look_try in ('AgX - Medium High Contrast', 'AgX - Base Contrast', 'None'):
        try:
            vs.look = look_try
            break
        except TypeError:
            continue
    vs.exposure = look['exposure']
    cd = bpy.data.cameras.new('Studio_Cam')
    cam = bpy.data.objects.new('Studio_Cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    rig_home = [(o, o.location.copy()) for o in rig]
    for shot in shots:
        pos, tgt, lens = SHOTS[shot]
        pos, tgt = V(pos), V(tgt)
        cam.location = pos
        cam.rotation_euler = (tgt - pos).to_track_quat('-Z', 'Y').to_euler()
        cd.lens = lens
        cd.clip_end = 1000
        cd.dof.use_dof = shot == 'detail'
        cd.dof.focus_distance = (tgt - pos).length
        cd.dof.aperture_fstop = 5.6
        # turn backdrop + light rig so the wall sits behind the bus and the key stays camera-left
        d = pos - tgt
        theta = math.atan2(d.x, -d.y)
        cyc.rotation_euler = (0, 0, theta)
        for o, home in rig_home:
            rel = home - TARGET
            c, s = math.cos(theta), math.sin(theta)
            o.location = TARGET + V((rel.x * c - rel.y * s, rel.x * s + rel.y * c, rel.z))
            o.rotation_euler = (TARGET - o.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = '%s/minibus_%s_%s%s.png' % (out_dir, look_name, shot, '_preview' if preview else '')
        bpy.ops.render.render(write_still=True)
        print('RENDERED', sc.render.filepath)


if __name__ == '__main__':
    main()
