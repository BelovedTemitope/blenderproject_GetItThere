"""Report topology stats for every minibus mesh: ngons, tris, non-manifold, loose verts, doubles."""
import sys
import bpy
import bmesh

def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if args:
        bpy.ops.wm.open_mainfile(filepath=args[0])
    tot = {'quads': 0, 'tris': 0, 'ngons': 0}
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        if o.type != 'MESH' or not o.name.startswith('GIT_Veh_Minibus'):
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        q = sum(1 for f in bm.faces if len(f.verts) == 4)
        t = sum(1 for f in bm.faces if len(f.verts) == 3)
        n = sum(1 for f in bm.faces if len(f.verts) > 4)
        nm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        bnd = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        loose = sum(1 for v in bm.verts if not v.link_faces)
        dbl = len(bmesh.ops.find_doubles(bm, verts=bm.verts, dist=1e-4)['targetmap'])
        zero = sum(1 for f in bm.faces if f.calc_area() < 1e-7)
        flag = ' <<' if (t or n or nm or loose or dbl or zero) else ''
        print(f"{o.name:48s} v{len(bm.verts):5d} q{q:5d} t{t:3d} n{n:3d} nonman{nm:3d} border{bnd:4d} loose{loose:3d} dbl{dbl:3d} zero{zero:3d}{flag}")
        tot['quads'] += q; tot['tris'] += t; tot['ngons'] += n
        bm.free()
    print('TOTAL', tot)

main()
