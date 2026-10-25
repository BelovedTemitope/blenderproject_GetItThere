"""Danfos A and B: VW T3 base. A = fibreglass high roof, stripes, roof rack with cargo (configure('high'));
B = wrecked standard-roof T3: crushed nose, glass gone, rust/primer atlas (configure('standard'), build_wreck).

Front is -Y, +X is the vehicle's left, Z up. One quad lattice whose cut lines are the T3's own lines:
  belt (window sill), gutter flange at window-top height with a small lip, the high-roof cap above it
  (sides sloping in, big front face sloping back over the windscreen), large chamfered front corners,
  door / B pillar / sliding-door panes / C pillar / rear window, wheel arches with welded wells.
"""
import math

from mathutils import Matrix, Vector as V

import ev_lib as E
import ev_danfo as D

L2, W2 = 7.5, 4.0
Z0, ZARCH, ZBELT, ZFL, ZLIP, ZROOF = 1.6, 3.5, 5.3, 8.0, 8.18, 9.45
WHEEL_Y, WHEEL_R, WHEEL_W, WHEEL_X = (-5.0, 4.45), 1.6, 1.25, 3.3
ARCH = {-5.0: (-6.55, -5.6, -4.4, -3.45), 4.45: (3.0, 3.95, 5.0, 5.95)}
WINDOWS = [(-7.05, -3.95, 'region'), (-3.45, 2.5, 'panes'), (3.0, 5.95, 'region')]
XS = [-W2, -3.5, -2.6, 2.6, 3.5, W2]
YS = sorted({-L2, -7.05, 7.05, L2, -3.95, -3.45, -0.45, 2.5} | {y for a in ARCH.values() for y in a})
ZS = [Z0, ZARCH, ZBELT, ZFL, ZLIP, ZROOF]
LEN = 1.113                                # length from the fSpy-style camera fit (ev_vpprop.py)
WRECK = False
RAKE = 0.6                                 # windscreen rake (y per z)
STRIPES = ((4.3, 4.55), (4.75, 5.0))
CAP_TOP_X = (3.05, 2.8)                    # roof cap top: outer and second column half widths
CAP_FRONT_Y, CAP_REAR_Y = -4.75, 6.55      # where the flat roof top starts / ends


KIND = 'high'


def configure(kind):
    global KIND, ZFL, ZLIP, ZROOF, ZS, CAP_TOP_X, CAP_FRONT_Y, CAP_REAR_Y, LEN
    KIND = kind
    if kind == 'high':
        ZFL, ZLIP, ZROOF = 8.0, 8.18, 9.45
        CAP_TOP_X, CAP_FRONT_Y, CAP_REAR_Y, LEN = (3.05, 2.8), -4.75, 6.55, 1.113
    else:                                  # standard T3 roof: gutter, then a short rounded roof edge
        ZFL, ZLIP, ZROOF = 7.75, 8.15, 8.4
        CAP_TOP_X, CAP_FRONT_Y, CAP_REAR_Y, LEN = (3.6, 3.35), None, L2 - 0.45, 1.07
    ZS = [Z0, ZARCH, ZBELT, ZFL, ZLIP, ZROOF]


def front_y(z):
    if z <= ZBELT:
        return -L2 + (z - Z0) * 0.03                     # lower front leans back a touch
    if z <= ZFL:
        return -L2 + (ZBELT - Z0) * 0.03 + (z - ZBELT) * RAKE
    top = -L2 + (ZBELT - Z0) * 0.03 + (ZFL - ZBELT) * RAKE
    if CAP_FRONT_Y is None:                               # standard roof: rounded front roof edge
        return top + (0.12 if z == ZLIP else 0.45)
    return top - 0.18 if z == ZLIP else CAP_FRONT_Y


def rear_y(z):
    if z <= ZBELT:
        return L2
    if z <= ZLIP:
        return L2 - (z - ZBELT) * 0.1
    return CAP_REAR_Y


def deform(co, key):
    i, j, k = key
    x, y, z = XS[i], YS[j], ZS[k]
    last = len(YS) - 1
    outer = abs(x) == W2
    if j == 0:
        y = front_y(z)
    elif j == last:
        y = rear_y(z)
    elif j <= 3 and ZBELT < z < ZROOF:
        y = max(y, front_y(z) + (0.45, 0.8, 1.1)[j - 1])   # A pillar / door-window front follow the rake
    elif j <= 3 and z == ZROOF:
        y = max(y, front_y(z) + 0.15 * j)                # flat roof top starts behind the sloped cap front
    # big chamfered vertical corners front and rear
    if j in (0, last) and outer:
        y += 0.2 if j == 0 else -0.35
        x = math.copysign(3.85, x)
    if j in (0, last) and abs(x) == 3.5:
        y += 0.04 if j == 0 else -0.08
    # sides: tumblehome above the belt, gutter lip, roof cap sloping in
    if abs(x) >= 3.5 and z > ZBELT:
        s = math.copysign(1, x)
        if z == ZFL:
            x = s * (abs(x) - 0.08)
        elif z == ZLIP:
            x = s * (abs(x) - 0.02)
        elif z == ZROOF:
            x = s * (CAP_TOP_X[0] if outer else CAP_TOP_X[1])
    if z == ZROOF and j in (0, last) and outer:
        y += 0.25 if j == 0 else -0.2
    if WRECK and j <= 1 and z <= ZBELT:
        y = -L2 + 0.35 if j == 0 else max(y, -L2 + 0.75)  # nose structure set back; crushed panel goes in front
    # wheel arches: faceted arch from the opening's top corners
    for ya, y1, y2, yb in ARCH.values():
        if outer and z == ZARCH and YS[j] in (ya, yb):
            z = 2.65
            y += 0.2 if YS[j] == ya else -0.2
    return V((x, y, z))


def in_arch(y):
    return any(a[0] < y < a[3] for a in ARCH.values())


def build(col, origin, mats, wreck=False):
    global WRECK, RAKE
    configure('standard' if wreck else 'high')
    WRECK, RAKE = wreck, (0.8 if wreck else 0.6)
    tag = 'B' if wreck else 'A'
    M = mats
    YEL, BLK, GLS, LGT, TYR, HUB, RED, SEAT = range(8)
    bd = E.Builder()
    tags = []

    def fm(axis, side, c):
        if axis == 0:
            if c.z < ZARCH and in_arch(c.y):
                return None
            if ZBELT < c.z < ZFL:
                for n, (a, b, mode) in enumerate(WINDOWS):
                    if a < c.y < b:
                        tags.append(('win', side, n, round(c.y, 2)) if mode == 'panes' else ('win', side, n))
                        return GLS
            return YEL
        if axis == 2 and side < 0 and abs(c.x) > 2.6 and in_arch(c.y):
            return None
        if axis == 1 and ZBELT < c.z < ZFL and abs(c.x) < 3.5:
            tags.append(('glass', side))
            return GLS
        return YEL

    vmap, faces, _ = E.grid_box(bd, XS, YS, ZS, deform=deform, face_mat=fm)
    groups = {}
    gi = 0
    for f in faces:
        if f.material_index == GLS:
            groups.setdefault(tags[gi], []).append(f)
            gi += 1
    for fs in groups.values():
        res = E.bmesh.ops.inset_region(bd.bm, faces=fs, thickness=0.13, depth=-0.07, use_even_offset=True)
        for f in res['faces']:
            f.material_index = YEL if wreck else BLK      # black rubber window seals (A); rotted out (B)
    if wreck:
        E.bmesh.ops.delete(bd.bm, geom=[f for f in bd.bm.faces if f.material_index == GLS], context='FACES_ONLY')
        crushed_nose(bd, YEL)
        for x in (-1.9, 1.9):                                           # gutted cabin: seats + floor read
            E.box(bd, (x, -5.0, 3.25), (1.9, 1.7, 0.5), SEAT)
            E.box(bd, (x, -4.15, 4.3), (1.9, 0.35, 1.7), SEAT)
        E.box(bd, (0, -0.6, 3.25), (6.6, 1.7, 0.5), SEAT)
        E.box(bd, (0, 0.25, 4.3), (6.6, 0.35, 1.7), SEAT)
        E.box(bd, (0, 0.0, 2.85), (7.6, 13.6, 0.12), SEAT)
    for wy, (ya, y1, y2, yb) in ARCH.items():
        for s in (1, -1):
            i_out, i_in = (len(XS) - 1, len(XS) - 3) if s > 0 else (0, 2)      # inner wall at x = +-2.6
            loop = [vmap[(i_out, YS.index(y), k)] for y, k in ((ya, 0), (ya, 1), (y1, 1), (y2, 1), (yb, 1), (yb, 0))]
            mids = [vmap[(i_in, YS.index(y), 0)] for y in (y1, y2)]
            E.well(bd, loop, (-s * (W2 - 2.6), 0, 0), BLK, mids)
    # bumpers, black grille band with square lamps at its ends, stripes, mirrors, tail lamps
    if wreck:
        rot = Matrix.Rotation(math.radians(-9), 3, 'Y') @ Matrix.Rotation(math.radians(3), 3, 'Z')
        E.box(bd, (0.15, -L2 - 0.45, 1.8), (7.5, 0.5, 0.65), BLK, rot)          # sagging bumper
    else:
        E.box(bd, (0, -L2 - 0.18, 2.05), (8.1, 0.6, 0.8), BLK)
    E.box(bd, (0, L2 + 0.15, 2.05), (8.1, 0.55, 0.75), BLK)
    gy = front_y(3.5) - 0.02
    if not wreck:
        E.quad(bd, [(-3.15, gy, 3.1), (3.15, gy, 3.1), (3.15, gy + 0.02, 3.95), (-3.15, gy + 0.02, 3.95)], BLK)
    for sx in (1, -1):
        x0, x1 = sorted((sx * 2.35, sx * 3.0))
        if not wreck:
            E.quad(bd, [(x0, gy - 0.02, 3.18), (x1, gy - 0.02, 3.18), (x1, gy, 3.88), (x0, gy, 3.88)], LGT)
        x0, x1 = sorted((sx * 3.0, sx * 3.55))
        ry = rear_y(3.4) + 0.02
        E.quad(bd, [(x1, ry, 2.8), (x0, ry, 2.8), (x0, ry, 4.0), (x1, ry, 4.0)], RED)
        for z0, z1 in (() if wreck else STRIPES):        # B's stripes are painted into its atlas
            x = sx * (W2 + 0.012)
            pts = [(x, -7.35, z0), (x, 7.0, z0), (x, 7.0, z1), (x, -7.35, z1)]
            E.quad(bd, pts if sx > 0 else pts[::-1], BLK)
        E.beam(bd, (sx * 3.95, -6.55, 5.6), (sx * 4.45, -6.7, 5.8), 0.12, 0.12, BLK, caps=False)
        E.box(bd, (sx * 4.55, -6.7, 6.0), (0.16, 0.5, 0.85), BLK)
    names = ['M_Env_Danfo_Paint', 'M_Env_Black', 'M_Env_Glass', 'M_Env_Lamp', 'M_Env_Tyre',
             'M_Env_Hub_Rust' if wreck else 'M_Env_Hub', 'M_Env_TailLamp', 'M_Env_Seat']
    pre = None
    if wreck:
        import os
        import bpy
        import ev_rust
        os.makedirs(D.TEX_DIR, exist_ok=True)
        png = ev_rust.paint(os.path.join(D.TEX_DIR, 'T_Env_DanfoB_Paint.png'), stripes=STRIPES, z0=Z0, belt=ZBELT,
                            win_top=ZFL, gutter=ZLIP, windows=[(a, b) for a, b, _ in WINDOWS], wheels=WHEEL_Y,
                            primer_front=-6.4, b_pillar=(-3.95, -3.45))
        img = bpy.data.images.load(png)
        img.pack()
        names[0] = 'M_Env_DanfoB_Paint'
        M[names[0]] = E.material(names[0], D.COL['yellow'], 0.7, image=img)

        def pre(bm):
            E.orient_outward(bm, {YEL}, (0, 0, (Z0 + ZROOF) / 2))
            E.uv_tiles(bm, {YEL}, ev_rust.tile_of)
            for f in bm.faces:
                c = f.calc_center_median()
                if f.material_index == YEL and c.y < -L2 + 1.0 and c.z < ZBELT + 0.1:
                    f.smooth = False
    body = E.finish('GIT_Env_Danfo%s_Body' % tag, bd, col, [M[n] for n in names], pre=pre)
    body.data.transform(Matrix.Diagonal((1, LEN, 1, 1)))
    body.location = origin
    parts = [body]
    for wy in WHEEL_Y:
        for s in (1, -1):
            wb = E.Builder()
            E.wheel(wb, (0, 0, 0), WHEEL_R, WHEEL_W, 12, s, 0, 1)
            w = E.finish('GIT_Env_Danfo%s_Wheel_%s%s' % (tag, 'F' if wy < 0 else 'R', 'L' if s > 0 else 'R'), wb, col,
                         [M['M_Env_Tyre'], M['M_Env_Hub_Rust' if wreck else 'M_Env_Hub']])
            w.location = V(origin) + V((s * WHEEL_X, wy * LEN, WHEEL_R))
            parts.append(w)
    if not wreck:
        parts.append(roof_cargo(col, origin, M))
    return parts


def crushed_nose(bd, mat, nx=6, nz=4):
    """Crumpled front of the wreck: a faceted sheet-metal mass bulging forward over the bumper, the left front
    corner folded out, the right side caved in. Clean quad grid, flat-shaded."""
    import random
    rnd = random.Random(9)
    zs = [Z0 + 0.1, 2.55, 3.35, 4.25, ZBELT + 0.02]
    rows = []
    for k in range(nz + 1):
        row = []
        for i in range(nx + 1):
            t = i / nx
            x, z = -W2 + 2 * W2 * t, zs[k]
            y = -L2 - 0.25 - 0.25 * math.sin(math.pi * t) * (1 - k / nz)
            if i in (0, nx):
                y = -L2 + 0.85
                x = math.copysign(W2 + (0.18 if x > 0 else 0.04), x)
            elif i in (1, nx - 1):
                y = -L2 + 0.05
            if x < 0 and 0 < i < nx:
                y += 0.35 * math.exp(-((x + 1.6) ** 2) / 2.0) * (1 - abs(z - 3.0) / 2.5)
            if k == nz:
                y = front_y(ZBELT) + (0.05 if 0 < i < nx else 0.85)
            elif 0 < i < nx and 0 < k:
                y += rnd.uniform(-0.28, 0.28)
                z += rnd.uniform(-0.18, 0.18)
                x += rnd.uniform(-0.15, 0.15)
            row.append(bd.vert((x, y, z)))
        rows.append(row)
    for k in range(nz):
        for i in range(nx):
            bd.face((rows[k][i], rows[k + 1][i], rows[k + 1][i + 1], rows[k][i + 1]), mat)


def roof_cargo(col, origin, M):
    """Layered detail: roof rack on the cap (legs hooked down the cap sides to the gutter) with boxes and sacks."""
    RCK, BOX, BOX2, SCK = 0, 1, 2, 3
    bd = E.Builder()
    zt, xr, y0, y1 = ZROOF + 0.55, 2.75, -2.9, 4.9
    t = 0.16
    for x in (-xr, xr):
        E.beam(bd, (x, y0, zt), (x, y1, zt), t, t, RCK)
    for y in (y0, y1):
        E.beam(bd, (-xr + t / 2, y, zt), (xr - t / 2, y, zt), t, t, RCK, caps=False)
    for y in (-0.3, 2.3):
        E.beam(bd, (-xr + t / 2, y, zt - 0.05), (xr - t / 2, y, zt - 0.05), t, 0.08, RCK, caps=False)
    for x in (-xr, xr):
        s = 1 if x > 0 else -1
        for y in (y0 + 0.3, 1.0, y1 - 0.3):
            knee = (s * 3.25, y, ZROOF - 0.15)
            E.beam(bd, (x, y, zt - t / 2), knee, 0.14, 0.14, RCK, caps=False)
            E.beam(bd, knee, (s * 3.75, y, ZLIP + 0.02), 0.14, 0.14, RCK, caps=False)
    zb = zt + t / 2
    E.box(bd, (-1.2, -1.3, zb + 0.45), (1.9, 2.0, 0.9), BOX)
    E.box(bd, (0.9, -1.6, zb + 0.35), (1.7, 1.5, 0.7), BOX2)
    E.box(bd, (0.35, 0.8, zb + 0.55), (2.6, 1.9, 1.1), BOX, Matrix.Rotation(math.radians(6), 3, 'Z'))
    E.box(bd, (0.55, 0.9, zb + 1.5), (1.5, 1.3, 0.85), BOX2, Matrix.Rotation(math.radians(-10), 3, 'Z'))
    E.box(bd, (-1.5, 2.6, zb + 0.4), (1.5, 1.8, 0.8), BOX2)
    for x, y, r in ((1.2, 3.2, 8), (-0.6, 3.9, -12)):
        E.box(bd, (x, y, zb + 0.45), (1.7, 2.4, 0.9), SCK, Matrix.Rotation(math.radians(r), 3, 'Z'))
    ob = E.finish('GIT_Env_DanfoA_RoofRack_Cargo', bd, col,
                  [M['M_Env_Black'], M['M_Env_Box'], M['M_Env_Box_Dark'], M['M_Env_Sack']], smooth_angle=30)
    ob.data.transform(Matrix.Diagonal((1, LEN, 1, 1)))
    ob.location = origin
    return ob
