"""Silhouette masks of vehicles A-D from the concept lineup sheet (background + blue shadow removed).

    python ev_concept_mask.py <concept.webp> <out_dir>
"""
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
SRC = sys.argv[1]
BOX = {'A': (25, 20, 350, 320), 'B': (335, 75, 650, 310), 'C': (600, 115, 925, 320), 'D': (915, 90, 1150, 330)}
im = np.array(Image.open(SRC).convert('RGB')).astype(int)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
mx, mn = im.max(-1), im.min(-1)
sat = (mx - mn)
bg = (abs(r - 201) < 14) & (abs(g - 203) < 14) & (abs(b - 203) < 14)
shadow = (b - r > 22) & (sat < 60) & (mx < 190)
veh = ~bg & ~shadow
# neighbours touching in the sheet: keep each vehicle's own pixels
yy, xx = np.mgrid[0:veh.shape[0], 0:veh.shape[1]]
CUT = {'B': (xx > 612) & (yy > 228), 'C': (xx < 611) | ((xx < 642) & (yy < 228))}
out = {}
for k, (x0, y0, x1, y1) in BOX.items():
    vv = veh & ~CUT[k] if k in CUT else veh
    m = vv[y0:y1, x0:x1]
    m = ndi.binary_opening(m, iterations=1)
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = lab == (int(np.argmax(sizes)) + 1)
    keep = ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=2))
    full = np.zeros(veh.shape, bool); full[y0:y1, x0:x1] = keep
    np.save(os.path.join(sys.argv[2], 'mask_%s.npy' % k), full)
    vis = im.copy().astype(np.uint8)
    vis[full] = (vis[full] * 0.4 + np.array([255, 0, 255]) * 0.6).astype(np.uint8)
    Image.fromarray(vis[y0:y1, x0:x1]).resize(((x1 - x0) * 2, (y1 - y0) * 2)).save(
        os.path.join(sys.argv[2], 'maskvis_%s.png' % k))
    print(k, full.sum())
