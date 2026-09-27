"""Bounded CPU Sionna RT Dortmund research. Outputs are unvalidated simulation, never coverage."""
import csv, json, math, argparse, time, hashlib
from pathlib import Path
import numpy as np, rasterio
from shapely.geometry import Polygon, box
import mitsuba as mi, drjit as dr
from sionna.rt import load_scene, Transmitter, PlanarArray, RadioMapSolver, Receiver, PathSolver
p=argparse.ArgumentParser();p.add_argument('--quick',action='store_true');p.add_argument('--fold',type=int,default=2,choices=range(5));p.add_argument('--rays',type=int,default=0);p.add_argument('--source',default='/tmp/donext-hbahn.csv');p.add_argument('--buildings',default='/tmp/dortmund-buildings.json');p.add_argument('--dem',default='/tmp/dortmund-copernicus.tif');p.add_argument('--out',default='/tmp/sionna-dortmund');a=p.parse_args()
out=Path(a.out);out.mkdir(exist_ok=True,parents=True)
assert hashlib.md5(Path(a.source).read_bytes()).hexdigest()=='2319a9cefcd48839bf70a2198586fbb7', 'unexpected DoNext source'
lon0,lat0=7.4126012,51.4855669;mx=111320*math.cos(math.radians(lat0));my=111320
key=('C','28365056.0','371.0','1300.0');R=200 if a.quick else 400
rows=[]
with open(a.source,encoding='utf-8-sig',newline='') as f:
 for i,r in enumerate(csv.DictReader(f,delimiter=';')):
  if i%47 or (r['MNO'],r['cell_index'],r['physical_cellid'],r['earfcn'])!=key:continue
  try: x=(float(r['longitude'])-lon0)*mx;y=(float(r['latitude'])-lat0)*my;v=float(r['ss_rsrp'])
  except:continue
  if abs(x)<R and abs(y)<R and -160<v<-20:rows.append((x,y,v))
rows=np.asarray(rows)
# Assign all samples sharing a rounded 10m receiver site to one spatial fold.
sitekeys=[(round(x/10),round(y/10)) for x,y,_ in rows]
sitex={key:float(np.median([row[0] for row,k in zip(rows,sitekeys) if k==key])) for key in set(sitekeys)}
unique_x=np.asarray(list(sitex.values()));edges=np.quantile(unique_x,np.linspace(0,1,6))
sitefold={key:min(4,int(np.searchsorted(edges[1:-1],value,side='right'))) for key,value in sitex.items()}
test=np.asarray([sitefold[key]==a.fold for key in sitekeys]);train=~test
weights=10**((rows[train,2]-np.max(rows[train,2]))/10);a.anchor_x,a.anchor_y=np.average(rows[train,:2],axis=0,weights=weights)
np.savez(out/'observations.npz',rows=rows,train=train,test=test,edges=edges,anchor=np.array([a.anchor_x,a.anchor_y]))
print('train-only anchor',a.anchor_x,a.anchor_y,'test edges',edges,'train/test',sum(train),sum(test),flush=True);print('rows',len(rows),'bounds',np.min(rows[:,:2],axis=0),np.max(rows[:,:2],axis=0),flush=True)
with rasterio.open(a.dem) as dem:
 def height(x,y):return float(next(dem.sample([(lon0+x/mx,lat0+y/my)]))[0])
 z0=height(0,0)
 def z(x,y):return height(x,y)-z0
 ztx=z(a.anchor_x,a.anchor_y)+25
 # DEM is a digital surface model, not bare earth; sampled ground approximation.
 step=50;xs=np.arange(-R-50,R+step+51,step);ys=xs.copy();verts=[];faces=[]
 for yy in ys:
  for xx in xs:verts.append((xx,yy,z(xx,yy)))
 ny=len(ys);nx=len(xs)
 for i in range(ny-1):
  for j in range(nx-1):
   q=i*nx+j;faces.extend([(q,q+1,q+nx),(q+1,q+nx+1,q+nx)])
 floor_faces=len(faces)
 # OSM ways have footprints but no heights here: 12m assumption, hard-coded for sensitivity.
 buildings=json.load(open(a.buildings));n=0
 for oid,coords in buildings:
  pp=Polygon([((lon-lon0)*mx,(lat-lat0)*my) for lon,lat in coords]);pp=pp.buffer(0)
  if pp.is_empty or not isinstance(pp,Polygon) or not pp.intersects(box(-R,-R,R,R)) or pp.area<8:continue
  coords=list(pp.exterior.coords)[:-1]
  if len(coords)>80 or len(coords)<3:continue
  # fan roof only for convex polygons; nonconvex OSM ways omitted.
  if abs(pp.area-pp.convex_hull.area)>max(2,pp.area*.02):continue
  base=len(verts);n+=1;h=12
  for x,y in coords:verts.append((x,y,z(x,y)))
  for x,y in coords:verts.append((x,y,z(x,y)+h))
  m=len(coords)
  for j in range(1,m-1):faces.append((base+m,base+m+j,base+m+j+1))
  for j in range(m):
   k=(j+1)%m;faces.extend([(base+j,base+k,base+m+j),(base+k,base+m+k,base+m+j)])
 print('mesh',n,'buildings',len(verts),'vertices',len(faces),'triangles',flush=True)
 def write_ply(path,v,ff):
  with open(path,'w') as f:
   f.write(f'ply\nformat ascii 1.0\nelement vertex {len(v)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(ff)}\nproperty list uchar int vertex_indices\nend_header\n')
   for pt in v:f.write('%.3f %.3f %.3f\n'%pt)
   for tri in ff:f.write('3 %d %d %d\n'%tri)
 write_ply(out/'terrain.ply',verts[:nx*ny],faces[:floor_faces]);write_ply(out/'buildings.ply',verts[nx*ny:],[(i-nx*ny,j-nx*ny,k-nx*ny) for i,j,k in faces[floor_faces:]])
 xml='''<scene version="2.1.0"><bsdf type="itu-radio-material" id="concrete"><string name="type" value="concrete"/><float name="thickness" value="0.1"/></bsdf><shape type="ply" id="terrain"><string name="filename" value="terrain.ply"/><ref id="concrete" name="bsdf"/></shape><shape type="ply" id="buildings"><string name="filename" value="buildings.ply"/><ref id="concrete" name="bsdf"/></shape></scene>'''
 (out/'scene.xml').write_text(xml)
scene=load_scene(str(out/'scene.xml'));scene.frequency=2.1e9
scene.tx_array=PlanarArray(num_rows=1,num_cols=1,pattern='iso',polarization='V');scene.rx_array=PlanarArray(num_rows=1,num_cols=1,pattern='iso',polarization='V')
# Assumed transmitter at a training-only, receiver-derived signal-weighted center; not a tower.
scene.add(Transmitter(name='estimated_anchor',position=[float(a.anchor_x),float(a.anchor_y),float(ztx)],power_dbm=40))
# DEM varies across the area; a flat receiver plane at z=1.5 would lie underground.
# For this bounded test choose a horizontal plane above the maximum DSM elevation.
plane_z=max(v[2] for v in verts[:nx*ny])+2
t=time.time();rmap=RadioMapSolver()(scene,center=[0,0,plane_z],orientation=[0,0,0],size=[2*R,2*R],cell_size=[10,10],samples_per_tx=a.rays or (5000 if a.quick else 30000),max_depth=1,seed=41,refraction=False,diffraction=False)
pg=np.asarray(rmap.path_gain);print('radio map shape',pg.shape,'positive',int(np.count_nonzero(pg)),'max',float(np.max(pg)),'elapsed',time.time()-t,flush=True)
np.save(out/'path_gain.npy',pg)
# True receiver heights sampled from DSM, unlike horizontal radio-map plane.
# Choose one measured point per rounded 10m coordinate, never input signal value to solver.
selected={};
for i,(x,y,v) in enumerate(rows):selected.setdefault((round(x/10),round(y/10)),i)
point_indices=np.asarray(list(selected.values()),dtype=int);point_indices=point_indices[:400]
with rasterio.open(a.dem) as dem:
 for i in point_indices:
  x,y,_=rows[i];scene.add(Receiver(name=f'rx_{i}',position=[float(x),float(y),float(z(x,y)+1.5)]))
t=time.time();paths=PathSolver(deterministic=True)(scene,max_depth=1,los=True,specular_reflection=True,refraction=False,diffraction=False,samples_per_src=20000,max_num_paths_per_src=100000,seed=41)
real,imag=paths.a;gain=np.sum(np.asarray(real)**2+np.asarray(imag)**2,axis=(1,2,3,4));print('path receiver gain',gain.shape,int(np.count_nonzero(gain)),'elapsed',time.time()-t,flush=True)
np.savez(out/'receiver_path_gains.npz',indices=point_indices,gain=gain)
(out/'run.json').write_text(json.dumps({'stage':'bounded_path_and_map_simulation','buildings':n,'vertices':len(verts),'triangles':len(faces),'path_gain_shape':pg.shape,'positive_cells':int(np.count_nonzero(pg)),'receiver_plane_z_above_anchor_dsm_m':float(plane_z),'frequency_hz':2.1e9,'assumed_transmit_power_dbm':40,'height_m':25,'assumed_building_height_m':12,'cell_size_m':10,'rays':a.rays or (5000 if a.quick else 30000),'bounds_m':R,'receiver_sample_count':len(rows),'train_count':int(sum(train)),'test_count':int(sum(test)),'fold':a.fold,'test_x_m':edges[a.fold:a.fold+2].tolist(),'anchor_xy_m':[a.anchor_x,a.anchor_y],'note':'WorldCover not used in this bounded scene; anchor calculated from training-only samples, no test RF labels used in scene. DEM is surface model, heights and frequency assumed, simulated RSS is not measured NR SS-RSRP.'},indent=2)+'\n')
