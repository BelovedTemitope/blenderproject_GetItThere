"""Front end: bumper, bull bar, fascia (grille, lamps, plates), skid plate, shackles, mirrors, handles."""
import math

from mathutils import Matrix, Vector as V

import mb_body as B
import mb_lib as L

FACE_Y = -9.1                    # flat front panel (z 2.7 .. 6.2)
BUMPER = dict(y=-9.38, z=(2.71, 3.63), half=4.25, side_back=-8.45)
BAR_Y = -9.47                    # bull bar uprights / hoops
BAR_Z = (4.4, 5.75)
A_TUBE = (4.13, -8.47)           # cage A-pillar tube (x, y) the bull-bar hoops tie into
HEAD_X, HEAD_Z = 2.89, 5.12


def build(ctx):
    bumper(ctx)
    bullbar(ctx)
    fascia(ctx)
    plates(ctx)
    skid(ctx)
    shackles(ctx)
    mirrors(ctx)
    handles_and_rockers(ctx)


def _chamfer_rect(hu, hv, c):
    return [(hu, -hv + c), (hu, hv - c), (hu - c, hv), (-hu + c, hv), (-hu, hv - c), (-hu, -hv + c),
            (-hu + c, -hv), (hu - c, -hv)]


def bumper(ctx):
    bd = L.Builder()
    zc = sum(BUMPER['z']) / 2
    hu = (BUMPER['z'][1] - BUMPER['z'][0]) / 2
    h = BUMPER['half']
    y = BUMPER['y']
    pts = [(h, BUMPER['side_back'], zc), (h, y + 0.33, zc), (h - 0.4, y, zc), (-h + 0.4, y, zc),
           (-h, y + 0.33, zc), (-h, BUMPER['side_back'], zc)]
    path = L.fillet_path(pts, 0.22)
    L.sweep(bd, path, _chamfer_rect(hu, 0.27, 0.09), 0, True, False, True, True)
    # top tread strip / reinforcement lip on the front face
    L.rbox(bd, (2 * h - 1.1, 0.06, 0.16), 0.02, 1, (4, 0, 0), 0, Matrix.Translation((0, y - 0.29, BUMPER['z'][1] - 0.2)))
    ctx.obj('Bumper_Front', bd, 'Front', ['steel'])


def bullbar(ctx):
    bd = L.Builder()
    r = 0.12
    ax, ay = A_TUBE
    for z in BAR_Z:
        pts = [(ax, ay, z), (4.3, -9.0, z), (3.85, BAR_Y, z), (-3.85, BAR_Y, z), (-4.3, -9.0, z), (-ax, ay, z)]
        L.tube(bd, pts, r, 8, 0, fillet=0.3, caps=True)
    for x in (-3.55, -2.15, 2.15, 3.55):
        L.tube(bd, [(x, BAR_Y, BUMPER['z'][1] - 0.15), (x, BAR_Y, BAR_Z[1])], r * 0.85, 8, 0, caps=True)
    # lower guard legs under the bumper, tied back into the frame rails
    for s in (1, -1):
        pts = [(s * 3.4, -9.5, BUMPER['z'][0] + 0.15), (s * 3.4, -9.2, 2.05), (s * 3.4, -8.65, 1.8),
               (s * 2.42, -7.7, 2.4)]
        L.tube(bd, pts, 0.1, 8, 0, fillet=0.25, caps=True)
    ctx.obj('BullBar', bd, 'Front', ['steel'])


def fascia(ctx):
    bd = L.Builder()
    BLK, LENS, CHR, ORG, NAV = 0, 1, 2, 3, 4
    fwd = V((0, -1, 0))
    for s in (1, -1):
        c = V((s * HEAD_X, FACE_Y, HEAD_Z))
        m = L.frame_matrix(c + fwd * 0.1, fwd)
        L.square_ring(bd, m, 0.52, 0.41, 0.1, 16, BLK)
        # chrome trim ring + domed lens recessed into the bezel
        L.lathe(bd, [(0.41, -9.13), (0.43, -9.17), (0.38, -9.19)], 16, CHR, V((c.x, 0, c.z)), 'Y', False, False)
        L.lathe(bd, [(0.38, -9.19), (0.3, -9.22), (0.17, -9.245), (0.06, -9.25)], 16, LENS, V((c.x, 0, c.z)), 'Y',
                False, True)
        # indicator: black housing + orange lens
        iz = 4.14 if B.RIDGES else 4.05
        L.rbox(bd, (0.6, 0.05, 0.44), 0.02, 1, (0, 0, 0), BLK, Matrix.Translation((s * 3.2, FACE_Y - 0.025, iz)))
        L.rbox(bd, (0.5, 0.06, 0.34), 0.03, 1, (0, 0, 0), ORG, Matrix.Translation((s * 3.2, FACE_Y - 0.075, iz)))
    # grille: black housing, slats, centre badge
    L.rbox(bd, (3.9, 0.1, 1.1), 0.04, 1, (2, 0, 0), BLK, Matrix.Translation((0, FACE_Y - 0.05, HEAD_Z)))
    for k in range(5):
        z = HEAD_Z - 0.42 + k * 0.21
        L.rbox(bd, (3.72, 0.06, 0.1), 0.025, 1, (2, 0, 0), CHR, Matrix.Translation((0, FACE_Y - 0.12, z)))
    L.lathe(bd, [(0.32, FACE_Y - 0.14), (0.32, FACE_Y - 0.18), (0.27, FACE_Y - 0.21), (0.12, FACE_Y - 0.22)], 16, CHR,
            V((0, 0, HEAD_Z)), 'Y', False, True)
    # lower intake slot
    L.rbox(bd, (5.0, 0.05, 0.38), 0.03, 1, (4, 0, 0), BLK, Matrix.Translation((0, FACE_Y - 0.025, 4.0)))
    ctx.obj('Grille_Headlights', bd, 'Front', ['black', 'lens_white', 'chrome', 'lens_orange', 'navy'])


def _front_surface(x, z):
    """Point + outward normal on the front cowl (vertical to z=6.2, then sloped to the windscreen)."""
    if z <= 6.2:
        return V((x, FACE_Y, z)), V((0, -1, 0))
    t = (z - 6.2) / 0.65
    n = V((0, -0.65, 0.4)).normalized()
    return V((x, FACE_Y + 0.4 * t, z)), n


def plates(ctx):
    """Riveted bash plates on the cowl corners, bent over the crease."""
    bd = L.Builder()
    for s in (1, -1):
        zs = [5.92, 6.2, 6.68]
        xs_bottom = [1.6, 2.5, 3.45]
        xs_top = [1.75, 2.5, 3.25]
        P, N = [], []
        for i, z in enumerate(zs):
            row_p, row_n = [], []
            for j in range(3):
                x = xs_bottom[j] if i < 2 else xs_top[j]
                p, n = _front_surface(s * x, z)
                if abs(z - 6.2) < 1e-6:
                    n = (V((0, -1, 0)) + V((0, -0.65, 0.4)).normalized()).normalized()
                row_p.append(p + n * 0.055)
                row_n.append(n)
            P.append(row_p)
            N.append(row_n)
        if s < 0:
            P = [r[::-1] for r in P]
            N = [r[::-1] for r in N]
        L.thick_grid(bd, P, N, 0.04, 0)
        for (x, z) in ((1.75, 5.99), (3.32, 5.99), (1.88, 6.58), (3.12, 6.58), (2.5, 5.99), (2.5, 6.6)):
            p, n = _front_surface(s * x, z)
            L.rbox(bd, (0.08, 0.08, 0.05), 0.02, 1, (0, 0, 0), 0, L.frame_matrix(p + n * 0.065, n))
    ctx.obj('HoodPlates', bd, 'Front', ['metal'])


def skid(ctx):
    bd = L.Builder()
    prof = [((-9.52, 2.72), 2.0), ((-9.05, 1.55), 1.65), ((-7.75, 1.55), 1.65), ((-7.35, 2.22), 1.85)]
    P, N = [], []
    for k, ((y, z), hw) in enumerate(prof):
        if k == 0:
            d = V((0, prof[1][0][0] - y, prof[1][0][1] - z))
        elif k == len(prof) - 1:
            d = V((0, y - prof[k - 1][0][0], z - prof[k - 1][0][1]))
        else:
            d = V((0, prof[k + 1][0][0] - prof[k - 1][0][0], prof[k + 1][0][1] - prof[k - 1][0][1]))
        d.normalize()
        n = V((0, d.z, -d.y))  # outward = down/front
        P.append([V((x * hw, y, z)) for x in (-1, -0.5, 0, 0.5, 1)])
        N.append([n] * 5)
    L.thick_grid(bd, P, N, 0.06, 0)
    # slots on the sloped nose
    a = V((0, -9.52, 2.72))
    b = V((0, -9.05, 1.55))
    d = (b - a).normalized()
    n = V((0, d.z, -d.y))
    for x in (-1.05, -0.35, 0.35, 1.05):
        c = a.lerp(b, 0.5) + V((x, 0, 0)) + n * 0.005
        m = L.frame_matrix(c, n, d)
        L.rbox(bd, (0.3, 0.85, 0.02), 0.03, 1, (0, 0, 0), 1, m)
    ctx.obj('SkidPlate', bd, 'Front', ['metal', 'black'])


def shackle(bd, x, y_face, z, fwd, mat_bow, mat_tab):
    """Tab on a bumper face + red D-shackle hanging from it. fwd = +1 (rear) / -1 (front)."""
    L.rbox(bd, (0.12, 0.3, 0.34), 0.02, 1, (0, 0, 0), mat_tab, Matrix.Translation((x, y_face + fwd * 0.13, z)))
    py = y_face + fwd * 0.2
    L.lathe(bd, [(0.07, x - 0.22), (0.07, x + 0.22)], 8, mat_bow, V((0, py, z)), 'X', True, True)
    pts = [(x + 0.17, py, z), (x + 0.17, py + fwd * 0.06, z - 0.22), (x, py + fwd * 0.12, z - 0.46),
           (x - 0.17, py + fwd * 0.06, z - 0.22), (x - 0.17, py, z)]
    L.tube(bd, pts, 0.055, 8, mat_bow, fillet=0.15, caps=True)


def shackles(ctx):
    bd = L.Builder()
    for s in (1, -1):
        shackle(bd, s * 2.3, BUMPER['y'] - 0.27, 2.98, -1, 0, 1)
    ctx.obj('TowShackles_Front', bd, 'Front', ['red', 'steel'])


def mirrors(ctx):
    bd = L.Builder()
    if B.SHAPE:
        # real-world proportions: ~17 x 25 cm head (0.6 x 0.9 units at ~0.28 m/unit), held ~10 cm off the door
        for s in (1, -1):
            dx = B.side_x_at(6.55)
            L.rbox(bd, (0.06, 0.3, 0.26), 0.02, 1, (0, 0, 0), 0, Matrix.Translation((s * (dx + 0.02), -7.55, 6.55)))
            L.tube(bd, [(s * (dx + 0.02), -7.55, 6.55), (s * 4.12, -7.5, 6.6), (s * 4.3, -7.38, 6.82)], 0.055, 8, 0,
                   fillet=0.12, caps=True)
            L.rbox(bd, (0.6, 0.2, 0.9), 0.07, 1, (1, 0, 2), 0, Matrix.Translation((s * 4.42, -7.38, 7.18)))
            L.rbox(bd, (0.5, 0.03, 0.8), 0.025, 1, (0, 0, 0), 1, Matrix.Translation((s * 4.42, -7.27, 7.18)))
        ctx.obj('Mirrors', bd, 'Body', ['steel', 'chrome'])
        return
    for s in (1, -1):
        L.rbox(bd, (0.06, 0.32, 0.26), 0.02, 1, (0, 0, 0), 0, Matrix.Translation((s * 3.93, -7.55, 6.95)))
        L.tube(bd, [(s * 3.93, -7.55, 6.95), (s * 4.38, -7.55, 7.02), (s * 4.62, -7.5, 7.3)], 0.05, 8, 0,
               fillet=0.15, caps=True)
        L.rbox(bd, (0.46, 0.18, 0.76), 0.06, 1, (0, 0, 1), 0, Matrix.Translation((s * 4.8, -7.47, 7.58)))
        L.rbox(bd, (0.38, 0.03, 0.66), 0.02, 1, (0, 0, 0), 1, Matrix.Translation((s * 4.8, -7.37, 7.58)))
    ctx.obj('Mirrors', bd, 'Body', ['steel', 'chrome'])


def handles_and_rockers(ctx):
    bd = L.Builder()
    for s in (1, -1):
        hx, hz = ((3.895 if B.GROOVE else 3.965), 5.75) if B.RIDGES else (3.93, 5.9)   # handle sits in/on the swage line
        L.rbox(bd, (0.06, 0.62, 0.1), 0.025, 1, (0, 0, 0), 1, Matrix.Translation((s * hx, -4.05, hz)))
        # navy rocker panel between the arches (covers the sill edge, sits under the cage sliders)
        L.rbox(bd, (0.33, 4.6, 0.36), 0.06, 1, (0, 6, 0), 0, Matrix.Translation((s * 3.765, -0.62, 2.62)))
    ctx.obj('Rocker_Sills', bd, 'Body', ['navy', 'chrome'])
