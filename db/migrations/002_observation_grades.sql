-- Apply manually to an existing database; fresh deployments run all files in order.
ALTER TABLE cells ADD COLUMN IF NOT EXISTS knowledge_grade text NOT NULL DEFAULT 'inferred_inventory';
ALTER TABLE cells ADD CONSTRAINT cells_grade CHECK (knowledge_grade = 'inferred_inventory');
CREATE TABLE IF NOT EXISTS measured_rf_observations (
 id bigserial PRIMARY KEY,
 source text NOT NULL,
 source_record_id text NOT NULL,
 source_license text NOT NULL,
 country_code char(2) NOT NULL,
 technology text NOT NULL,
 operator_name text,
 location geography(Point,4326) NOT NULL,
 measured_at timestamptz,
 rsrp_dbm double precision,
 rsrq_db double precision,
 sinr_db double precision,
 rssi_dbm double precision,
 latency_ms double precision,
 downlink_mbps double precision,
 knowledge_grade text NOT NULL DEFAULT 'measured_rf',
 imported_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(source,source_record_id),
 CONSTRAINT measured_grade CHECK (knowledge_grade = 'measured_rf'),
 CONSTRAINT measured_metric_present CHECK (num_nonnulls(rsrp_dbm,rsrq_db,sinr_db,rssi_dbm,latency_ms,downlink_mbps) >= 1),
 CONSTRAINT measured_nonnegative CHECK ((latency_ms IS NULL OR latency_ms >= 0) AND (downlink_mbps IS NULL OR downlink_mbps >= 0))
);
CREATE INDEX IF NOT EXISTS measured_rf_geo_gist ON measured_rf_observations USING gist(location);
CREATE INDEX IF NOT EXISTS measured_rf_country_time ON measured_rf_observations(country_code,measured_at);
-- Inventory and measured RF deliberately have different identifiers and uncertainty.
-- Consumers unify through explicit grade/source metadata, never by pretending cell estimates are measurements.
