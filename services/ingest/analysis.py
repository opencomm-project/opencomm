"""DuckDB day-one analytical profile and row iterator for licensed raw CSV bytes.

This layer is in-memory on purpose; no derived source data is committed to Git.
It is an analytical sidecar to the PostGIS system of record, not a second serving DB.
"""
import tempfile
import csv
from pathlib import Path
from collections.abc import Iterator
import duckdb

REQUIRED = {"radio", "mcc", "net", "area", "cell", "lon", "lat", "samples"}

def _with_csv(payload: bytes, fn):
    with tempfile.TemporaryDirectory(prefix="opencomm-raw-") as directory:
        source = Path(directory) / "input.csv"
        source.write_bytes(payload)
        conn = duckdb.connect(":memory:")
        try:
            # Preserve original values as strings for the canonical Python validator.
            conn.execute("CREATE TEMP TABLE raw AS SELECT * FROM read_csv(?, header=true, all_varchar=true)", [str(source)])
            names = {item[0] for item in conn.execute("DESCRIBE raw").fetchall()}
            if not REQUIRED.issubset(names):
                raise ValueError("Unexpected OpenCellID CSV schema")
            return fn(conn)
        finally:
            conn.close()

def quality_profile(payload: bytes, country_mcc: int) -> dict:
    def profile(conn):
        row = conn.execute("""SELECT count(*) total_rows,
 sum(CASE WHEN try_cast(mcc AS INTEGER)=? THEN 1 ELSE 0 END) country_rows,
 sum(CASE WHEN try_cast(lat AS DOUBLE) BETWEEN -90 AND 90 AND
 try_cast(lon AS DOUBLE) BETWEEN -180 AND 180 THEN 0 ELSE 1 END) invalid_coordinates,
 sum(CASE WHEN try_cast(samples AS BIGINT)>=0 THEN 0 ELSE 1 END) invalid_samples
 FROM raw""",[country_mcc]).fetchone()
        return dict(zip(("total_rows","country_rows","invalid_coordinates","invalid_samples"),row))
    return _with_csv(payload, profile)

def iter_rows(payload: bytes) -> Iterator[dict[str,str]]:
    # Preserve each raw CSV field exactly (including leading zeros and blanks).
    # DuckDB owns the analytical quality profile; the canonical Python parser
    # receives unmodified source strings to avoid lossy type inference.
    import io
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
        raise ValueError("Unexpected OpenCellID CSV schema")
    yield from reader
