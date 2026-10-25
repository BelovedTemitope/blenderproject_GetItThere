"""Background danfo (VW T3 style) - concept A (clean, roof rack + cargo) and B (wrecked, rusty).

Front is -Y, +X is the vehicle's left side, Z up, 1 unit = 1 Roblox stud (18 x 8 x 9 body like the hero minibus).
"""
import math
import random

from mathutils import Matrix, Vector as V

import ev_lib as E

L2, W2 = 8.0, 4.0                         # half length / half width (chunky, as in the concept)
Z0, ZARCH, ZBELT, ZWIN, ZROOF1, ZROOF = 1.6, 3.5, 5.3, 8.0, 8.8, 9.4
WHEEL_Y, WHEEL_R, WHEEL_W, WHEEL_X = (-4.85, 4.75), 1.6, 1.25, 3.3
ARCH = {-4.85: (-6.5, -5.5, -4.2, -3.2), 4.75: (3.2, 4.2, 5.4, 6.4)}
WINDOWS = [(-7.6, -4.2, 'region'), (-3.2, 2.2, 'panes'), (3.2, 6.4, 'region')]
XS = [-W2, -2.6, 2.6, W2]
YS = sorted({-L2, -7.6, 7.6, L2, -0.5, 2.2} | {y for a in ARCH.values() for y in a})
ZS = [Z0, ZARCH, ZBELT, ZWIN, ZROOF1, ZROOF]
TEX_DIR = '//textures'
STRIPES = ((4.3, 4.55), (4.75, 5.0))         # two black side stripes (z bands) just under the window sill
SLOPE = 0.72                              # windscreen rake (y per z)
ARCH_SHOULDER = 2.65

COL = dict(yellow='#F2B705', black='#1E1E22', glass='#8D8B85', light='#E8E6DA', tyre='#2A2A2D', hub='#B9BCC0',
           rack='#24262A', box='#B98B5A', box2='#9C7044', sack='#A89A72', rust='#8A4A25', dark='#2B2420',
           grey='#9C9EA0', red='#B0342A')


LEN_SCALE = 0.94                          # final length trim from the concept overlay (A; B uses 0.90)
VISOR = 0.15                              # roof overhang over the windscreen (A high roof); B has none
ROOFS = {'high': (5.3, 8.0, 8.8, 9.4, 0.15), 'standard': (4.95, 7.8, 8.35, 8.8, -0.15)}
STRIPE_SETS = {'high': ((4.3, 4.55), (4.75, 5.0)), 'standard': ((3.95, 4.2), (4.4, 4.65))}


def configure(roof):
    global ZBELT, ZWIN, ZROOF1, ZROOF, ZS, VISOR, STRIPES, XS
    ZBELT, ZWIN, ZROOF1, ZROOF, VISOR = ROOFS[roof]
    # the wreck gets a centre cut so the crushed nose has enough vertices to crumple
    XS = [-W2, -2.6, 0.0, 2.6, W2] if roof == 'standard' else [-W2, -2.6, 2.6, W2]
    STRIPES = STRIPE_SETS[roof]
    ZS = [Z0, ZARCH, ZBELT, ZWIN, ZROOF1, ZROOF]


def front_y(z):
    if z <= ZBELT:
        return -L2
    if z <= ZWIN:
        return -L2 + (z - ZBELT) * SLOPE
    top = -L2 + (ZWIN - ZBELT) * SLOPE
    return top - VISOR if z == ZROOF1 else top + 0.25 + max(0.0, -VISOR)


def rear_y(z):
    return L2 - max(0.0, z - ZBELT) * 0.16 - (0.6 if z == ZROOF else (0.15 if z == ZROOF1 else 0.0))


def deform(co, key, wreck):
    i, j, k = key
    x, y, z = XS[i], YS[j], ZS[k]             # exact nominal values (Vector is float32)
    # windscreen rake / rear slope on the end stations
    if j == 0:
        y = front_y(z)
    elif j == len(YS) - 1:
        y = rear_y(z)
    elif j <= 3 and z > ZBELT:
        # A pillar and the door-window front edge follow the windscreen rake
        y = max(y, front_y(z) + (0.62, 1.1, 1.5)[j - 1])
    # tumblehome above the belt, rounded roof edge
    if abs(x) == W2:
        if z >= ZWIN:
            x *= 0.97 if z == ZWIN else (0.95 if z == ZROOF1 else 0.86)
        if j in (0, len(YS) - 1):
            x *= 0.89                      # rounded vertical corners
    # wheel arches: pull the top corners of each opening down into a faceted arch
    for wy, (ya, y1, y2, yb) in ARCH.items():
        if abs(x) >= W2 * 0.85 and z == ZARCH and y in (ya, yb):
            z = ARCH_SHOULDER
            y += 0.2 if y == ya else -0.2
    if wreck and j <= 1 and z <= ZBELT:
        # crumpled nose: pushed in, worst at the vehicle's right (-x) corner, a little uneven
        rnd = random.Random(i * 31 + k * 7 + j)
        y += 0.15 + 0.4 * (1 - x / W2) / 2 + rnd.uniform(0.0, 0.18)
        if Z0 < z < ZBELT:
            z += rnd.uniform(-0.1, 0.1)
    return V((x, y, z))


def in_arch(y):
    return any(a[0] < y < a[3] for a in ARCH.values())


def build(col, origin, wreck=False, mats=None):
    global LEN_SCALE
    configure('standard' if wreck else 'high')
    LEN_SCALE = 0.90 if wreck else 0.94
    random.seed(7)
    M = mats
    YEL, BLK, GLS, LGT, TYR, HUB = 0, 1, 2, 3, 4, 5
    bd = E.Builder()
    glass = {'front': [], 'rear': []}
    side_win = {}

    def face_mat(axis, side, c):
        if axis == 0:                                   # sides
            if c.z < ZARCH and in_arch(c.y):
                return None                             # wheel opening
            if ZBELT < c.z < ZWIN:
                for n, (a, b, mode) in enumerate(WINDOWS):
                    if a < c.y < b:
                        return ('win', side, n, round(c.y, 2)) if mode == 'panes' else ('win', side, n)
            return YEL
        if axis == 2 and side < 0 and abs(c.x) > 2.6 and in_arch(c.y):
            return None                                 # floor under the wheel wells
        if axis == 1 and ZBELT < c.z < ZWIN:
            return ('glass', 'front' if side < 0 else 'rear')
        return YEL

    tagged = []

    def fm(axis, side, c):
        m = face_mat(axis, side, c)
        if isinstance(m, tuple):
            tagged.append((m, len(tagged)))
            fm.last = m
            return GLS
        return m

    vmap, faces, ax = E.grid_box(bd, XS, YS, ZS, deform=lambda co, k: deform(co, k, wreck), face_mat=fm)
    # group window faces (glass material, by tag order)
    groups = {}
    gi = 0
    for f in faces:
        if f.material_index == GLS:
            groups.setdefault(tagged[gi][0], []).append(f)
            gi += 1
    for key, fs in groups.items():
        res = E.bmesh.ops.inset_region(bd.bm, faces=fs, thickness=0.14, depth=-0.07, use_even_offset=True)
        for f in res['faces']:
            f.material_index = YEL
    if wreck:
        # glass long gone: open the panes (frames stay) so the cabin reads through, as in the concept
        E.bmesh.ops.delete(bd.bm, geom=[f for f in bd.bm.faces if f.material_index == GLS], context='FACES_ONLY')
        for x in (-1.9, 1.9):                                   # front seats + one bench
            E.box(bd, (x, -5.2, 3.25), (1.9, 1.7, 0.5), 7)
            E.box(bd, (x, -4.35, 4.3), (1.9, 0.35, 1.7), 7)
        E.box(bd, (0, -0.9, 3.25), (6.6, 1.7, 0.5), 7)
        E.box(bd, (0, -0.05, 4.3), (6.6, 0.35, 1.7), 7)
    # wheel wells
    for wy, (ya, y1, y2, yb) in ARCH.items():
        for s in (1, -1):
            i_out, i_in = (len(XS) - 1, len(XS) - 2) if s > 0 else (0, 1)
            loop = [vmap[(i_out, YS.index(y), k)] for y, k in
                    ((ya, 0), (ya, 1), (y1, 1), (y2, 1), (yb, 1), (yb, 0))]
            mids = [vmap[(i_in, YS.index(y), 0)] for y in (y1, y2)]
            E.well(bd, loop, (-s * (W2 - 2.6), 0, 0), BLK, mids)
    # bumpers (black), front grille band + lamps, stripes, tail lamps
    fy = -L2
    if wreck:
        rot = Matrix.Rotation(math.radians(-7), 3, 'Y') @ Matrix.Rotation(math.radians(6), 3, 'Z')
        E.box(bd, (0.2, fy - 0.05, 1.85), (8.0, 0.55, 0.7), BLK, rot)
    else:
        E.box(bd, (0, fy - 0.2, 2.05), (8.3, 0.6, 0.8), BLK)
    E.box(bd, (0, L2 + 0.15, 2.05), (8.3, 0.55, 0.75), BLK)
    gy = (fy + (0.45 if wreck else 0)) - 0.02
    E.quad(bd, [(-3.25, gy, 3.15), (3.25, gy, 3.15), (3.25, gy, 3.95), (-3.25, gy, 3.95)], BLK)
    for sx in ((1, -1) if not wreck else (1,)):
        x0, x1 = sorted((sx * 2.55, sx * 3.3))
        E.quad(bd, [(x0, gy - 0.02, 3.22), (x1, gy - 0.02, 3.22), (x1, gy - 0.02, 3.88), (x0, gy - 0.02, 3.88)], LGT)
    for sx in (1, -1):
        x0, x1 = sorted((sx * 3.0, sx * 3.5))
        E.quad(bd, [(x1, rear_y(2.9) + 0.02, 2.9), (x0, rear_y(2.9) + 0.02, 2.9), (x0, rear_y(3.9) + 0.02, 3.9), (x1, rear_y(3.9) + 0.02, 3.9)], 6)
    if not wreck:                                       # B has its stripes painted into the rust atlas
        for s in (1, -1):
            for z0 in (STRIPES[0][0], STRIPES[1][0]):
                x = s * (W2 + 0.012)
                pts = [(x, -7.45, z0), (x, 7.55, z0), (x, 7.55, z0 + 0.25), (x, -7.45, z0 + 0.25)]
                E.quad(bd, pts if s > 0 else pts[::-1], BLK)
    # mirrors on short arms
    for s in (1, -1):
        E.beam(bd, (s * 3.95, -6.75, 5.6), (s * 4.45, -6.9, 5.8), 0.12, 0.12, BLK, caps=False)
        E.box(bd, (s * 4.55, -6.9, 6.0), (0.16, 0.5, 0.85), BLK)
    names = ['M_Env_Danfo_Paint', 'M_Env_Black', 'M_Env_Glass' if not wreck else 'M_Env_Broken_Glass',
             'M_Env_Lamp', 'M_Env_Tyre', 'M_Env_Hub' if not wreck else 'M_Env_Hub_Rust', 'M_Env_TailLamp',
             'M_Env_Seat']
    tag = 'B' if wreck else 'A'
    pre = None
    if wreck:
        import os
        import bpy
        import ev_rust
        os.makedirs(TEX_DIR, exist_ok=True)
        png = ev_rust.paint(os.path.join(TEX_DIR, 'T_Env_DanfoB_Paint.png'), stripes=STRIPES)
        img = bpy.data.images.load(png)
        img.pack()
        names[0] = 'M_Env_DanfoB_Paint'
        M[names[0]] = E.material(names[0], COL['yellow'], 0.7, image=img)
        def pre(bm):
            E.orient_outward(bm, {YEL}, (0, 0, (Z0 + ZROOF) / 2))
            E.uv_tiles(bm, {YEL}, ev_rust.tile_of)
    body = E.finish('GIT_Env_Danfo%s_Body' % tag, bd, col, [M[n] for n in names], pre=pre)
    body.data.transform(Matrix.Diagonal((1, LEN_SCALE, 1, 1)))
    body.location = origin
    parts = [body]
    # wheels: separate objects, origin at the hub
    for wy in WHEEL_Y:
        for s in (1, -1):
            wb = E.Builder()
            E.wheel(wb, (0, 0, 0), WHEEL_R, WHEEL_W, 12, s, 0, 1)
            w = E.finish('GIT_Env_Danfo%s_Wheel_%s%s' % (tag, 'F' if wy < 0 else 'R', 'L' if s > 0 else 'R'), wb, col,
                         [M['M_Env_Tyre'], M['M_Env_Hub' if not wreck else 'M_Env_Hub_Rust']])
            w.location = V(origin) + V((s * WHEEL_X, wy * LEN_SCALE, WHEEL_R))
            if wreck and wy < 0 and s > 0:
                w.rotation_euler = (0, 0, math.radians(-8))     # front wheel knocked out of line
            parts.append(w)
    if not wreck:
        parts.append(roof_cargo(col, origin, M))
    return parts


def roof_cargo(col, origin, M):
    """Layered detail: roof rack with boxes and sacks (separate object)."""
    RCK, BOX, BOX2, SCK = 0, 1, 2, 3
    bd = E.Builder()
    zt, xr, y0, y1 = ZROOF + 0.75, 2.8, -2.6, 4.7
    t = 0.16
    for x in (-xr, xr):
        E.beam(bd, (x, y0, zt), (x, y1, zt), t, t, RCK)
    for y in (y0, y1):
        E.beam(bd, (-xr + t / 2, y, zt), (xr - t / 2, y, zt), t, t, RCK, caps=False)
    for y in (0.0, 2.4):
        E.beam(bd, (-xr + t / 2, y, zt - 0.05), (xr - t / 2, y, zt - 0.05), t, 0.08, RCK, caps=False)
    for x in (-xr, xr):
        for y in (y0 + 0.3, 1.1, y1 - 0.3):
            s = 1 if x > 0 else -1
            E.beam(bd, (x, y, zt - t / 2), (s * 3.55, y, ZROOF1 + 0.25), 0.14, 0.14, RCK, caps=False)
    zb = zt + t / 2
    E.box(bd, (-1.2, -1.2, zb + 0.45), (1.9, 2.0, 0.9), BOX)
    E.box(bd, (0.9, -1.4, zb + 0.35), (1.7, 1.5, 0.7), BOX2)
    E.box(bd, (0.4, 0.9, zb + 0.55), (2.6, 1.9, 1.1), BOX, Matrix.Rotation(math.radians(6), 3, 'Z'))
    E.box(bd, (0.6, 1.0, zb + 1.5), (1.5, 1.3, 0.85), BOX2, Matrix.Rotation(math.radians(-10), 3, 'Z'))
    E.box(bd, (-1.5, 2.7, zb + 0.4), (1.5, 1.8, 0.8), BOX2)
    for x, y, r in ((1.2, 3.3, 8), (-0.6, 3.9, -12)):
        E.box(bd, (x, y, zb + 0.45), (1.7, 2.4, 0.9), SCK, Matrix.Rotation(math.radians(r), 3, 'Z'))
    ob = E.finish('GIT_Env_DanfoA_RoofRack_Cargo', bd, col,
                  [M['M_Env_Black'], M['M_Env_Box'], M['M_Env_Box_Dark'], M['M_Env_Sack']], smooth_angle=30)
    ob.data.transform(Matrix.Diagonal((1, LEN_SCALE, 1, 1)))
    ob.location = origin
    return ob


def materials():
    m = {}
    for n, c, r in (('M_Env_Danfo_Paint', COL['yellow'], 0.55), ('M_Env_Black', COL['black'], 0.6),
                    ('M_Env_Glass', COL['glass'], 0.2), ('M_Env_Broken_Glass', COL['dark'], 0.9),
                    ('M_Env_Lamp', COL['light'], 0.3), ('M_Env_Tyre', COL['tyre'], 0.85),
                    ('M_Env_Hub', COL['hub'], 0.4), ('M_Env_Hub_Rust', COL['rust'], 0.8),
                    ('M_Env_TailLamp', COL['red'], 0.4), ('M_Env_Seat', '#4A4D55', 0.8), ('M_Env_Box', COL['box'], 0.8),
                    ('M_Env_Box_Dark', COL['box2'], 0.8), ('M_Env_Sack', COL['sack'], 0.9)):
        m[n] = E.material(n, c, r)
    return m
