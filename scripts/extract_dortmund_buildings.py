"""Extract closed OSM building ways within Dortmund bounds from Geofabrik Arnsberg PBF.
Output is an ODbL derivative database; do not redistribute without matching terms.
"""
import argparse,hashlib,osmium,json
from shapely.geometry import Polygon
class Buildings(osmium.SimpleHandler):
 def __init__(self):super().__init__();self.out=[]
 def way(self,w):
  if 'building' not in w.tags:return
  try:
   pts=[(n.lon,n.lat) for n in w.nodes]
   if not pts or pts[0]!=pts[-1] or len(pts)<4:return
   if not any(7.40<=p[0]<=7.475 and 51.475<=p[1]<=51.51 for p in pts):return
   poly=Polygon(pts)
   if poly.is_valid and poly.area>0:self.out.append([w.id,pts])
  except osmium.InvalidLocationError:pass
args=argparse.ArgumentParser();args.add_argument('pbf');args.add_argument('output');a=args.parse_args()
assert hashlib.sha256(open(a.pbf,'rb').read()).hexdigest()=='903f2c6bef970d99646b1015465362fb380794b35a765368a1c81a6892af1675', 'Unexpected PBF'
b=Buildings();b.apply_file(a.pbf,locations=True)
with open(a.output,'w') as f:json.dump(b.out,f,separators=(',',':'))
print(len(b.out),'footprints',sum(len(p) for _,p in b.out),'vertices')
