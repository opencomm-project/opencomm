"""Dortmund route-boundary research prototype, not coverage or tower localization.

Raw DoNext source and external rasters/OSM building extract are local inputs. All
spatial validation recomputes noisy anchors using training-only readings.
"""
import argparse,csv,hashlib,json,math
from collections import defaultdict
from pathlib import Path
import h3,lightgbm as lgb,numpy as np,rasterio
from scipy.spatial import cKDTree
from shapely.geometry import LineString,Polygon
from shapely.strtree import STRtree
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--source',default='/tmp/donext-hbahn.csv')
parser.add_argument('--buildings',default='/tmp/dortmund-buildings.json')
parser.add_argument('--worldcover',default='/tmp/dortmund-worldcover.tif')
parser.add_argument('--dem',default='/tmp/dortmund-copernicus.tif')
a=parser.parse_args()
assert hashlib.md5(Path(a.source).read_bytes()).hexdigest()=='2319a9cefcd48839bf70a2198586fbb7'
center_file=json.loads((ROOT/'docs/assets/reception-centers.geojson').read_text())['features']
keys={(f['properties']['mno_code'],f['properties']['cell_index'],f['properties']['physical_cellid'],f['properties']['earfcn']) for f in center_file if f['properties']['mno_code']=='C'}
rows=[]
with open(a.source,encoding='utf-8-sig',newline='') as f:
 for index,row in enumerate(csv.DictReader(f,delimiter=';')):
  if index%47:continue
  key=(row['MNO'],row['cell_index'],row['physical_cellid'],row['earfcn'])
  if key not in keys or not row.get('ss_rsrp'):continue
  try:
   lon,lat,y=float(row['longitude']),float(row['latitude']),float(row['ss_rsrp'])
   if not (7.39<=lon<=7.48 and 51.47<=lat<=51.52 and -160<=y<=-20):continue
  except (ValueError,TypeError):continue
  rows.append((key,lon,lat,y))
print('usable observations',len(rows),'eligible anchors',len({r[0] for r in rows}),flush=True)
lat0=51.49;mx=111320*math.cos(math.radians(lat0));my=111320
xy=np.array([[r[1]*mx,r[2]*my] for r in rows]);y=np.array([r[3] for r in rows]);lon=xy[:,0]/mx
building_coords=json.load(open(a.buildings));polys=[]
for _,coords in building_coords:
 p=Polygon([(x*mx,y*my) for x,y in coords])
 if p.is_valid and not p.is_empty:polys.append(p)
spatial=STRtree(polys)
wc=rasterio.open(a.worldcover);dem=rasterio.open(a.dem)
def raster_sample(dataset,coords):
 return np.array([v[0] for v in dataset.sample([(x/mx,y/my) for x,y in coords])],dtype=float)
def anchor_map(mask):
 groups=defaultdict(list)
 for i,(key,_,_,_) in enumerate(rows):
  if mask[i]:groups[key].append(i)
 anchors={}
 for k,idx in groups.items():
  if len(idx)<20:continue
  yy=y[idx];w=10**(np.maximum(yy-yy.max(),-20)/10)
  anchors[k]=np.average(xy[idx],axis=0,weights=w)
 return anchors
def features(mask,inds):
 anchors=anchor_map(mask);out=[];used=[];groups=[]
 for i in inds:
  key=rows[i][0];anchor=anchors.get(key)
  if anchor is None:continue
  p=xy[i];dx,dy=p-anchor;d=np.hypot(dx,dy);az=math.atan2(dy,dx)
  # Limit path features to 750m. Beyond that anchors are too noisy for obstruction modeling.
  if d>750:continue
  path=LineString([anchor,p]);candidates=spatial.query(path)
  crossings=sum(polys[j].intersects(path) for j in candidates)
  steps=np.linspace(0,1,9)[1:-1,None];points=anchor[None,:]+steps*(p-anchor)[None,:]
  de=raster_sample(dem,np.vstack([anchor,points,p]));land=raster_sample(wc,points)
  if np.any(~np.isfinite(de)) or np.any(de< -100):continue
  terrain_bulge=max(0,float(np.max(de[1:-1]-np.linspace(de[0],de[-1],9)[1:-1])))
  urban=float(np.mean(np.isin(land,[50,60])));tree=float(np.mean(land==10))
  # Baseline includes directional sector geometry, not isotropic distance alone.
  baseline=[math.log1p(d),math.sin(az),math.cos(az),math.sin(2*az),math.cos(2*az),dx/100,dy/100]
  extra=[min(crossings,30),terrain_bulge,urban,tree,float(de[-1]-de[0])]
  out.append(baseline+extra);used.append(i);groups.append(key)
 return np.asarray(out),np.asarray(used,dtype=int),groups,anchors
params=dict(n_estimators=100,learning_rate=.045,num_leaves=8,min_child_samples=80,max_depth=4,verbosity=-1,random_state=29,n_jobs=2)
q=np.quantile(lon,[.4,.6]);test=(lon>=q[0])&(lon<q[1]);train=~test
fold_edges=np.quantile(lon[train],np.linspace(0,1,6));fold=np.searchsorted(fold_edges[1:-1],lon,side='right')
results=[]
def evaluate(name,tr,te):
 xtr,itr,_,at=features(tr,np.where(tr)[0]);xte,ite,_,_=features(tr,np.where(te)[0])
 if len(ite)<50:return
 out={'split':name,'train_n':len(itr),'test_n':len(ite),'anchors':len(at),'test_anchor_count':len(set(rows[i][0] for i in ite))}
 for method,cols in [('sector_distance',7),('sector_clutter',12)]:
  model=lgb.LGBMRegressor(**params);model.fit(xtr[:,:cols],y[itr]);pred=model.predict(xte[:,:cols]);out[method+'_mae_db']=round(float(np.mean(np.abs(pred-y[ite]))),3)
 print(out,flush=True);results.append(out)
for k in range(5):evaluate('cv_'+str(k+1),train&(fold!=k),train&(fold==k))
evaluate('contiguous_holdout',train,test)
# Fit final with full data only after validation. Output a sector-aware line-of-sight
# diagnostic, not a coverage polygon: measured-route path endpoints to each noisy anchor.
allmask=np.ones(len(rows),dtype=bool);xf,ids,groups,anchors=features(allmask,np.arange(len(rows)))
model=lgb.LGBMRegressor(**params);model.fit(xf,y[ids]);pred=model.predict(xf)
# One path per anchor & 45-degree directional bin, from actual receiver endpoints.
paths=[]
for key,anchor in anchors.items():
 selected=[j for j,k in enumerate(groups) if k==key]
 for sector in range(8):
  ss=[j for j in selected if int((math.atan2(xy[ids[j],1]-anchor[1],xy[ids[j],0]-anchor[0])+math.pi)/(math.pi/4))%8==sector]
  if len(ss)<10:continue
  j=max(ss,key=lambda z:np.linalg.norm(xy[ids[z]]-anchor));point=xy[ids[j]]
  midpoint=np.mean(pred[ss]);observed=np.mean(y[ids[ss]])
  ring=[[float(anchor[0]/mx),float(anchor[1]/my)],[float(point[0]/mx),float(point[1]/my)]]
  paths.append({'type':'Feature','geometry':{'type':'LineString','coordinates':ring},'properties':{'knowledge_grade':'route_bound_model_diagnostic','sector':sector,'sample_count':len(ss),'mean_model_rsrp_dbm':round(float(midpoint),1),'mean_observed_rsrp_dbm':round(float(observed),1),'anchor_grade':'estimated_reception_center','not_coverage':True}})
report={'scope':'DoNext H-Bahn anonymized MNO C NR SS-RSRP; center estimates from training-only measurements in each split','source_md5':'2319a9cefcd48839bf70a2198586fbb7','building_extract':'OSM Geofabrik Arnsberg 2026-09-26, ODbL 1.0','landcover':'ESA WorldCover 10m 2021 v200, CC BY 4.0','terrain':'Copernicus DEM GLO-30 DSM, free use with credit','split':'longitude-contiguous middle 20% untouched and five longitudinal blocks on the other 80%; both models same split and features; no off-route evaluation','max_path_m':750,'n_rows':len(rows),'n_final_paths':len(paths),'results':results,'caveats':'Reception centers are noisy receiver-derived anchors, not towers; same rail route and time-correlated samples. Building footprints have no heights and DSM is not bare-earth ground elevation. Feature paths and eight directional bins are diagnostics, not RF rays or service coverage. No off-route ground truth.'}
(ROOT/'docs/assets/clutter-metrics.json').write_text(json.dumps(report,indent=2)+'\n')
(ROOT/'docs/assets/sector-paths.geojson').write_text(json.dumps({'type':'FeatureCollection','features':paths},separators=(',',':')))
print('paths',len(paths),'MAE final',results[-1],flush=True)
