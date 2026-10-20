# usage: python preview.py -- file.blend outprefix [views...]
import bpy, sys, math
from mathutils import Vector
args = sys.argv[sys.argv.index('--')+1:]
path, out = args[0], args[1]
views = args[2:] or ['fl','rl','side','front','rear','top']
bpy.ops.wm.open_mainfile(filepath=path)
sc = bpy.context.scene
# hide non-vehicle
for c in bpy.data.collections:
    if c.name in ('MCP_Test','M3_Reference','Minibus__Cutters','M3_Ref_Colour','M3_Ref_Pencil'):
        c.hide_render = True
for o in sc.objects:
    if o.name.startswith('CUT_') or o.name.startswith('GIT_TubeProfile') or o.name.startswith('Danfo') or o.type=='CURVE' and o.name=='BézierCurve':
        o.hide_render = True
def col_for(n):
    n=n.lower()
    table=[('tyre',(0.05,0.05,0.05)),('wheel',(0.05,0.05,0.05)),('tire',(0.05,0.05,0.05)),('rim',(0.08,0.1,0.15)),('body',(0.85,0.5,0.08)),('door',(0.85,0.5,0.08)),('fender',(0.12,0.15,0.22)),
           ('cage',(0.12,0.15,0.22)),('bullbar',(0.12,0.15,0.22)),('bumper',(0.12,0.15,0.22)),('rack',(0.12,0.15,0.22)),('wing',(0.12,0.15,0.22)),('chassis',(0.1,0.1,0.12)),
           ('axle',(0.1,0.1,0.12)),('shackle',(0.7,0.05,0.03)),('light',(0.9,0.9,0.85)),('plate',(0.5,0.5,0.5)),('ladder',(0.5,0.5,0.5)),('exhaust',(0.5,0.5,0.5)),
           ('seat',(0.45,0.45,0.42)),('bench',(0.45,0.45,0.42)),('glass',(0.3,0.4,0.45)),('mirror',(0.12,0.15,0.22)),('sill',(0.12,0.15,0.22)),('grille',(0.2,0.2,0.2)),
           ('red',(0.5,0.08,0.06)),('navy',(0.1,0.13,0.25)),('purple',(0.2,0.12,0.25)),('plaid',(0.8,0.6,0.2)),('jerry',(0.6,0.1,0.05)),('grey',(0.4,0.38,0.35))]
    for k,c in table:
        if k in n: return c
    return (0.6,0.6,0.6)
for o in sc.objects:
    if o.type in ('MESH','CURVE') and (len(o.material_slots)==0 or all(s.material is None for s in o.material_slots)):
        m = bpy.data.materials.new('PV_'+o.name); m.use_nodes=True
        m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*col_for(o.name),1)
        if o.type=='MESH':
            o.data.materials.clear(); o.data.materials.append(m)
        else:
            o.data.materials.clear(); o.data.materials.append(m)
# cutaway option
if any(v.startswith('cut') for v in views):
    for o in sc.objects:
        if any(k in o.name for k in ('Body','Cage','Rack','Cargo','LightBar','RoofWing','Fender','Livery','Mirrors','Rear_Corner','Ladder','Exhaust','Spare','Rocker','Bumper','BullBar','Grille','HoodPlates','TailLights')):
            o.hide_render=True
# lights
for o in list(sc.objects):
    if o.type in ('LIGHT','CAMERA'): o.hide_render=True
w = bpy.data.worlds.new('pv'); w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.9,0.9,0.92,1); w.node_tree.nodes['Background'].inputs[1].default_value=0.6; sc.world=w
ld = bpy.data.lights.new('sun','SUN'); ld.energy=3.5; lo=bpy.data.objects.new('sun',ld); sc.collection.objects.link(lo); lo.rotation_euler=(math.radians(40),math.radians(10),math.radians(-30))
# ground
bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,0))
if 'under' in views or 'cut_under' in views: bpy.context.active_object.hide_render=True
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=48; sc.cycles.use_denoising=True
sc.render.resolution_x=1376; sc.render.resolution_y=768; sc.render.film_transparent=False
cd = bpy.data.cameras.new('pvcam'); cam=bpy.data.objects.new('pvcam',cd); sc.collection.objects.link(cam); sc.camera=cam
target=Vector((0,-0.9,5.2))
V={'fl':((22,-26,10),False),'rl':((24,22,10),False),'side':((60,0,5.5),True),'front':((0,-60,5.5),True),'rear':((0,60,5.5),True),'top':((0,-0.9,60),True),
   'fl_close':((12,-16,8),False),'under':((16,-10,-2.5),False),'rear_close':((6,18,6),False),'top':((0,-0.9,60),True),'cab':((6,-14,9),False),'rr_close':((-10,16,6),False),'seats':((7.5,-0.8,7.2),False),'band':((14,4,6.5),False),'cut_int':((10,-14,16),False),'cut_chassis':((12,-12,5),False),'cut_under':((10,-6,-6),False),'cage_fl':((9,-15,11),False),'cage_top':((5,-12,16),False),'cage_fr':((-9,-15,11),False),'cage_front':((0,-30,8.5),False),'side_r':((-60,0,5.5),True),'door_close':((11,-1,6.5),False),'door_close_r':((-11,-1,6.5),False),'cargo':((5,9,13.5),False),'cage_fl':((9,-15,11),False),'cage_top':((5,-12,16),False),'cage_fr':((-9,-15,11),False),'cage_front':((0,-30,8.5),False),'side_r':((-60,0,5.5),True),'door_close':((11,-1,6.5),False),'door_close_r':((-11,-1,6.5),False),'cargo':((5,9,13.5),False),'rr':((-24,22,10),False),'fr':((-22,-26,10),False)}
for v in views:
    pos,ortho=V[v]
    cam.location=pos
    t={'under':Vector((0,-1,2.0)),'rear_close':Vector((0,6.5,5.5)),'cab':Vector((1.5,-6.5,6.0)),'rr_close':Vector((-1,6.5,5.0)),'fl_close':Vector((2,-6,4.5)),'seats':Vector((0,-3.5,5.4)),'band':Vector((3.9,4.5,6.3)),'cut_int':Vector((0,-1.5,4.5)),'cut_chassis':Vector((0,-1,2.2)),'cut_under':Vector((0,-0.5,2.0)),'cage_fl':Vector((2.5,-7.0,7.5)),'cage_top':Vector((1.5,-6.0,8.5)),'cage_fr':Vector((-2.5,-7.0,7.5)),'cage_front':Vector((0,-7.5,7.0)),'door_close':Vector((3.9,-1.0,5.6)),'door_close_r':Vector((-3.9,-1.0,5.6)),'cargo':Vector((0,3.5,10.8))}.get(v, Vector((0,-0.9,5.2)) if v!='top' else Vector((0,-0.9,0)))
    d=(t-Vector(pos)); cam.rotation_euler=d.to_track_quat('-Z','Y' if v!='top' else 'X').to_euler()
    if v=='top': cam.rotation_euler=(0,0,math.radians(90))
    cd.type='ORTHO' if ortho else 'PERSP'; cd.ortho_scale=21; cd.lens=50; cd.clip_end=500
    sc.render.filepath=f"{out}_{v}.png"
    bpy.ops.render.render(write_still=True)
