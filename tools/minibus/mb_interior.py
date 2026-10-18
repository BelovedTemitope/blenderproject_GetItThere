"""Interior: stepped floor pan, dashboard, steering, pedals/shifter, front seats, benches."""
import math

import bpy
from mathutils import Matrix, Vector as V

import mb_body as B
import mb_lib as L

FLOOR = [(-8.98, 3.0), (-7.7, 3.0), (-7.7, 4.45), (-2.95, 4.45), (-2.95, 3.0), (1.9, 3.0), (1.9, 4.45), (7.13, 4.45)]
INNER_X = 3.76
CAB_Z = 4.45
DRIVER_X = 1.95


def build(ctx):
    for n in ('Interior_Bench_Row3', 'Interior_CabConsole'):
        o = bpy.data.objects.get('GIT_Veh_Minibus_' + n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    floor(ctx)
    dashboard(ctx)
    steering(ctx)
    controls(ctx)
    for name, x in (('Interior_Seat_Driver', DRIVER_X), ('Interior_Seat_FrontPassenger', -DRIVER_X)):
        bd = L.Builder()
        front_seat(bd, x, -6.45, 1.62, CAB_Z)
        ctx.obj(name, bd, 'Interior', ['seat', 'metal', 'seat_dark'])
    bd = L.Builder()
    if B.DOORS:   # doors both sides: centre the middle bench so each doorway keeps an aisle
        bench(bd, -1.75, 1.75, 2, -0.62, 1.62, 3.0, 4.0, 2.15, 13)
    else:
        bench(bd, -3.62, -0.2, 2, -0.62, 1.62, 3.0, 4.0, 2.15, 13)
    ctx.obj('Interior_Bench_Row1', bd, 'Interior', ['seat', 'metal', 'seat_dark'])
    bd = L.Builder()
    bench(bd, -3.6, 3.6, 3, 4.55, 1.6, CAB_Z, 4.85, 2.1, 15)
    ctx.obj('Interior_Bench_Row2', bd, 'Interior', ['seat', 'metal', 'seat_dark'])


# ---------------------------------------------------------------------------
def clip_to_shell(bd, front=-8.97, rear=7.1, half=3.77):
    """Keep interior parts inside the shell, following the 45deg corner chamfers."""
    for v in bd.bm.verts:
        ax = abs(v.co.x)
        lim = min(half, B.side_x_at(v.co.z) - 0.13)   # follow the tumblehome
        if ax > lim:
            v.co.x = lim if v.co.x > 0 else -lim
            ax = lim
        lift = max(0.0, (v.co.z - 6.2) / 0.65) * 0.4 if v.co.z > 6.2 else 0.0
        ymin = front + lift + max(0.0, ax - 3.47)
        ymax = rear - max(0.0, ax - 3.47)
        if v.co.y < ymin:
            v.co.y = ymin
        if v.co.y > ymax:
            v.co.y = ymax


def floor(ctx):
    bd = L.Builder()
    xs = [-INNER_X + 2 * INNER_X * k / 8 for k in range(9)]
    P, N = [], []
    n = len(FLOOR)
    for i, (y, z) in enumerate(FLOOR):
        nrm = V()
        for j in (i - 1, i + 1):
            if 0 <= j < n:
                y2, z2 = FLOOR[j]
                d = V((0, y2 - y, z2 - z)).normalized() * (1 if j > i else -1)
                nrm += V((0, -d.z, d.y))
        nrm.normalize()
        P.append([V((x, y, z)) for x in xs])
        N.append([nrm] * len(xs))
    L.thick_grid(bd, P, N, 0.1, 0)
    clip_to_shell(bd)
    ctx.obj('Interior_Floor', bd, 'Interior', ['seat_dark'])


def dashboard(ctx):
    bd = L.Builder()
    prof_yz = [(-8.55, 6.75), (-7.95, 6.92), (-7.62, 6.72), (-7.62, 6.05), (-7.85, 5.55), (-8.4, 5.45), (-8.95, 5.5),
               (-8.95, 6.1)]
    yc, zc = -8.3, 6.2
    prof = [(z - zc, y - yc) for (y, z) in prof_yz]
    xs = [3.76, 2.65, 1.25, 0.6, -0.6, -1.25, -2.65, -3.76]
    path = [V((x, yc, zc)) for x in xs]
    L.sweep(bd, path, prof, 0, True, False, True, True)
    clip_to_shell(bd, front=-8.95)
    # instrument binnacle + gauges facing the driver
    L.rbox(bd, (1.3, 0.55, 0.36), (0.1, 0.1, 0.1), 2, (0, 0, 0), 0, Matrix.Translation((DRIVER_X, -7.98, 6.98)))
    for dx in (-0.3, 0.3):
        c = V((DRIVER_X + dx, -7.7, 7.0))
        L.lathe(bd, [(0.15, -7.71), (0.15, -7.69), (0.12, -7.69), (0.12, -7.72)], 12, 2, V((c.x, 0, c.z)), 'Y', False,
                True)
    # glovebox lid + centre radio panel
    L.rbox(bd, (1.2, 0.03, 0.5), 0.02, 1, (0, 0, 0), 1, Matrix.Translation((-DRIVER_X, -7.61, 6.38)))
    L.rbox(bd, (0.9, 0.03, 0.35), 0.02, 1, (0, 0, 0), 1, Matrix.Translation((0.0, -7.61, 6.4)))
    ctx.obj('Interior_Dashboard', bd, 'Interior', ['dash', 'black', 'chrome'])


def steering(ctx):
    bd = L.Builder()
    n = V((0, 0.64, 0.77)).normalized()          # wheel plane normal (toward the driver)
    hub = V((DRIVER_X, -7.0, 6.95))
    col_base = hub - n * 0.95
    L.tube(bd, [col_base, hub - n * 0.1], 0.07, 8, 1, caps=True)
    L.lathe(bd, [(0.14, -0.04), (0.17, 0.0), (0.17, 0.1), (0.12, 0.14)], 8, 1, V(), 'Z', True, True)
    m = L.frame_matrix(hub, n, V((0, 0, 1)))
    # move the hub lathe (built at the origin) into place
    hub_verts = bd.bm.verts[-32:]
    bd.transform(m, hub_verts)
    ring = [m @ V((0.62 * math.cos(a), 0.62 * math.sin(a), 0.06)) for a in
            (2 * math.pi * k / 18 for k in range(18))]
    L.sweep(bd, ring, L.circle_profile(0.055, 6), 0, True, True, False, False, up=n)
    for a in (math.radians(-90), math.radians(30), math.radians(150)):
        p0 = m @ V((0.12 * math.cos(a), 0.12 * math.sin(a), 0.08))
        p1 = m @ V((0.62 * math.cos(a), 0.62 * math.sin(a), 0.06))
        L.tube(bd, [p0, p1], 0.045, 6, 0, caps=True)
    ctx.obj('Interior_SteeringWheel', bd, 'Interior', ['black', 'metal'])


def controls(ctx):
    bd = L.Builder()
    for k, x in enumerate((DRIVER_X - 0.45, DRIVER_X, DRIVER_X + 0.4)):
        top = V((x, -8.7, 5.45))
        pad = V((x, -8.45, 3.75))
        L.tube(bd, [top, pad], 0.035, 6, 0, caps=True)
        w = 0.3 if k else 0.24
        L.rbox(bd, (w, 0.05, 0.28), 0.02, 1, (0, 0, 0), 1,
               Matrix.Translation(pad) @ Matrix.Rotation(math.radians(-25), 4, 'X'))
    # gear lever + boot on the cab floor, handbrake beside it
    base = V((0.95, -7.25, CAB_Z))
    L.lathe(bd, [(0.22, 0.0), (0.2, 0.08), (0.1, 0.25), (0.05, 0.32)], 8, 1, base, 'Z', False, True)
    L.tube(bd, [base + V((0, 0, 0.2)), base + V((0, 0.12, 1.25))], 0.03, 6, 0, caps=True)
    L.rbox(bd, (0.16, 0.16, 0.16), 0.06, 2, (0, 0, 0), 1, Matrix.Translation(base + V((0, 0.12, 1.3))))
    ctx.obj('Interior_Pedals_Shifter', bd, 'Interior', ['metal', 'black'])


# ---------------------------------------------------------------------------
def _bolster_cushion(w, depth, amount):
    def f(co):
        t = min(1.0, max(0.0, (abs(co.x) - 0.28 * w) / (0.22 * w)))
        if co.z > 0:
            co = co + V((0, 0, amount * t))
        return co
    return f


def _bolster_back(w, amount):
    def f(co):
        t = min(1.0, max(0.0, (abs(co.x) - 0.28 * w) / (0.22 * w)))
        if co.y < 0:
            co = co + V((0, -amount * t, 0))
        return co
    return f


def front_seat(bd, x, y_front, depth, floor_z):
    SEAT, METAL, DARK = 0, 1, 2
    w = 1.6
    cz = floor_z + 0.75                               # cushion bottom
    # pedestal (seat box) from the floor up into the cushion underside
    ph = cz - floor_z + 0.06
    L.rbox(bd, (1.2, depth - 0.35, ph), 0.05, 1, (0, 0, 0), METAL,
           Matrix.Translation((x, y_front + depth / 2 + 0.05, floor_z + ph / 2)))
    # cushion, tipped back a little, with side bolsters
    mc = Matrix.Translation((x, y_front + depth / 2, cz + 0.25)) @ Matrix.Rotation(math.radians(-6), 4, 'X')
    L.rbox(bd, (w, depth, 0.5), 0.14, 2, (2, 2, 0), SEAT, mc, _bolster_cushion(w, depth, 0.1))
    # backrest pivots at the cushion's rear edge
    yb = y_front + depth - 0.07
    mb = Matrix.Translation((x, yb, cz + 0.05)) @ Matrix.Rotation(math.radians(-12), 4, 'X')
    bh = 2.15
    L.rbox(bd, (w, 0.42, bh), 0.14, 2, (2, 0, 3), SEAT, mb @ Matrix.Translation((0, 0.21, bh / 2)),
           _bolster_back(w, 0.12))
    # recliner covers on the hinge
    for s in (1, -1):
        c = mb @ V((s * (w / 2 + 0.03), 0.22, 0.28))
        L.lathe(bd, [(0.16, c.x - 0.04), (0.16, c.x + 0.04)], 10, DARK, V((0, c.y, c.z)), 'X', True, True)
    # open-frame headrest on two posts
    hz = bh + 0.2 + 0.32
    ring = L.fillet_path([V((-0.48, 0.2, hz - 0.32)), V((0.48, 0.2, hz - 0.32)), V((0.48, 0.2, hz + 0.32)),
                          V((-0.48, 0.2, hz + 0.32))], 0.17, closed=True)
    ring = [mb @ p for p in ring]
    up = (mb.to_3x3() @ V((0, 1, 0))).normalized()
    L.sweep(bd, ring, [(0.11, -0.09), (0.11, 0.09), (-0.11, 0.09), (-0.11, -0.09)], SEAT, True, True, False, False,
            up=up)
    for s in (1, -1):
        L.tube(bd, [mb @ V((s * 0.28, 0.2, bh - 0.25)), mb @ V((s * 0.28, 0.2, hz - 0.3))], 0.035, 6, METAL,
               caps=True)


def bench(bd, x0, x1, nseat, y_front, depth, floor_z, cz, bh, recline):
    SEAT, METAL, DARK = 0, 1, 2
    w = x1 - x0
    xc = (x0 + x1) / 2
    # plinth (seat pan) on sled-style tube legs
    L.rbox(bd, (w - 0.1, depth - 0.15, 0.12), 0.03, 1, (nseat, 0, 0), METAL,
           Matrix.Translation((xc, y_front + depth / 2, cz - 0.04)))
    legs = [x0 + 0.3, x1 - 0.3] + ([xc] if nseat > 2 else [])
    for lx in legs:
        pts = [(lx, y_front + 0.3, cz - 0.04), (lx, y_front + 0.3, floor_z + 0.06), (lx, y_front + depth - 0.35,
               floor_z + 0.06), (lx, y_front + depth - 0.35, cz - 0.04)]
        L.tube(bd, pts, 0.06, 8, METAL, fillet=0.12, caps=True)
    sw = w / nseat
    for k in range(nseat):
        sx = x0 + sw * (k + 0.5)
        mc = Matrix.Translation((sx, y_front + depth / 2, cz + 0.27)) @ Matrix.Rotation(math.radians(-4), 4, 'X')
        L.rbox(bd, (sw - 0.03, depth, 0.5), 0.13, 2, (1, 2, 0), SEAT, mc)
        mb = Matrix.Translation((sx, y_front + depth - 0.07, cz + 0.06)) @ Matrix.Rotation(math.radians(-recline), 4,
                                                                                            'X')
        L.rbox(bd, (sw - 0.03, 0.4, bh), 0.13, 2, (1, 0, 3), SEAT, mb @ Matrix.Translation((0, 0.2, bh / 2)))
    # backrest support brackets from the plinth up the back of the seat
    mb = Matrix.Translation((xc, y_front + depth - 0.07, cz + 0.06)) @ Matrix.Rotation(math.radians(-recline), 4, 'X')
    for lx in (x0 + 0.3 - xc, x1 - 0.3 - xc):
        L.rbox(bd, (0.1, 0.08, 1.1), 0.02, 1, (0, 0, 0), METAL, mb @ Matrix.Translation((lx, 0.43, 0.45)))
