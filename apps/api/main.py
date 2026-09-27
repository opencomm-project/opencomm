"""Public-data cell inventory API. No coverage or signal claims."""
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
import psycopg
from psycopg.rows import dict_row

app = FastAPI(title="opencomm", version="0.2.0", description="Public cellular observations with explicit knowledge grades; measured RF is never inferred from OpenCellID.")
ATTRIBUTION = {"name":"OpenCellID", "url":"https://opencellid.org", "license":"https://creativecommons.org/licenses/by-sa/4.0/", "note":"Coordinates and range are estimated, not measured signal or coverage."}

@app.get("/health")
def health():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    return {"ok":True}

@app.get("/v1/cells")
def cells(min_lon: float = Query(34, ge=-180, le=180), min_lat: float = Query(29, ge=-90, le=90), max_lon: float = Query(36, ge=-180, le=180), max_lat: float = Query(34, ge=-90, le=90), limit: int = Query(500, ge=1, le=2000), radio: str | None = None):
    if min_lon >= max_lon or min_lat >= max_lat or (max_lon-min_lon)*(max_lat-min_lat) > 10:
        raise HTTPException(400, "invalid or overly broad bbox")
    query = """SELECT radio,mcc,mnc,area,cell,ST_X(location::geometry) AS lon,
 ST_Y(location::geometry) AS lat,estimated_range_m,samples,last_seen,source,knowledge_grade
 FROM cells WHERE ST_Intersects(location, ST_MakeEnvelope(%s,%s,%s,%s,4326)::geography)
 AND (%s::text IS NULL OR radio=%s) ORDER BY last_seen DESC NULLS LAST LIMIT %s"""
    with psycopg.connect(os.environ["DATABASE_URL"],row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (min_lon,min_lat,max_lon,max_lat,radio.upper() if radio else None,radio.upper() if radio else None,limit))
            records = cur.fetchall()
    return {"source":ATTRIBUTION,"knowledge_grade":"inferred_inventory","count":len(records),"truncated":len(records)==limit,"cells":[{**r,"last_seen":r["last_seen"].isoformat() if r["last_seen"] else None} for r in records]}

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>opencomm</title><style>body{font-family:system-ui;max-width:760px;margin:7vh auto;padding:1rem;background:#101b27;color:#eef6f9}a{color:#72e3d4}code{background:#26384a;padding:.15rem .4rem}h1{font-size:3rem}</style><h1>opencomm</h1><p>Open cellular infrastructure observability, starting with Israel. These are <b>estimated cell locations</b>, not measured coverage or signal strength.</p><p><a href='/docs'>Explore the API</a> · <a href='/v1/cells'>Browse estimated cells</a></p><p>Source: <a href='https://opencellid.org'>OpenCellID</a> · <a href='https://creativecommons.org/licenses/by-sa/4.0/'>CC BY-SA 4.0</a>. Data is incomplete and unevenly sampled. No private network data.</p></html>"""

@app.get("/v1/measured-rf")
def measured_rf(min_lon: float = Query(-180, ge=-180, le=180), min_lat: float = Query(-90, ge=-90, le=90), max_lon: float = Query(180, ge=-180, le=180), max_lat: float = Query(90, ge=-90, le=90), country_code: str = Query(..., min_length=2, max_length=2), limit: int = Query(500, ge=1, le=2000)):
    if min_lon >= max_lon or min_lat >= max_lat or (max_lon-min_lon)*(max_lat-min_lat) > 10:
        raise HTTPException(400, "invalid or overly broad bbox")
    query = """SELECT source,source_record_id,source_license,country_code,technology,operator_name,
 ST_X(location::geometry) AS lon,ST_Y(location::geometry) AS lat,measured_at,
 rsrp_dbm,rsrq_db,sinr_db,rssi_dbm,latency_ms,downlink_mbps,knowledge_grade
 FROM measured_rf_observations WHERE country_code=%s
 AND ST_Intersects(location,ST_MakeEnvelope(%s,%s,%s,%s,4326)::geography)
 ORDER BY measured_at DESC NULLS LAST LIMIT %s"""
    with psycopg.connect(os.environ["DATABASE_URL"],row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query,(country_code.upper(),min_lon,min_lat,max_lon,max_lat,limit))
            records=cur.fetchall()
    return {"knowledge_grade":"measured_rf","count":len(records),"truncated":len(records)==limit,
            "observations":[{**r,"measured_at":r["measured_at"].isoformat() if r["measured_at"] else None} for r in records]}
