# Static experiment, not the server API

`pages-static` is an isolated branch. GitHub Pages publishes its `/docs` folder. The server version remains untouched on `main`, tagged `v0.1-server`. Do not merge without product-owner approval.

The site loads MapLibre GL JS and DuckDB-Wasm from public CDNs. DuckDB-Wasm runs in the visitor's browser over `assets/observations.parquet`. That file has the unified observation schema and **zero rows**: no source token, approved export, or measured dataset is available yet. There are no live API calls, uploads or server. CDNs and map tiles require internet access.

When real source rights and schemas have been checked, an explicit export step should produce an appropriately attributed Parquet with rows carrying `knowledge_grade`, `source`, `source_license`, and the relevant provenance fields. Never present the synthetic fixture as live data. An empty map is the correct current result.
