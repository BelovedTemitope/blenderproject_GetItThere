"""Fit ONE camera to the whole concept lineup: shared camera, each vehicle placed on the ground.

    python ev_fitjoint.py <work_dir> <cams.json> A B [C D]   (reads tris_<k>.npy and mask_<k>.npy)

The first key is the reference (camera looks at it); the others get a ground offset (dx, dy).
Writes per-vehicle entries {p, off, box, iou} used by ev_overlay.py and ev_render.py.
"""
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import minimize

import ev_fitcam as F


def main():
    wd, store, keys = sys.argv[1], sys.argv[2], sys.argv[3:]
    tris = {k: np.load(os.path.join(wd, 'tris_%s.npy' % k)) for k in keys}
    masks = {k: np.load(os.path.join(wd, 'mask_%s.npy' % k)) for k in keys}
    boxes = {}
    for k in keys:
        ys, xs = np.nonzero(masks[k])
        boxes[k] = (max(0, ys.min() - 40), min(masks[k].shape[0], ys.max() + 40),
                    max(0, xs.min() - 40), min(masks[k].shape[1], xs.max() + 40))
    try:
        cams = json.load(open(store))
    except Exception:
        cams = {}
    ref = keys[0]
    p0 = np.array(cams[ref]['p'], float) if ref in cams else np.array([math.radians(44), math.radians(16), 37, 660, 200, 195])
    # initial offsets: place each vehicle so its mask centroid lines up (rough: 1 px ~ dist/F studs)
    offs0 = []
    for k in keys[1:]:
        if k in cams and 'off' in cams[k] and cams[k].get('iou', 0) > 0.5:
            offs0 += cams[k]['off']
            continue
        # coarse search on the ground for where this vehicle sits with the current camera
        best, bs = (0.0, 0.0), -1
        for dx in np.arange(-10, 60, 2.0):
            for dy in np.arange(-10, 60, 2.0):
                sc = F.iou(tris[k] + [dx, dy, 0], masks[k], p0, boxes[k])[0]
                if sc > bs:
                    best, bs = (dx, dy), sc
        offs0 += list(best)
    x0 = np.concatenate([p0, offs0])
    scale = np.concatenate([[0.04, 0.04, 4.0, 40.0, 3.0, 3.0], [2.0] * (2 * (len(keys) - 1))])

    def unpack(z):
        x = x0 + z * scale
        offs = {ref: np.zeros(3)}
        for i, k in enumerate(keys[1:]):
            offs[k] = np.array([x[6 + 2 * i], x[7 + 2 * i], 0.0])
        return x[:6], offs

    def score(z):
        p, offs = unpack(z)
        return -np.mean([F.iou(tris[k] + offs[k], masks[k], p, boxes[k])[0] for k in keys])

    best = np.zeros_like(x0)
    for _ in range(4):
        r = minimize(score, best, method='Nelder-Mead',
                     options=dict(maxiter=1500, initial_simplex=np.vstack([best, best + np.eye(len(x0))])))
        best = r.x
    p, offs = unpack(best)
    for k in keys:
        s = F.iou(tris[k] + offs[k], masks[k], p, boxes[k])[0]
        cams[k] = dict(p=[float(v) for v in p], off=[float(offs[k][0]), float(offs[k][1])],
                       box=[int(v) for v in boxes[k]], iou=float(s))
        print('JOINT %s iou=%.3f off=(%.1f, %.1f)' % (k, s, offs[k][0], offs[k][1]))
    print('CAMERA az=%.1f el=%.1f dist=%.1f F=%.0f' % (math.degrees(p[0]), math.degrees(p[1]), p[2], p[3]))
    json.dump(cams, open(store, 'w'), indent=1)


if __name__ == '__main__':
    main()
