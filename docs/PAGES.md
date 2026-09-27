# Static measured-data experiment, not the server API

`pages-static` is an isolated branch, served from `/docs`. The server stays on `main`, tagged `v0.1-server`; do not merge without product-owner approval.

The browser loads MapLibre GL JS and DuckDB-Wasm from public CDNs; DuckDB queries `assets/observations.parquet` locally. This Parquet holds 10,148 *real* sampled DoNext H-Bahn `cell_data.csv` RF points, one route near Dortmund, Germany. Dataset: Schippers, H.; Geis, M.; Böcker, S.; Wietfeld, C. (2026), DoNext, TUDOdata V2, https://doi.org/10.17877/TUDODATA-2026-T6MYPO . License: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ . Related article: https://doi.org/10.1109/TMLCN.2025.3564239 .

The raw public CSV is Dataverse file 81633 (`https://data.tu-dortmund.de/api/access/datafile/81633`), published MD5 `2319a9cefcd48839bf70a2198586fbb7`. Rebuild from a verified download with `PYTHONPATH=<duckdb package path> python3 scripts/export_donext.py /path/to/cell_data.csv`. The exporter takes every 47th source row, retains valid WGS84 points with an observed RSRP, checks a Germany bounding box and keeps source row IDs, unit, grade, license, and time. It does not interpolate or infer RF. Source CSV is not committed. The Parquet is a bounded demo extract, not the complete source dataset or comprehensive coverage.

No UK Ofcom points have been loaded: Ofcom's general open-data policy is not proof of this specific file's terms, and direct download is currently inaccessible here. No Israeli OpenCellID points have been loaded pending account/token and authorized export. No synthetic test points are shown. There are no live API calls, uploads, or server-side PostGIS on this branch.

## SEO and map architecture

The Pages branch has canonical URLs, descriptive meta tags, Open Graph, Dataset JSON-LD, sitemap/robots, `llms.txt`, a method page and a source-linked comparison page. Names of other services and operators are contextual comparisons, not claimed integrations or affiliations. MapLibre remains the base map. Add deck.gl *as an overlay*, not a rewrite, if future dense OpenCellID extracts need hexbin/H3 aggregation; today's capped 2,000-point sample query does not require it.
