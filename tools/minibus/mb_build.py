"""Build GIT_Veh_Minibus v03 from the v02 blockout.

Run headless:
    python mb_build.py -- <repo_dir> <out.blend> [v03|ridges|shape]
(or inside Blender: blender -b GIT_Veh_Minibus_Blockout_v02.blend -P mb_build.py -- <repo_dir> <out.blend>)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402

import mb_lib as L  # noqa: E402
import mb_parts as P  # noqa: E402


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    repo = args[0] if args else os.path.dirname(os.path.dirname(HERE))
    out = args[1] if len(args) > 1 else os.path.join(repo, 'GIT_Veh_Minibus_v03.blend')
    src = os.path.join(repo, 'GIT_Veh_Minibus_Blockout_v02.blend')
    tires = os.path.join(repo, 'ILikeTheTires.blend')
    if os.path.abspath(bpy.data.filepath or '') != os.path.abspath(src):
        bpy.ops.wm.open_mainfile(filepath=src)
    variant = args[2] if len(args) > 2 else 'shape'
    import mb_body
    mb_body.configure(ridges=variant in ('ridges', 'shape'), shape=variant == 'shape')
    print('VARIANT', variant)
    ctx = P.Context(tires)
    import mb_chassis, mb_front, mb_cage, mb_rear, mb_interior, mb_cargo, mb_decals
    P.EXTRA[:] = [mb_chassis.build, mb_front.build, mb_cage.build, mb_rear.build, mb_interior.build,
                  mb_cargo.build, mb_decals.build]
    P.build_all(ctx)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print('SAVED', out)


if __name__ == '__main__':
    main()
