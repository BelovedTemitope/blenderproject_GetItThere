"""Proportions implied by the fSpy-style camera: keep its rotation + focal length, fit distance, offset and
the model's length / height scale (width fixed) to the concept silhouette.

    python ev_vpprop.py <work_dir> <cams.json> <key>        (uses cams[key + '_vp'])
"""
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import minimize

import ev_fitcam as F

wd, store, key = sys.argv[1:4]
tris = np.load(os.path.join(wd, 'tris_%s.npy' % key))
mask = np.load(os.path.join(wd, 'mask_%s.npy' % key))
cam = json.load(open(store))[key + '_vp']
p0, off0, box = np.array(cam['p']), np.array(cam['off'] + [0.0]), cam['box']


AXES = sys.argv[4] if len(sys.argv) > 4 else 'yz'      # which two axes to scale (the third is fixed)


def unpack(z):
    p = p0.copy()
    p[2] = p0[2] + z[0] * 4
    off = off0 + [z[1], z[2], 0]
    sc = [1.0, 1.0, 1.0]
    sc['xyz'.index(AXES[0])] = 1 + z[3] * 0.05
    sc['xyz'.index(AXES[1])] = 1 + z[4] * 0.05
    return p, off, sc


def score(z):
    p, off, sc = unpack(z)
    return -F.iou(tris * sc + off, mask, p, box)[0]


best = np.zeros(5)
for _ in range(4):
    r = minimize(score, best, method='Nelder-Mead', options=dict(maxiter=1200, initial_simplex=np.vstack([best, best + np.eye(5)])))
    best = r.x
p, off, sc = unpack(best)
print('VPPROP %s iou=%.3f width x%.3f length x%.3f height x%.3f dist=%.1f' % (key, -score(best), *sc, p[2]))
