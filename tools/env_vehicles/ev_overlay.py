"""Draw the fitted model silhouette over the concept: model outline red, concept outline green, side by side.

    python ev_overlay.py <concept.png> <tris.npy> <mask.npy> <cams.json> <key> <out.png> [render.png]
"""
import json
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

import ev_fitcam as F


def edge(m):
    return m & ~ndi.binary_erosion(m, iterations=2)


def main():
    src, trisf, maskf, camf, key, out = sys.argv[1:7]
    im = np.array(Image.open(src).convert('RGB'))
    tris, mask = np.load(trisf), np.load(maskf)
    cam = json.load(open(camf))[key]
    y0, y1, x0, x1 = cam['box']
    off = np.array(cam.get('off', [0, 0]) + [0.0])
    s, m = F.iou(tris + off, mask, np.array(cam['p']), cam['box'])
    crop = im[y0:y1, x0:x1].copy()
    ov = crop.copy()
    ov[edge(mask[y0:y1, x0:x1])] = (40, 200, 60)
    ov[edge(m)] = (230, 30, 30)
    panels = [crop, ov]
    if len(sys.argv) > 7:
        rd = np.array(Image.open(sys.argv[7]).convert('RGB'))[y0:y1, x0:x1]
        blend = (crop * 0.5 + rd * 0.5).astype(np.uint8)
        panels += [rd, blend]
    sheet = np.concatenate(panels, 1)
    Image.fromarray(sheet).resize((sheet.shape[1] * 2, sheet.shape[0] * 2), Image.LANCZOS).save(out)
    print('OVERLAY %s iou=%.3f' % (key, s))


if __name__ == '__main__':
    main()
