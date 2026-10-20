import sys,bpy,math
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])
me=bpy.data.objects['GIT_Veh_Minibus_WheelFL'].data
angs=sorted({round(math.degrees(math.atan2(v.co.z,v.co.y))%360,1) for v in me.vertices})
rs=sorted({round(math.hypot(v.co.y,v.co.z),2) for v in me.vertices})
xs=sorted({round(v.co.x,2) for v in me.vertices})
print('V',len(me.vertices),'F',len(me.polygons),'nang',len(angs),angs[:40]); print('R',rs); print('X',xs)
from collections import Counter
print(Counter(len(p.vertices) for p in me.polygons), Counter(p.material_index for p in me.polygons))
