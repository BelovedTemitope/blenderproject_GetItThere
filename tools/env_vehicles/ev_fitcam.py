"""Fit a perspective camera so a vehicle's silhouette matches its concept mask.

    python ev_fitcam.py <tris.npy> <mask.npy> <key> <cams.json> [--fix]   (--fix: keep the stored camera, just score)

Camera: looks at the vehicle origin (+ small target height) from azimuth/elevation/distance,
focal length in pixels, and the image point (px, py) where that target lands.
"""
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import minimize

TARGET_Z = 4.0


def cam_axes(az, el, dist):
    d = np.array([math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)])
    T = np.array([0, 0, TARGET_Z])
    C = T + d * dist
    f = (T - C) / np.linalg.norm(T - C)
    r = np.cross(f, [0, 0, 1]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return C, r, u, f


def project(tris, p):
    az, el, dist, F, px, py = p
    C, r, u, f = cam_axes(az, el, dist)
    q = tris.reshape(-1, 3) - C
    zc = q @ f
    x = px + F * (q @ r) / zc
    y = py - F * (q @ u) / zc
    return np.stack([x, y], 1).reshape(-1, 3, 2)


def raster(tris2d, shape):
    img = Image.new('1', (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(img)
    for t in tris2d:
        d.polygon([tuple(v) for v in t], fill=1)
    return np.array(img, bool)


def iou(tris, mask, p, box):
    y0, y1, x0, x1 = box
    t2 = project(tris, p) - [x0, y0]
    m = raster(t2, (y1 - y0, x1 - x0))
    ref = mask[y0:y1, x0:x1]
    inter = (m & ref).sum()
    return inter / max(1, (m | ref).sum()), m


import os
EL_RANGE = tuple(math.radians(float(v)) for v in os.environ.get('EV_EL', '16,30').split(','))


def clamp(p):
    p = np.array(p, float)
    p[1] = min(max(p[1], EL_RANGE[0]), EL_RANGE[1])
    return p


def main():
    tris = np.load(sys.argv[1])
    mask = np.load(sys.argv[2])
    key, store = sys.argv[3], sys.argv[4]
    ys, xs = np.nonzero(mask)
    box = (max(0, ys.min() - 40), min(mask.shape[0], ys.max() + 40), max(0, xs.min() - 40), min(mask.shape[1], xs.max() + 40))
    try:
        cams = json.load(open(store))
    except Exception:
        cams = {}
    if '--fix' in sys.argv and key in cams:
        best = np.array(cams[key]['p'])
    else:
        cx, cy = xs.mean(), ys.mean()
        span = xs.max() - xs.min()
        best, bs = None, -1
        for az in np.radians([30, 40, 50, 60, 70]):
            for el in np.radians([16, 22, 28]):
                for dist in (45, 80, 140):
                    p0 = np.array([az, el, dist, 0, cx, cy])
                    p0[3] = span / 24.0 * dist          # rough: ~24 studs of vehicle across `span` px
                    s, _ = iou(tris, mask, p0, box)
                    if s > bs:
                        best, bs = p0, s
        scale = np.array([0.05, 0.05, 5.0, 50.0, 3.0, 3.0])
        for _ in range(3):
            res = minimize(lambda z: -iou(tris, mask, clamp(best + z * scale), box)[0], np.zeros(6), method='Nelder-Mead',
                           options=dict(maxiter=600, xatol=1e-3, fatol=1e-5,
                                                initial_simplex=np.vstack([np.zeros(6), np.eye(6)])))
            best = clamp(best + res.x * scale)
    s, m = iou(tris, mask, best, box)
    cams[key] = dict(p=[float(v) for v in best], off=[0.0, 0.0], iou=float(s), box=[int(v) for v in box])
    json.dump(cams, open(store, 'w'), indent=1)
    print('FIT %s iou=%.3f az=%.1f el=%.1f dist=%.1f F=%.0f px=%.1f py=%.1f' % (
        key, s, math.degrees(best[0]), math.degrees(best[1]), best[2], best[3], best[4], best[5]))


if __name__ == '__main__':
    main()
