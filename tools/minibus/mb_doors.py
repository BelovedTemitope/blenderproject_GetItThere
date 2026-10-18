"""Sliding doors (both sides) for the door variant.

Each door is a separate part whose outer skin is sampled from the same body
surface (tumblehome + swage-line grooves), so when closed it continues the
panel flush, with a small shut-line gap all round the opening.
"""
from mathutils import Matrix, Vector as V

import mb_body as B
import mb_lib as L

GAP = 0.03
OPEN_Y = (-2.86, 1.0)          # body columns c8 / c9
OPEN_Z = (B.SILL_Z, B.ROW_Z['r3'])
WIN_TOP = 8.58
FRAME = 0.26


def surface_x(z):
    """Outer skin half-width at height z, including the grooves (matches the body lattice rows)."""
    x = B.side_x_at(z)
    if B.RIDGES:
        d = -B.RIDGE_D if B.GROOVE else B.RIDGE_D
        for rows in (B.RIDGE_UPPER_Z, B.RIDGE_LOWER_Z):
            z0, z1, z2, z3 = rows
            if z1 <= z <= z2:
                x += d
            elif z0 < z < z1:
                x += d * (z - z0) / (z1 - z0)
            elif z2 < z < z3:
                x += d * (z3 - z) / (z3 - z2)
    return x


def build(ctx):
    if not B.DOORS:
        return
    ya, yb = OPEN_Y[0] + GAP, OPEN_Y[1] - GAP
    za, zb = OPEN_Z[0] + GAP, OPEN_Z[1] - GAP * 1.6
    zs = [za]
    if B.RIDGES:
        zs += B.RIDGE_LOWER_Z
    zs += [5.1]
    if B.RIDGES:
        zs += B.RIDGE_UPPER_Z
    zs += [B.ROW_Z['rf'], B.ROW_Z['r2'], WIN_TOP, zb]
    ys = [ya, ya + FRAME, yb - FRAME, yb]
    iw0 = zs.index(B.ROW_Z['r2'])
    skip = {(iw0, 1)}                                  # window: middle column, belt -> window top
    for s, tag in ((1, 'L'), (-1, 'R')):
        bd = L.Builder()
        P, N = [], []
        for z in zs:
            x = surface_x(z)
            dxdz = (B.side_x_at(z + 0.01) - B.side_x_at(z - 0.01)) / 0.02
            n = V((s, 0, -dxdz)).normalized()          # true panel normal (tumblehome), like the body solidify
            P.append([V((s * x, y, z)) for y in ys])
            N.append([n] * len(ys))
        L.thick_grid_holes(bd, P, N, 0.1, skip, 0, 1, 0)
        # pull handle sitting in the upper groove near the rear edge, lock below it
        hz = sum(B.RIDGE_UPPER_Z[1:3]) / 2 if B.RIDGES else 5.9
        hx = surface_x(hz) + 0.03
        L.rbox(bd, (0.06, 0.62, 0.1), 0.025, 1, (0, 0, 0), 2, Matrix.Translation((s * hx, yb - 0.6, hz)))
        L.lathe(bd, [(0.05, s * (surface_x(5.35) - 0.01)), (0.05, s * (surface_x(5.35) + 0.04))], 8, 2,
                V((0, yb - 0.4, 5.35)), 'X', True, True)
        o = ctx.obj('Door_Sliding_%s' % tag, bd, 'Body', ['paint', 'interior', 'chrome'])
        # pivot at the door centre so it can be slid / animated on its own
        c = V((s * surface_x(6.0), (ya + yb) / 2, (za + zb) / 2))
        o.data.transform(Matrix.Translation(-c))
        o.location = c
