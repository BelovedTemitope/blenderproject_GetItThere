"""List intersecting face pairs between minibus parts (to spot unintended clashes)."""
import sys
import bpy
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if args:
    bpy.ops.wm.open_mainfile(filepath=args[0])
dg = bpy.context.evaluated_depsgraph_get()
objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('GIT_Veh_Minibus') and not o.hide_render]
trees = {}
for o in objs:
    trees[o.name] = BVHTree.FromObject(o, dg, deform=True, cage=False, epsilon=0.0)
    # FromObject is in local space; all parts sit at identity except wheels -> transform
for o in objs:
    if o.matrix_world != o.matrix_world.Identity(4):
        me = o.evaluated_get(dg).to_mesh()
        vs = [o.matrix_world @ v.co for v in me.vertices]
        ps = [tuple(p.vertices) for p in me.polygons]
        trees[o.name] = BVHTree.FromPolygons(vs, ps)
        o.evaluated_get(dg).to_mesh_clear()
names = sorted(trees)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        n = len(trees[a].overlap(trees[b]))
        if n:
            print(f"{n:5d}  {a[16:]:34s} x {b[16:]}")
