"""Build GIT_Veh_Minibus v03 from the v02 blockout.

Run headless:
    python mb_build.py -- <repo_dir> <out.blend> [v03|ridges|shape|v04|v04doors|v05|v05tris|v06]
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


# v06 game load: triangle budget per part (~7k total; the Body lattice and doors are already at budget)
LOD_BUDGET = {
    'Cage_Exoskeleton': 650, 'RoofRack': 130, 'LightBar': 130, 'RoofWing': 58,
    'Axles_Suspension': 100, 'Suspension_Coilovers': 64, 'Driveline_Exhaust': 50, 'Wheel_Tubs': 70,
    'Chassis_Frame': 90,
    'BullBar': 190, 'Grille_Headlights': 190, 'TowShackles_Front': 40, 'TowShackles_Rear': 40,
    'Bumper_Front': 100, 'Livery_Decals': 100, 'Mirrors': 70, 'FenderFL': 66, 'FenderFR': 66,
    'FenderRL': 66, 'FenderRR': 66,
    'RearLadder': 90, 'ExhaustStack': 60, 'TailLights': 60, 'Rear_CornerPanels': 90,
    'Interior_Bench_Row2': 96, 'Interior_Bench_Row1': 90, 'Interior_SteeringWheel': 40,
    'Interior_Seat_Driver': 70, 'Interior_Seat_FrontPassenger': 70, 'Interior_Dashboard': 60,
    'Cargo_Duffel_NavyTop': 72, 'Cargo_Duffel_Purple': 72, 'Cargo_Duffel_NavyB': 72, 'Cargo_Plaid_A': 72,
    'Cargo_Plaid_B': 72, 'Cargo_Bundle_Grey': 64, 'Cargo_Jerrycan_A': 50, 'Cargo_Jerrycan_B': 50,
    'Cargo_Crate_Red': 60,
}


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
    v6 = variant == 'v06'
    v5 = variant in ('v05', 'v05tris') or v6
    v4 = variant in ('v04', 'v04doors') or v5
    # v06 game load: grooves/ridges are left to the texture, so the body lattice stays coarse
    mb_body.configure(ridges=(variant in ('ridges', 'shape') or v4) and not v6, shape=variant == 'shape' or v4,
                      groove=v4 and not v6, doors=variant == 'v04doors' or v5)
    import mb_lib
    mb_lib.OPTIMIZE = v5
    mb_lib.LOD = v6
    print('VARIANT', variant)
    ctx = P.Context(tires)
    import mb_chassis, mb_front, mb_cage, mb_rear, mb_interior, mb_cargo, mb_decals, mb_doors
    P.EXTRA[:] = [mb_chassis.build, mb_front.build, mb_cage.build, mb_rear.build, mb_interior.build,
                  mb_cargo.build, mb_decals.build, mb_doors.build]
    P.build_all(ctx)
    if v5:
        import mb_optimize
        mb_optimize.cull_hidden()
        if variant in ('v05tris', 'v06'):
            mb_optimize.planar_tris()
        if v6:
            mb_optimize.lod_budget(LOD_BUDGET)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print('SAVED', out)


if __name__ == '__main__':
    main()
