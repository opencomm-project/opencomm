"""Zero-test-label geographic holdout: compare physical and simulation-only proxies.

These do not claim valid NR SS-RSRP link budgets or off-rail transfer.
"""
import argparse,json
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
p=argparse.ArgumentParser();p.add_argument('--run',required=True);a=p.parse_args();d=Path(a.run)
o=np.load(d/'observations.npz');g=np.load(d/'receiver_path_gains.npz');idx=g['indices'];rows=o['rows'][idx];anchor=o['anchor'];gain=g['gain'];train=o['train'][idx];test=o['test'][idx]
assert not np.any(train&test) and sum(train)+sum(test)==len(idx)
assert not ({(round(x/10),round(y/10)) for x,y,_ in rows[train]} & {(round(x/10),round(y/10)) for x,y,_ in rows[test]})
dist=np.maximum(10,np.linalg.norm(rows[:,:2]-anchor,axis=1));y=rows[:,2]
# EIRP 40 dBm, isotropic 2.1GHz, free-space attenuation. NR SS-RSRP is not total received power.
fspl=32.44+20*np.log10(2100)+20*np.log10(dist/1000)
raw_fspl=40-fspl
# Calibration here sees training-area measured RF only, never a target-area observation.
fspl_intercept=float(np.median(y[train]-raw_fspl[train]));cal_fspl=raw_fspl+fspl_intercept
xx=np.log10(dist).reshape(-1,1);m=Ridge(alpha=25).fit(xx[train],y[train]);distance=m.predict(xx)
# Ray-traced path gain, loss floor for no-found-path, training-only offset.
ray_db=40+10*np.log10(np.maximum(gain,1e-13));ray_offset=float(np.median(y[train]-ray_db[train]));sim_only=ray_db+ray_offset
# Sim-only hybrid: replace free-space proxy with Sionna-derived excess attenuation where a ray exists.
# For solver misses, abstain to calibrated FSPL rather than interpret as no service.
excess=np.clip(10*np.log10(np.maximum(gain,1e-13))+fspl,-50,15)
physics=raw_fspl+np.where(gain>0,excess,0)
physics_offset=float(np.median(y[train]-physics[train]));hybrid=physics+physics_offset
out={'fold':json.loads((d/'run.json').read_text())['fold'],'raw_rows':len(o['rows']),'distinct_scored_sites':len(idx),'train_sites':int(sum(train)),'test_sites':int(sum(test)),'test_x_m':json.loads((d/'run.json').read_text())['test_x_m'],'test_sites_with_simulated_path':int(sum((gain>0)&test)),'assumed_anchor_xy_m':anchor.tolist(),'grade':'unvalidated_transfer','test_region_measurements_used_in_fit':0,'methods':{}}
for key,pred in [('raw_free_space',raw_fspl),('training_intercept_free_space',cal_fspl),('training_distance_only',distance),('simulated_path_only',sim_only),('simulated_excess_or_free_space_on_miss',hybrid)]:
 residual_train=y[train]-pred[train];e=pred[test]-y[test];q=float(np.quantile(abs(residual_train),.9));out['methods'][key]={'mae_db':round(float(np.mean(abs(e))),3),'signed_bias_db':round(float(np.mean(e)),3),'rmse_db':round(float(np.sqrt(np.mean(e*e))),3),'training_residual_abs_q90_db':round(q,3),'heldout_fraction_within_training_q90':round(float(np.mean(abs(e)<=q)),3)}
print(json.dumps(out,indent=2));(d/'transfer_evaluation.json').write_text(json.dumps(out,indent=2)+'\n')
