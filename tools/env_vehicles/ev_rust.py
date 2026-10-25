"""Painted atlas for the wrecked danfo (B): yellow paint, black stripes, flaking rust and grey primer.

Faces are box-projected into five tiles (left side, right side, front, rear, top); each tile pixel
knows its world position, so the damage is placed where it happens on a real wreck: rust grows from
the sills, wheel-arch lips, window corners, roof gutter and door seams with ragged (noise) edges, and
the crash-repaired nose, front corners and B pillar are bare grey primer. No extra geometry needed.
"""
import math

import numpy as np
from PIL import Image

RES = 1024
LY, LX, LZ = 8.6, 4.6, 10.6
TILES = {
    'L': (0.0, 0.625, 1.0, 1.0), 'R': (0.0, 0.25, 1.0, 0.625),
    'F': (0.0, 0.0, 0.333, 0.25), 'B': (0.333, 0.0, 0.666, 0.25), 'T': (0.666, 0.0, 1.0, 0.25),
}
YELLOW = np.array((242, 183, 5), float)
YELLOW_D = np.array((214, 156, 10), float)
BLACK = np.array((30, 30, 34), float)
RUST = np.array((176, 90, 38), float)
RUST_D = np.array((118, 57, 26), float)
PRIMER = np.array((167, 169, 171), float)
PRIMER_D = np.array((126, 129, 132), float)


def tile_uv(name, a, b):
    u0, v0, u1, v1 = TILES[name]
    return (u0 + a * (u1 - u0), v0 + b * (v1 - v0))


def tile_of(n, co, c=None):
    """Tile by the face's dominant normal axis; side of the body by the face centre (robust to flipped faces)."""
    ax = max(range(3), key=lambda i: abs(n[i]))
    x, y, z = co
    c = c if c is not None else co
    if ax == 0:
        return tile_uv('L' if c[0] > 0 else 'R', (y + LY) / (2 * LY), z / LZ)
    if ax == 1:
        return tile_uv('F' if c[1] < 0 else 'B', (x + LX) / (2 * LX), z / LZ)
    return tile_uv('T', (y + LY) / (2 * LY), (x + LX) / (2 * LX))


def fractal(shape, seed, octaves=5, base=6):
    """Smooth value noise in 0..1 (sum of upsampled random grids)."""
    rng = np.random.default_rng(seed)
    h, w = shape
    out = np.zeros(shape)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((n + 1, int(n * w / h) + 2))
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(img, float) / 255.0
        tot += amp
        amp *= 0.5
    return out / tot


def tile_grid(name):
    """World coordinates (a: along, b: up/across) for every pixel of a tile, plus the pixel slice."""
    u0, v0, u1, v1 = TILES[name]
    x0, x1 = int(round(u0 * RES)), int(round(u1 * RES))
    y0, y1 = int(round((1 - v1) * RES)), int(round((1 - v0) * RES))
    a = (np.arange(x0, x1) + 0.5) / RES
    b = 1 - (np.arange(y0, y1) + 0.5) / RES
    A, B = np.meshgrid((a - u0) / (u1 - u0), (b - v0) / (v1 - v0))
    return (slice(y0, y1), slice(x0, x1)), A, B


def soft(d, w):
    return np.exp(-np.maximum(d, 0) / w)


def paint(path, stripes=((3.95, 4.2), (4.4, 4.65)), stripe_y=(-7.45, 7.55), wheels=(-4.85, 4.75), arch_r=1.95,
          z0=1.6, belt=4.95, win_top=7.8, gutter=8.35, windows=((-7.6, -4.2), (-3.2, 2.2), (3.2, 6.4)),
          primer_front=-6.7, b_pillar=(-4.35, -3.95)):
    img = np.zeros((RES, RES, 3)) + YELLOW
    # sides ---------------------------------------------------------------
    for s, seed in (('L', 3), ('R', 7)):
        sl, A, B = tile_grid(s)
        y = A * 2 * LY - LY
        z = B * LZ
        col = np.zeros(A.shape + (3,)) + YELLOW
        col[(z > belt) & (z < win_top)] = YELLOW_D * 0.15 + YELLOW * 0.85      # slight tone change above the belt
        for za, zb in stripes:
            m = (z > za) & (z < zb) & (y > stripe_y[0]) & (y < stripe_y[1])
            col[m] = BLACK
        nz = fractal(A.shape, seed, octaves=4, base=3)                          # patch shapes
        nz2 = fractal(A.shape, seed + 11, octaves=4, base=10)                   # ragged edges / tone
        bias = 0.5 * soft(z - z0, 0.7)                                           # sills
        for wy in wheels:
            d = np.abs(np.hypot(y - wy, (z - z0) * 0.95) - arch_r)
            bias = np.maximum(bias, 0.55 * soft(d, 0.7) * (z > z0))             # arch lips
        for ya, yb in windows:
            near = ((y > ya - 0.8) & (y < yb + 0.8) & (z > belt - 1.0) & (z < win_top + 0.8))
            dc = np.minimum.reduce([np.hypot(y - ya, z - belt), np.hypot(y - yb, z - belt),
                                    np.hypot(y - ya, z - win_top), np.hypot(y - yb, z - win_top)])
            bias = np.maximum(bias, near * 0.6 * soft(dc - 0.3, 0.8))           # window corners
        bias = np.maximum(bias, 0.4 * soft(np.abs(z - gutter), 0.45))            # roof gutter
        for sy in (b_pillar[0], 2.7):
            bias = np.maximum(bias, 0.35 * soft(np.abs(y - sy), 0.45) * (z < belt))  # door seams
        p = bias * (0.45 + 0.9 * nz) + 0.5 * nz + 0.18 * nz2 - 0.66
        # primer: nose corner (ragged edge) and the B pillar repair
        prim = (y + (nz2 - 0.5) * 1.6 < primer_front) | ((y > b_pillar[0]) & (y < b_pillar[1]) & (z > z0 + 0.1))
        if s == 'L':                                                            # door-panel filler patch
            prim |= ((y > -3.0 + (nz2 - 0.5) * 0.9) & (y < -1.1 + (nz2 - 0.5) * 0.9) & (z > 2.1 + (nz - 0.5) * 0.8)
                     & (z < 3.5 + (nz2 - 0.5) * 1.0))
        col[prim] = PRIMER * (0.92 + 0.12 * nz2[prim, None])
        rust = p > 0.0
        core = p > 0.2
        col[rust] = RUST * (0.9 + 0.25 * nz2[rust, None])
        col[core] = RUST_D * (0.9 + 0.25 * nz2[core, None])
        edge = rust & ~core & (p < 0.035)
        col[edge] = col[edge] * 0.6 + PRIMER_D * 0.4                             # flaked edge shows primer
        img[sl] = col
    # nose: bare primer, crumple creases, rust in the folds ---------------
    sl, A, B = tile_grid('F')
    x = A * 2 * LX - LX
    z = B * LZ
    nz = fractal(A.shape, 21)
    col = np.zeros(A.shape + (3,)) + YELLOW
    nose = z < 6.0 + (nz - 0.5)
    col[nose] = PRIMER * (0.9 + 0.15 * nz[nose, None])
    # crushed grille band with bent slats, one cracked headlamp, one empty socket
    grille = (np.abs(x) < 3.25) & (z > 3.15 + 0.15 * np.sin(x * 1.7)) & (z < 3.95 + 0.12 * np.sin(x * 2.3 + 1))
    col[grille] = BLACK * 1.2
    for zz in (3.35, 3.55, 3.75):
        slat = grille & (np.abs(z - zz - 0.12 * np.sin(x * 2.6 + zz * 7)) < 0.045)
        col[slat] = PRIMER_D * 0.8
    lamp = (x > 2.55) & (x < 3.3) & (z > 3.2) & (z < 3.85)
    col[lamp] = np.array((215, 214, 205), float)
    col[lamp & (np.abs((x - 2.9) * 1.3 - (z - 3.5)) < 0.04)] = BLACK
    col[(x < -2.55) & (x > -3.3) & (z > 3.2) & (z < 3.85)] = BLACK * 0.7
    nc = fractal(A.shape, 23, octaves=3, base=4)
    crease = (np.abs(nc - 0.5) < 0.012) & nose                               # crumple folds follow noise contours
    col[crease] = PRIMER_D * 0.85
    nzl = fractal(A.shape, 25, octaves=4, base=3)
    p = 0.45 * soft(z - 1.7, 0.8) * (0.5 + nzl) + 0.5 * nzl - 0.55
    rust = (p > 0.0) & nose
    col[rust] = RUST * (0.9 + 0.2 * nz[rust, None])
    col[(p > 0.12) & nose] = RUST_D
    img[sl] = col
    # rear + roof ------------------------------------------------------------
    for t, seed in (('B', 31), ('T', 41)):
        sl, A, B = tile_grid(t)
        nz = fractal(A.shape, seed, octaves=4, base=3)
        col = np.zeros(A.shape + (3,)) + YELLOW
        if t == 'B':
            z = B * LZ
            bias = 0.55 * soft(z - 1.7, 0.6) + 0.35 * soft(np.abs(z - belt), 0.3)
        else:
            yy = A * 2 * LY - LY
            xx = B * 2 * LX - LX
            bias = 0.45 * soft(np.abs(np.abs(xx) - 3.3), 0.35) + 0.5 * soft(yy + 7.0, 0.8)
            prim = yy + (nz - 0.5) * 1.5 < -6.4
            col[prim] = PRIMER
        p = bias * (0.45 + 0.9 * nz) + 0.5 * nz - 0.6
        col[p > 0.0] = RUST
        col[p > 0.13] = RUST_D
        img[sl] = col
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path)
    return path
