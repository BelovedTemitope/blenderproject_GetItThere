"""Background taxi (concept C): boxy 80s saloon, yellow with a black side stripe and a roof sign.

Front is -Y, +X is the vehicle's left. One connected quad body: a lattice for the lower body and the
cabin extruded from the deck faces; windows are insets in the cabin walls.
"""
import math

import bmesh
from mathutils import Matrix, Vector as V

import ev_lib as E

L2, W2 = 6.3, 3.45
Z0, ZARCH, ZTOP, ZROOF = 1.2, 2.75, 3.7, 6.1
ARCH_SHOULDER = 2.05
WHEEL_Y, WHEEL_R, WHEEL_W, WHEEL_X = (-3.95, 3.75), 1.25, 1.05, 2.9
ARCH = {-3.95: (-5.35, -4.55, -3.35, -2.55), 3.75: (2.35, 3.15, 4.35, 5.15)}
CAB = (-2.05, 0.15, 2.35)                        # windscreen base, B pillar, rear-window base
XC = 2.85                                     # cabin base half width (and the shoulder / well cut)
XS = [-W2, -XC, XC, W2]
YS = sorted({-L2, -5.95, 5.95, L2} | set(CAB) | {y for a in ARCH.values() for y in a})
ZS = [Z0, ZARCH, ZTOP]
ROOF_Y = {CAB[0]: -0.65, CAB[1]: 0.3, CAB[2]: 2.05}
ROOF_X = 2.45

COL = dict(paint='#F2B705', black='#1E1E22', glass='#8D8B85', bumper='#8E9194', grille='#3A3C40',
           light='#E3E1D4', orange='#E07A1F', red='#B0342A', plate='#EDEDE6', tyre='#2A2A2D', hub='#C4C6C9',
           sign='#F4F4EE')
PAINT, BLK, GLS, BMP, GRL, LGT, ORG, RED, PLT = range(9)


def top_z(y):
    if y <= -5.95:
        return 3.2 if y == -L2 else 3.38
    if y < CAB[0]:
        return 3.38 + (y + 5.95) / (CAB[0] + 5.95) * (ZTOP - 3.38)
    if y >= 5.95:
        return 3.45 if y == L2 else 3.72
    return ZTOP if y <= CAB[2] else 3.76


def in_arch(y):
    return any(a[0] < y < a[3] for a in ARCH.values())


def deform(co, key):
    i, j, k = key
    x, y, z = XS[i], YS[j], ZS[k]
    if k == 2:
        z = top_z(y)
        if abs(x) == W2:
            x *= 0.975
    for ya, y1, y2, yb in ARCH.values():
        if abs(x) == W2 and k == 1 and y in (ya, yb):
            z = ARCH_SHOULDER
            y += 0.2 if y == ya else -0.2
    return V((x, y, z))


def face_mat(axis, side, c):
    if axis == 0 and c.z < ZARCH and in_arch(c.y):
        return None
    if axis == 2 and side < 0 and abs(c.x) > XC and in_arch(c.y):
        return None
    return PAINT


def build(col, origin):
    M = materials()
    bd = E.Builder()
    vmap, faces, ax = E.grid_box(bd, XS, YS, ZS, deform=deform, face_mat=face_mat)
    bm = bd.bm
    # cabin: extrude the two deck faces between windscreen base and rear-window base
    deck = [f for f in faces if f.is_valid and f.normal_update() is None and f.calc_center_median().z > ZTOP - 0.05
            and abs(f.calc_center_median().x) < XC and CAB[0] < f.calc_center_median().y < CAB[2]]
    res = bmesh.ops.extrude_face_region(bm, geom=deck)
    new_v = [g for g in res['geom'] if isinstance(g, bmesh.types.BMVert)]
    for v in new_v:
        yk = min(ROOF_Y, key=lambda y: abs(y - v.co.y))
        v.co = V((math.copysign(ROOF_X, v.co.x), ROOF_Y[yk], ZROOF))
    walls = [g for g in res['geom'] if isinstance(g, bmesh.types.BMFace) and g not in deck]
    walls = [f for f in bm.faces if f not in deck and all(v in new_v or v.co.z <= ZTOP + 1e-4 for v in f.verts)
             and any(v in new_v for v in f.verts) and any(v not in new_v for v in f.verts)]
    for f in walls:
        f.material_index = GLS
    done = set()                          # one frame per pane: pillars show between door windows
    while True:
        todo = [f for f in bm.faces if f.material_index == GLS and f.index not in done and f not in ()]
        todo = [f for f in todo if tuple(round(c, 1) for c in f.calc_center_median()) not in done]
        if not todo:
            break
        w = todo[0]
        ins = bmesh.ops.inset_region(bm, faces=[w], thickness=0.28, depth=-0.05, use_even_offset=True)
        for f in ins['faces']:
            f.material_index = PAINT
        done.add(tuple(round(c, 1) for c in w.calc_center_median()))
    # wheel wells welded to the floor
    for wy, (ya, y1, y2, yb) in ARCH.items():
        for s in (1, -1):
            i_out, i_in = (3, 2) if s > 0 else (0, 1)
            loop = [vmap[(i_out, YS.index(y), k)] for y, k in ((ya, 0), (ya, 1), (y1, 1), (y2, 1), (yb, 1), (yb, 0))]
            E.well(bd, loop, (-s * (W2 - XC), 0, 0), BLK, [vmap[(i_in, YS.index(y), 0)] for y in (y1, y2)])
    # bumpers, plates, grille + slats, lamps, stripe, handles, mirrors, tail lamps
    for y, sgn in ((-L2 - 0.15, -1), (L2 + 0.15, 1)):
        E.box(bd, (0, y, 1.55), (7.2, 0.5, 0.62), BMP)
        py = y + sgn * 0.26
        pts = [(-0.85, py, 1.33), (0.85, py, 1.33), (0.85, py, 1.75), (-0.85, py, 1.75)]
        E.quad(bd, pts if sgn < 0 else pts[::-1], PLT)
    fy = -L2 - 0.01
    E.quad(bd, [(-1.55, fy, 2.15), (1.55, fy, 2.15), (1.55, fy, 2.95), (-1.55, fy, 2.95)], GRL)
    for z in (2.3, 2.5, 2.7):
        E.quad(bd, [(-1.45, fy - 0.01, z), (1.45, fy - 0.01, z), (1.45, fy - 0.01, z + 0.08), (-1.45, fy - 0.01, z + 0.08)], BMP)
    for s in (1, -1):
        for (a, b), m in (((1.7, 2.62), LGT), ((2.7, 3.32), ORG)):
            x0, x1 = sorted((s * a, s * b))
            E.quad(bd, [(x0, fy, 2.2), (x1, fy, 2.2), (x1, fy, 2.9), (x0, fy, 2.9)], m)
        x0, x1 = sorted((s * 2.0, s * 3.2))
        ry = L2 + 0.01
        E.quad(bd, [(x1, ry, 2.65), (x0, ry, 2.65), (x0, ry, 3.3), (x1, ry, 3.3)], RED)
        x = s * (W2 + 0.012)
        pts = [(x, -6.05, 2.85), (x, 6.05, 2.85), (x, 6.05, 3.35), (x, -6.05, 3.35)]
        E.quad(bd, pts if s > 0 else pts[::-1], BLK)
        for hy in (-0.95, 1.05):
            hx = s * (W2 * 0.985 + 0.012)
            pts = [(hx, hy, 3.45), (hx, hy + 0.4, 3.45), (hx, hy + 0.4, 3.56), (hx, hy, 3.56)]
            E.quad(bd, pts if s > 0 else pts[::-1], BLK)
        E.box(bd, (s * 3.25, -1.8, 3.98), (0.55, 0.22, 0.34), BLK)
    names = ['M_Env_Taxi_Paint', 'M_Env_Black', 'M_Env_Glass', 'M_Env_Bumper', 'M_Env_Grille', 'M_Env_Lamp',
             'M_Env_Indicator', 'M_Env_TailLamp', 'M_Env_Plate']
    body = E.finish('GIT_Env_TaxiC_Body', bd, col, [M[n] for n in names])
    body.location = origin
    parts = [body]
    for wy in WHEEL_Y:
        for s in (1, -1):
            wb = E.Builder()
            E.wheel(wb, (0, 0, 0), WHEEL_R, WHEEL_W, 12, s, 0, 1)
            w = E.finish('GIT_Env_TaxiC_Wheel_%s%s' % ('F' if wy < 0 else 'R', 'L' if s > 0 else 'R'), wb, col,
                         [M['M_Env_Tyre'], M['M_Env_Hub']])
            w.location = V(origin) + V((s * WHEEL_X, wy, WHEEL_R))
            parts.append(w)
    parts.append(sign(col, origin, M))
    return parts


def sign(col, origin, M):
    """Layered detail: roof taxi sign (dark foot, white tapered box)."""
    bd = E.Builder()
    E.box(bd, (0, -0.1, ZROOF + 0.06), (1.5, 0.7, 0.12), 0)

    def taper(co, key):
        return V((co.x * (0.82 if key[2] else 1.0), co.y * (0.75 if key[2] else 1.0), co.z))
    E.grid_box(bd, [-0.68, 0.68], [-0.43, 0.23], [ZROOF + 0.12, ZROOF + 0.55], mat=1,
               deform=lambda co, k: taper(co - V((0, -0.1, 0)), k) + V((0, -0.1, 0)))
    ob = E.finish('GIT_Env_TaxiC_RoofSign', bd, col, [M['M_Env_Black'], M['M_Env_Sign']], smooth_angle=30)
    ob.location = origin
    return ob


def materials():
    m = {}
    for n, c, r in (('M_Env_Taxi_Paint', COL['paint'], 0.5), ('M_Env_Black', COL['black'], 0.6),
                    ('M_Env_Glass', COL['glass'], 0.2), ('M_Env_Bumper', COL['bumper'], 0.45),
                    ('M_Env_Grille', COL['grille'], 0.6), ('M_Env_Lamp', COL['light'], 0.3),
                    ('M_Env_Indicator', COL['orange'], 0.4), ('M_Env_TailLamp', COL['red'], 0.4),
                    ('M_Env_Plate', COL['plate'], 0.5), ('M_Env_Tyre', COL['tyre'], 0.85),
                    ('M_Env_Hub', COL['hub'], 0.4), ('M_Env_Sign', COL['sign'], 0.4)):
        m[n] = E.material(n, c, r)
    return m
