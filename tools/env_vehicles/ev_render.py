"""Review renders of the background vehicles.

    python ev_render.py -- <file.blend> <out_prefix> <A|B|C|D> [view ...] [--samples N] [--size WxH]

Views: fl fr rl rr side side_r front rear top concept (concept = camera matched to the lineup sheet).
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector as V

HERE = os.path.dirname(os.path.abspath(__file__))
CAMS = os.environ.get('EV_CAMS', os.path.join(HERE, 'concept_cams.json'))
CONCEPT_RES = (1343, 749)
NAMES = {'A': 'GIT_Env_Danfo_A', 'B': 'GIT_Env_Danfo_B_Wrecked', 'C': 'GIT_Env_Taxi_C', 'D': 'GIT_Env_Keke_D'}
VIEWS = {  # direction from the vehicle centre (unit-ish), ortho flag
    'fl': (V((1.0, -1.15, 0.55)), False), 'fr': (V((-1.0, -1.15, 0.55)), False),
    'rl': (V((1.0, 1.15, 0.55)), False), 'rr': (V((-1.0, 1.15, 0.55)), False),
    'side': (V((1, 0, 0.05)), True), 'side_r': (V((-1, 0, 0.05)), True),
    'front': (V((0, -1, 0.05)), True), 'rear': (V((0, 1, 0.05)), True), 'top': (V((0, 0, 1)), True),
}


def setup(sc, samples, size, transparent=False):
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('rv')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.78, 0.8, 0.84, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.9
    sc.world = w
    ld = bpy.data.lights.new('sun', 'SUN')
    ld.energy = 3.2
    ld.angle = math.radians(8)
    lo = bpy.data.objects.new('sun', ld)
    sc.collection.objects.link(lo)
    lo.rotation_euler = (math.radians(42), 0, math.radians(-38))
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = 'ABSOLUTE'
    sc.render.line_thickness = 1.1
    vl = sc.view_layers[0]
    vl.use_freestyle = True
    ls = vl.freestyle_settings.linesets[0] if vl.freestyle_settings.linesets else vl.freestyle_settings.linesets.new('L')
    ls.select_by_visibility = True
    ls.select_silhouette = ls.select_border = True
    ls.select_crease = False
    if ls.linestyle is None:
        ls.linestyle = bpy.data.linestyles.new('LS')
    ls.linestyle.color = (0.08, 0.07, 0.06)


def albedo_mode(sc):
    """Flat colours, no lighting or outlines: for the landmark comparison against the concept."""
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        nt = m.node_tree
        b = nt.nodes.get('Principled BSDF')
        out = nt.nodes.get('Material Output')
        if not b or not out:
            continue
        em = nt.nodes.new('ShaderNodeEmission')
        tex = [n for n in nt.nodes if n.type == 'TEX_IMAGE']
        if tex:
            nt.links.new(tex[0].outputs['Color'], em.inputs['Color'])
        else:
            em.inputs['Color'].default_value = b.inputs['Base Color'].default_value
        nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = 0.0
    sc.render.use_freestyle = False
    sc.render.film_transparent = True
    sc.cycles.samples = 4
    sc.cycles.use_denoising = False
    sc.render.filter_size = 0.6
    sc.view_settings.view_transform = 'Standard'
    for o in sc.objects:
        if o.type == 'LIGHT' or o.name.startswith('Plane'):
            o.hide_render = True


def bbox(objs):
    pts = [o.matrix_world @ V(c) for o in objs for c in o.bound_box]
    lo = V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    samples, size = 32, (1000, 700)
    if '--samples' in args:
        i = args.index('--samples'); samples = int(args[i + 1]); del args[i:i + 2]
    if '--size' in args:
        i = args.index('--size'); size = tuple(int(v) for v in args[i + 1].split('x')); del args[i:i + 2]
    path, out, key = args[0], args[1], args[2]
    albedo = '--albedo' in args
    wire = '--wire' in args
    args = [a for a in args if a not in ('--albedo', '--wire')]
    views = args[3:] or ['fl', 'rl', 'side', 'front']
    bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    col = bpy.data.collections['GIT_Env_Vehicles' if key == 'ALL' else NAMES[key]]
    objs = [o for o in col.all_objects if o.type == 'MESH']
    for o in sc.objects:
        if o.type == 'MESH' and o not in objs:
            o.hide_render = True
    lo, hi = bbox(objs)
    c = (lo + hi) / 2
    ground = (lo.x, lo.y, 0)
    bpy.ops.mesh.primitive_plane_add(size=400, location=(c.x, c.y, 0))
    gm = bpy.data.materials.new('ground'); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.72, 0.74, 0.78, 1)
    bpy.context.active_object.data.materials.append(gm)
    setup(sc, samples, size)
    if albedo:
        albedo_mode(sc)
    if wire:
        # wireframe pass: a Wireframe-modifier copy of every mesh traces each real (quad) edge; the solid
        # model hides the back edges
        wm = bpy.data.materials.new('wire')
        wm.use_nodes = True
        wm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.02, 0.03, 1)
        wm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
        for o in objs:
            w = o.copy()
            w.data = o.data.copy()
            w.data.materials.clear()
            w.data.materials.append(wm)
            sc.collection.objects.link(w)
            if o.parent:
                w.parent = o.parent
                w.matrix_world = o.matrix_world.copy()
            md = w.modifiers.new('wire', 'WIREFRAME')
            md.thickness = 0.045
            md.use_even_offset = True
            md.use_relative_offset = False
            md.offset = 0.0
        sc.render.use_freestyle = False
    cd = bpy.data.cameras.new('cam')
    cam = bpy.data.objects.new('cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    ext = (hi - lo).length
    for v in views:
        if v == 'concept':
            # camera fitted to the concept lineup sheet (ev_fitcam.py): full sheet resolution + lens shift
            cc = json.load(open(CAMS))[key]
            az, el, dist, F, px, py = cc['p']
            rx, ry = CONCEPT_RES
            sc.render.resolution_x, sc.render.resolution_y = rx, ry
            org = [o for o in objs if o.name.endswith('_Body')][0].location
            off = cc.get('off', [0, 0])
            T = org - V((off[0], off[1], 0)) + V((0, 0, 4.0))
            dvec = V((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
            cam.location = T + dvec * dist
            cam.rotation_euler = (-dvec).to_track_quat('-Z', 'Y').to_euler()
            cd.type = 'PERSP'
            cd.sensor_fit = 'HORIZONTAL'
            cd.sensor_width = 36
            cd.lens = F / rx * 36
            cd.shift_x = (rx / 2 - px) / rx
            cd.shift_y = (py - ry / 2) / rx
        else:
            sc.render.resolution_x, sc.render.resolution_y = size
            cd.shift_x = cd.shift_y = 0
            d, ortho = VIEWS[v]
            d = d.normalized()
            cam.location = c + d * ext * (2.2 if key != 'ALL' else 1.25)
            cam.rotation_euler = (-d).to_track_quat('-Z', 'Y' if v != 'top' else 'X').to_euler()
            if v == 'top':
                cam.rotation_euler = (0, 0, math.radians(90))
            cd.type = 'ORTHO' if ortho else 'PERSP'
            cd.ortho_scale = ext * (0.95 if key != 'ALL' else 0.75)
            cd.lens = 50
            cd.sensor_width = 36
        cd.clip_end = 2000
        if albedo and v == 'concept':
            y0, y1, x0, x1 = cc['box']
            sc.render.use_border = sc.render.use_crop_to_border = False
            sc.render.use_border = True
            sc.render.border_min_x, sc.render.border_max_x = x0 / rx, x1 / rx
            sc.render.border_min_y, sc.render.border_max_y = 1 - y1 / ry, 1 - y0 / ry
        sc.render.filepath = '%s_%s_%s%s.png' % (out, key, v, '_wire' if wire else '')
        bpy.ops.render.render(write_still=True)
        print('RENDERED', sc.render.filepath)


if __name__ == '__main__':
    main()
