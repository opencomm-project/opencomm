"""Reproduce separate OpenCellID Israel inventory (CC BY-SA 4.0).

Download the MCC 425 CSV/GZIP with your private token. NEVER commit source or token.
These are estimated cell positions, not surveyed masts or measured signal.
"""
import argparse,csv,gzip,hashlib,json
from pathlib import Path
EXPECTED='1f389f22013a7acbc22565c470d616e4fdcf2c36fb2cf22212f9dd59014cc829'
def main():
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--output',default='docs/assets/israel-inventory.json');a=p.parse_args();source=Path(a.source)
 digest=hashlib.sha256(source.read_bytes()).hexdigest()
 if digest!=EXPECTED:raise ValueError('Not the verified 2026-09-27 MCC 425 export')
 records=[];seen=set();invalid=0
 with gzip.open(source,'rt',newline='') as f:
  for row in csv.reader(f):
   try:
    radio,mcc,mnc,area,cell,unit,lon,lat,rg,samples,changeable,created,updated,avg=row[:14]
    if mcc!='425' or radio not in ('GSM','UMTS','LTE','NR'):raise ValueError('Unexpected MCC/radio')
    lo,la=float(lon),float(lat);n=int(samples);radius=int(rg)
    if not(34<=lo<=36 and 29<=la<=34 and n>=1 and radius>=0):raise ValueError('Coordinates/metadata out of bounds')
    key=(radio,mcc,mnc,area,cell)
    if key in seen:continue
    seen.add(key)
    # Value array keeps separate source-license stream compact. No secret enters output.
    records.append([round(lo,6),round(la,6),radio,mnc,area,cell,n,radius,int(updated)])
   except (ValueError,IndexError):invalid+=1
 output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
 output.write_text(json.dumps(records,separators=(',',':')))
 print(f'{len(records)} unique cells, {invalid} rejected, {output.stat().st_size} bytes; source SHA256 {digest}')
if __name__=='__main__':main()
