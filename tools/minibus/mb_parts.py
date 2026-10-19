"""Part builders for the minibus. Each build_* writes one or more objects."""
import math

import bpy
import bmesh
from mathutils import Matrix, Vector as V

import mb_body as B
import mb_lib as L

ROOT = 'GIT_Veh_Minibus'
PFX = 'GIT_Veh_Minibus_'


class Context:
    def __init__(self, tire_file):
        self.tire_file = tire_file
        self.root = bpy.data.objects[ROOT]
        self.cols = {}
        top = bpy.data.collections[ROOT]
        for n in ('Body', 'Wheels', 'Chassis', 'Front', 'Cage_Rack', 'Rear', 'Interior', 'Cargo'):
            self.cols[n] = L.get_collection('Minibus_' + n, top)
        self.m = make_materials()

    def obj(self, name, bd, col, mats, recalc=True):
        return L.finish_object(PFX + name, bd, self.cols[col], [self.m[k] for k in mats], self.root, recalc)


def make_materials():
    M = {}
    M['paint'] = L.material('M_Minibus_Paint_Yellow', (0.83, 0.47, 0.06), 0.45)
    M['navy'] = L.material('M_Minibus_Paint_Navy', (0.07, 0.09, 0.15), 0.5)
    M['interior'] = L.material('M_Minibus_Interior_Panel', (0.42, 0.40, 0.36), 0.8)
    M['steel'] = L.material('M_Minibus_Steel_Navy', (0.09, 0.11, 0.17), 0.45, 0.3)
    M['chassis'] = L.material('M_Minibus_Chassis_Dark', (0.05, 0.055, 0.07), 0.6, 0.2)
    M['metal'] = L.material('M_Minibus_Metal_Grey', (0.45, 0.46, 0.47), 0.35, 0.6)
    M['rust'] = L.material('M_Minibus_Metal_Rust', (0.22, 0.12, 0.07), 0.8, 0.2)
    M['rubber'] = L.material('M_Minibus_Rubber', (0.035, 0.032, 0.03), 0.9)
    M['rim'] = L.material('M_Minibus_Rim_Dark', (0.05, 0.065, 0.1), 0.45, 0.4)
    M['red'] = L.material('M_Minibus_Shackle_Red', (0.6, 0.03, 0.02), 0.4)
    M['lens_white'] = L.material('M_Minibus_Lens_White', (0.9, 0.9, 0.85), 0.15, 0, (1.0, 0.95, 0.85), 2.0)
    M['lens_orange'] = L.material('M_Minibus_Lens_Orange', (0.9, 0.35, 0.02), 0.2)
    M['lens_red'] = L.material('M_Minibus_Lens_Red', (0.65, 0.03, 0.02), 0.2)
    M['lens_clear'] = L.material('M_Minibus_Lens_Clear', (0.55, 0.58, 0.62), 0.1)
    M['chrome'] = L.material('M_Minibus_Chrome', (0.6, 0.6, 0.62), 0.2, 1.0)
    M['black'] = L.material('M_Minibus_Plastic_Black', (0.02, 0.02, 0.022), 0.7)
    M['seat'] = L.material('M_Minibus_Seat_Grey', (0.32, 0.31, 0.29), 0.85)
    M['seat_dark'] = L.material('M_Minibus_Seat_Dark', (0.16, 0.16, 0.16), 0.85)
    M['dash'] = L.material('M_Minibus_Dash_Navy', (0.07, 0.085, 0.13), 0.7)
    M['decal_white'] = L.material('M_Minibus_Decal_White', (0.85, 0.85, 0.82), 0.5)
    M['decal_red'] = L.material('M_Minibus_Decal_Red', (0.65, 0.04, 0.03), 0.5)
    M['decal_black'] = L.material('M_Minibus_Decal_Black', (0.02, 0.02, 0.02), 0.5)
    M['bag_navy'] = L.material('M_Minibus_Bag_Navy', (0.06, 0.08, 0.14), 0.9)
    M['bag_purple'] = L.material('M_Minibus_Bag_Purple', (0.09, 0.06, 0.13), 0.9)
    M['bag_red'] = L.material('M_Minibus_Bag_Red', (0.3, 0.04, 0.03), 0.9)
    M['strap'] = L.material('M_Minibus_Strap_Red', (0.35, 0.05, 0.04), 0.8)
    M['plaid'] = plaid_material()
    M['jerry'] = L.material('M_Minibus_Jerrycan_Red', (0.45, 0.04, 0.025), 0.5)
    M['canvas'] = L.material('M_Minibus_Canvas_Grey', (0.3, 0.29, 0.26), 0.95)
    return M


def plaid_material():
    m = L.material('M_Minibus_Bag_Plaid', (0.7, 0.5, 0.15), 0.9)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type not in ('BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'):
            nt.nodes.remove(n)
    bsdf = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (2.5, 2.5, 2.5)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(mp.outputs['Vector'], sep.inputs['Vector'])

    def stripes(inp, width):
        fr = nt.nodes.new('ShaderNodeMath')
        fr.operation = 'FRACT'
        nt.links.new(inp, fr.inputs[0])
        lt = nt.nodes.new('ShaderNodeMath')
        lt.operation = 'LESS_THAN'
        lt.inputs[1].default_value = width
        nt.links.new(fr.outputs[0], lt.inputs[0])
        return lt.outputs[0]

    a = stripes(sep.outputs['X'], 0.32)
    b = stripes(sep.outputs['Z'], 0.32)
    c = stripes(sep.outputs['Y'], 0.32)
    mx = nt.nodes.new('ShaderNodeMath')
    mx.operation = 'MAXIMUM'
    nt.links.new(a, mx.inputs[0])
    nt.links.new(c, mx.inputs[1])
    mix1 = nt.nodes.new('ShaderNodeMix')
    mix1.data_type = 'RGBA'
    mix1.inputs['A'].default_value = (0.75, 0.55, 0.18, 1)
    mix1.inputs['B'].default_value = (0.55, 0.08, 0.05, 1)
    nt.links.new(mx.outputs[0], mix1.inputs['Factor'])
    mix2 = nt.nodes.new('ShaderNodeMix')
    mix2.data_type = 'RGBA'
    mix2.inputs['B'].default_value = (0.35, 0.04, 0.03, 1)
    nt.links.new(mix1.outputs['Result'], mix2.inputs['A'])
    nt.links.new(b, mix2.inputs['Factor'])
    nt.links.new(mix2.outputs['Result'], bsdf.inputs['Base Color'])
    return m


# ---------------------------------------------------------------------------
# Body + fenders
# ---------------------------------------------------------------------------
def build_body(ctx):
    bd, cols = B.build_body({'paint': 0, 'navy': 1})
    o = ctx.obj('Body', bd, 'Body', ['paint', 'navy', 'interior', 'interior'], recalc=False)
    mod = o.modifiers.new('Panel_Thickness', 'SOLIDIFY')
    mod.thickness = 0.1
    mod.offset = -1.0
    mod.use_even_offset = True
    mod.use_rim = True
    mod.material_offset = 2
    mod.material_offset_rim = 0
    return o


def build_fenders(ctx):
    for wy, tag in ((B.WHEEL_Y[0], 'F'), (B.WHEEL_Y[1], 'R')):
        for s, side in ((1, 'L'), (-1, 'R')):
            bd = L.Builder()
            pts = B.arch_points(wy, 2.62, 15)
            n = len(pts)
            rings = []
            for k, (y, z) in enumerate(pts):
                t = k / (n - 1)
                w = 0.27 + 0.31 * math.sin(math.pi * t)          # flare width: wide at the top, slim at the ends
                radial = V((0, y - wy, z - B.ARCH_CZ)).normalized()
                base = V((0, y, z))
                prof = [(w, 3.9), (w * 0.86, 4.42), (w * 0.42, 4.76), (0.0, 4.80), (0.0, 4.36), (0.0, 3.84)]
                ring = []
                for (d, x) in prof:
                    p = base + radial * d
                    ring.append(bd.vert((s * x, p.y, p.z)))
                rings.append(ring)
            bd.loft(rings, 0, closed=False)
            for ring in (rings[0], rings[-1]):
                a, b, c, d, e, f = ring
                bd.face((a, b, e, f), 0)
                bd.face((b, c, d, e), 0)
            ctx.obj('Fender%s%s' % (tag, side), bd, 'Body', ['navy'])


# ---------------------------------------------------------------------------
# Wheels: appended from ILikeTheTires.blend and fitted to the wheel centres
# ---------------------------------------------------------------------------
WHEEL_SCALE = 1.83 / 1.95   # tire file tyres are r=1.95; the hubs sit at z=1.83 -> fit to r=1.83


def build_wheels(ctx):
    names = ['WheelFL', 'WheelFR', 'WheelRL', 'WheelRR', 'SpareTyre']
    with bpy.data.libraries.load(ctx.tire_file, link=False) as (src, dst):
        dst.meshes = [PFX + n for n in names]
    loaded = dict(zip(names, dst.meshes))
    for n in names:
        me = loaded[n]
        bm = bmesh.new()
        bm.from_mesh(me)
        L.quadify_ngons(bm)
        caps = cap_holes(bm)
        drop_loose_caps(bm, caps)
        bmesh.ops.scale(bm, vec=(WHEEL_SCALE,) * 3, verts=bm.verts)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        # the hub-nut caps sit on the wheel's outer face: make them face outward along the axle
        for f in caps:
            f.normal_update()
            if f.normal.x * f.calc_center_median().x < 0:
                f.normal_flip()
        for f in bm.faces:
            r = max(math.hypot(v.co.y, v.co.z) for v in f.verts) / WHEEL_SCALE
            f.material_index = 1 if r < 1.1 else 0
        # set the slots before writing the faces: clearing slots afterwards resets every index to 0
        me.materials.clear()
        me.materials.append(ctx.m['rubber'])
        me.materials.append(ctx.m['rim'])
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.get(PFX + n)
        old = obj.data
        obj.data = me
        me.name = PFX + n
        if old.users == 0:
            bpy.data.meshes.remove(old)
        obj.modifiers.clear()
        for p in me.polygons:
            p.use_smooth = False
        if n == 'SpareTyre':
            for c in list(obj.users_collection):
                c.objects.unlink(obj)
            ctx.cols['Rear'].objects.link(obj)
            obj.location = SPARE_LOC
            obj.rotation_euler = (0, 0, math.pi / 2)
        else:
            obj.location.z = B.WHEEL_Z
            obj.rotation_euler = (0, 0, 0)


SPARE_LOC = (-1.55, 8.17, 5.72)


def drop_loose_caps(bm, caps):
    """The tyre file's hub-nut cap is a loose, inward-facing hexagon floating over the open nut;
    now that the nut is properly capped, remove the loose copy (it z-fights with the real cap)."""
    if not caps:
        return
    planes = {round(abs(f.calc_center_median().x), 3) for f in caps}
    capset = set(caps)
    seen, kill = set(), []
    for f in bm.faces:
        if f in seen or f in capset:
            continue
        stack, isl = [f], []
        seen.add(f)
        while stack:
            g = stack.pop()
            isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h not in seen:
                        seen.add(h)
                        stack.append(h)
        if len(isl) <= 3 and all(round(abs(v.co.x), 3) in planes for g in isl for v in g.verts):
            kill += isl
    if kill:
        bmesh.ops.delete(bm, geom=kill, context='FACES')


def cap_holes(bm):
    """Close small open boundary loops (the tyre file's hub nut is open) with quads."""
    capped = []
    border = {e for e in bm.edges if len(e.link_faces) == 1}
    while border:
        e = border.pop()
        loop = [e.verts[0], e.verts[1]]
        closed = False
        while True:
            nxt = [x for x in loop[-1].link_edges if x in border]
            if not nxt:
                break
            x = nxt[0]
            border.discard(x)
            v = x.other_vert(loop[-1])
            if v is loop[0]:
                closed = True
                break
            loop.append(v)
        if closed and 4 <= len(loop) <= 16 and len(loop) % 2 == 0:
            n = len(loop)
            for i in range(n // 2 - 1):
                q = (loop[i], loop[i + 1], loop[n - 2 - i], loop[n - 1 - i])
                if bm.faces.get(q) is None:
                    capped.append(bm.faces.new(q))
    return capped


# ---------------------------------------------------------------------------
def cleanup(ctx):
    cut = bpy.data.collections.get('Minibus__Cutters')
    if cut:
        for o in list(cut.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(cut)
    for n in ('Rocker_Sills',):
        o = bpy.data.objects.get(PFX + n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)


def build_all(ctx):
    cleanup(ctx)
    build_body(ctx)
    build_fenders(ctx)
    build_wheels(ctx)
    for fn in EXTRA:
        fn(ctx)
    for me in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(me)


EXTRA = []
