"""Ladder frame, solid axles, coil-over suspension, steering, driveline, exhaust run."""
import math

from mathutils import Matrix, Vector as V

import mb_body as B
import mb_lib as L

FRAME_X = 2.35          # rail centre line
FRAME_W = 0.32
FRAME_Z = (2.22, 2.69)  # rail bottom / top (top sits just under the body floor pan at 2.7)
FRAME_Y = (-9.2, 7.32)  # ends tuck into the bumpers
AXLE_HALF = 3.35        # axle housing reaches the hub
SPRING_X = 2.82
PERCH_Z = 3.3           # upper spring perch (bracket on the wheel-tub wall)
TUB_X = 2.45            # inner wheel-tub wall
DIFF_X = (-0.45, 0.35)  # front / rear diff offsets


def build(ctx):
    frame(ctx)
    axles(ctx)
    suspension(ctx)
    driveline(ctx)
    wheel_tubs(ctx)


def frame(ctx):
    bd = L.Builder()
    zc = sum(FRAME_Z) / 2
    h = FRAME_Z[1] - FRAME_Z[0]
    ln = FRAME_Y[1] - FRAME_Y[0]
    yc = sum(FRAME_Y) / 2
    for s in (1, -1):
        L.rbox(bd, (FRAME_W, ln, h), 0.04, 1, (0, 6, 0), 0, Matrix.Translation((s * FRAME_X, yc, zc)))
    # crossmembers (ends buried in the rails' centre plane)
    for y in (-8.55, -2.6, 0.6, 1.6, 7.08):
        L.rbox(bd, (2 * FRAME_X, 0.36, h * 0.8), 0.04, 1, (2, 0, 0), 0, Matrix.Translation((0, y, zc)))
    # outrigger brackets for the rock sliders / body mounts
    for s in (1, -1):
        for y in (-3.2, 1.95):
            L.rbox(bd, (0.6, 0.3, 0.3), 0.03, 1, (0, 0, 0), 0, Matrix.Translation((s * (FRAME_X + 0.3), y, 2.45)))
    ctx.obj('Chassis_Frame', bd, 'Chassis', ['chassis'])


def _diff(bd, cx, cy, cz, snout_dir, mat_house, mat_cover):
    # pumpkin: lathe around Y (snout points along snout_dir in Y)
    sd = snout_dir
    prof = [(0.12, -0.36), (0.33, -0.33), (0.47, -0.18), (0.5, 0.0), (0.47, 0.18), (0.36, 0.3), (0.22, 0.36)]
    rings, _ = L.lathe(bd, [(r, a * sd) for r, a in prof], 12, mat_house, V((cx, cy, cz)), 'Y', True, True)
    # pinion snout
    sn = [(0.24, 0.3), (0.2, 0.55), (0.2, 0.75), (0.15, 0.78)]
    L.lathe(bd, [(r, a * sd) for r, a in sn], 8, mat_house, V((cx, cy, cz)), 'Y', False, True)
    # diff cover plate on the back face
    L.lathe(bd, [(0.36, -0.37 * sd), (0.36, -0.42 * sd), (0.3, -0.45 * sd)], 12, mat_cover, V((cx, cy, cz)), 'Y',
            False, True)


def axles(ctx):
    bd = L.Builder()
    for i, wy in enumerate(B.WHEEL_Y):
        cz = B.WHEEL_Z
        dx = DIFF_X[i]
        # housing tube, both sides of the pumpkin
        for s in (1, -1):
            x0 = dx + s * 0.35
            x1 = s * AXLE_HALF
            L.tube(bd, [(x0, wy, cz), (x1, wy, cz)], 0.17, 8, 0, caps=True)
        _diff(bd, dx, wy, cz, 1 if i == 0 else -1, 0, 1)
        for s in (1, -1):
            # hub / brake drum (inside the rim barrel, rim mount face at x=4.14)
            hx = s * AXLE_HALF
            prof = [(0.2, 0.0), (0.42, 0.0), (0.56, 0.08), (0.56, 0.55), (0.42, 0.62), (0.3, 0.62), (0.3, 0.79)]
            L.lathe(bd, [(r, hx + s * a) for r, a in prof], 12, 2, V((0, wy, cz)), 'X', True, True)
            # spring perch on the axle
            L.rbox(bd, (0.62, 0.62, 0.12), 0.03, 1, (0, 0, 0), 0, Matrix.Translation((s * SPRING_X, wy, cz + 0.2)))
            # trailing-arm / shock brackets
            L.rbox(bd, (0.14, 0.7, 0.42), 0.02, 1, (0, 0, 0), 0, Matrix.Translation((s * 2.2, wy, cz - 0.05)))
            if i == 0:
                # steering knuckle (king-pin boss)
                L.lathe(bd, [(0.22, -0.45), (0.25, -0.38), (0.25, 0.38), (0.22, 0.45)], 8, 0,
                        V((s * 3.12, wy, cz)), 'Z', True, True)
                # steering arm toward the tie rod (behind the axle)
                L.rbox(bd, (0.14, 0.7, 0.14), 0.02, 1, (0, 1, 0), 0, Matrix.Translation((s * 3.0, wy + 0.4, cz - 0.3)))
    # front tie rod and drag link
    wy = B.WHEEL_Y[0]
    L.tube(bd, [(-3.0, wy + 0.72, B.WHEEL_Z - 0.3), (3.0, wy + 0.72, B.WHEEL_Z - 0.3)], 0.06, 8, 0, caps=True)
    L.tube(bd, [(2.95, wy + 0.72, B.WHEEL_Z - 0.3), (1.98, -7.62, 1.98)], 0.06, 8, 0, caps=True)
    L.rbox(bd, (0.36, 0.55, 0.45), 0.04, 1, (0, 0, 0), 0, Matrix.Translation((1.99, -7.75, 2.3)))  # steering box
    L.rbox(bd, (0.1, 0.16, 0.42), 0.02, 1, (0, 0, 0), 0, Matrix.Translation((1.99, -7.62, 2.0)))   # pitman arm
    ctx.obj('Axles_Suspension', bd, 'Chassis', ['chassis', 'rust', 'metal'])


def coil(bd, base, top, r, wire, turns, mat):
    if L.LOD:
        # game load: the spring reads as a hexagonal sleeve between the perches
        L.tube(bd, [base, V((base.x, base.y, top))], r, 8, mat, caps=False)
        return
    pts = []
    n = int(turns * 10)
    h = top - base.z
    for k in range(n + 1):
        a = 2 * math.pi * turns * k / n
        pts.append(V((r * math.cos(a), r * math.sin(a), h * k / n)) + base)
    L.sweep(bd, pts, L.circle_profile(wire, 6), mat, True, False, True, True)


def suspension(ctx):
    bd = L.Builder()
    for i, wy in enumerate(B.WHEEL_Y):
        perch_lo = B.WHEEL_Z + 0.26
        for s in (1, -1):
            x = s * SPRING_X
            coil(bd, V((x, wy, perch_lo)), PERCH_Z, 0.22, 0.045, 5.5, 0)
            # upper perch bracket welded to the tub wall
            w = SPRING_X + 0.26 - TUB_X
            L.rbox(bd, (w, 0.62, 0.12), 0.03, 1, (0, 0, 0), 1,
                   Matrix.Translation((s * (TUB_X + w / 2), wy, PERCH_Z + 0.06)))
            # shock top bracket on the tub wall
            L.rbox(bd, (0.2, 0.22, 0.3), 0.02, 1, (0, 0, 0), 1,
                   Matrix.Translation((s * (TUB_X + 0.1), wy + (0.58 if i == 0 else -0.58), PERCH_Z + 0.1)))
            # shock absorber beside the spring (behind the axle), body + shaft + eyes
            ys = wy + (0.58 if i == 0 else -0.58)
            lo = V((s * 2.75, ys, B.WHEEL_Z - 0.05))
            hi = V((s * 2.6, ys, PERCH_Z + 0.1))
            mid = lo.lerp(hi, 0.55)
            L.tube(bd, [lo, mid], 0.1, 8, 2, caps=True)
            L.tube(bd, [mid, hi], 0.045, 6, 1, caps=True)
            # trailing arm to the frame
            fy = (-2.6, 1.6)[i]
            L.tube(bd, [(s * 2.2, wy, B.WHEEL_Z - 0.15), (s * FRAME_X, fy, FRAME_Z[0] + 0.05)], 0.09, 8, 1, caps=True)
        # panhard rod
        L.tube(bd, [(-2.25, wy + (0.3 if i else -0.3), B.WHEEL_Z + 0.05), (FRAME_X, wy + (0.3 if i else -0.3), 2.3)],
               0.07, 8, 1, caps=True)
    ctx.obj('Suspension_Coilovers', bd, 'Chassis', ['metal', 'chassis', 'red'])


def driveline(ctx):
    bd = L.Builder()
    # rear engine block (flat-four style) under the rear deck, transaxle ahead of it into the rear diff
    L.rbox(bd, (2.6, 1.8, 1.25), 0.15, 2, (1, 1, 1), 0, Matrix.Translation((0.2, 5.95, 3.15)))
    L.rbox(bd, (0.9, 1.3, 0.8), 0.12, 2, (0, 1, 0), 0, Matrix.Translation((0.25, 3.55, 2.25)))
    # front prop shaft: transaxle -> front diff pinion
    a = V((0.25, 2.9, 2.0))
    b = V((DIFF_X[0], B.WHEEL_Y[0] + 0.78, B.WHEEL_Z))
    L.tube(bd, [a, b], 0.08, 8, 1, caps=True)
    for p in (a.lerp(b, 0.02), a.lerp(b, 0.98)):
        L.lathe(bd, [(0.13, -0.08), (0.13, 0.08)], 8, 1, p, 'Y', True, True)
    # exhaust: header -> muffler -> pipe to the stack at the rear-left corner
    L.rbox(bd, (2.0, 0.5, 0.45), 0.12, 2, (1, 0, 0), 2, Matrix.Translation((1.05, 6.35, 2.2)))
    L.tube(bd, [(0.55, 5.7, 2.6), (0.55, 6.1, 2.45), (0.55, 6.35, 2.3)], 0.09, 8, 2, fillet=0.2, caps=True)
    L.tube(bd, [(1.9, 6.35, 2.12), (2.9, 6.45, 1.98), (3.8, 6.85, 2.12), (4.15, 6.9, 2.6)], 0.11, 8, 2,
           fillet=0.25, caps=True)
    ctx.obj('Driveline_Exhaust', bd, 'Chassis', ['chassis', 'metal', 'rust'])


def wheel_tubs(ctx):
    """Inner wheel housings: arch band from the skin to the tub wall + the wall itself."""
    bd = L.Builder()
    for wy in B.WHEEL_Y:
        pts = B.arch_points(wy, 2.75, 15)
        for s in (1, -1):
            outer = [bd.vert((s * 3.82, y, z)) for (y, z) in pts]
            inner = [bd.vert((s * TUB_X, y, z)) for (y, z) in pts]
            bot = [bd.vert((s * TUB_X, y, 2.7)) for (y, z) in pts]
            if s > 0:
                bd.strip(outer, inner, 0)
                bd.strip(inner, bot, 0)
            else:
                bd.strip(inner, outer, 0)
                bd.strip(bot, inner, 0)
    ctx.obj('Wheel_Tubs', bd, 'Chassis', ['chassis'])
