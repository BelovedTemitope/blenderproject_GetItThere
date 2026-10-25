"""Build the background vehicles into one .blend.

    python ev_build.py -- <out.blend> [A B C D]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402

import ev_lib as E  # noqa: E402

SPACING = 14.0
LINEUP = {'A': (-1.5 * SPACING * 1.4, 0, 0), 'B': (-0.5 * SPACING * 1.4, 0, 0),
          'C': (0.5 * SPACING * 1.4, 0, 0), 'D': (1.5 * SPACING * 1.4, 0, 0)}
NAMES = {'A': 'GIT_Env_Danfo_A', 'B': 'GIT_Env_Danfo_B_Wrecked', 'C': 'GIT_Env_Taxi_C', 'D': 'GIT_Env_Keke_D'}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    out = args[0]
    which = args[1:] or ['A', 'B', 'C', 'D']
    reset()
    import ev_danfo
    ev_danfo.TEX_DIR = os.path.join(os.path.dirname(os.path.abspath(out)), 'textures')
    root = E.get_collection('GIT_Env_Vehicles')
    report = {}
    for k in which:
        col = E.get_collection(NAMES[k], root)
        if k == 'A':
            import ev_danfo as D
            import ev_danfoA as DA
            parts = DA.build(col, LINEUP[k], D.materials())
        elif k == 'B':
            import ev_danfo as D
            parts = D.build(col, LINEUP[k], wreck=True, mats=D.materials())
        elif k == 'C':
            import ev_taxi as T
            parts = T.build(col, LINEUP[k])
        else:
            import ev_keke as K
            parts = K.build(col, LINEUP[k])
        body = parts[0]
        bpy.context.view_layer.update()
        for o in parts[1:]:                      # wheels / canopy / roof layers follow the body
            o.parent = body
            o.matrix_parent_inverse = body.matrix_world.inverted()
        report[k] = E.stats(parts)
        for o in parts:
            print('PART %-36s faces %4d' % (o.name, len(o.data.polygons)))
        print('STATS', k, NAMES[k], report[k])
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print('SAVED', out)


if __name__ == '__main__':
    main()
