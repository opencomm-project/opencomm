"""One of five site-exclusive contiguous x-block tests; training labels only."""
import json,argparse
from pathlib import Path
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
p=argparse.ArgumentParser();p.add_argument('--run',default='/tmp/sionna-dortmund-validation');a=p.parse_args();d=Path(a.run)
o=np.load(d/'observations.npz');q=np.load(d/'receiver_path_gains.npz');rows=o['rows'];idx=q['indices'];gain=q['gain'];train=o['train'][idx];test=o['test'][idx];anchor=o['anchor'];xy=rows[idx,:2];target=rows[idx,2]
dx=xy[:,0]-anchor[0];dy=xy[:,1]-anchor[1];dist=np.hypot(dx,dy);az=np.arctan2(dy,dx)
# A fixed alpha, same train/test, no hyperparameter selection on holdout.
base=np.column_stack([np.log1p(dist),np.sin(az),np.cos(az),dx/100,dy/100]);sim=np.column_stack([np.log10(np.maximum(gain,1e-13)),(gain>0).astype(int)])
methods={'train_median':None,'sector_distance':base,'sector_distance_plus_sionna':np.column_stack([base,sim])}
results={}
for name,x in methods.items():
 if x is None: pred=np.full(sum(test),np.median(target[train]))
 else:
  model=make_pipeline(StandardScaler(),Ridge(alpha=50));model.fit(x[train],target[train]);pred=model.predict(x[test])
 err=pred-target[test];results[name]={'test_n':int(sum(test)),'mae_db':round(float(np.mean(abs(err))),3),'bias_db':round(float(np.mean(err)),3),'rmse_db':round(float(np.sqrt(np.mean(err**2))),3)}
report={'grade':'unvalidated_transfer','scope':'single DoNext Dortmund H-Bahn MNO C serving-cell key (cell_index 28365056, PCI 371, EARFCN 1300); one of five site-exclusive contiguous route holdouts, no off-route or new-region validation','run':json.loads((d/'run.json').read_text()),'raw_measured_rows':len(rows),'evaluation_unique_10m_sites':len(idx),'train_sites':int(sum(train)),'test_sites':int(sum(test)),'test_longitudinal_block_m':json.loads((d/'run.json').read_text())['test_x_m'],'anchor_is_training_only_receiver_weighted_not_tower':anchor.tolist(),'nonzero_sionna_path_gain_train':int(np.count_nonzero(gain[train])),'nonzero_sionna_path_gain_test':int(np.count_nonzero(gain[test])),'metrics':results,'method':'Ridge alpha=50 with StandardScaler, same measured train and contiguous test, median-only and sector-distance baselines; simulated feature is 10log10(path gain clipped at 1e-13) and path-found bit; no measured test labels in anchor, features or model fit','limitations':'NR SS-RSRP is not Sionna generic RSS; transmitter location, 25m height, 40 dBm, isotropic antenna, 2.1 GHz, 12m OSM building heights and concrete material all assumed. GLO-30 is DSM, not ground elevation; terrain sampled at 50m, Sionna map is on a horizontal plane rather than receiver height. Rays use first-order reflection, no diffraction, only a single guessed site. The train and test are samples from one route and likely time-correlated. No inference about unmeasured city blocks or global transfer. OSM/DEM licenses and attribution must travel with any derived artifacts.'}
print(json.dumps(report,indent=2));(d/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
