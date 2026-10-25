"""Landmark comparison: concept vs flat-colour model render, region by region.

    python ev_landmarks.py <concept.webp> <albedo_render.png> <mask.npy> <cams.json> <key> <out.png>

Both images are classified into the same colour regions (paint, dark, grey, light, warm). The score
per region is IoU inside the box; the diff image shows concept regions | model regions | mismatch.
"""
import colorsys
import json
import sys

import numpy as np
from PIL import Image

CLASSES = ['bg', 'paint', 'dark', 'grey', 'light', 'warm']
COLORS = np.array([(255, 255, 255), (242, 183, 5), (30, 30, 34), (140, 140, 140), (235, 235, 225), (170, 80, 40)],
                  np.uint8)


def classify(rgb):
    a = rgb.astype(np.float32) / 255.0
    mx, mn = a.max(-1), a.min(-1)
    v = mx
    s = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.zeros_like(v)
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, ((g - b) / d) % 6, h)
    h = np.where(mx == g, (b - r) / d + 2, h)
    h = np.where(mx == b, (r - g) / d + 4, h)
    h = h * 60.0
    out = np.full(v.shape, 3, np.uint8)                    # grey by default
    out[(v > 0.78) & (s < 0.2)] = 4                        # light
    warm = (s > 0.32) & (v > 0.2) & ((h < 36) | (h > 330))
    out[warm] = 5
    out[(s > 0.4) & (v > 0.38) & (h >= 36) & (h < 70)] = 1  # yellow paint
    out[v < 0.3] = 2                                       # dark
    return out


def main():
    src, rnd, maskf, camf, key, outp = sys.argv[1:7]
    cam = json.load(open(camf))[key]
    y0, y1, x0, x1 = cam['box']
    con = np.array(Image.open(src).convert('RGB'))[y0:y1, x0:x1]
    mask = np.load(maskf)[y0:y1, x0:x1]
    ren = Image.open(rnd).convert('RGBA')
    ren = np.array(ren)[y0:y1, x0:x1]
    m_alpha = ren[..., 3] > 128 if ren.shape[-1] == 4 else None
    rgb = ren[..., :3]
    cc = classify(con)
    cc[~mask] = 0
    mc = classify(rgb)
    model_mask = m_alpha if m_alpha is not None else (rgb.sum(-1) > 6)
    mc[~model_mask] = 0
    print('LANDMARKS %s' % key)
    tot = []
    for i, n in enumerate(CLASSES[1:], 1):
        a, b = cc == i, mc == i
        u = (a | b).sum()
        if u < 30:
            continue
        iou = (a & b).sum() / u
        tot.append((iou, u))
        print('  %-6s iou=%.3f  concept_px=%d model_px=%d' % (n, iou, a.sum(), b.sum()))
    sil = (mask & model_mask).sum() / max(1, (mask | model_mask).sum())
    w = sum(t[0] * t[1] for t in tot) / sum(t[1] for t in tot)
    print('  silhouette=%.3f  region_weighted=%.3f' % (sil, w))
    mis = np.full(cc.shape + (3,), 255, np.uint8)
    mis[(cc != mc)] = (220, 40, 40)
    mis[(cc == mc) & (cc > 0)] = (200, 200, 200)
    sheet = np.concatenate([con, COLORS[cc], COLORS[mc], mis], 1)
    Image.fromarray(sheet).resize((sheet.shape[1] * 2, sheet.shape[0] * 2), Image.NEAREST).save(outp)


if __name__ == '__main__':
    main()
