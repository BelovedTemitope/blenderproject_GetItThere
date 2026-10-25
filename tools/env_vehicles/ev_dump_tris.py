"""Dump each vehicle's world triangles (relative to its lineup origin) for the concept camera fit.

    python ev_dump_tris.py -- <file.blend> <out_dir>
"""
import os
import sys

import bpy
import numpy as np

CLASS_KEYS = [(1, ('Paint',)), (2, ('Black', 'Tyre', 'Canopy', 'Grille', 'Broken')), (3, ('Glass', 'Bumper')),
              (4, ('Lamp', 'Hub', 'Plate', 'Sign', 'Chrome')), (5, ('Box', 'Sack', 'Rust', 'Indicator', 'Seat', 'TailLamp'))]


def mat_class(name):
    for c, keys in CLASS_KEYS:
        if any(k in name for k in keys):
            return c if not ('Hub_Rust' in name) else 5
    return 3


NAMES = {'A': 'GIT_Env_Danfo_A', 'B': 'GIT_Env_Danfo_B_Wrecked', 'C': 'GIT_Env_Taxi_C', 'D': 'GIT_Env_Keke_D'}


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    bpy.ops.wm.open_mainfile(filepath=args[0])
    dg = bpy.context.evaluated_depsgraph_get()
    for k, n in NAMES.items():
        col = bpy.data.collections.get(n)
        if not col:
            continue
        objs = [o for o in col.all_objects if o.type == 'MESH']
        base = min(objs, key=lambda o: len(o.name)).location if False else None
        body = [o for o in objs if o.name.endswith('_Body')][0]
        org = body.location.copy()
        tris, cls = [], []
        for o in objs:
            me = o.evaluated_get(dg).to_mesh()
            me.calc_loop_triangles()
            mw = o.matrix_world
            co = [mw @ v.co - org for v in me.vertices]
            mc = [mat_class(m.name if m else '') for m in me.materials]
            for t in me.loop_triangles:
                tris.append([tuple(co[i]) for i in t.vertices])
                cls.append(mc[t.material_index] if mc else 3)
            o.evaluated_get(dg).to_mesh_clear()
        np.save(os.path.join(args[1], 'tris_%s.npy' % k), np.array(tris, dtype=np.float32))
        np.save(os.path.join(args[1], 'cls_%s.npy' % k), np.array(cls, dtype=np.uint8))
        print('DUMP', k, len(tris))


if __name__ == '__main__':
    main()
