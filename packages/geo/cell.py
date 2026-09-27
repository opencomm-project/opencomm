"""OpenCellID CSV validation. Not RF observations or measured coverage."""
from dataclasses import dataclass
from datetime import datetime, timezone
import math

COLUMNS = ("radio", "mcc", "net", "area", "cell", "unit", "lon", "lat", "range", "samples", "changeable", "created", "updated", "averageSignal")

@dataclass(frozen=True)
class Cell:
    radio: str
    mcc: int
    mnc: int
    area: int
    cell: int
    lon: float
    lat: float
    estimated_range_m: int | None
    samples: int
    first_seen: datetime | None
    last_seen: datetime | None

def parse_cell(row: dict[str, str], mcc_filter: int | None = 425) -> Cell | None:
    mcc = int(row["mcc"])
    if mcc_filter is not None and mcc != mcc_filter:
        return None
    lat, lon = float(row["lat"]), float(row["lon"])
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("invalid coordinates")
    radio = row["radio"].strip().upper()
    if not radio:
        raise ValueError("missing radio")
    samples = int(row["samples"])
    if samples < 0:
        raise ValueError("negative samples")
    range_m = int(row["range"]) if row.get("range") else None
    if range_m is not None and range_m < 0:
        raise ValueError("negative range")
    def stamp(field: str) -> datetime | None:
        value = int(row[field]) if row.get(field) else 0
        return datetime.fromtimestamp(value, tz=timezone.utc) if value > 0 else None
    return Cell(radio, mcc, int(row["net"]), int(row["area"]), int(row["cell"]), lon, lat, range_m, samples, stamp("created"), stamp("updated"))
