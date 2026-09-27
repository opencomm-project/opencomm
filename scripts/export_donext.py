"""Reproducible, bounded CC BY 4.0 DoNext H-Bahn sample for Pages.

Source CSV must be downloaded separately from Dataverse; no source archive is committed.
Every eligible 47th row is sampled in source order. No interpolation or invented values.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import duckdb

COLUMNS = ('source','source_license','source_url','source_record_id','knowledge_grade','country_code',
           'radio','operator_name','lon','lat','estimated_range_m','samples','measured_at',
           'rsrp_dbm','rsrq_db','sinr_db','rssi_dbm','latency_ms','downlink_mbps')
DOI='https://doi.org/10.17877/TUDODATA-2026-T6MYPO'
LICENSE='https://creativecommons.org/licenses/by/4.0/'

def number(raw, lo, hi):
    try:
        value=float(raw)
        return value if lo <= value <= hi else None
    except (TypeError,ValueError): return None

def main():
    a=argparse.ArgumentParser();a.add_argument('csv_path');a.add_argument('--output',default='docs/assets/observations.parquet');a.add_argument('--stride',type=int,default=47);args=a.parse_args()
    if args.stride<1:raise ValueError('stride must be positive')
    path=Path(args.csv_path)
    digest=hashlib.md5(path.read_bytes()).hexdigest()
    if digest!='2319a9cefcd48839bf70a2198586fbb7':raise ValueError('Source MD5 does not match Dataverse file 81633')
    db=duckdb.connect();db.execute('''CREATE TABLE observations(source VARCHAR,source_license VARCHAR,source_url VARCHAR,source_record_id VARCHAR,
knowledge_grade VARCHAR,country_code VARCHAR,radio VARCHAR,operator_name VARCHAR,lon DOUBLE,lat DOUBLE,
estimated_range_m INTEGER,samples INTEGER,measured_at TIMESTAMP,rsrp_dbm DOUBLE,rsrq_db DOUBLE,sinr_db DOUBLE,
rssi_dbm DOUBLE,latency_ms DOUBLE,downlink_mbps DOUBLE)''')
    batch=[];selected=0
    with path.open(newline='',encoding='utf-8-sig') as f:
        for rownum,row in enumerate(csv.DictReader(f,delimiter=';'),start=2):
            if (rownum-2)%args.stride:continue
            lat=number(row.get('latitude'),-90,90);lon=number(row.get('longitude'),-180,180)
            rsrp=number(row.get('ss_rsrp') or row.get('rsrp'),-160,-20)
            if None in (lat,lon,rsrp) or not 50<=lat<=53 or not 6<=lon<=9:continue
            rsrq=number(row.get('ss_rsrq') or row.get('rsrq'),-40,20)
            sinr=number(row.get('ss_sinr') or row.get('sinr'),-40,100)
            # DoNext anonymized mobile rows differ; H-Bahn has a real Unix timestamp.
            stamp=row.get('timestamp','')
            try: measured=db.execute('SELECT to_timestamp(?)::TIMESTAMP',[int(stamp)]).fetchone()[0]
            except (ValueError,TypeError): measured=None
            radio=row.get('network') or ('5G NSA' if row.get('ss_rsrp') else '4G LTE (inferred from LTE RSRP)')
            batch.append(('DoNext · TU Dortmund',LICENSE,DOI,f'H-Bahn/cell_data.csv:row-{rownum}',
                'measured_rf','DE',radio,row.get('MNO') or None,lon,lat,None,None,measured,rsrp,rsrq,sinr,
                number(row.get('rssi'),-160,20),None,None))
            selected+=1
            if len(batch)>=1000:
                db.executemany('INSERT INTO observations VALUES ('+','.join(['?']*len(COLUMNS))+')',batch);batch=[]
    if batch: db.executemany('INSERT INTO observations VALUES ('+','.join(['?']*len(COLUMNS))+')',batch)
    if selected<100:raise ValueError('Too few observations; inspect source')
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    db.execute(f"COPY observations TO '{output.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f'{selected} measured samples from MD5 {digest}; {output.stat().st_size} bytes; source rows sampled every {args.stride}')
if __name__=='__main__':main()
