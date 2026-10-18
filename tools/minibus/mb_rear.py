"""Rear: bumper, shackles, tail lights, corner armour panels, exhaust stack, ladder, spare carrier."""
import math

from mathutils import Matrix, Vector as V

import mb_body as B
import mb_cage as C
import mb_front as F
import mb_lib as L

REAR_Y = 7.25
BUMPER = dict(y=7.6, z=(2.72, 3.48), half=3.95)
STACK = (4.15, 6.9)
LADDER_X = (1.7, 2.6)


def build(ctx):
    bumper(ctx)
    taillights(ctx)
    panels_and_stack(ctx)
    ladder(ctx)
    spare_carrier(ctx)


def bumper(ctx):
    bd = L.Builder()
    zc = sum(BUMPER['z']) / 2
    hu = (BUMPER['z'][1] - BUMPER['z'][0]) / 2
    h = BUMPER['half']
    path = [V((h, BUMPER['y'], zc)), V((h * 0.5, BUMPER['y'], zc)), V((0, BUMPER['y'], zc)),
            V((-h * 0.5, BUMPER['y'], zc)), V((-h, BUMPER['y'], zc))]
    L.sweep(bd, path, F._chamfer_rect(hu, 0.29, 0.09), 0, True, False, True, True)
    ctx.obj('Bumper_Rear', bd, 'Rear', ['steel'])
    sh = L.Builder()
    for s in (1, -1):
        F.shackle(sh, s * 2.7, BUMPER['y'] + 0.29, 2.98, 1, 0, 1)
    ctx.obj('TowShackles_Rear', sh, 'Rear', ['red', 'steel'])


def taillights(ctx):
    bd = L.Builder()
    y = REAR_Y
    for s in (1, -1):
        L.rbox(bd, (1.16, 0.06, 0.74), 0.03, 1, (0, 0, 0), 0, Matrix.Translation((s * 2.9, y + 0.03, 3.96)))
        L.rbox(bd, (0.52, 0.06, 0.62), 0.03, 1, (0, 0, 0), 1, Matrix.Translation((s * 3.17, y + 0.07, 3.96)))
        L.rbox(bd, (0.5, 0.06, 0.28), 0.03, 1, (0, 0, 0), 2, Matrix.Translation((s * 2.6, y + 0.07, 4.12)))
        L.rbox(bd, (0.5, 0.06, 0.28), 0.03, 1, (0, 0, 0), 3, Matrix.Translation((s * 2.6, y + 0.07, 3.8)))
    # tailgate handle + lock
    L.rbox(bd, (0.6, 0.07, 0.12), 0.03, 1, (2, 0, 0), 4, Matrix.Translation((0.95, y + 0.035, 6.5)))
    L.lathe(bd, [(0.06, y + 0.02), (0.06, y + 0.09)], 8, 4, V((1.45, 0, 6.5)), 'Y', True, True)
    ctx.obj('TailLights', bd, 'Rear', ['black', 'lens_red', 'lens_orange', 'lens_white', 'chrome'])


def _row_interp(table, z):
    zs = [B.ROW_Z['r0'], B.SILL_Z, 4.8, B.ROW_Z['rf'], B.ROW_Z['r2'], B.ROW_Z['r3'], B.ROW_Z['r4'], B.ROW_Z['r5']]
    for k in range(len(zs) - 1):
        if zs[k] <= z <= zs[k + 1]:
            t = (z - zs[k]) / (zs[k + 1] - zs[k])
            return table[k] + (table[k + 1] - table[k]) * t
    return table[-1]


def corner_section(z, s):
    """Body cross-section points around the rear corner at height z (side -> rear)."""
    sx = _row_interp(B.SIDE_X, z)
    ry = _row_interp(B.REAR_Y, z)
    ch = _row_interp(B.CORNER_CH, z)
    k = sx / 3.9
    return [V((s * sx, 6.35, z)), V((s * sx, ry - ch, z)), V((s * 3.6 * k, ry, z)), V((s * 3.5 * k, ry, z))]


def panels_and_stack(ctx):
    bvh = C.body_bvh()
    bd = L.Builder()
    zs = [3.75, 4.75, 5.8, 6.85, 7.6, 8.3]
    for s in (1, -1):
        P, N = [], []
        for z in zs:
            sec = corner_section(z, s)
            row_p, row_n = [], []
            for j, p in enumerate(sec):
                # normal = average of neighbouring face normals from the shell
                nrms = []
                for q in ([sec[j - 1]] if j > 0 else []) + ([sec[j + 1]] if j < len(sec) - 1 else []):
                    mid = p.lerp(q, 0.5)
                    loc, n, idx, d = bvh.find_nearest(mid)
                    nrms.append(n)
                n = sum(nrms, V()).normalized()
                row_p.append(p + n * 0.075)
                row_n.append(n)
            P.append(row_p)
            N.append(row_n)
        if s < 0:
            P = [r[::-1] for r in P]
            N = [r[::-1] for r in N]
        L.thick_grid(bd, P, N, 0.045, 0)
        # rivets down the front edge and across the top
        for z in (3.8, 5.0, 6.2, 7.4, 8.2):
            sec = corner_section(z, s)
            p = sec[0].lerp(sec[1], 0.12)
            loc, n, idx, d = bvh.find_nearest(p)
            L.rbox(bd, (0.08, 0.08, 0.05), 0.02, 1, (0, 0, 0), 0, L.frame_matrix(loc + n * 0.08, n))
    ctx.obj('Rear_CornerPanels', bd, 'Rear', ['metal'])

    ex = L.Builder()
    x, y = STACK
    pts = [(x, y, 2.6), (x, y, 9.2), (x, y + 0.15, 9.55), (x, y + 0.5, 9.75)]
    L.tube(ex, pts, 0.15, 8, 0, fillet=0.3, caps=True)
    # clamps with stand-off brackets to the armour panel
    for z in (3.9, 6.0, 8.0):
        L.lathe(ex, [(0.18, z - 0.07), (0.18, z + 0.07)], 8, 1, V((x, y, 0)), 'Z', True, True)
        sec = corner_section(z, 1)
        panel_x = sec[0].x + 0.06
        w = (x - 0.12) - panel_x
        L.rbox(ex, (w, 0.12, 0.1), 0.02, 1, (0, 0, 0), 1, Matrix.Translation((panel_x + w / 2, y, z)))
    ctx.obj('ExhaustStack', ex, 'Rear', ['metal', 'steel'])


def ladder(ctx):
    bvh = C.body_bvh()
    paths = getattr(ctx, 'cage_paths', None)
    bd = L.Builder()
    x0, x1 = LADDER_X
    hz0 = C.z_at(paths['R'], x0) if paths else 9.86
    hz1 = C.z_at(paths['R'], x1) if paths else 9.86

    def rail(x, hz):
        return [(x, C.HOOP_Y['R'], hz), (x, 6.35, 9.72), (x, 6.8, 9.45), (x, 7.22, 8.75), (x, 7.48, 6.85), (x, 7.48, 4.55)]
    left = rail(x0, hz0)
    right = rail(x1, hz1)
    pts = left + right[::-1]
    path = L.fillet_path(pts, 0.2)
    path = L.push_out(path, bvh, 0.18)
    path = L.fillet_path(path, 0.0)
    L.sweep(bd, path, L.circle_profile(0.065, 8), 0, True, False, True, True)
    print('ladder clearance', round(L.min_clearance(path, bvh), 3))

    def rail_y(z):
        if z <= 6.85:
            return 7.48
        return 7.48 + (7.22 - 7.48) * (z - 6.85) / (8.75 - 6.85)
    z = 4.95
    while z < 8.6:
        y = rail_y(z)
        L.tube(bd, [(x0, y, z), (x1, y, z)], 0.045, 8, 0, caps=True)
        z += 0.45
    for zz in (4.75, 6.6):
        for x in (x0, x1):
            L.rbox(bd, (0.08, 0.26, 0.1), 0.02, 1, (0, 0, 0), 0, Matrix.Translation((x, REAR_Y + 0.12, zz)))
    ctx.obj('RearLadder', bd, 'Rear', ['metal'])


def spare_carrier(ctx):
    from mb_parts import SPARE_LOC
    bd = L.Builder()
    x, y, z = SPARE_LOC
    L.rbox(bd, (1.6, 0.1, 0.42), 0.03, 1, (2, 0, 0), 0, Matrix.Translation((x, REAR_Y + 0.05, z)))
    L.rbox(bd, (0.42, 0.1, 1.5), 0.03, 1, (0, 0, 2), 0, Matrix.Translation((x, REAR_Y + 0.05, z)))
    hub_end = y + 0.19
    L.lathe(bd, [(0.3, REAR_Y + 0.08), (0.3, REAR_Y + 0.2), (0.24, REAR_Y + 0.3), (0.24, hub_end), (0.2, hub_end + 0.08)],
            12, 0, V((x, 0, z)), 'Y', True, True)
    ctx.obj('SpareCarrier', bd, 'Rear', ['steel'])
