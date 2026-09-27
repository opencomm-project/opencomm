CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS cells (
  radio text NOT NULL, mcc integer NOT NULL, mnc integer NOT NULL,
  area bigint NOT NULL, cell bigint NOT NULL,
  location geography(Point,4326) NOT NULL,
  estimated_range_m integer, samples integer NOT NULL,
  first_seen timestamptz, last_seen timestamptz,
  imported_at timestamptz NOT NULL DEFAULT now(),
  source text NOT NULL DEFAULT 'OpenCellID',
  PRIMARY KEY (radio,mcc,mnc,area,cell),
  CONSTRAINT valid_samples CHECK (samples >= 0),
  CONSTRAINT valid_range CHECK (estimated_range_m IS NULL OR estimated_range_m >= 0)
);
CREATE INDEX IF NOT EXISTS cells_geo_gist ON cells USING gist(location);
CREATE INDEX IF NOT EXISTS cells_updated ON cells(last_seen);
CREATE TABLE IF NOT EXISTS ingest_runs (
 id bigserial PRIMARY KEY, source text NOT NULL, source_sha256 text NOT NULL,
 ingested_at timestamptz NOT NULL DEFAULT now(), accepted integer NOT NULL,
 rejected integer NOT NULL, UNIQUE (source,source_sha256)
);
