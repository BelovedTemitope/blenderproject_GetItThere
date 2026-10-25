"""fSpy-style camera from vanishing points (what the fSpy app + Blender add-on compute), headless.

    python ev_vpcam.py <lines.json> <work_dir> <cams.json> <key> [--pp image|crop]

lines.json: {key: {"length": [[x0,y0,x1,y1], ...],   # edges parallel to the vehicle's length (world Y)
                   "width":  [[...], ...]}}          # edges parallel to its width (world X)
Concept-pixel coordinates. Two orthogonal vanishing points + a principal point give the focal length
and the rotation (fSpy's 2-VP mode); only the distance and ground offset are then fitted to the silhouette.
"""
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import minimize

import ev_fitcam as F

IMG = (1343, 749)


def vanishing_point(segs):
    L = []
    for x0, y0, x1, y1 in segs:
        l = np.cross([x0, y0, 1.0], [x1, y1, 1.0])
        L.append(l / np.linalg.norm(l[:2]))
    _, _, vt = np.linalg.svd(np.array(L))
    v = vt[-1]
    return v[:2] / v[2]


def solve(segs_len, segs_wid, pp):
    v1, v2 = vanishing_point(segs_len), vanishing_point(segs_wid)
    p = np.array(pp, float)
    f2 = -np.dot(v1 - p, v2 - p)
    if f2 <= 0:
        raise ValueError('vanishing points not compatible with an orthogonal pair for this principal point')
    f = math.sqrt(f2)
    d1 = np.array([v1[0] - p[0], -(v1[1] - p[1]), -f]); d1 /= np.linalg.norm(d1)
    d2 = np.array([v2[0] - p[0], -(v2[1] - p[1]), -f]); d2 /= np.linalg.norm(d2)
    # world +Y = vehicle rear; we see the front face, so +Y points away from the camera (camera z < 0)
    rY = d1 if d1[2] < 0 else -d1
    # world +X = vehicle left side, which faces the camera (camera z > 0)
    rX = d2 if d2[2] > 0 else -d2
    rX = rX - rY * np.dot(rX, rY); rX /= np.linalg.norm(rX)
    rZ = np.cross(rX, rY)
    M = np.stack([rX, rY, rZ], 1)                 # world -> camera
    fwd = M.T @ np.array([0, 0, -1.0])
    d = -fwd
    el = math.asin(d[2])
    az = math.atan2(d[0], -d[1])
    roll = math.degrees(math.atan2(rZ[0], rZ[1]))
    return dict(v1=v1.tolist(), v2=v2.tolist(), f=f, az=az, el=el, roll=roll, up_ok=bool(rZ[1] > 0))


def main():
    lines, wd, store, key = sys.argv[1:5]
    mode = sys.argv[sys.argv.index('--pp') + 1] if '--pp' in sys.argv else 'image'
    L = json.load(open(lines))[key]
    tris = np.load(os.path.join(wd, 'tris_%s.npy' % key))
    mask = np.load(os.path.join(wd, 'mask_%s.npy' % key))
    cams = json.load(open(store))
    box = cams[key]['box']
    if mode == 'image':
        pp = (IMG[0] / 2, IMG[1] / 2)
    else:
        ys, xs = np.nonzero(mask)
        pp = (xs.mean(), ys.mean())
    r = solve(L['length'], L['width'], pp)
    print('VP %s pp=%s f=%.0f az=%.1f el=%.1f roll=%.1f up_ok=%s v1=(%.0f,%.0f) v2=(%.0f,%.0f)' % (
        key, mode, r['f'], math.degrees(r['az']), math.degrees(r['el']), r['roll'], r['up_ok'], *r['v1'], *r['v2']))

    def unpack(z):
        dist, ox, oy = 40 + z[0] * 5, z[1], z[2]
        return np.array([r['az'], r['el'], dist, r['f'], pp[0], pp[1]]), np.array([ox, oy, 0.0])

    def score(z):
        p, off = unpack(z)
        return -F.iou(tris + off, mask, p, box)[0]
    best, bs = None, 1
    for d0 in (-4, -2, 0, 2, 4, 8):
        for ox in (-20, -10, 0, 10, 20):
            for oy in (-20, -10, 0, 10, 20):
                s = score([d0, ox, oy])
                if s < bs:
                    best, bs = np.array([d0, ox, oy], float), s
    for _ in range(3):
        res = minimize(score, best, method='Nelder-Mead',
                       options=dict(maxiter=800, initial_simplex=np.vstack([best, best + np.eye(3) * 2])))
        best = res.x
    p, off = unpack(best)
    s = -score(best)
    cams[key + '_vp'] = dict(p=[float(v) for v in p], off=[float(off[0]), float(off[1])], box=box, iou=float(s),
                             vp=r)
    json.dump(cams, open(store, 'w'), indent=1)
    print('VPFIT %s iou=%.3f dist=%.1f off=(%.1f, %.1f)' % (key, s, p[2], off[0], off[1]))


if __name__ == '__main__':
    main()
