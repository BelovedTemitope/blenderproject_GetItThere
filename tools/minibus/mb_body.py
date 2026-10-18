"""Body shell: a structured quad lattice (VW T3 style van body).

Axes: -Y is the front, +X is the vehicle's left (driver / sliding-door side), Z up.
The shell is one quad surface whose edge loops run along every window,
door and wheel-arch edge, so openings are just missing faces (no booleans).
A Solidify modifier gives it panel thickness.
"""
import math
from mathutils import Vector as V

from mb_lib import Builder

# --- wheel / arch layout (matches the v02 blockout + ortho sheet) -----------
WHEEL_Y = (-5.28, 4.31)
WHEEL_Z = 1.83
ARCH_CZ = 2.15          # arch circle centre height
ARCH_R = 2.0            # arch circle radius (top = 4.15)
SILL_Z = 3.05           # r1 at non-arch columns (sill / floor line)
ARCH_OFFS = (-1.786, -1.45, -0.78, 0.0, 0.78, 1.45, 1.786)  # y offsets of arch columns


def arch_z(dy):
    return ARCH_CZ + math.sqrt(max(ARCH_R ** 2 - dy * dy, 0.0))


# rows: r0 bottom, r1 sill/arch, rs stripe line, rf front crease, r2 belt, r3 window top, r4 roof shoulder, r5 roof
ROWS = ['r0', 'r1', 'rs', 'rf', 'r2', 'r3', 'r4', 'r5']
ROW_Z = {'r0': 2.7, 'rf': 6.2, 'r2': 6.85, 'r3': 8.8, 'r4': 9.3, 'r5': 9.55}
SIDE_X = [3.82, 3.9, 3.9, 3.9, 3.9, 3.62, 3.45, 3.15]          # half width per row (tumblehome)
FRONT_Y = [-9.1, -9.1, -9.1, -9.1, -8.7, -6.88, -6.55, -6.25]   # front face per row
REAR_Y = [7.25, 7.25, 7.25, 7.25, 7.25, 6.88, 6.52, 6.1]        # rear face per row
FRONT_Z = {'r3': 9.02, 'r4': 9.37}   # windscreen top sits higher than the side windows
REAR_Z = {'r3': 8.98, 'r4': 9.36}
CORNER_CH = [0.3, 0.3, 0.3, 0.3, 0.3, 0.12, 0.08, 0.06]         # vertical corner chamfer per row
ROOF_CROWN = 0.1

X_LAT = [-3.9, -3.6, -3.25, 0.0, 3.25, 3.6, 3.9]   # ix lattice (scaled per row by SIDE_X/3.9)
BASE_ROWS = ROWS[:]

# --- variants ---------------------------------------------------------------
# RIDGES: T3 swage lines (upper at door-handle height, lower between the arches)
# SHAPE:  stronger tumblehome measured from the front ortho reference
RIDGES = False
SHAPE = False
GROOVE = False        # creases pressed into the panel instead of standing proud
DOORS = False         # sliding-door openings on both sides (doors are separate parts)
SIDE_X_V03 = SIDE_X[:]
SIDE_X_SHAPE = [3.82, 3.9, 3.9, 3.9, 3.8, 3.33, 3.05, 2.75]
RIDGE_UPPER_Z = [5.6, 5.7, 5.8, 5.9]   # slope / plateau / plateau / slope
RIDGE_LOWER_Z = [3.6, 3.7, 3.8, 3.9]
RIDGE_D = 0.035                            # how far the plateau stands proud of the panel
RIDGE_D_FRONT = 0.03
LOWER_RIDGE_COLS = (0, 8, 9, 10)           # lower ridge only ahead of / between the arches
UPPER_RIDGE_OFF = (17, 18)                 # upper ridge fades out before the rear corner armour


def configure(ridges=False, shape=False, groove=False, doors=False):
    global RIDGES, SHAPE, ROWS, GROOVE, DOORS
    RIDGES, SHAPE, GROOVE, DOORS = ridges, shape, groove, doors
    SIDE_X[:] = SIDE_X_SHAPE if shape else SIDE_X_V03
    ROWS = (['r0', 'r1'] + (['L1', 'L2', 'L3', 'L4'] if ridges else []) + ['rs'] +
            (['U1', 'U2', 'U3', 'U4'] if ridges else []) + ['rf', 'r2', 'r3', 'r4', 'r5'])


def side_x_at(z):
    """Body half-width at height z (base rows, current variant)."""
    zs = [ROW_Z['r0'], SILL_Z, 4.8, ROW_Z['rf'], ROW_Z['r2'], ROW_Z['r3'], ROW_Z['r4'], ROW_Z['r5']]
    for k in range(len(zs) - 1):
        if zs[k] <= z <= zs[k + 1]:
            t = (z - zs[k]) / (zs[k + 1] - zs[k])
            return SIDE_X[k] + (SIDE_X[k + 1] - SIDE_X[k]) * t
    return SIDE_X[0] if z < zs[0] else SIDE_X[-1]


def _base_index(name):
    if name[0] == 'L' or name[0] == 'U':
        return BASE_ROWS.index('rs')
    return BASE_ROWS.index(name)


def _interp(a, b, t):
    return a + (b - a) * t


def column_table():
    """Return list of columns; each is (y_per_row[8], z_r1)."""
    fy = WHEEL_Y[0]
    ry = WHEEL_Y[1]
    cols = []
    cols.append((FRONT_Y[:], SILL_Z))                                        # c0 front face
    c1 = [fy + ARCH_OFFS[0], fy + ARCH_OFFS[0], -7.3, -7.6, -7.95, -6.55, -6.15, -5.85]
    c7 = [fy + ARCH_OFFS[6], fy + ARCH_OFFS[6], -3.47, -3.45, -3.45, -3.45, -3.45, -3.45]
    cols.append((c1, SILL_Z))
    for k in range(1, 6):                                                    # c2..c6 front arch
        low = fy + ARCH_OFFS[k]
        t = k / 6.0
        ys = [low, low]
        ys.append(_interp(low, _interp(c1[2], c7[2], t), 0.35))              # rs
        ys.append(_interp(low, _interp(c1[3], c7[3], t), 0.65))              # rf
        for r in range(4, 8):
            ys.append(_interp(c1[r], c7[r], t))
        cols.append((ys, arch_z(ARCH_OFFS[k])))
    cols.append((c7, SILL_Z))                                                # c7 B-pillar / arch end
    cols.append(([-2.86] * 8, SILL_Z))                                       # c8 sliding door front
    cols.append(([1.0] * 8, SILL_Z))                                         # c9 sliding door rear
    c10 = [1.68] * 8
    cols.append((c10, SILL_Z))                                               # c10 rear window front
    c15u = [5.04, 5.04, 5.04, 5.04]
    rear_low = [ry + d for d in ARCH_OFFS]                                   # c11..c17 lower
    c15 = [rear_low[4], rear_low[4], rear_low[4], 5.06] + c15u
    for k in range(0, 4):                                                    # c11..c14
        low = rear_low[k]
        t = (k + 1) / 5.0
        ys = [low, low, low, _interp(low, _interp(1.68, 5.04, t), 0.5)]
        for r in range(4, 8):
            ys.append(_interp(1.68, 5.04, t))
        cols.append((ys, arch_z(ARCH_OFFS[k]) if k else SILL_Z))
    cols.append((c15, arch_z(ARCH_OFFS[4])))                                 # c15
    c16 = [rear_low[5], rear_low[5], rear_low[5], 5.78, 5.75, 5.7, 5.6, 5.4]
    cols.append((c16, arch_z(ARCH_OFFS[5])))                                 # c16
    c17 = [rear_low[6], rear_low[6], rear_low[6], 6.3, 6.45, 6.35, 6.15, 5.75]
    cols.append((c17, SILL_Z))                                               # c17
    cols.append((REAR_Y[:], SILL_Z))                                         # c18 rear face
    return cols


# stripe row height per column (front navy band top edge rises toward the B-pillar)
def stripe_z(ci, ncols):
    if ci <= 8:
        return 4.45 + 0.09 * ci
    return 5.0


# opening definitions: (side sign or 0 for both, col_from, col_to, row_from, row_to)
def openings():
    o = []
    for s in (1, -1):
        o.append((s, 1, 7, 'r2', 'r3'))      # front door windows
        o.append((s, 10, 15, 'r2', 'r3'))    # rear quarter windows
        o.append((s, 1, 7, 'r0', 'r1'))      # front arch
        o.append((s, 11, 17, 'r0', 'r1'))    # rear arch
    o.append((1, 8, 9, 'r1', 'r3'))          # sliding door opening (left)
    if DOORS:
        o.append((-1, 8, 9, 'r1', 'r3'))     # second sliding door opening (right)
    else:
        o.append((-1, 8, 9, 'r2', 'r3'))     # middle window (right)
    return o


NAVY_SIDE = [(0, 7, 'r1', 'rs')]             # navy band on both sides (front section)


def build_body(mats):
    """mats: dict name->index used: paint, navy."""
    cols = column_table()
    nc = len(cols)
    nr = len(ROWS)
    ri = {r: i for i, r in enumerate(ROWS)}
    bd = Builder()
    vmap = {}

    def row_z(r, ci):
        name = ROWS[r]
        if name == 'r1':
            return cols[ci][1]
        if name == 'rs':
            return stripe_z(ci, nc)
        if name[0] == 'L':
            i = int(name[1]) - 1
            # over the arches the rows ride just above the arch edge (hidden under the flares)
            return max(RIDGE_LOWER_Z[i], cols[ci][1] + 0.1 + 0.08 * i)
        if name[0] == 'U':
            return RIDGE_UPPER_Z[int(name[1]) - 1]
        return ROW_Z[name]

    def col_y(ci, r, z):
        name = ROWS[r]
        ys = cols[ci][0]
        if name[0] in 'LU':
            a, b = ('r1', 'rs') if name[0] == 'L' else ('rs', 'rf')
            ia, ib = BASE_ROWS.index(a), BASE_ROWS.index(b)
            za, zb = row_z(ri[a], ci), row_z(ri[b], ci)
            t = (z - za) / (zb - za) if zb != za else 0.0
            return ys[ia] + (ys[ib] - ys[ia]) * t
        return ys[BASE_ROWS.index(name)]

    def pos(ix, ci, r):
        """Lattice -> world position. ix in 0..6, ci column, r row index."""
        name = ROWS[r]
        b = _base_index(name)
        sx = SIDE_X[b] / 3.9
        x = X_LAT[ix] * sx
        z = row_z(r, ci)
        y = col_y(ci, r, z)
        edge_x = ix in (0, 6)
        if ci == 0 and edge_x:
            y += CORNER_CH[b]
        if ci == nc - 1 and edge_x:
            y -= CORNER_CH[b]
        if ci == 0 and name in FRONT_Z:
            z = FRONT_Z[name]
        if ci == nc - 1 and name in REAR_Z:
            z = REAR_Z[name]
        if r == nr - 1:          # roof crown
            z += ROOF_CROWN * (1 - (x / SIDE_X[b]) ** 2)
        if RIDGES and name in ('U2', 'U3', 'L2', 'L3'):
            upper = name[0] == 'U'
            rs = -1.0 if GROOVE else 1.0
            sgn = 1 if X_LAT[ix] > 0 else -1
            if ci == nc - 1:
                pass                                   # no ridge across the tailgate
            elif ci == 0:
                front_w = 1.0 if upper else (1.0 if ix in (0, 1, 5, 6) else 0.0)
                y -= rs * RIDGE_D_FRONT * front_w
                if edge_x:
                    x += rs * sgn * RIDGE_D * front_w
            elif edge_x:
                w = (0.0 if ci in UPPER_RIDGE_OFF else 1.0) if upper else (1.0 if ci in LOWER_RIDGE_COLS else 0.0)
                x += rs * sgn * RIDGE_D * w
        return V((x, y, z))

    def get(ix, ci, r):
        key = (ix, ci, r)
        if key not in vmap:
            vmap[key] = bd.vert(pos(ix, ci, r))
        return vmap[key]

    open_set = set()
    for (s, c0, c1, r0, r1) in openings():
        for ci in range(c0, c1):
            for r in range(ri[r0], ri[r1]):
                open_set.add(('side', s, ci, r))
    navy = set()
    for (c0, c1, r0, r1) in NAVY_SIDE:
        for ci in range(c0, c1):
            for r in range(ri[r0], ri[r1]):
                navy.add((ci, r))

    P, N = mats['paint'], mats['navy']
    # side faces (x = +/-)
    for s, ix in ((1, 6), (-1, 0)):
        for ci in range(nc - 1):
            for r in range(nr - 1):
                if ('side', s, ci, r) in open_set:
                    continue
                q = [get(ix, ci, r), get(ix, ci + 1, r), get(ix, ci + 1, r + 1), get(ix, ci, r + 1)]
                if s < 0:
                    q = q[::-1]
                bd.face(q, N if (ci, r) in navy else P)
    # front (ci=0) and rear (ci=nc-1) faces
    for ci, flip in ((0, False), (nc - 1, True)):
        for ix in range(6):
            for r in range(nr - 1):
                if 2 <= ix < 4 and ri['r2'] <= r < ri['r3']:
                    continue  # windscreen / tailgate window (ix 2..4)
                q = [get(ix, ci, r), get(ix + 1, ci, r), get(ix + 1, ci, r + 1), get(ix, ci, r + 1)]
                if flip:
                    q = q[::-1]
                m = P
                # wrap the navy band around the front corner chamfer
                if ci == 0 and ix in (0, 5) and ri['r1'] <= r < ri['rs']:
                    m = N
                bd.face(q, m)
    # roof (r = top)
    r = nr - 1
    for ci in range(nc - 1):
        for ix in range(6):
            q = [get(ix, ci, r), get(ix + 1, ci, r), get(ix + 1, ci + 1, r), get(ix, ci + 1, r)]
            bd.face(q, P)
    # orient: roof faces point up
    bd.recalc()
    top = [f for f in bd.bm.faces if f.calc_center_median().z > 9.5]
    if top and sum(f.normal.z for f in top) < 0:
        bd.flip_all()
    # drop verts left floating by the openings (arch bottoms)
    for v in [v for v in bd.bm.verts if not v.link_faces]:
        bd.bm.verts.remove(v)
    return bd, cols


def arch_points(wheel_y, z_min=2.6, n=13, side=1):
    """Points of the arch circle from rear-bottom to front-bottom (for flares)."""
    dy_end = math.sqrt(ARCH_R ** 2 - (z_min - ARCH_CZ) ** 2)
    a_end = math.atan2(z_min - ARCH_CZ, dy_end)
    pts = []
    for k in range(n):
        a = a_end + (math.pi - 2 * a_end) * k / (n - 1)
        pts.append((wheel_y + ARCH_R * math.cos(a), ARCH_CZ + ARCH_R * math.sin(a)))
    return pts
