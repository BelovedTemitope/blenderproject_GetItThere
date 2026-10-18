"""Exo-cage, rock sliders, roof rack, light bar and roof wing.

Every tube either runs continuously (filleted bends) or ends on the centre
line of the tube/part it is welded to, so no end caps poke out of a joint.
Paths are pushed off the body shell to a fixed clearance with a BVH.
"""
import math

from mathutils import Matrix, Vector as V
from mathutils.bvhtree import BVHTree

import mb_body as B
import mb_lib as L

R_CAGE = 0.15
R_RACK = 0.11
CLEAR = R_CAGE + 0.1
HOOP_Y = {'A': -5.85, 'B': -2.9, 'C': 1.34, 'R': 5.9}
RAIL = (3.44, 9.56)       # roof-edge rail (x, z)
HOOP_TOP = 9.86           # hoop centre height over the roof
SLIDER = (4.16, 2.42)
RACK_X = (2.95, 0.95)
RACK_Y = (-2.9, 5.9)
LAMP_X = (-1.86, -0.62, 0.62, 1.86)


def body_bvh():
    bd, _ = B.build_body({'paint': 0, 'navy': 0})
    bvh = BVHTree.FromBMesh(bd.bm)
    bd.bm.free()
    return bvh


def _path(pts, fillet, bvh, clear=CLEAR):
    p = L.fillet_path(pts, fillet)
    if bvh is not None:
        p = L.push_out(p, bvh, clear)
        p = L.fillet_path(p, 0.0)
    return p


def z_at(path, x, y=None):
    """Height of a path at a given x (first crossing)."""
    best = None
    for a, b in zip(path[:-1], path[1:]):
        if (a.x - x) * (b.x - x) <= 0 and abs(b.x - a.x) > 1e-9:
            t = (x - a.x) / (b.x - a.x)
            z = a.z + (b.z - a.z) * t
            if best is None or z > best:
                best = z
    return best


def build(ctx):
    bvh = body_bvh()
    paths = {}
    bd = L.Builder()
    for s in (1, -1):
        side = [(4.08 * s, -8.47, 3.4), (4.08 * s, -8.47, 6.85), (3.8 * s, -6.75, 8.8), (RAIL[0] * s, -6.15, RAIL[1]),
                (RAIL[0] * s, 6.2, RAIL[1]), (3.75 * s, 7.1, 8.8), (3.9 * s, 7.27, 7.3), (3.9 * s, 7.27, 4.0),
                (3.8 * s, 7.5, 3.3)]
        p = _path(side, 0.4, bvh)
        paths['side%d' % s] = p
        L.sweep(bd, p, L.circle_profile(R_CAGE, 8), 0, True, False, True, True)
        slider = [(2.65 * s, -3.2, 2.45), (SLIDER[0] * s, -3.2, SLIDER[1]), (SLIDER[0] * s, 1.95, SLIDER[1]),
                  (2.65 * s, 1.95, 2.45)]
        p = _path(slider, 0.3, None)
        L.sweep(bd, p, L.circle_profile(R_CAGE * 1.12, 8), 0, True, False, True, True)
    for key in ('B', 'C'):
        y = HOOP_Y[key]
        half = [(SLIDER[0], y, SLIDER[1]), (4.15, y, 6.85), (3.82, y, 8.8), (RAIL[0], y, RAIL[1]), (2.85, y, HOOP_TOP)]
        pts = half + [(-x, yy, z) for (x, yy, z) in reversed(half)]
        p = _path(pts, 0.35, bvh)
        paths[key] = p
        L.sweep(bd, p, L.circle_profile(R_CAGE, 8), 0, True, False, True, True)
    for key in ('A', 'R'):
        y = HOOP_Y[key]
        pts = [(RAIL[0], y, RAIL[1]), (2.85, y, HOOP_TOP), (-2.85, y, HOOP_TOP), (-RAIL[0], y, RAIL[1])]
        p = _path(pts, 0.35, bvh)
        paths[key] = p
        L.sweep(bd, p, L.circle_profile(R_CAGE * 0.87, 8), 0, True, False, True, True)
    ctx.obj('Cage_Exoskeleton', bd, 'Cage_Rack', ['steel'])
    ctx.cage_paths = paths
    for k, p in paths.items():
        print('cage clearance', k, round(L.min_clearance(p, bvh), 3))
    rack(ctx, paths)
    lightbar(ctx, paths)
    wing(ctx, paths)


def rack(ctx, paths):
    bd = L.Builder()
    zr = HOOP_TOP + R_CAGE + R_RACK
    y0, y1 = RACK_Y
    for x in (RACK_X[0], RACK_X[1], -RACK_X[1], -RACK_X[0]):
        zf = z_at(paths['B'], x)
        zb = z_at(paths['R'], x)
        pts = [(x, y0, zf), (x, y0 + 0.32, zr), (x, y1 - 0.32, zr), (x, y1, zb)]
        L.tube(bd, pts, R_RACK, 8, 0, fillet=0.18, caps=True)
    for y in (-0.8, 1.75, 3.6):
        L.tube(bd, [(RACK_X[0], y, zr), (-RACK_X[0], y, zr)], R_RACK * 0.9, 8, 0, caps=True)
    ctx.obj('RoofRack', bd, 'Cage_Rack', ['steel'])
    ctx.rack_top = zr + R_RACK


def lightbar(ctx, paths):
    bd = L.Builder()
    y0 = -6.1
    zc = 10.55
    for x in LAMP_X:
        hz = z_at(paths['A'], x)
        L.tube(bd, [(x, HOOP_Y['A'], hz), (x, -5.98, zc - 0.43)], 0.06, 8, 0, caps=True)
        L.rbox(bd, (0.1, 0.2, 0.14), 0.02, 1, (0, 0, 0), 0, Matrix.Translation((x, -5.98, zc - 0.44)))
        prof = [(0.1, y0 + 0.34), (0.3, y0 + 0.31), (0.42, y0 + 0.16), (0.45, y0 - 0.08), (0.45, y0 - 0.22),
                (0.38, y0 - 0.24), (0.37, y0 - 0.2)]
        L.lathe(bd, prof, 16, 0, V((x, 0, zc)), 'Y', True, False)
        L.lathe(bd, [(0.37, y0 - 0.2), (0.3, y0 - 0.25), (0.17, y0 - 0.28), (0.06, y0 - 0.29)], 16, 1, V((x, 0, zc)),
                'Y', False, True)
    ctx.obj('LightBar', bd, 'Cage_Rack', ['black', 'lens_clear'])


def wing(ctx, paths):
    bd = L.Builder()
    yc, zc, aoa = 6.6, 10.5, math.radians(14)
    foil = [(-0.8, 0.0), (-0.62, 0.09), (-0.1, 0.12), (0.5, 0.065), (0.8, 0.0), (0.5, -0.02), (-0.1, -0.04),
            (-0.62, -0.05)]
    ca, sa = math.cos(aoa), math.sin(aoa)
    rot = [(y * ca - z * sa, y * sa + z * ca) for (y, z) in foil]

    def ring(x):
        return [bd.vert((x, yc + y, zc + z)) for (y, z) in rot]
    xs = [-3.3, -1.6, 0.0, 1.6, 3.3]
    rings = [ring(x) for x in xs]
    bd.loft(rings, 0, closed=True)
    bd.cap(rings[0], 0)
    bd.cap(rings[-1], 0)
    # end plates
    for s in (1, -1):
        outline = [(5.62, 10.12), (5.72, 10.62), (7.42, 10.98), (7.38, 10.28)]
        P = [[V((s * 3.38, outline[0][0], outline[0][1])), V((s * 3.38, outline[3][0], outline[3][1]))],
             [V((s * 3.38, outline[1][0], outline[1][1])), V((s * 3.38, outline[2][0], outline[2][1]))]]
        N = [[V((s, 0, 0))] * 2] * 2
        L.thick_grid(bd, P, N, 0.08, 0)
    # struts: plates from the rear hoop up into the wing's lower surface
    under = lambda yy: zc + (yy - yc) * math.tan(aoa)
    for s in (1, -1):
        x = s * 1.6
        hz = z_at(paths['R'], x)
        P = [[V((x + 0.03, 5.75, hz)), V((x + 0.03, 6.05, hz))],
             [V((x + 0.03, 6.25, under(6.25))), V((x + 0.03, 6.75, under(6.75)))]]
        N = [[V((1, 0, 0))] * 2] * 2
        L.thick_grid(bd, P, N, 0.06, 0)
    ctx.obj('RoofWing', bd, 'Cage_Rack', ['steel'])
