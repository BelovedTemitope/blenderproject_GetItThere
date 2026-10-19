"""v05 optimisation passes.

cull_hidden(): delete faces nobody can ever see - faces buried inside another
closed part (tube end caps inside the tube they weld to, the backs of plates
and lights sitting on the body, strap bands inside bags, spout/post bases in
the jerrycan...) or pressed flat against another part.

planar_tris(): for the tris variant, merge near-coplanar faces and
re-triangulate them (fewer triangles, identical flat-shaded look).
"""
import math

import bpy
import bmesh
from mathutils import Vector as V
from mathutils.bvhtree import BVHTree

PFX = 'GIT_Veh_Minibus_'
SKIP = ('Body', 'Livery_Decals')          # the shell (solidify) and the paper-thin decals are left alone
ON_SURFACE = 0.003
DIRS = (V((0.577, 0.577, 0.577)), V((-0.6, 0.48, -0.64)), V((0.31, -0.81, 0.5)))


def _islands(bm):
    seen, out = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, isl = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        out.append(isl)
    return out


def _closed(isl):
    fs = set(isl)
    for f in isl:
        for e in f.edges:
            if sum(1 for g in e.link_faces if g in fs) != 2:
                return False
    return True


class Solid:
    def __init__(self, verts, polys, tag):
        self.bvh = BVHTree.FromPolygons(verts, polys)
        self.tag = tag
        xs, ys, zs = zip(*verts)
        m = 0.01
        self.lo = V((min(xs) - m, min(ys) - m, min(zs) - m))
        self.hi = V((max(xs) + m, max(ys) + m, max(zs) + m))

    def hides(self, p, fn):
        if not (self.lo.x <= p.x <= self.hi.x and self.lo.y <= p.y <= self.hi.y and self.lo.z <= p.z <= self.hi.z):
            return False
        loc, n, idx, d = self.bvh.find_nearest(p)
        if loc is None:
            return False
        if d < ON_SURFACE:
            return fn.dot(n) < -0.3            # pressed face-to-face against this solid
        if (p - loc).dot(n) >= 0:
            return False
        # nearest-normal says inside; confirm with ray parity (robust for concave parts like rims)
        votes = 0
        for dvec in DIRS:
            votes += self._crossings(p, dvec) % 2
        return votes >= 2

    def _crossings(self, p, dvec):
        n, o = 0, p.copy()
        for _ in range(64):
            hit = self.bvh.ray_cast(o, dvec)
            if hit[0] is None:
                break
            n += 1
            o = hit[0] + dvec * 1e-4
        return n


def cull_hidden(report=True):
    dg = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(PFX) and not o.hide_render]
    solids = []
    parts = {}
    for o in objs:
        mw = o.matrix_world
        if o.name[len(PFX):] in SKIP:
            if o.name == PFX + 'Body':
                me = o.evaluated_get(dg).to_mesh()          # with panel thickness
                solids.append(Solid([mw @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons],
                                    (o.name, -1)))
                o.evaluated_get(dg).to_mesh_clear()
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.faces.ensure_lookup_table()
        isls = _islands(bm)
        parts[o.name] = (bm, isls)
        for k, isl in enumerate(isls):
            if not _closed(isl):
                continue
            vmap, vs, ps = {}, [], []
            for f in isl:
                idx = []
                for v in f.verts:
                    if v.index not in vmap:
                        vmap[v.index] = len(vs)
                        vs.append(mw @ v.co)
                    idx.append(vmap[v.index])
                ps.append(tuple(idx))
            solids.append(Solid(vs, ps, (o.name, k)))
    total_before = total_after = 0
    for o in objs:
        if o.name not in parts:
            continue
        bm, isls = parts[o.name]
        mw = o.matrix_world
        rot = mw.to_3x3().normalized()
        kill = []
        for k, isl in enumerate(isls):
            for f in isl:
                fn = (rot @ f.normal).normalized()
                pts = [mw @ v.co for v in f.verts]
                pts += [(pts[i] + pts[(i + 1) % len(pts)]) * 0.5 for i in range(len(pts))]
                pts.append(sum(pts[:len(f.verts)], V()) / len(f.verts))
                if all(any(sd.tag != (o.name, k) and sd.hides(p, fn) for sd in solids) for p in pts):
                    kill.append(f)
        before = len(bm.faces)
        if kill:
            bmesh.ops.delete(bm, geom=kill, context='FACES_ONLY')
            loose = [v for v in bm.verts if not v.link_faces]
            bmesh.ops.delete(bm, geom=loose, context='VERTS')
            loose_e = [e for e in bm.edges if not e.link_faces]
            bmesh.ops.delete(bm, geom=loose_e, context='EDGES')
        after = len(bm.faces)
        bm.to_mesh(o.data)
        o.data.update()
        bm.free()
        total_before += before
        total_after += after
        if report and before != after:
            print('cull %-40s %5d -> %5d' % (o.name[len(PFX):], before, after))
    print('CULL TOTAL faces %d -> %d' % (total_before, total_after))


def planar_tris(angle_deg=1.0, report=True):
    """Dissolve near-coplanar edges (same material only) and triangulate the resulting ngons."""
    total = [0, 0]
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.name.startswith(PFX):
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        tris_before = sum(len(f.verts) - 2 for f in bm.faces)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(angle_deg), use_dissolve_boundaries=False,
                                 verts=bm.verts, edges=bm.edges, delimit={'MATERIAL'})
        ngons = [f for f in bm.faces if len(f.verts) > 4]
        if ngons:
            bmesh.ops.triangulate(bm, faces=ngons, quad_method='BEAUTY', ngon_method='BEAUTY')
        # pair triangles back into quads where that is clean (keeps the wireframe readable)
        tri = [f for f in bm.faces if len(f.verts) == 3]
        if tri:
            bmesh.ops.join_triangles(bm, faces=tri, angle_face_threshold=math.radians(angle_deg),
                                     angle_shape_threshold=math.radians(25))
        tris_after = sum(len(f.verts) - 2 for f in bm.faces)
        bm.to_mesh(o.data)
        o.data.update()
        bm.free()
        total[0] += tris_before
        total[1] += tris_after
        if report and tris_before != tris_after:
            print('tris %-40s %5d -> %5d' % (o.name[len(PFX):], tris_before, tris_after))
    print('PLANAR TOTAL triangles %d -> %d' % tuple(total))


def lod_budget(budget, report=True):
    """v06: collapse-decimate each part down to its triangle budget {object suffix: tris}."""
    total = [0, 0]
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.name.startswith(PFX):
            continue
        key = o.name[len(PFX):]
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        target = budget.get(key)
        total[0] += tris
        if target is None or tris <= target:
            total[1] += tris
            continue
        mod = o.modifiers.new('LOD', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = target / tris
        mod.use_collapse_triangulate = True
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        o.modifiers.remove(mod)
        old = o.data
        o.data = me
        if old.users == 0:
            bpy.data.meshes.remove(old)
        after = sum(len(p.vertices) - 2 for p in me.polygons)
        total[1] += after
        if report:
            print('lod  %-40s %5d -> %5d' % (key, tris, after))
    print('LOD TOTAL triangles %d -> %d' % tuple(total))
