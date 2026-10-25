"""Background keke / tricycle taxi (concept D, Bajaj RE type).

Front is -Y, +X is the vehicle's left, Z up. Built from interlocking quad parts, the way the real
vehicle is put together:
  cowl      shield-shaped nose: wide flat front tapering to a narrow chin, chamfered corner facets
  frame     yellow windscreen surround (thick top bar, off-centre post) sitting on the cowl
  floor     low footwell pan behind the cowl
  rear tub  raised passenger-side panels, rear deck and bulging fenders over the rear wheels
  canopy    rounded black shell over everything, closed rear quarters, rear window opening
plus mudguard + headlamp, fork, seats, grab poles, rail, seam / vent / indicator / tail-lamp decals.
The canopy is single-sided (set DoubleSided on import).
"""
import math

from mathutils import Matrix, Vector as V

import ev_lib as E

YF = -4.65                       # nose front
Y_COWL_BACK = -2.75
Z_CHIN, Z_FLOOR, Z_BELT, Z_COWL = 2.0, 1.15, 4.45, 4.75
ROOF_Z, ROOF_EDGE_Z, CANOPY_LOW = 7.4, 6.75, 4.05
Y_REAR = 4.42
WHEEL_R, WHEEL_W = 0.95, 0.62
FRONT_WHEEL = (0.0, -4.4)
REAR_WHEEL = (2.2, 3.0)

COL = dict(paint='#F2B705', canopy='#3B3630', glass='#9DA3A6', seat='#6B4A33', chrome='#B7BBBF', black='#1E1E22',
           orange='#E07A1F', light='#E3E1D4', tyre='#2A2A2D', hub='#C4C6C9', red='#B0342A')
PAINT, CAN, GLS, SEAT, CHR, BLK, ORG, LGT, RED = range(9)


# ---------------------------------------------------------------------------
# cowl
# ---------------------------------------------------------------------------
C_US = [-1.0, -0.78, 0.78, 1.0]
C_YS = [YF, -4.3, -3.0, Y_COWL_BACK]
C_WS = [0.0, 0.55, 0.88, 1.0]


def cowl_point(i, j, k):
    y, u, w = C_YS[j], C_US[i], C_WS[k]
    # the whole cowl narrows towards the bottom (V cross-section), most at the nose
    if j == 0:
        zb, hw = Z_CHIN, 0.75 + (2.05 - 0.75) * w ** 0.85
    elif j == 1:
        zb, hw = 1.75, 1.05 + (2.3 - 1.05) * w ** 0.7
    else:
        zb, hw = Z_FLOOR, 1.5 + (2.35 - 1.5) * w ** 0.55
    z = zb + (Z_COWL - zb) * w
    if k == 2:
        z = Z_BELT
    x = u * hw
    if j == 0:
        if abs(u) == 1.0:
            y += 0.32                  # chamfered corner facets fold back into the sides
        if k == 3:
            y += 0.18                  # softened top front edge
    return V((x, y, z))


def cowl(bd):
    vm, _, _ = E.grid_box(bd, C_US, C_YS, C_WS, deform=lambda co, k: cowl_point(*k), mat=PAINT)
    return vm


# ---------------------------------------------------------------------------
# rear tub: passenger-side panels, rear deck, fenders
# ---------------------------------------------------------------------------
R_YS = [-0.7, 0.55, 1.05, 1.6, 2.15, 2.6, 3.4, 3.85, Y_REAR]
R_US = [-1.0, -0.66, 0.66, 1.0]
R_WS = [0.0, 0.45, 0.75, 1.0]
ARCH = (2.15, 2.6, 3.4, 3.85)


def rear_top(y):
    if y <= 0.55:
        return 3.2                         # passenger seat base
    if y < 1.6:
        return 3.2 + (y - 0.55) / 1.05 * (CANOPY_LOW - 3.2)
    return CANOPY_LOW if y < Y_REAR else CANOPY_LOW - 0.12


def rear_point(i, j, k):
    y, u, w = R_YS[j], R_US[i], R_WS[k]
    top = rear_top(y)
    z = Z_FLOOR + (top - Z_FLOOR) * w
    if k == 1:
        z = 2.15                           # fender shoulder line
    if k == 2:
        z = min(top - 0.25, 2.95)
    fender = 2.15 <= y <= 3.85
    if fender and k <= 1:
        hw = 2.72                          # bulging fender over the rear wheel
    elif fender and k == 2:
        hw = 2.6
    else:
        hw = 2.42
    if y == Y_REAR:
        hw -= 0.18
    if y == R_YS[0]:
        hw -= 0.06
    if abs(u) == 1.0 and k == 1 and y in (ARCH[0], ARCH[3]):
        z = 1.85
        y += 0.12 if y == ARCH[0] else -0.12
    if abs(u) == 1.0 and k == 3:
        hw -= 0.15                         # rounded top edge
    return V((u * hw, y, z))


def rear_tub(bd):
    def fm(axis, side, c):
        in_arch = ARCH[0] < c.y < ARCH[3]
        if axis == 0 and c.z < 0.45 and in_arch:
            return None
        if axis == 2 and side < 0 and abs(c.x) > 0.66 and in_arch:
            return None
        return PAINT
    vm, _, _ = E.grid_box(bd, R_US, R_YS, R_WS, deform=lambda co, k: rear_point(*k), face_mat=fm)
    for s in (1, -1):
        i_out, i_in = (3, 2) if s > 0 else (0, 1)
        ya, y1, y2, yb = ARCH
        loop = [vm[(i_out, R_YS.index(y), k)] for y, k in ((ya, 0), (ya, 1), (y1, 1), (y2, 1), (yb, 1), (yb, 0))]
        mids = [vm[(i_in, R_YS.index(y), 0)] for y in (y1, y2)]
        E.well(bd, loop, (-s * (abs(loop[0].co.x) - abs(mids[0].co.x)), 0, 0), BLK, mids)
    return vm


# ---------------------------------------------------------------------------
# windscreen frame
# ---------------------------------------------------------------------------
def frame(bd):
    xs = [-2.22, -1.9, -0.72, -0.56, 1.9, 2.22]
    zs = [Z_COWL, Z_COWL + 0.28, 6.45, 6.95]
    ys = [-4.38, -3.75]                                      # deep hood: side bands wrap back along the cowl

    def deform(co, key):
        i, j, k = key
        x, y, z = xs[i], ys[j], zs[k]
        t = (z - Z_COWL) / (zs[-1] - Z_COWL)
        y += 0.42 * t                                        # raked back
        if i in (0, 5) and k == 3:
            x *= 0.93                                        # rounded top corners
        return V((x, y, z))

    def fm(axis, side, c):
        pane = zs[1] < c.z < zs[2] and (xs[1] < c.x < xs[2] or xs[3] < c.x < xs[4])
        if axis == 1 and side < 0 and pane:
            return GLS
        if axis == 1 and side > 0 and (pane or zs[1] < c.z < zs[2] and xs[1] < c.x < xs[4]):
            return None                                      # open behind the glass (seen from the cabin)
        if axis == 2 and side < 0 and xs[0] < c.x < xs[-1] and xs[1] < c.x < xs[4]:
            return None                                      # sits on the cowl top
        return PAINT
    _, faces, _ = E.grid_box(bd, xs, ys, zs, deform=deform, face_mat=fm)
    glass = [f for f in faces if f.material_index == GLS]
    E.bmesh.ops.inset_individual(bd.bm, faces=glass, thickness=0.02, depth=-0.04)


# ---------------------------------------------------------------------------
def build(col, origin):
    M = materials()
    bd = E.Builder()
    cvm = cowl(bd)
    rear_tub(bd)
    frame(bd)
    # footwell floor between cowl and passenger panels
    E.box(bd, (0, (Y_COWL_BACK - 0.05 + R_YS[0] + 0.05) / 2, (Z_FLOOR + 1.62) / 2),
          (4.7, R_YS[0] - Y_COWL_BACK + 0.1, 1.62 - Z_FLOOR), PAINT)
    # belt seam (dark band round the cowl), indicators, vent
    seam = []
    for i in range(len(C_US) - 1):
        a0, a1 = cowl_point(i, 0, 2), cowl_point(i + 1, 0, 2)
        seam.append((a0, a1))
    for s in (1, -1):
        i = 3 if s > 0 else 0
        seam.append((cowl_point(i, 0, 2), cowl_point(i, 3, 2)) if s > 0 else (cowl_point(i, 3, 2), cowl_point(i, 0, 2)))
    for a, b in seam:
        n = (b - a).cross(V((0, 0, 1)))
        n = n.normalized() * 0.015 if n.length > 1e-6 else V()
        out = n if (((a + b) / 2 - V((0, -3.6, 0))).dot(n) > 0) else -n
        E.quad(bd, [a + out + V((0, 0, -0.06)), b + out + V((0, 0, -0.06)), b + out + V((0, 0, 0.1)),
                    a + out + V((0, 0, 0.1))], BLK)
    for s in (1, -1):                                      # orange indicators on the cowl side faces
        i = 3 if s > 0 else 0
        p00, p10 = cowl_point(i, 1, 1), cowl_point(i, 2, 1)
        p01, p11 = cowl_point(i, 1, 2), cowl_point(i, 2, 2)
        q = lambda u, v: (p00.lerp(p10, u)).lerp(p01.lerp(p11, u), v) + V((s * 0.015, 0, 0))
        pts = [q(0.08, 0.45), q(0.55, 0.45), q(0.55, 0.78), q(0.08, 0.78)]
        E.quad(bd, pts if s > 0 else pts[::-1], ORG)
    fy = YF - 0.015
    vb, vt = cowl_point(1, 0, 0), cowl_point(1, 0, 2)
    E.quad(bd, [(-0.62, fy, 2.3), (-0.28, fy, 2.3), (-0.22, fy, 4.25), (-0.78, fy, 4.25)], BLK)
    # front mudguard (rounded shroud), fork, headlamp
    wc = V((FRONT_WHEEL[0], FRONT_WHEEL[1], WHEEL_R))
    rr = WHEEL_R + 0.2
    angs = [math.radians(d) for d in (28, 62, 96, 130, 160)]
    arc = [wc + V((0, -math.cos(a) * rr, math.sin(a) * rr)) for a in angs]
    for a, b in zip(arc, arc[1:]):
        E.beam(bd, a, b, 1.2, 0.28, PAINT, up=V((1, 0, 0)), caps=False)      # chunky mudguard over the wheel
    for s in (1, -1):
        E.beam(bd, wc + V((s * 0.42, 0, 0)), V((s * 0.42, FRONT_WHEEL[1] + 0.3, Z_CHIN + 0.05)), 0.13, 0.13, BLK,
               caps=False)
    lamp = arc[1] + V((0, -math.cos(angs[1]), math.sin(angs[1]))) * 0.36    # sits on the mudguard front
    E.lathe(bd, [(0.38, lamp.y + 0.25), (0.38, lamp.y - 0.05), (0.3, lamp.y - 0.12)], 10, (lamp.x, 0, lamp.z), 'Y',
            [BLK, BLK], cap_start=BLK, cap_end=LGT)
    # driver seat on its base, rail + pad behind it, rear bench, grab poles
    E.box(bd, (0, -1.85, 2.05), (1.2, 0.9, 0.8), BLK)
    E.box(bd, (0, -1.85, 2.7), (1.6, 1.15, 0.5), SEAT)
    E.box(bd, (0, -1.2, 3.4), (1.5, 0.22, 0.95), SEAT)
    E.beam(bd, (-2.25, -0.75, 3.85), (2.25, -0.75, 3.85), 0.1, 0.1, CHR, caps=False)
    E.box(bd, (0, 0.05, 3.42), (4.4, 1.15, 0.45), SEAT)
    E.box(bd, (0, 0.85, 4.5), (4.4, 0.3, 1.75), SEAT)
    for s in (1, -1):
        E.beam(bd, (s * 2.22, -0.5, 1.62), (s * 2.22, -0.5, ROOF_EDGE_Z), 0.11, 0.11, CHR, caps=False)
    # tail lamps on the rear corners
    ry = Y_REAR + 0.02
    for s in (1, -1):
        x0, x1 = sorted((s * 1.25, s * 1.95))
        E.quad(bd, [(x1, ry, 2.35), (x0, ry, 2.35), (x0, ry, 2.85), (x1, ry, 2.85)], RED)
    names = ['M_Env_Keke_Paint', 'M_Env_Keke_Canopy', 'M_Env_Glass', 'M_Env_Seat_Brown', 'M_Env_Chrome',
             'M_Env_Black', 'M_Env_Indicator', 'M_Env_Lamp', 'M_Env_TailLamp']
    body = E.finish('GIT_Env_KekeD_Body', bd, col, [M[n] for n in names])
    body.location = origin
    parts = [body, canopy(col, origin, M)]
    for name, c, out in (('F', (FRONT_WHEEL[0], FRONT_WHEEL[1], WHEEL_R), 1),
                         ('RL', (REAR_WHEEL[0], REAR_WHEEL[1], WHEEL_R), 1),
                         ('RR', (-REAR_WHEEL[0], REAR_WHEEL[1], WHEEL_R), -1)):
        wb = E.Builder()
        E.wheel(wb, (0, 0, 0), WHEEL_R, WHEEL_W, 10, out, 0, 1)
        w = E.finish('GIT_Env_KekeD_Wheel_%s' % name, wb, col, [M['M_Env_Tyre'], M['M_Env_Hub']])
        w.location = V(origin) + V(c)
        parts.append(w)
    return parts


def canopy(col, origin, M):
    """Rounded black canopy: roof from the windscreen bar back, closed rear quarters and back panel with
    the rear window opening, open sides and front."""
    bd = E.Builder()
    xs, ys = [-2.42, -2.0, 2.0, 2.42], [-3.62, 1.6, Y_REAR + 0.05]
    zs = [CANOPY_LOW, 5.6, ROOF_EDGE_Z, 7.15, ROOF_Z]

    def deform(co, key):
        i, j, k = key
        x, y, z = xs[i], ys[j], zs[k]
        if i in (0, 3):
            x *= {3: 0.95, 4: 0.82}.get(k, 1.0)
        if j == 0:
            y += {3: 0.1, 4: 0.32}.get(k, 0.0)
        if j == 2:
            y -= 0.1 * (z - CANOPY_LOW) / (ROOF_Z - CANOPY_LOW) + {3: 0.1, 4: 0.32}.get(k, 0.0)
        return V((x, y, z))

    def fm(axis, side, c):
        if axis == 2:
            return 0 if side > 0 else None
        if axis == 0:
            return 0 if (c.z > ROOF_EDGE_Z or c.y > 1.6) else None
        if side < 0:
            return 0 if c.z > ROOF_EDGE_Z else None
        if abs(c.x) < 2.0 and 5.6 < c.z < ROOF_EDGE_Z:
            return None                             # rear window opening
        return 0
    E.grid_box(bd, xs, ys, zs, deform=deform, face_mat=fm)
    ob = E.finish('GIT_Env_KekeD_Canopy', bd, col, [M['M_Env_Keke_Canopy']], smooth_angle=40)
    ob.location = origin
    return ob


def materials():
    m = {}
    for n, c, r in (('M_Env_Keke_Paint', COL['paint'], 0.5), ('M_Env_Keke_Canopy', COL['canopy'], 0.85),
                    ('M_Env_Glass', COL['glass'], 0.2), ('M_Env_Seat_Brown', COL['seat'], 0.8),
                    ('M_Env_Chrome', COL['chrome'], 0.3), ('M_Env_Black', COL['black'], 0.6),
                    ('M_Env_Indicator', COL['orange'], 0.4), ('M_Env_Lamp', COL['light'], 0.3),
                    ('M_Env_Tyre', COL['tyre'], 0.85), ('M_Env_Hub', COL['hub'], 0.4),
                    ('M_Env_TailLamp', COL['red'], 0.4)):
        m[n] = E.material(n, c, r)
    return m
