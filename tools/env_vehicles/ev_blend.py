"""Zoomed 50/50 blend of a concept-camera render over the concept, plus the model's outline/landmark edges.

    python ev_blend.py <concept.webp> <render.png> <cams.json> <key> <out.png> [zoom]
"""
import json
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

src, rnd, camf, key, out = sys.argv[1:6]
zoom = int(sys.argv[6]) if len(sys.argv) > 6 else 3
y0, y1, x0, x1 = json.load(open(camf))[key]['box']
c = np.array(Image.open(src).convert('RGB')).astype(float)[y0:y1, x0:x1]
r = np.array(Image.open(rnd).convert('RGBA')).astype(float)[y0:y1, x0:x1]
a = r[..., 3:] / 255
blend = c * (1 - 0.5 * a) + r[..., :3] * 0.5 * a
# model colour-region edges in magenta on top of the plain concept
q = (r[..., :3] // 24).astype(int)
lab = q[..., 0] * 10000 + q[..., 1] * 100 + q[..., 2]
lab[a[..., 0] < 0.5] = -1
e = (lab != np.roll(lab, 1, 0)) | (lab != np.roll(lab, 1, 1))
edges = c.copy()
edges[e] = (255, 0, 200)
sheet = np.concatenate([blend, edges], 1).astype(np.uint8)
Image.fromarray(sheet).resize((sheet.shape[1] * zoom, sheet.shape[0] * zoom), Image.LANCZOS).save(out)
