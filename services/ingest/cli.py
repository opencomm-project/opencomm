"""Explicit one-shot ingest: a local OpenCellID CSV."""
import argparse
import gzip
import hashlib
import os
from pathlib import Path
import sys
import psycopg
from services.ingest.analysis import quality_profile, iter_rows
from packages.geo.cell import parse_cell

UPSERT = """INSERT INTO cells (radio,mcc,mnc,area,cell,location,estimated_range_m,samples,first_seen,last_seen)
 VALUES (%s,%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography,%s,%s,%s,%s)
 ON CONFLICT (radio,mcc,mnc,area,cell) DO UPDATE SET
 location=EXCLUDED.location, estimated_range_m=EXCLUDED.estimated_range_m,
 samples=EXCLUDED.samples, first_seen=EXCLUDED.first_seen,last_seen=EXCLUDED.last_seen,
 imported_at=now() WHERE cells.last_seen IS NULL OR
 EXCLUDED.last_seen >= cells.last_seen"""

def load_bytes(path: str | None) -> bytes:
    if not path:
        raise ValueError("Provide --file with your own authorized OpenCellID CSV download")
    return Path(path).read_bytes()

def ingest(data: bytes, country_mcc: int, dsn: str, source: str = "OpenCellID") -> tuple[int,int]:
    digest = hashlib.sha256(data).hexdigest()
    payload = gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data
    accepted = rejected = 0
    profile = quality_profile(payload, country_mcc)
    print(f"DuckDB quality profile: {profile}")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM ingest_runs WHERE source=%s AND source_sha256=%s", (source,digest))
            if cur.fetchone():
                return 0,0
            for lineno, row in enumerate(iter_rows(payload), start=2):
                try:
                    cell = parse_cell(row, country_mcc)
                    if cell is None:
                        continue
                    cur.execute(UPSERT, (cell.radio,cell.mcc,cell.mnc,cell.area,cell.cell,cell.lon,cell.lat,cell.estimated_range_m,cell.samples,cell.first_seen,cell.last_seen))
                    accepted += 1
                except (ValueError, OverflowError, KeyError) as exc:
                    rejected += 1
                    print(f"invalid row {lineno}: {type(exc).__name__}", file=sys.stderr)
            cur.execute("INSERT INTO ingest_runs(source,source_sha256,accepted,rejected) VALUES (%s,%s,%s,%s)", (source,digest,accepted,rejected))
    return accepted,rejected

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Locally downloaded licensed OpenCellID CSV or .gz")
    parser.add_argument("--mcc", type=int, default=int(os.environ.get("SOURCE_COUNTRY_MCC","425")))
    args = parser.parse_args()
    data = load_bytes(args.file)
    print("accepted/rejected:", ingest(data,args.mcc,os.environ["DATABASE_URL"]))

if __name__ == "__main__": main()
