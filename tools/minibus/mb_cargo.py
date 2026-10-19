"""Roof cargo: duffels, plaid bags, bedroll, hard case, jerrycans - all resting on the rack bars."""
import math

from mathutils import Matrix, Vector as V

import mb_lib as L


def duffel(bd, c, length, dia, h, mats, straps=True, handle=True, axis='Y'):
    """Soft bag lying along an axis with a flattened bottom resting at c.z."""
    BODY, STRAP = mats
    rr = dia / 2
    hl = length / 2
    prof = [(0.28 * rr, -hl), (0.72 * rr, -hl + 0.05), (0.94 * rr, -hl + 0.16), (rr, -hl + 0.34),
            (rr, hl - 0.34), (0.94 * rr, hl - 0.16), (0.72 * rr, hl - 0.05), (0.28 * rr, hl)]
    if L.LOD:
        prof = [(0.3 * rr, -hl), (0.85 * rr, -hl + 0.1), (rr, -hl + 0.34),
                (rr, hl - 0.34), (0.85 * rr, hl - 0.1), (0.3 * rr, hl)]
        straps = False            # straps go to the texture on the game load
    sz = h / dia
    flat = -0.4 * h

    def shape(v):
        z = v.z * sz
        if z < flat:
            z = flat + (z - flat) * 0.12
        return V((v.x, v.y, z))
    start = len(bd.bm.verts)
    L.lathe(bd, prof, 12, BODY, V(), 'Y', True, True)
    body_verts = bd.bm.verts[start:] if False else list(bd.bm.verts)[start:]
    for v in body_verts:
        v.co = shape(v.co)
    parts = [body_verts]
    if straps:
        for a in (-0.22 * length, 0.22 * length):
            s0 = len(bd.bm.verts)
            L.lathe(bd, [(rr - 0.02, a - 0.07), (rr + 0.03, a - 0.07), (rr + 0.03, a + 0.07), (rr - 0.02, a + 0.07)],
                    12, STRAP, V(), 'Y', False, False)
            vs = list(bd.bm.verts)[s0:]
            first = vs[:L.lod_sides(12)]
            last = vs[-L.lod_sides(12):]
            bd.strip(last, first, STRAP, True)
            for v in vs:
                v.co = shape(v.co)
            parts.append(vs)
    if handle:
        top = rr * sz
        a = 0.22 * length
        s0 = len(bd.bm.verts)
        L.tube(bd, [(0, -a, top - 0.03), (0, -a * 0.7, top + 0.24), (0, a * 0.7, top + 0.24), (0, a, top - 0.03)], 0.04,
               6, STRAP, fillet=0.12, caps=True)
        parts.append(list(bd.bm.verts)[s0:])
    m = Matrix.Translation(V(c) + V((0, 0, -flat)))
    if axis == 'X':
        m = m @ Matrix.Rotation(math.pi / 2, 4, 'Z')
    for vs in parts:
        for v in vs:
            v.co = m @ v.co
    return rr * sz - flat


def jerrycan(bd, c, yaw=0.0):
    BODY, CAP = 0, 1
    w, t, h = 1.25, 0.6, 1.35
    m = Matrix.Translation(V(c) + V((0, 0, h / 2))) @ Matrix.Rotation(yaw, 4, 'Z')
    L.rbox(bd, (w, t, h), 0.07, 1, (2, 0, 2), BODY, m)
    # embossed X panels (raised slightly on both faces)
    for s in (1, -1):
        for dx in (-0.3, 0.3):
            if L.OPTIMIZE:
                # pressed panel: just the raised face and its four walls, standing on the can side
                L.rbox(bd, (0.44, 0.03, 0.9), 0.0, 1, (0, 0, 0), BODY, m @ Matrix.Translation((dx, s * (t / 2 + 0.005), -0.05)))
            else:
                L.rbox(bd, (0.44, 0.04, 0.9), 0.02, 1, (0, 0, 0), BODY, m @ Matrix.Translation((dx, s * t / 2, -0.05)))
    # three-bar handle across the top
    top = h / 2
    L.tube(bd, [m @ V((-0.42, 0, top + 0.16)), m @ V((0.3, 0, top + 0.16))], 0.045, 6, BODY, caps=True)
    for dx in (-0.4, -0.05, 0.28):
        L.tube(bd, [m @ V((dx, 0, top - 0.04)), m @ V((dx, 0, top + 0.18))], 0.04, 6, BODY, caps=True)
    # spout + cap on the free corner
    s0 = len(bd.bm.verts)
    L.lathe(bd, [(0.1, -0.05), (0.1, 0.12), (0.12, 0.12), (0.12, 0.24)], 8, CAP, V(), 'Z', True, True)
    ms = m @ Matrix.Translation((0.47, 0, top - 0.02)) @ Matrix.Rotation(math.radians(30), 4, 'Y')
    for v in list(bd.bm.verts)[s0:]:
        v.co = ms @ v.co
    return h


def hard_case(bd, c, size):
    BODY, BLACK, METAL = 0, 1, 2
    sx, sy, sz = size
    m = Matrix.Translation(V(c) + V((0, 0, sz / 2)))
    L.rbox(bd, size, 0.08, 1, (1, 2, 1), BODY, m)
    L.rbox(bd, (sx + 0.03, sy + 0.03, 0.06), 0.02, 1, (1, 2, 0), BLACK, m @ Matrix.Translation((0, 0, sz * 0.2)))
    for dy in (-sy * 0.3, sy * 0.3):
        L.rbox(bd, (0.05, 0.16, 0.2), 0.015, 1, (0, 0, 0), METAL, m @ Matrix.Translation((sx / 2 + 0.03, dy, sz * 0.2)))
    L.tube(bd, [m @ V((0, -0.3, sz / 2 - 0.03)), m @ V((0, -0.22, sz / 2 + 0.14)), m @ V((0, 0.22, sz / 2 + 0.14)),
                m @ V((0, 0.3, sz / 2 - 0.03))], 0.04, 6, BLACK, fillet=0.08, caps=True)
    return sz


def build(ctx):
    base = getattr(ctx, 'rack_top', 10.24)
    tops = {}

    def put(name, fn, mats):
        bd = L.Builder()
        top = fn(bd)
        ctx.obj('Cargo_' + name, bd, 'Cargo', mats)
        return top

    tops['crate'] = put('Crate_Red', lambda bd: hard_case(bd, (-1.38, -0.5, base), (1.25, 2.8, 0.72)),
                        ['bag_red', 'black', 'metal'])
    tops['bundle'] = put('Bundle_Grey', lambda bd: duffel(bd, (-0.15, -0.3, base), 2.4, 0.95, 0.68, (0, 1), True, False),
                         ['canvas', 'strap'])
    tops['purple'] = put('Duffel_Purple',
                         lambda bd: duffel(bd, (1.15, -0.58, base), 2.85, 1.29, 0.8, (0, 1)), ['bag_purple', 'strap'])
    stack = base + max(tops['crate'], tops['bundle'])
    put('Duffel_NavyTop', lambda bd: duffel(bd, (-0.32, -0.3, stack - 0.04), 3.0, 1.55, 0.95, (0, 1)),
        ['bag_navy', 'strap'])
    put('Duffel_NavyB', lambda bd: duffel(bd, (-0.35, 2.65, base), 2.7, 1.2, 0.8, (0, 1)), ['bag_navy', 'strap'])
    put('Plaid_A', lambda bd: duffel(bd, (-1.78, 2.72, base), 2.75, 1.34, 0.92, (0, 1)), ['plaid', 'strap'])
    put('Plaid_B', lambda bd: duffel(bd, (1.08, 2.82, base), 2.75, 1.43, 0.92, (0, 1)), ['plaid', 'strap'])
    put('Jerrycan_A', lambda bd: jerrycan(bd, (-0.9, 4.68, base)), ['jerry', 'black'])
    put('Jerrycan_B', lambda bd: jerrycan(bd, (1.1, 4.68, base), math.pi), ['jerry', 'black'])
