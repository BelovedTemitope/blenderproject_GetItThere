"""Geometry helpers for the GIT minibus build.

Everything here produces quad-only topology (caps use ladder quads,
boxes use a chamfered lattice) so the generated parts stay clean and
subdivision/bevel friendly.
"""
import math
import bpy
import bmesh
from mathutils import Matrix, Quaternion, Vector

V = Vector


# ---------------------------------------------------------------------------
# Builder: thin wrapper around a bmesh
# ---------------------------------------------------------------------------
class Builder:
    def __init__(self):
        self.bm = bmesh.new()

    def vert(self, co):
        return self.bm.verts.new(V(co))

    def verts(self, cos):
        return [self.vert(c) for c in cos]

    def face(self, vs, mat=0):
        f = self.bm.faces.new(list(vs))
        f.material_index = mat
        return f

    def strip(self, a, b, mat=0, closed=False):
        """Quads between two equal-length vertex rows."""
        n = len(a)
        rng = range(n) if closed else range(n - 1)
        out = []
        for i in rng:
            j = (i + 1) % n
            out.append(self.face((a[i], a[j], b[j], b[i]), mat))
        return out

    def loft(self, rings, mat=0, closed=False, closed_path=False):
        out = []
        m = len(rings)
        rng = range(m) if closed_path else range(m - 1)
        for i in rng:
            out += self.strip(rings[i], rings[(i + 1) % m], mat, closed)
        return out

    def cap(self, ring, mat=0, flip=False, start=0):
        """Ladder quad cap for an even, roughly convex ring."""
        n = len(ring)
        if n % 2:
            raise ValueError("cap needs an even vertex count, got %d" % n)
        r = ring[start:] + ring[:start]
        if flip:
            r = [r[0]] + r[1:][::-1]
        out = []
        for i in range(n // 2 - 1):
            out.append(self.face((r[i], r[i + 1], r[n - 2 - i], r[n - 1 - i]), mat))
        return out

    def merge(self, dist=1e-5):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=dist)

    def recalc(self):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)

    def transform(self, mat, verts=None):
        bmesh.ops.transform(self.bm, matrix=mat, verts=verts if verts is not None else self.bm.verts)

    def flip_all(self):
        bmesh.ops.reverse_faces(self.bm, faces=self.bm.faces)


# ---------------------------------------------------------------------------
# Paths / frames
# ---------------------------------------------------------------------------
def fillet_path(pts, radius, closed=False, seg_angle=math.radians(22.5), min_segs=2):
    """Round every interior corner of a polyline with an arc."""
    pts = [V(p) for p in pts]
    n = len(pts)
    out = []
    for i in range(n):
        if not closed and (i == 0 or i == n - 1):
            out.append(pts[i].copy())
            continue
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        d1 = p1 - p0
        d2 = p2 - p1
        l1, l2 = d1.length, d2.length
        d1.normalize()
        d2.normalize()
        ang = d1.angle(d2) if l1 > 1e-9 and l2 > 1e-9 else 0.0
        r = radius[i] if isinstance(radius, (list, tuple)) else radius
        if ang < 1e-3 or r <= 0:
            out.append(p1.copy())
            continue
        t = r * math.tan(ang / 2)
        lim1 = 0.5 * l1 if (closed or i - 1 > 0) else 0.95 * l1
        lim2 = 0.5 * l2 if (closed or i + 1 < n - 1) else 0.95 * l2
        t = min(t, lim1, lim2)
        a = p1 - d1 * t
        b = p1 + d2 * t
        r_eff = t / math.tan(ang / 2)
        bis = (d2 - d1).normalized()
        c = p1 + bis * (r_eff / math.cos(ang / 2))
        va, vb = a - c, b - c
        axis = va.cross(vb).normalized()
        k = max(min_segs, int(math.ceil(ang / seg_angle)))
        for j in range(k + 1):
            q = Quaternion(axis, ang * j / k)
            out.append(c + q @ va)
    # drop near duplicates
    clean = [out[0]]
    for p in out[1:]:
        if (p - clean[-1]).length > 1e-6:
            clean.append(p)
    if closed and (clean[0] - clean[-1]).length < 1e-6:
        clean.pop()
    return clean


def path_frames(pts, closed=False, up=V((0, 0, 1))):
    """Parallel-transport frames: list of (tangent, normal, binormal, miter_dir, miter_scale)."""
    n = len(pts)
    segs = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        segs.append((pts[(i + 1) % n] - pts[i]).normalized())
    tans = []
    info = []
    for i in range(n):
        if closed:
            din, dout = segs[i - 1], segs[i % len(segs)]
        else:
            din = segs[i - 1] if i > 0 else segs[0]
            dout = segs[i] if i < n - 1 else segs[-1]
        t = (din + dout)
        if t.length < 1e-9:
            t = dout.copy()
        t.normalize()
        tans.append(t)
        ang = din.angle(dout) if (din - dout).length > 1e-9 else 0.0
        bend = (dout - din)
        bend = (bend - t * bend.dot(t))
        info.append((bend.normalized() if bend.length > 1e-9 else None, 1.0 / max(math.cos(ang / 2), 0.2)))
    # initial normal
    t0 = tans[0]
    upv = V(up)
    if abs(t0.dot(upv)) > 0.95:
        upv = V((1, 0, 0)) if abs(t0.x) < 0.9 else V((0, 1, 0))
    nrm = (upv - t0 * upv.dot(t0)).normalized()
    frames = []
    for i in range(n):
        if i > 0:
            q = tans[i - 1].rotation_difference(tans[i])
            nrm = q @ nrm
            nrm = (nrm - tans[i] * nrm.dot(tans[i])).normalized()
        b = tans[i].cross(nrm)
        frames.append((tans[i], nrm, b, info[i][0], info[i][1]))
    return frames


def _miter(off, bend, scale):
    if bend is None or scale <= 1.0001:
        return off
    comp = off.dot(bend)
    return off + bend * comp * (scale - 1.0)


def sweep(bd, path, profile, mat=0, closed_profile=True, closed_path=False,
          cap_start=False, cap_end=False, up=V((0, 0, 1)), frames=None, scales=None):
    """Sweep a 2D profile [(u, v)] along a path. u runs along the frame normal, v along binormal."""
    frames = frames or path_frames(path, closed_path, up)
    rings = []
    for i, (p, fr) in enumerate(zip(path, frames)):
        t, nrm, b, bend, ms = fr
        s = scales[i] if scales else 1.0
        ring = []
        for (u, v) in profile:
            off = nrm * (u * s) + b * (v * s)
            ring.append(bd.vert(p + _miter(off, bend, ms)))
        rings.append(ring)
    faces = bd.loft(rings, mat, closed=closed_profile, closed_path=closed_path)
    if cap_start and not closed_path:
        faces += bd.cap(rings[0], mat)
    if cap_end and not closed_path:
        faces += bd.cap(rings[-1], mat)
    return rings, faces


def circle_profile(r, sides=8, phase=None):
    phase = math.pi / sides if phase is None else phase
    return [(r * math.cos(phase + 2 * math.pi * k / sides), r * math.sin(phase + 2 * math.pi * k / sides))
            for k in range(sides)]


def tube(bd, pts, r, sides=8, mat=0, fillet=0.0, closed=False, caps=True, up=V((0, 0, 1)), seg_angle=math.radians(22.5)):
    path = fillet_path(pts, fillet, closed, seg_angle) if fillet else [V(p) for p in pts]
    return sweep(bd, path, circle_profile(r, sides), mat, True, closed, caps, caps, up)


# ---------------------------------------------------------------------------
# Lathe
# ---------------------------------------------------------------------------
def lathe(bd, profile, segs=12, mat=0, center=V((0, 0, 0)), axis='X', cap_start=False, cap_end=False,
          mats=None, phase=None):
    """Revolve [(radius, axial)] around an axis. mats: optional per-band material list."""
    phase = math.pi / segs if phase is None else phase
    rings = []
    c = V(center)
    for (r, a) in profile:
        ring = []
        for k in range(segs):
            ang = phase + 2 * math.pi * k / segs
            ca, sa = math.cos(ang) * r, math.sin(ang) * r
            if axis == 'X':
                co = (a, ca, sa)
            elif axis == 'Y':
                co = (sa, a, ca)
            else:
                co = (ca, sa, a)
            ring.append(bd.vert(c + V(co)))
        rings.append(ring)
    faces = []
    for i in range(len(rings) - 1):
        m = mats[i] if mats else mat
        faces += bd.strip(rings[i], rings[i + 1], m, True)
    if cap_start:
        faces += bd.cap(rings[0], mats[0] if mats else mat)
    if cap_end:
        faces += bd.cap(rings[-1], mats[-1] if mats else mat)
    return rings, faces


# ---------------------------------------------------------------------------
# Chamfered lattice box (all quads)
# ---------------------------------------------------------------------------
def _axis_coords(h, c, segs, cuts):
    if c <= 0:
        return [-h + 2 * h * k / (cuts + 1) for k in range(cuts + 2)]
    if c >= h * 0.98:
        # fully rounded axis: band meets in the middle, no flat
        lo = [-h + h * j / segs for j in range(segs)]
        return lo + [0.0] + [-x for x in reversed(lo)]
    lo = [-h + c * j / segs for j in range(segs + 1)]  # -h .. -h+c
    inner = [(-h + c) + (2 * (h - c)) * k / (cuts + 1) for k in range(1, cuts + 1)]
    hi = [h - c * j / segs for j in range(segs, -1, -1)]
    coords = lo + inner + hi
    out = []
    for x in coords:
        if not out or abs(x - out[-1]) > 1e-7:
            out.append(x)
    return out


def rbox(bd, size, chamfer=0.0, segs=1, cuts=(0, 0, 0), mat=0, matrix=None, deform=None, face_mat=None):
    """Chamfered box centred on the origin. size = full dimensions.

    deform(co) -> co is applied after rounding (local space), then matrix.
    face_mat(normal_axis, sign, center) -> material index (optional).
    Returns dict of {(i,j,k): BMVert} and faces.
    """
    hx, hy, hz = (s / 2 for s in size)
    ch = chamfer if isinstance(chamfer, (list, tuple)) else (chamfer, chamfer, chamfer)
    ch = [min(c, h) for c, h in zip(ch, (hx, hy, hz))]
    ax = [_axis_coords(hx, ch[0], segs, cuts[0]), _axis_coords(hy, ch[1], segs, cuts[1]),
          _axis_coords(hz, ch[2], segs, cuts[2])]
    inner = [max(0.0, hx - ch[0]), max(0.0, hy - ch[1]), max(0.0, hz - ch[2])]
    lim = [len(a) - 1 for a in ax]
    vmap = {}

    def get(i, j, k):
        key = (i, j, k)
        if key in vmap:
            return vmap[key]
        p = [ax[0][i], ax[1][j], ax[2][k]]
        inn = [max(-inner[a], min(inner[a], p[a])) for a in range(3)]
        d = V([p[a] - inn[a] for a in range(3)])
        if d.length > 1e-9 and max(ch) > 0:
            # anisotropic chamfer: normalise in chamfer-scaled space
            ds = V([d[a] / ch[a] if ch[a] > 0 else 0 for a in range(3)])
            if ds.length > 1e-9:
                ds.normalize()
                d = V([ds[a] * ch[a] for a in range(3)])
        co = V(inn) + d
        if deform:
            co = deform(co)
        if matrix:
            co = matrix @ co
        v = bd.vert(co)
        vmap[key] = v
        return v

    faces = []
    for a in range(3):
        b, c = (a + 1) % 3, (a + 2) % 3
        for side in (0, lim[a]):
            for u in range(lim[b]):
                for w in range(lim[c]):
                    idx = []
                    for (du, dw) in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        key = [0, 0, 0]
                        key[a] = side
                        key[b] = u + du
                        key[c] = w + dw
                        idx.append(get(*key))
                    if side == 0:
                        idx = idx[::-1]
                    m = mat
                    if face_mat:
                        m = face_mat(a, 1 if side else -1, (u, w))
                    faces.append(bd.face(idx, m))
    return vmap, faces


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------
def get_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def finish_object(name, bd, collection, materials, parent=None, recalc=True, smooth=False):
    """Write builder into an object (re-using an existing object of that name)."""
    bmesh.ops.remove_doubles(bd.bm, verts=bd.bm.verts, dist=1e-5)
    if recalc:
        bd.recalc()
    obj = bpy.data.objects.get(name)
    old_mesh = None
    if obj is not None and obj.type != 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)
        obj = None
    me = bpy.data.meshes.new(name)
    bd.bm.to_mesh(me)
    bd.bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    for m in materials:
        me.materials.append(m)
    if obj is None:
        obj = bpy.data.objects.new(name, me)
    else:
        old_mesh = obj.data
        obj.data = me
        obj.modifiers.clear()
    for c in list(obj.users_collection):
        if c != collection:
            c.objects.unlink(obj)
    if collection not in obj.users_collection:
        collection.objects.link(obj)
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)
    obj.scale = (1, 1, 1)
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = Matrix.Identity(4)
    if old_mesh is not None and old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    me.name = name
    return obj


def material(name, color, rough=0.6, metal=0.0, emission=None, emission_strength=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emission:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emission_strength
    m.diffuse_color = (*color, 1.0)
    return m


def mirror_x_builder(bd):
    """Duplicate all geometry mirrored across X=0 (faces flipped so normals stay outward)."""
    bm = bd.bm
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    ret = bmesh.ops.duplicate(bm, geom=geom)
    nv = [e for e in ret['geom'] if isinstance(e, bmesh.types.BMVert)]
    nf = [e for e in ret['geom'] if isinstance(e, bmesh.types.BMFace)]
    bmesh.ops.scale(bm, vec=(-1, 1, 1), verts=nv)
    bmesh.ops.reverse_faces(bm, faces=nf)


def quadify_ngons(bm):
    """Split every ngon (even sides) into balanced quads; odd ngons get one tri."""
    for f in [f for f in bm.faces if len(f.verts) > 4]:
        vs = list(f.verts)
        mat = f.material_index
        smooth = f.smooth
        bm.faces.remove(f)
        _split_poly(bm, vs, mat, smooth)


def _split_poly(bm, vs, mat, smooth):
    n = len(vs)
    if n <= 4:
        f = bm.faces.new(vs)
        f.material_index = mat
        f.smooth = smooth
        return
    # chop quads of 3 edges around the rim, recurse on the inner polygon
    inner = []
    i = 0
    while i + 3 < n or (i + 3 == n and False):
        q = [vs[i], vs[i + 1], vs[i + 2], vs[(i + 3) % n]]
        f = bm.faces.new(q)
        f.material_index = mat
        f.smooth = smooth
        inner.append(vs[i])
        i += 3
    rest = vs[i:] + [vs[0]] if i < n else [vs[0]]
    inner_poly = inner + vs[i:]
    # dedupe while keeping order
    seen = []
    for v in inner_poly:
        if v not in seen:
            seen.append(v)
    if len(seen) >= 3:
        _split_poly(bm, seen, mat, smooth)


# ---------------------------------------------------------------------------
# Clearance helpers (keep tubes / plates off the body shell)
# ---------------------------------------------------------------------------
def densify(pts, step):
    out = [V(pts[0])]
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = V(a), V(b)
        n = max(1, int(math.ceil((b - a).length / step)))
        for k in range(1, n + 1):
            out.append(a.lerp(b, k / n))
    return out


def _dp(pts, tol, fixed):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    best, bi = -1.0, -1
    for i in range(1, len(pts) - 1):
        p = pts[i]
        if ab.length < 1e-9:
            d = (p - a).length
        else:
            t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
            d = (p - (a + ab * t)).length
        if i in fixed:
            d = max(d, tol * 10)
        if d > best:
            best, bi = d, i
    if best <= tol:
        return [a, b]
    left = _dp(pts[:bi + 1], tol, {k for k in fixed if k <= bi})
    right = _dp(pts[bi:], tol, {k - bi for k in fixed if k >= bi})
    return left[:-1] + right


def push_out(pts, bvh, clear, step=0.25, iters=6, keep_ends=True, tol=0.004):
    """Densify a (filleted) path, push points that are closer than `clear`
    to the shell out along the surface normal, smooth, then simplify."""
    p = densify(pts, step)
    n = len(p)
    for it in range(iters):
        moved = False
        for i in range(n):
            if keep_ends and (i == 0 or i == n - 1):
                continue
            loc, nrm, idx, dist = bvh.find_nearest(p[i])
            if loc is None:
                continue
            if dist < clear:
                p[i] = loc + nrm * clear
                moved = True
        if not moved:
            break
        if it < iters - 1:
            q = p[:]
            for i in range(1, n - 1):
                q[i] = p[i - 1] * 0.25 + p[i] * 0.5 + p[i + 1] * 0.25
            p = q
    return _dp(p, tol, set())


def min_clearance(pts, bvh, step=0.05):
    worst = 1e9
    for q in densify(pts, step):
        loc, nrm, idx, dist = bvh.find_nearest(q)
        if loc is None:
            continue
        side = (q - loc).dot(nrm)
        d = dist if (side >= 0 or dist > 0.3) else -dist
        worst = min(worst, d)
    return worst


def thick_grid(bd, P, N, t, mat=0, side_mat=None):
    """Closed plate from a rows x cols grid of outer points P and outward normals N."""
    side_mat = mat if side_mat is None else side_mat
    R, C = len(P), len(P[0])
    A = [[bd.vert(P[i][j]) for j in range(C)] for i in range(R)]
    Bk = [[bd.vert(V(P[i][j]) - V(N[i][j]) * t) for j in range(C)] for i in range(R)]
    for i in range(R - 1):
        for j in range(C - 1):
            bd.face((A[i][j], A[i][j + 1], A[i + 1][j + 1], A[i + 1][j]), mat)
            bd.face((Bk[i][j], Bk[i + 1][j], Bk[i + 1][j + 1], Bk[i][j + 1]), mat)
    ring_a = [A[0][j] for j in range(C)] + [A[i][C - 1] for i in range(1, R)] + \
             [A[R - 1][j] for j in range(C - 2, -1, -1)] + [A[i][0] for i in range(R - 2, 0, -1)]
    ring_b = [Bk[0][j] for j in range(C)] + [Bk[i][C - 1] for i in range(1, R)] + \
             [Bk[R - 1][j] for j in range(C - 2, -1, -1)] + [Bk[i][0] for i in range(R - 2, 0, -1)]
    bd.strip(ring_b, ring_a, side_mat, closed=True)
    return A, Bk


def frame_matrix(origin, normal, up=V((0, 0, 1))):
    """Matrix whose local Z = normal, local Y ~ up."""
    z = V(normal).normalized()
    upv = V(up)
    if abs(z.dot(upv)) > 0.98:
        upv = V((0, 1, 0)) if abs(z.y) < 0.9 else V((1, 0, 0))
    x = upv.cross(z).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = V(origin)
    return m


def square_ring(bd, m, half, r_in, depth, segs=16, mat=0, inner_depth=None):
    """Square plate with a round hole, local XY plane, front at z=0, back at z=-depth."""
    inner_depth = depth if inner_depth is None else inner_depth
    rings = {}
    for key, zz in (('f', 0.0), ('b', -depth)):
        sq, ci = [], []
        for k in range(segs):
            a = 2 * math.pi * k / segs + math.pi / 4
            c, s = math.cos(a), math.sin(a)
            k2 = half / max(abs(c), abs(s))
            sq.append(bd.vert(m @ V((c * k2, s * k2, zz))))
            ci.append(bd.vert(m @ V((c * r_in, s * r_in, zz if key == 'f' else -inner_depth))))
        rings[key] = (sq, ci)
    (sqf, cif), (sqb, cib) = rings['f'], rings['b']
    bd.strip(cif, sqf, mat, True)
    bd.strip(sqf, sqb, mat, True)
    bd.strip(sqb, cib, mat, True)
    bd.strip(cib, cif, mat, True)
