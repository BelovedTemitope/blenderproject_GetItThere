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
    """Straight runs + filleted bends; corners only where the body forces one."""
    if bvh is None:
        return L.fillet_path(pts, fillet)
    c = clear
    for _ in range(4):
        ctrl = L.clean_path(pts, bvh, c)
        p = L.fillet_path(ctrl, fillet)
        if L.min_clearance(p, bvh) >= R_CAGE + 0.05:
            break
        c += 0.03                      # a fillet cut a convex corner too tight: give it more room
    return p
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


def _layout():
    """Cage key points for the current body variant."""
    if B.SHAPE:   # narrower greenhouse (front ortho tumblehome)
        return dict(rail=(3.06, 9.62), top=9.96, top_x=2.25, belt=(4.15, 6.2), win=3.6, rack_x=(2.15, 0.75),
                    rear=[(3.5, 7.05, 8.8), (3.9, 7.27, 6.6)], aw=(3.6, -6.75, 8.8))
    return dict(rail=RAIL, top=HOOP_TOP, top_x=2.85, belt=(4.15, 6.85), win=3.82, rack_x=RACK_X,
                rear=[(3.75, 7.1, 8.8), (3.9, 7.27, 7.3)], aw=(3.8, -6.75, 8.8))


STANDOFF = 0.24            # tube axis to panel


def _off(bvh, p, d, clear=STANDOFF):
    """Point `clear` off the panel: ray from outside along -d onto the shell through p."""
    d = V(d).normalized()
    hit = bvh.ray_cast(V(p) + d * 6.0, -d, 12.0)
    if hit[0] is None:
        return V(p)
    return hit[0] + d * clear


def _crease_zs():
    return [B.ROW_Z['rf'], B.ROW_Z['r2'], B.ROW_Z['r3']]


def clean_layout(bvh, tx):
    """Cage centre lines built from the shell itself: bends only at the body creases."""
    up = V((0.64, 0, 0.77))                       # roof-shoulder normal
    zr = 9.43                                     # mid roof shoulder
    def rail(y):
        return _off(bvh, (2.9, y, zr), up, STANDOFF + 0.04)
    zrf, zr2, zr3 = _crease_zs()
    out = {}
    for s in (1, -1):
        sx = V((s, 0, 0))
        diag = V((s * 0.707, 0.707, 0))
        a_y = {zrf: -8.47, zr2: -8.15, zr3: -6.72}
        front = [V((s * (B.SIDE_X[1] + STANDOFF), -8.47, 3.4))]
        front += [_off(bvh, (0, a_y[z], z), sx) for z in (zrf, zr2, zr3)]
        rf, rr = rail(-6.0), rail(5.95)
        rf.x *= s
        rr.x *= s
        rear = [_off(bvh, (s * 3.55, 6.95, z), diag) for z in (8.6, zr2, zrf, 4.0)]
        rear += [V((s * 3.8, 7.5, 3.3))]

        def bend(a, b, t, clear):
            # a single extra bend over a roof corner, lifted off the shell to `clear`
            m = a.lerp(b, t)
            loc, n, idx, d = bvh.find_nearest(m)
            return loc + n * clear if d < clear else m
        fc = bend(front[-1], rf, 0.3, 0.26)
        rc = bend(rr, rear[0], 0.7, 0.27)
        out['side%d' % s] = front + [fc, rf, rr, rc] + rear
    def hoop(y):
        half = [V((SLIDER[0], y, SLIDER[1]))]
        half += [_off(bvh, (0, y, z), V((1, 0, 0))) for z in (zrf, zr2, zr3)]
        r = rail(y)
        half += [r, V((tx, y, HOOP_TOP))]
        return half + [V((-p.x, p.y, p.z)) for p in reversed(half)]
    for key in ('B', 'C'):
        out[key] = hoop(HOOP_Y[key])
    for key in ('A', 'R'):
        r = rail(HOOP_Y[key])
        out[key] = [r, V((tx, r.y, HOOP_TOP)), V((-tx, r.y, HOOP_TOP)), V((-r.x, r.y, r.z))]
    out['rail_x'], out['rail_z'] = rail(0.0).x, rail(0.0).z
    return out


def build(ctx):
    global RAIL, HOOP_TOP, RACK_X
    lay = _layout()
    RAIL, HOOP_TOP, RACK_X = lay['rail'], lay['top'], lay['rack_x']
    tx = lay['top_x']
    bvh = body_bvh()
    CL = clean_layout(bvh, tx)
    RAIL = (CL['rail_x'], CL['rail_z'])
    paths = {}
    bd = L.Builder()
    for s in (1, -1):
        p = L.fillet_path(CL['side%d' % s], 0.35)
        paths['side%d' % s] = p
        L.sweep(bd, p, L.circle_profile(R_CAGE, 8), 0, True, False, True, True)
        slider = [(2.65 * s, -3.2, 2.45), (SLIDER[0] * s, -3.2, SLIDER[1]), (SLIDER[0] * s, 1.95, SLIDER[1]),
                  (2.65 * s, 1.95, 2.45)]
        p = _path(slider, 0.3, None)
        L.sweep(bd, p, L.circle_profile(R_CAGE * 1.12, 8), 0, True, False, True, True)
    for key in ('B', 'C'):
        y = HOOP_Y[key]
        p = L.fillet_path(CL[key], 0.35)
        paths[key] = p
        L.sweep(bd, p, L.circle_profile(R_CAGE, 8), 0, True, False, True, True)
    for key in ('A', 'R'):
        y = HOOP_Y[key]
        p = L.fillet_path(CL[key], 0.35)
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
    zc = HOOP_TOP + 0.69
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
    yc, zc, aoa = 6.6, HOOP_TOP + 0.64, math.radians(14)
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
