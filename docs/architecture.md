# Architecture and constraints

Current execution path: operator obtains OpenCellID country download and runs one-shot ingest -> schema validation -> idempotent upsert with timestamp guard into PostGIS -> bounded API bbox -> provenance-aware landing page. Default MCC 425 is Israel, but set SOURCE_COUNTRY_MCC for other countries. Docker Compose only runs API and DB by default; ingest profile is manually triggered and not automatically scheduled. No live stream, ML model, H3 rollup, object store, or actual interactive map yet. Do not claim these exist.

Proposed phase 2: persist immutable raw snapshot with SHA-256 manifest; download daily diffs, reconcile deletions against periodic full snapshots; quarantine invalid input; add H3 aggregation with suppression of sparse tiles; MapLibre and locally permissible basemap; opt-in measurement collector with privacy protections and independent license; spatially held-out anomaly evaluation. Redpanda event-time stream and PySpark benchmarking only once representative scale or opt-in observations warrant them.

Do not combine OpenCellID-derived data with other datasets into a public export without reviewing ShareAlike and source rights. Keep code under Apache-2.0 and data under source-specific terms. No employer source, credentials, schemas, internal know-how, or proprietary data.
