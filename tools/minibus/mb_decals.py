"""Livery decals: '01' roundels on the front doors and the rear diagonal navy band.

Decals are thin quad surfaces projected onto the shell (offset a few mm along
the surface normal) so they follow the body exactly without z-fighting.
"""
import math

from mathutils import Vector as V

import mb_body as B
import mb_cage as C
import mb_lib as L

ROUNDEL = dict(y=-5.37, z=5.74, r_in=0.72, r_out=0.93)
BAND = [((1.12, 4.38), (1.12, 5.22)), ((1.9, 4.62), (1.8, 5.45)), ((2.8, 4.95), (2.66, 5.76)),
        ((3.6, 5.3), (3.45, 6.08)), ((4.35, 5.68), (4.2, 6.38)), ((5.05, 6.05), (4.9, 6.6)),
        ((5.7, 6.45), (5.32, 6.95)), ((6.05, 7.1), (5.35, 7.4)), ((6.2, 7.8), (5.38, 7.95)), ((6.3, 8.45), (5.45, 8.55))]
SEAMS_SIDE = [[(-8.22, 3.15), (-8.22, 6.8)], [(-3.56, 3.95), (-3.56, 6.8)]]          # front door edges (y, z)
# T3 rear: upper hatch from the roof down to just above the tail lights, engine lid between the lights
SEAMS_REAR = [[(3.3, 4.45), (3.3, 6.85), (3.3, 8.2), (3.3, 8.95)], [(-3.3, 4.45), (-3.3, 6.85), (-3.3, 8.2), (-3.3, 8.95)],
              [(3.3, 4.45), (-3.3, 4.45)], [(3.3, 9.12), (-3.3, 9.12)],
              [(2.2, 3.6), (2.2, 4.45)], [(-2.2, 3.6), (-2.2, 4.45)], [(2.2, 3.6), (-2.2, 3.6)]]


def _k(z):
    from mb_rear import _row_interp
    import mb_body as B
    return _row_interp(B.SIDE_X, z) / 3.9


def project(bvh, p, axis, off):
    """Drop a point straight onto the shell along -axis (no sliding over ridges), then lift it by off."""
    hit = bvh.ray_cast(p + axis * 1.5, -axis, 3.0)
    if hit[0] is not None and (hit[0] - p).length < 0.6:
        return hit[0] + axis * off, axis
    loc, nrm, idx, d = bvh.find_nearest(p)
    return loc + nrm * off, nrm


def ribbon(bd, bvh, pts, width, mat, off=0.03, axis=None):
    pts = L.densify([V(p) for p in pts], 0.06)
    proj = []
    for p in pts:
        if axis is not None:
            q, n = project(bvh, p, axis, 0.0)
            proj.append((q, axis))
        else:
            loc, nrm, idx, d = bvh.find_nearest(p)
            proj.append((loc, nrm))
    rows = []
    for i, (loc, nrm) in enumerate(proj):
        a = proj[max(i - 1, 0)][0]
        b = proj[min(i + 1, len(proj) - 1)][0]
        t = (b - a).normalized()
        side = nrm.cross(t).normalized() * (width / 2)
        rows.append([bd.vert(loc + nrm * off - side), bd.vert(loc + nrm * off + side)])
    bd.loft(rows, mat)


def _orient(bd, normal_fn):
    bd.bm.normal_update()
    for f in bd.bm.faces:
        want = normal_fn(f.calc_center_median())
        if f.normal.dot(want) < 0:
            f.normal_flip()


def build(ctx):
    if L.OPTIMIZE:
        return build_lite(ctx)
    bvh = C.body_bvh()
    bd = L.Builder()
    WHITE, RED, BLACK, NAVY = 0, 1, 2, 3
    for s in (1, -1):
        x0 = s * 3.9

        def P(u, v, off):
            # u: reading direction (screen right for a viewer outside this side), v: up.
            # Every decal vertex is projected onto the shell so it wraps over the body ridges.
            p = V((x0, ROUNDEL['y'] + s * u, ROUNDEL['z'] + v))
            q = project(bvh, p, V((s, 0, 0)), off + 0.01)[0]
            if B.GROOVE:
                # a printed sticker bridges a pressed groove instead of dipping into it
                flat = s * (B.side_x_at(p.z) + off + 0.01)
                if abs(flat) > abs(q.x):
                    q.x = flat
            return q

        def ring(cu, rx, ry, n, off):
            return [bd.vert(P(cu + rx * math.cos(2 * math.pi * k / n), ry * math.sin(2 * math.pi * k / n), off))
                    for k in range(n)]
        n = 48
        radii = [0.06 + (ROUNDEL['r_in'] - 0.06) * k / 7 for k in range(8)]
        rings = [ring(0, r, r, n, 0.02) for r in radii]
        bd.cap(rings[0], WHITE)
        bd.loft(rings, WHITE, closed=True)
        red = [rings[-1]] + [ring(0, r, r, n, 0.02) for r in (0.825, ROUNDEL['r_out'])]
        bd.loft(red, RED, closed=True)
        # "0"
        zero = [ring(-0.2, rx, ry, 24, 0.026) for rx, ry in ((0.085, 0.19), (0.13, 0.24), (0.18, 0.29))]
        bd.loft(zero, BLACK, closed=True)
        # "1": stem (subdivided so it follows the ridge) + flag
        stem = [[bd.vert(P(u, -0.29 + 0.58 * k / 8, 0.026)) for u in (0.16, 0.22, 0.28)] for k in range(9)]
        bd.loft(stem, BLACK)
        flag = [[stem[-1][0], stem[-2][0]], [bd.vert(P(0.11, 0.24, 0.026)), bd.vert(P(0.11, 0.15, 0.026))],
                [bd.vert(P(0.06, 0.16, 0.026)), bd.vert(P(0.06, 0.07, 0.026))]]
        bd.loft(flag, BLACK)
        # rear diagonal band
        # densely sampled so the strip follows the belt-line crease instead of cutting through it
        rows = []
        for k in range(len(BAND) - 1):
            (lo0, hi0), (lo1, hi1) = BAND[k], BAND[k + 1]
            for j in range(8 if k < len(BAND) - 2 else 9):
                u = j / 8.0
                lo = (lo0[0] + (lo1[0] - lo0[0]) * u, lo0[1] + (lo1[1] - lo0[1]) * u)
                hi = (hi0[0] + (hi1[0] - hi0[0]) * u, hi0[1] + (hi1[1] - hi0[1]) * u)
                row = []
                for t in (0.0, 1 / 6, 2 / 6, 0.5, 4 / 6, 5 / 6, 1.0):
                    y = lo[0] + (hi[0] - lo[0]) * t
                    z = lo[1] + (hi[1] - lo[1]) * t
                    row.append(bd.vert(project(bvh, V((x0, y, z)), V((s, 0, 0)), 0.03)[0]))
                rows.append(row)
        bd.loft(rows, NAVY)
        for seam in SEAMS_SIDE:
            ribbon(bd, bvh, [(x0, y, z) for (y, z) in seam], 0.035, BLACK, axis=V((s, 0, 0)))
        if B.DOORS:   # sliding-door track along the rear quarter panel
            ribbon(bd, bvh, [(x0, 1.06, 6.7), (x0, 4.55, 6.7)], 0.07, BLACK, axis=V((s, 0, 0)))
    for seam in SEAMS_REAR:
        ribbon(bd, bvh, [(x * _k(z), 7.4, z) for (x, z) in seam], 0.035, BLACK)
    _orient(bd, lambda c: V((0, 1, 0)) if c.y > 6.9 else V((1 if c.x > 0 else -1, 0, 0)))
    o = ctx.obj('Livery_Decals', bd, 'Body', ['decal_white', 'decal_red', 'decal_black', 'navy'], recalc=False)
    # smooth-shade the thin decal skin so it reads cleanly where it folds over the swage lines
    for p in o.data.polygons:
        p.use_smooth = True


# ---------------------------------------------------------------------------
# v05: light decals. The side panels under every decal depend only on height
# (tumblehome), so decals sit on that analytic surface, bridging the grooves
# like printed stickers, with vertices only where the panel actually creases.
# ---------------------------------------------------------------------------
OFF = 0.03
CREASES = (6.2, 6.85)


def _side(s, y, z, off=OFF):
    return V((s * (B.side_x_at(z) + off), y, z))


def _split_z(z0, z1):
    """Heights for a vertical run: its ends plus any panel crease in between."""
    lo, hi = min(z0, z1), max(z0, z1)
    zs = [z0] + [c for c in CREASES if lo < c < hi] + [z1]
    return sorted(zs, reverse=z0 > z1)


def build_lite(ctx):
    bvh = C.body_bvh()
    bd = L.Builder()
    WHITE, RED, BLACK, NAVY = 0, 1, 2, 3
    for s in (1, -1):
        cy, cz = ROUNDEL['y'], ROUNDEL['z']

        def P(u, v, off):
            return bd.vert(_side(s, cy + s * u, cz + v, off))

        n = 24
        ang = [math.pi / 2 + 2 * math.pi * k / n for k in range(n)]   # start at the top -> horizontal cap strips
        inner = [P(ROUNDEL['r_in'] * math.cos(a), ROUNDEL['r_in'] * math.sin(a), OFF) for a in ang]
        outer = [P(ROUNDEL['r_out'] * math.cos(a), ROUNDEL['r_out'] * math.sin(a), OFF) for a in ang]
        bd.cap(inner, WHITE)
        bd.strip(inner, outer, RED, True)
        m = 16
        a2 = [2 * math.pi * k / m for k in range(m)]
        o0 = [P(-0.2 + 0.085 * math.cos(a), 0.19 * math.sin(a), OFF + 0.006) for a in a2]
        o1 = [P(-0.2 + 0.18 * math.cos(a), 0.29 * math.sin(a), OFF + 0.006) for a in a2]
        bd.strip(o0, o1, BLACK, True)
        st = [P(u, v, OFF + 0.006) for (u, v) in ((0.16, -0.29), (0.28, -0.29), (0.28, 0.29), (0.16, 0.29))]
        bd.face(st, BLACK)
        bd.face((st[3], P(0.06, 0.16, OFF + 0.006), P(0.06, 0.07, OFF + 0.006), P(0.16, 0.17, OFF + 0.006)), BLACK)
        # rear diagonal band: two rows per segment, three across
        rows = []
        for k in range(len(BAND) - 1):
            (lo0, hi0), (lo1, hi1) = BAND[k], BAND[k + 1]
            for j in range(2 if k < len(BAND) - 2 else 3):
                u = j / 2.0
                lo = (lo0[0] + (lo1[0] - lo0[0]) * u, lo0[1] + (lo1[1] - lo0[1]) * u)
                hi = (hi0[0] + (hi1[0] - hi0[0]) * u, hi0[1] + (hi1[1] - hi0[1]) * u)
                rows.append([bd.vert(_side(s, lo[0] + (hi[0] - lo[0]) * t, lo[1] + (hi[1] - lo[1]) * t))
                             for t in (0.0, 0.5, 1.0)])
        bd.loft(rows, NAVY)
        # door shut-line seams and the slide track
        for (y0, z0), (y1, z1) in SEAMS_SIDE:
            zs = _split_z(z0, z1)
            bd.loft([[bd.vert(_side(s, y0 - 0.0175, z, OFF + 0.002)), bd.vert(_side(s, y0 + 0.0175, z, OFF + 0.002))]
                     for z in zs], BLACK)
        if B.DOORS:
            bd.loft([[bd.vert(_side(s, y, 6.665, OFF + 0.002)), bd.vert(_side(s, y, 6.735, OFF + 0.002))]
                     for y in (1.06, 4.55)], BLACK)
    for seam in SEAMS_REAR:
        ribbon_lite(bd, bvh, [(x * _k(z), 7.4, z) for (x, z) in seam], 0.035, BLACK)
    _orient(bd, lambda c: V((0, 1, 0)) if c.y > 6.9 else V((1 if c.x > 0 else -1, 0, 0)))
    ctx.obj('Livery_Decals', bd, 'Body', ['decal_white', 'decal_red', 'decal_black', 'navy'], recalc=False)


def ribbon_lite(bd, bvh, pts, width, mat, off=0.03):
    """Ribbon with vertices only at its ends and at the rear-face crease."""
    pts = [V(p) for p in pts]
    if len(pts) == 2 and abs(pts[0].z - pts[1].z) > 0.01:
        zs = _split_z(pts[0].z, pts[1].z)
        pts = [pts[0].lerp(pts[1], (z - pts[0].z) / (pts[1].z - pts[0].z)) for z in zs]
    proj = [bvh.find_nearest(p)[:2] for p in pts]
    rows = []
    for i, (loc, nrm) in enumerate(proj):
        a = proj[max(i - 1, 0)][0]
        b = proj[min(i + 1, len(proj) - 1)][0]
        side = nrm.cross((b - a).normalized()).normalized() * (width / 2)
        rows.append([bd.vert(loc + nrm * off - side), bd.vert(loc + nrm * off + side)])
    bd.loft(rows, mat)
