"""Compact browser-safe projection of the verified Parquet sample; no Wasm needed."""
import json
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1]
rows=duckdb.connect().execute("SELECT source_record_id,operator_name,radio,network_label,lon,lat,rsrp_dbm,cast(measured_at as varchar) FROM read_parquet(?) ORDER BY source_record_id",[str(ROOT/'docs/assets/observations.parquet')]).fetchall()
output=ROOT/'docs/assets/observations.json';output.write_text(json.dumps(rows,separators=(',',':'),ensure_ascii=False))
print(len(rows),output.stat().st_size,output)
