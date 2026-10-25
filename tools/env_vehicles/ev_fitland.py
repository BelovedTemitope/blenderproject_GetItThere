"""Landmark-aware camera refinement: silhouette + dark + glass regions, from the current camera.

    python ev_fitland.py <work_dir> <concept.webp> <cams.json> <key>
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import minimize

import ev_fitcam as F
from ev_landmarks import classify

W = {0: 0.5, 2: 0.25, 3: 0.25}           # silhouette, dark, grey


def raster_cls(t2, cls, depth, shape):
    img = Image.new('L', (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(img)
    for i in np.argsort(-depth):
        d.polygon([tuple(v) for v in t2[i]], fill=int(cls[i]))
    return np.array(img)


def depths(tris, p):
    az, el, dist = p[:3]
    C, r, u, f = F.cam_axes(az, el, dist)
    return ((tris.mean(1) - C) @ f)


def score(tris, cls, ref, mask, p, box):
    y0, y1, x0, x1 = box
    t2 = F.project(tris, p) - [x0, y0]
    m = raster_cls(t2, cls, depths(tris, p), (y1 - y0, x1 - x0))
    sil = (m > 0)
    out = {0: (sil & mask).sum() / max(1, (sil | mask).sum())}
    for c in (2, 3):
        a, b = ref == c, m == c
        out[c] = (a & b).sum() / max(1, (a | b).sum())
    return sum(W[k] * v for k, v in out.items()), out


def main():
    wd, src, store, key = sys.argv[1:5]
    tris = np.load(os.path.join(wd, 'tris_%s.npy' % key))
    cls = np.load(os.path.join(wd, 'cls_%s.npy' % key))
    mask_full = np.load(os.path.join(wd, 'mask_%s.npy' % key))
    cams = json.load(open(store))
    cam = cams[key]
    box = cam['box']
    y0, y1, x0, x1 = box
    ref = classify(np.array(Image.open(src).convert('RGB'))[y0:y1, x0:x1])
    mask = mask_full[y0:y1, x0:x1]
    ref[~mask] = 0
    p0 = np.array(cam['p'], float)
    sc0, parts0 = score(tris, cls, ref, mask, p0, box)
    scale = np.array([0.03, 0.03, 3.0, 30.0, 2.0, 2.0])
    best = np.zeros(6)
    for _ in range(3):
        r = minimize(lambda z: -score(tris, cls, ref, mask, p0 + z * scale, box)[0], best, method='Nelder-Mead',
                     options=dict(maxiter=500, initial_simplex=np.vstack([best, best + np.eye(6)])))
        best = r.x
    p = p0 + best * scale
    sc, parts = score(tris, cls, ref, mask, p, box)
    cam['p'] = [float(v) for v in p]
    cam['land'] = {str(k): float(v) for k, v in parts.items()}
    json.dump(cams, open(store, 'w'), indent=1)
    print('LAND %s %.3f -> %.3f  sil=%.3f dark=%.3f grey=%.3f  az=%.1f el=%.1f' % (
        key, sc0, sc, parts[0], parts[2], parts[3], math.degrees(p[0]), math.degrees(p[1])))


if __name__ == '__main__':
    main()
