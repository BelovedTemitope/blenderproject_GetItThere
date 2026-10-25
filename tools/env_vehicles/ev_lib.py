"""Geometry helpers for the background (environment) vehicles.

Low-poly, quad-only building blocks: a lattice box with explicit cut lines
(every edge loop runs cleanly around the part, no wandering loops), inset
windows, simple wheels and wheel wells. Self-contained: nothing here depends
on the minibus tools.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

V = Vector


class Builder:
    def __init__(self):
        self.bm = bmesh.new()

    def vert(self, co):
        return self.bm.verts.new(V(co))

    def face(self, vs, mat=0):
        f = self.bm.faces.new(list(vs))
        f.material_index = mat
        return f

    def strip(self, a, b, mat=0, closed=False):
        n = len(a)
        out = []
        for i in (range(n) if closed else range(n - 1)):
            j = (i + 1) % n
            out.append(self.face((a[i], a[j], b[j], b[i]), mat))
        return out

    def cap(self, ring, mat=0):
        """Ladder quad cap for an even, roughly convex ring."""
        n = len(ring)
        assert n % 2 == 0, n
        return [self.face((ring[i], ring[i + 1], ring[n - 2 - i], ring[n - 1 - i]), mat) for i in range(n // 2 - 1)]


def srgb(c):
    """Hex or 0-255 sRGB colour to linear RGB."""
    if isinstance(c, str):
        c = tuple(int(c.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(((x / 255) / 12.92) if x / 255 <= 0.04045 else (((x / 255) + 0.055) / 1.055) ** 2.4 for x in c)


def material(name, color, rough=0.6, metal=0.0, image=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    lin = srgb(color)
    b.inputs['Base Color'].default_value = (*lin, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    m.diffuse_color = (*lin, 1)
    if image is not None:
        tex = m.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = image
        tex.location = (-400, 200)
        m.node_tree.links.new(tex.outputs['Color'], b.inputs['Base Color'])
    return m


# ---------------------------------------------------------------------------
# Lattice box with explicit cuts
# ---------------------------------------------------------------------------
def grid_box(bd, xs, ys, zs, mat=0, deform=None, face_mat=None):
    """Quad box whose surface is the lattice of the given cut coordinates.

    deform(co, key) -> co   key = (i, j, k) lattice index; co starts at the nominal position.
    face_mat(axis, side, center) -> material index, or None to leave the face out (openings).
    Returns (vmap, faces) with vmap[(i, j, k)] -> BMVert.
    """
    ax = [sorted(xs), sorted(ys), sorted(zs)]
    lim = [len(a) - 1 for a in ax]
    vmap = {}

    def get(key):
        v = vmap.get(key)
        if v is None:
            co = V((ax[0][key[0]], ax[1][key[1]], ax[2][key[2]]))
            if deform:
                co = deform(co, key)
            v = vmap[key] = bd.vert(co)
        return v

    faces = []
    for a in range(3):
        b, c = (a + 1) % 3, (a + 2) % 3
        for side in (0, lim[a]):
            for u in range(lim[b]):
                for w in range(lim[c]):
                    keys = []
                    for du, dw in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        k = [0, 0, 0]
                        k[a], k[b], k[c] = side, u + du, w + dw
                        keys.append(tuple(k))
                    cen = [0.0, 0.0, 0.0]
                    cen[a] = ax[a][side]
                    cen[b] = (ax[b][u] + ax[b][u + 1]) / 2
                    cen[c] = (ax[c][w] + ax[c][w + 1]) / 2
                    m = face_mat(a, 1 if side else -1, V(cen)) if face_mat else mat
                    if m is None:
                        continue
                    vs = [get(k) for k in keys]
                    if side == 0:
                        vs = vs[::-1]
                    faces.append(bd.face(vs, m))
    return vmap, faces, ax


def idx(axis_list, value):
    return min(range(len(axis_list)), key=lambda i: abs(axis_list[i] - value))


def inset_windows(bd, faces, thickness, depth, frame_mat):
    """Inset each window face: a quad frame ring (frame_mat) around a slightly recessed pane."""
    res = bmesh.ops.inset_individual(bd.bm, faces=faces, thickness=thickness, depth=-depth,
                                     use_even_offset=True)
    for f in res['faces']:
        f.material_index = frame_mat
    return res


def well(bd, loop, offset, mat, mids=()):
    """Wheel well from an open U-shaped hole outline (bottom-front, top chain..., bottom-rear).

    Walls run inward by `offset`; the inner wall is closed with vertical column quads whose bottom
    vertices are the U ends plus `mids` (existing floor vertices, so the well welds to the floor).
    """
    inner = [bd.vert(v.co + V(offset)) for v in loop]
    out = bd.strip(loop, inner, mat)
    top = inner[1:-1]
    bottom = [inner[0]] + list(mids) + [inner[-1]]
    assert len(bottom) == len(top), (len(bottom), len(top))
    for i in range(len(top) - 1):
        out.append(bd.face((bottom[i], top[i], top[i + 1], bottom[i + 1]), mat))
    return out


# ---------------------------------------------------------------------------
# Revolved parts
# ---------------------------------------------------------------------------
def lathe(bd, prof, sides, center, axis, mats, cap_start=None, cap_end=None, phase=None):
    """prof: [(radius, axial)], mats: per band; caps take a material index or None."""
    phase = math.pi / sides if phase is None else phase
    c = V(center)
    rings = []
    for r, a in prof:
        ring = []
        for k in range(sides):
            t = phase + 2 * math.pi * k / sides
            ca, sa = math.cos(t) * r, math.sin(t) * r
            co = {'X': (a, ca, sa), 'Y': (sa, a, ca), 'Z': (ca, sa, a)}[axis]
            ring.append(bd.vert(c + V(co)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        bd.strip(rings[i], rings[i + 1], mats[i], True)
    if cap_start is not None:
        bd.cap(rings[0], cap_start)
    if cap_end is not None:
        bd.cap(rings[-1], cap_end)
    return rings


def wheel(bd, center, R, W, sides, out, tyre, hub, hub_r=0.6):
    """Low-poly wheel on the X axis; `out` = +1/-1 is the outboard side.

    3 bands (tread, shoulder, sidewall) + ladder caps: the inner face and the flat hub disc.
    """
    x0, x1 = -out * W / 2, out * W / 2
    prof = [(R, x0), (R, x1 - out * min(0.18, W * 0.16)), (R * 0.88, x1), (R * hub_r, x1)]
    return lathe(bd, prof, sides, center, 'X', [tyre, tyre, tyre], cap_start=tyre, cap_end=hub)


# ---------------------------------------------------------------------------
# Simple pieces
# ---------------------------------------------------------------------------
def box(bd, center, size, mat=0, rot=None):
    """Plain 6-quad box (rot: optional 3x3 matrix)."""
    c = V(center)
    hx, hy, hz = (s / 2 for s in size)
    m = rot if rot is not None else Matrix.Identity(3)
    vs = {}
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                vs[i, j, k] = bd.vert(c + m @ V(((2 * i - 1) * hx, (2 * j - 1) * hy, (2 * k - 1) * hz)))
    q = [((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
         ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
         ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))]
    return [bd.face([vs[k] for k in f], mat) for f in q]


def beam(bd, a, b, w, h, mat=0, up=V((0, 0, 1)), caps=True):
    """Square-section bar from a to b (4 quads + optional end caps)."""
    a, b = V(a), V(b)
    d = (b - a).normalized()
    side = d.cross(up)
    if side.length < 1e-6:
        side = d.cross(V((1, 0, 0)))
    side.normalize()
    upv = side.cross(d).normalized()
    offs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ra = [bd.vert(a + side * sx * w / 2 + upv * sz * h / 2) for sx, sz in offs]
    rb = [bd.vert(b + side * sx * w / 2 + upv * sz * h / 2) for sx, sz in offs]
    out = bd.strip(ra, rb, mat, True)
    if caps:
        out.append(bd.face(ra[::-1], mat))
        out.append(bd.face(rb, mat))
    return out


def quad(bd, pts, mat):
    return bd.face([bd.vert(p) for p in pts], mat)


# ---------------------------------------------------------------------------
# Objects
# ---------------------------------------------------------------------------
def get_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def finish(name, bd, col, mats, origin=None, smooth_angle=35.0, recalc=True, pre=None):
    bmesh.ops.remove_doubles(bd.bm, verts=bd.bm.verts, dist=1e-5)
    if recalc:
        bmesh.ops.recalc_face_normals(bd.bm, faces=bd.bm.faces)
    bd.bm.normal_update()
    for f in bd.bm.faces:
        f.smooth = True
    if pre:
        pre(bd.bm)                       # may set UVs, flip faces or flat-shade some faces
    me = bpy.data.meshes.new(name)
    bd.bm.to_mesh(me)
    bd.bm.free()
    for m in mats:
        me.materials.append(m)
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if origin is not None:
        me.transform(Matrix.Translation(-V(origin)))
        ob.location = origin
    return ob


def stats(objs):
    f = t = q = n = 0
    for o in objs:
        for p in o.data.polygons:
            k = len(p.vertices)
            f += 1
            t += k - 2
            q += k == 4
            n += k > 4
    return dict(faces=f, tris=t, quads=q, ngons=n)


# ---------------------------------------------------------------------------
# Texture atlas helpers (box-projected UVs into tiles)
# ---------------------------------------------------------------------------
def uv_tiles(bm, mats, tile_of):
    """Box-project UVs for faces whose material is in `mats`.

    tile_of(normal, co) -> (u, v) in 0..1 for a vertex position, chosen per face from its dominant normal.
    """
    uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        if f.material_index not in mats:
            for lp in f.loops:
                lp[uvl].uv = (0.999, 0.999)
            continue
        n = f.normal
        c = f.calc_center_median()
        for lp in f.loops:
            lp[uvl].uv = tile_of(n, lp.vert.co, c)


def orient_outward(bm, mats, center):
    """Open shells confuse normal recalculation: point the given faces away from `center`."""
    c = V(center)
    for f in bm.faces:
        if f.material_index in mats and f.normal.dot(f.calc_center_median() - c) < 0:
            f.normal_flip()
