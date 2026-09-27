"""Sampled per-serving-cell reception centers. These are NOT mast estimates.

Grouping uses (anonymized MNO, cell_index, PCI, EARFCN). No MNC/CGI is present;
identifiers may be reused and a railway trace biases all centers toward the track.
"""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPECTED='2319a9cefcd48839bf70a2198586fbb7'
def build(source,output):
 if hashlib.md5(source.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Source checksum mismatch')
 groups=defaultdict(list)
 with source.open(newline='',encoding='utf-8-sig') as f:
  for rownum,row in enumerate(csv.DictReader(f,delimiter=';'),start=2):
   if (rownum-2)%47:continue
   try:
    lat=float(row['latitude']);lon=float(row['longitude']);rsrp=float(row.get('ss_rsrp') or row.get('rsrp'))
    if not(50<=lat<=53 and 6<=lon<=9 and -160<=rsrp<=-20):continue
   except (TypeError,ValueError):continue
   key=(row['MNO'],row['cell_index'],row['physical_cellid'],row['earfcn'])
   if any(not part for part in key):continue
   groups[key].append((lon,lat,rsrp))
 features=[]
 for key,points in sorted(groups.items()):
  if len(points)<20:continue
  # Relative linear received-power weights, capped at 20 dB above group minimum
  # to avoid one extreme sample completely determining an estimated center.
  peak=max(p[2] for p in points)
  weights=[10**(max(p[2]-peak,-20)/10) for p in points]
  lon=sum(w*p[0] for w,p in zip(weights,points))/sum(weights)
  lat=sum(w*p[1] for w,p in zip(weights,points))/sum(weights)
  feature={'type':'Feature','geometry':{'type':'Point','coordinates':[round(lon,7),round(lat,7)]},'properties':{
   'knowledge_grade':'estimated_reception_center','mno_code':key[0],'cell_index':key[1],
   'physical_cellid':key[2],'earfcn':key[3],'sample_count':len(points),
   'strongest_rsrp_dbm':peak,'method':'signal-strength-weighted center of sampled receiver positions',
   'validated_tower_distance_m':None}}
  features.append(feature)
 output.parent.mkdir(parents=True,exist_ok=True)
 output.write_text(json.dumps({'type':'FeatureCollection','features':features},separators=(',',':')))
 print(len(features),'reception centers',sum(f['properties']['sample_count'] for f in features),'source samples',output.stat().st_size,'bytes')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('csv_path');p.add_argument('--output',default=str(ROOT/'docs/assets/reception-centers.geojson'))
 a=p.parse_args();build(Path(a.csv_path),Path(a.output))
