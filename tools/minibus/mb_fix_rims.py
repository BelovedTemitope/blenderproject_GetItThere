"""Patch the wheel rim material split into an already-built .blend (v03-v05 shipped all-rubber wheels).

    python mb_fix_rims.py -- <file.blend>

Faces whose outermost vertex sits inside the rim radius get the rim slot; nothing else is touched.
"""
import math
import sys

import bpy

PFX = 'GIT_Veh_Minibus_'
RIM_R = 1.1 * 1.83 / 1.95      # mb_parts rim test (r < 1.1 on the source tyre) at the built wheel scale


def main():
    path = sys.argv[sys.argv.index('--') + 1]
    bpy.ops.wm.open_mainfile(filepath=path)
    done = set()
    for n in ('WheelFL', 'WheelFR', 'WheelRL', 'WheelRR', 'SpareTyre'):
        me = bpy.data.objects[PFX + n].data
        if me in done:
            continue
        done.add(me)
        slot = [i for i, m in enumerate(me.materials) if m and 'Rim' in m.name]
        if not slot:
            me.materials.append(bpy.data.materials['M_Minibus_Rim_Dark'])
            slot = [len(me.materials) - 1]
        rim = 0
        for p in me.polygons:
            r = max(math.hypot(me.vertices[i].co.y, me.vertices[i].co.z) for i in p.vertices)
            p.material_index = slot[0] if r < RIM_R else 0
            rim += r < RIM_R
        print('RIM %-10s %d of %d faces' % (n, rim, len(me.polygons)))
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    print('SAVED', path)


if __name__ == '__main__':
    main()
