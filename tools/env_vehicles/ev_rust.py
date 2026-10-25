"""Painted 512 px atlas for the wrecked danfo (B): yellow paint, black stripes, rust and grey primer.

Faces are box-projected into five tiles (left side, right side, front, rear, top), so the paint is
placed in world coordinates and no extra geometry is needed for the damage.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

RES = 512
LY, LX, LZ = 8.6, 4.6, 10.6          # half length / half width / height covered by the tiles
TILES = {  # name: (u0, v0, u1, v1) in UV space (v up)
    'L': (0.0, 0.625, 1.0, 1.0), 'R': (0.0, 0.25, 1.0, 0.625),
    'F': (0.0, 0.0, 0.333, 0.25), 'B': (0.333, 0.0, 0.666, 0.25), 'T': (0.666, 0.0, 1.0, 0.25),
}
YELLOW, BLACK = (242, 183, 5), (30, 30, 34)
RUST, RUST_D, PRIMER, PRIMER_D = (154, 78, 35), (104, 52, 24), (167, 169, 171), (128, 131, 134)


def tile_uv(name, a, b):
    """a, b in 0..1 within a tile -> atlas uv."""
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


def to_px(name, a, b):
    u, v = tile_uv(name, a, b)
    return (u * RES, (1 - v) * RES)


def side(name, y, z):
    return to_px(name, (y + LY) / (2 * LY), z / LZ)


def front(name, x, z):
    return to_px(name, (x + LX) / (2 * LX), z / LZ)


def top(y, x):
    return to_px('T', (y + LY) / (2 * LY), (x + LX) / (2 * LX))


def blob(d, rnd, mapper, cx, cy, r, col, n=9, squash=1.0):
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n + rnd.uniform(-0.25, 0.25)
        rr = r * rnd.uniform(0.55, 1.15)
        pts.append(mapper(cx + math.cos(t) * rr, cy + math.sin(t) * rr * squash))
    d.polygon(pts, fill=col)


def rust_patch(d, rnd, mapper, cx, cy, r, primer=False):
    """Primer/rust patch: lighter halo, darker core, the way paint flakes in the concept."""
    if primer:
        blob(d, rnd, mapper, cx, cy, r * 1.25, PRIMER, 11)
    blob(d, rnd, mapper, cx, cy, r, RUST, 10)
    blob(d, rnd, mapper, cx + rnd.uniform(-0.2, 0.2) * r, cy + rnd.uniform(-0.2, 0.2) * r, r * 0.5, RUST_D, 8)


def paint(path, stripes=((3.9, 4.15), (4.35, 4.6)), stripe_y=(-7.45, 7.55)):
    rnd = random.Random(11)
    img = Image.new('RGB', (RES, RES), YELLOW)
    d = ImageDraw.Draw(img)
    for s in 'LR':
        mp = lambda y, z, s=s: side(s, y, z)
        for z0, z1 in stripes:
            d.polygon([mp(stripe_y[0], z0), mp(stripe_y[1], z0), mp(stripe_y[1], z1), mp(stripe_y[0], z1)], fill=BLACK)
        # front corner and nose in grey primer (crash repair), door-gap primer edge at the B pillar
        d.polygon([mp(-8.7, 1.4), mp(-6.9, 1.4), mp(-6.6, 2.6), mp(-7.3, 4.4), mp(-7.0, 5.1), mp(-8.7, 5.4)], fill=PRIMER)
        d.polygon([mp(-8.7, 7.9), mp(-6.4, 8.1), mp(-5.6, 9.0), mp(-8.7, 9.6)], fill=PRIMER)
        d.polygon([mp(-4.35, 1.6), mp(-3.95, 1.6), mp(-3.95, 8.0), mp(-4.35, 8.0)], fill=PRIMER_D)
        for (y, z, r, pr) in ((-6.7, 3.9, 0.7, False), (-2.6, 2.3, 0.75, False), (-0.6, 5.6, 0.55, False),
                              (1.6, 3.2, 0.9, True), (2.8, 7.4, 0.6, False), (3.4, 2.1, 0.6, False),
                              (6.9, 3.8, 0.85, False), (7.3, 6.6, 0.7, True), (-5.6, 8.3, 0.5, False),
                              (0.4, 8.5, 0.45, False), (5.2, 8.4, 0.55, False), (-1.8, 4.1, 0.4, False)):
            jy, jz = (rnd.uniform(-0.6, 0.6), rnd.uniform(-0.3, 0.3)) if s == 'R' else (0, 0)
            rust_patch(d, rnd, mp, y + jy, z + jz, r, pr)
    # nose: mostly primer with rust and dark crumple creases
    mf = lambda x, z: front('F', x, z)
    d.polygon([mf(-4.6, 1.4), mf(4.6, 1.4), mf(4.6, 6.0), mf(-4.6, 6.0)], fill=PRIMER)
    for x, z, r in ((-2.8, 2.4, 0.8), (1.5, 2.2, 0.7), (3.4, 4.6, 0.75), (-1.0, 4.9, 0.6), (0.4, 3.6, 0.5)):
        rust_patch(d, rnd, mf, x, z, r)
    for x0, z0, x1, z1 in ((-3.8, 4.2, -0.5, 3.7), (0.8, 4.4, 3.7, 3.9), (-3.5, 2.1, 3.2, 2.5)):
        d.line([mf(x0, z0), mf(x1, z1)], fill=PRIMER_D, width=3)
    mb = lambda x, z: front('B', x, z)
    for x, z, r in ((-2.6, 2.6, 0.7), (2.2, 4.8, 0.6), (0.8, 7.6, 0.5), (-3.2, 6.4, 0.45)):
        rust_patch(d, rnd, mb, x, z, r)
    for y, x, r in ((-6.4, 2.6, 0.8), (-5.5, -2.4, 0.6), (-1.0, 3.0, 0.5), (2.6, -2.8, 0.7), (5.8, 1.4, 0.55),
                    (6.6, -3.2, 0.5), (0.6, 0.4, 0.4)):
        rust_patch(d, rnd, top, y, x, r)
    img = img.filter(ImageFilter.SMOOTH)
    img.save(path)
    return path
