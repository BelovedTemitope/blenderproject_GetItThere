import sys, bpy
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])
dg = bpy.context.evaluated_depsgraph_get()
def tris(o):
    me = o.evaluated_get(dg).to_mesh(); t = sum(len(p.vertices) - 2 for p in me.polygons); o.evaluated_get(dg).to_mesh_clear(); return t
P = 'GIT_Veh_Minibus_'
g = {'Livery': [P+'Livery_Decals'], 'Roof rack': [P+'RoofRack'],
     'Luggage': [o.name for o in bpy.data.objects if o.name.startswith(P+'Cargo_')],
     'Side doors': [P+'Door_Sliding_L', P+'Door_Sliding_R']}
tot = 0
for k, ns in g.items():
    t = {n[len(P):]: tris(bpy.data.objects[n]) for n in ns if n in bpy.data.objects}
    tot += sum(t.values()); print('PART', k, sum(t.values()), t)
allt = sum(tris(o) for o in bpy.data.collections['GIT_Veh_Minibus'].all_objects if o.type == 'MESH' and not o.hide_render)
print('SUM', tot, 'WHOLE', allt)
