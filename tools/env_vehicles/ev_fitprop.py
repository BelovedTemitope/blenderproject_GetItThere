"""Proportion check: fit camera + length/height scale of a model to its concept mask (optionally fixed elevation).

    python ev_fitprop.py <tris.npy> <mask.npy> <key> <cams.json> [elevation_deg]
"""
import sys, math, json
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import ev_fitcam as F
from scipy.optimize import minimize
tris = np.load(sys.argv[1]); mask = np.load(sys.argv[2]); key = sys.argv[3]
cams = json.load(open(sys.argv[4])); p0 = np.array(cams[key]['p']); box = cams[key]['box']
el_fix = float(sys.argv[5]) if len(sys.argv) > 5 else None
def score(z):
    p = p0 + z[:6] * [0.05, 0.05, 5, 50, 3, 3]
    if el_fix is not None: p[1] = math.radians(el_fix)
    sy, sz = 1 + z[6] * 0.05, 1 + z[7] * 0.05
    t = tris * [1, sy, sz]
    return -F.iou(t, mask, p, box)[0]
best = np.zeros(8)
for _ in range(4):
    r = minimize(score, best, method='Nelder-Mead', options=dict(maxiter=900, initial_simplex=np.vstack([best, best + np.eye(8)])))
    best = r.x
p = p0 + best[:6] * [0.05, 0.05, 5, 50, 3, 3]
if el_fix is not None: p[1] = math.radians(el_fix)
print('%s iou=%.3f az=%.1f el=%.1f dist=%.1f sy=%.3f sz=%.3f' % (key, -score(best), math.degrees(p[0]), math.degrees(p[1]), p[2], 1 + best[6] * 0.05, 1 + best[7] * 0.05))
