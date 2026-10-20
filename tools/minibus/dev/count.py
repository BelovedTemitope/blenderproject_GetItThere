import sys, bpy
f = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.open_mainfile(filepath=f)
dg = bpy.context.evaluated_depsgraph_get()
col = bpy.data.collections['GIT_Veh_Minibus']
rows = []
for o in col.all_objects:
    if o.type != 'MESH' or o.hide_render:
        continue
    me = o.evaluated_get(dg).to_mesh()
    t = sum(len(p.vertices) - 2 for p in me.polygons)
    rows.append((t, o.name, o.users_collection[0].name))
    o.evaluated_get(dg).to_mesh_clear()
rows.sort(reverse=True)
grp = {}
for t, n, c in rows:
    grp[c] = grp.get(c, 0) + t
for t, n, c in rows:
    print('%6d  %-32s %s' % (t, n, c))
print('GROUPS', sorted(grp.items(), key=lambda x: -x[1]))
print('TOTAL', sum(r[0] for r in rows))
