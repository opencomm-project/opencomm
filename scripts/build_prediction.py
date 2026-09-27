"""Exploratory route-adjacent H3 model; never a coverage estimate.

Run after export_donext.py. Trains only anonymized code C, NR SS-RSRP rows.
A contiguous longitude interval is held out before five blocked CV folds.
"""
import json
from pathlib import Path
import duckdb
import h3
import lightgbm as lgb
import numpy as np
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
rows=duckdb.connect().execute("SELECT lon,lat,rsrp_dbm FROM read_parquet(?) WHERE operator_name='C' AND radio='NR SS-RSRP (5G signal)' ORDER BY source_record_id",[str(ROOT/'docs/assets/observations.parquet')]).fetchall()
a=np.asarray(rows,dtype=float); x=a[:,:2]; y=a[:,2]
# Held-out contiguous middle fifth of the route, never used in CV or final fitting.
q=np.quantile(x[:,0],[.4,.6]); test=(x[:,0]>=q[0])&(x[:,0]<q[1]); train=~test
params=dict(n_estimators=110,learning_rate=.05,num_leaves=10,min_child_samples=45,max_depth=5,verbosity=-1,random_state=29,n_jobs=2)
def fit(tr,te):
 m=lgb.LGBMRegressor(**params);m.fit(x[tr],y[tr]);return m,np.abs(m.predict(x[te])-y[te])
# Spatially blocked, deterministic 5-fold CV on the remaining non-holdout rows.
fold_edges=np.quantile(x[train,0],np.linspace(0,1,6));fold=np.minimum(np.searchsorted(fold_edges[1:-1],x[:,0],side='right'),4)
cv=[];models=[]
for k in range(5):
 tr=train&(fold!=k);te=train&(fold==k)
 m,e=fit(tr,te);cv.append({'fold':k+1,'n':int(te.sum()),'mae_db':round(float(e.mean()),2)});models.append(m)
hold_model,hold_error=fit(train,test)
final=lgb.LGBMRegressor(**params);final.fit(x,y)
# H3 r10 hexes within two rings of an actual sampled measurement and within 150m
# of the route. This is a narrow corridor, not a city-wide coverage surface.
resolution=10
base={h3.latlng_to_cell(float(lat),float(lon),resolution) for lon,lat in x}
hexes=set().union(*(h3.grid_disk(cell,2) for cell in base))
lat0=np.deg2rad(float(x[:,1].mean()))
def meters(points):return np.c_[points[:,0]*111320*np.cos(lat0),points[:,1]*111320]
tree=cKDTree(meters(x));centers=np.array([[h3.cell_to_latlng(c)[1],h3.cell_to_latlng(c)[0]] for c in sorted(hexes)])
distance,_=tree.query(meters(centers));keep=distance<=150
centers=centers[keep];distance=distance[keep];hexids=np.asarray(sorted(hexes))[keep]
pred=final.predict(centers)
spread=np.std(np.asarray([m.predict(centers) for m in models]),axis=0)
cv_mae=sum(v['mae_db']*v['n'] for v in cv)/sum(v['n'] for v in cv)
features=[]
for cell,rsrp,dist,sd in zip(hexids,pred,distance,spread):
 # Uncertainty is a heuristic, not a calibrated interval or confidence percent.
 uncertainty=max(cv_mae,float(sd))*(1+float(dist)/150)
 boundary=h3.cell_to_boundary(cell)
 ring=[[lon,lat] for lat,lon in boundary];ring.append(ring[0])
 features.append({'type':'Feature','properties':{'predicted_rsrp_dbm':round(float(rsrp),1),'uncertainty_db':round(uncertainty,1),'distance_m':round(float(dist)),'h3':cell},'geometry':{'type':'Polygon','coordinates':[ring]}})
report={'model':'LightGBM regression on coordinates only','scope':'anonymized MNO C, NR SS-RSRP, Dortmund H-Bahn','train_n':int(train.sum()),'holdout_n':int(test.sum()),'holdout_lon':[round(float(t),6) for t in q],'holdout_mae_db':round(float(hold_error.mean()),2),'cv_folds':cv,'cv_weighted_mae_db':round(cv_mae,2),'hex_resolution':resolution,'hex_count':len(features),'max_route_distance_m':150,'uncertainty':'Heuristic max(spatial-CV MAE, spread across spatial-fold models) multiplied by 1 + distance/150m. Not calibrated or probabilistic; no off-route ground truth.'}
out=ROOT/'docs/assets/predicted-rsrp.geojson';out.write_text(json.dumps({'type':'FeatureCollection','features':features},separators=(',',':')))
(ROOT/'docs/assets/model-metrics.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));print(out.stat().st_size,'bytes')
