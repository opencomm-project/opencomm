# opencomm (local prototype)

Clean-room, public-data cellular infrastructure observability. Currently a **Dockerized cell-inventory API scaffold**, not measured coverage, a map UI, streaming pipeline, or deployed service. Israel (MCC 425) is the default. No proprietary employer code, data or inside material.

## Run locally

```sh
cp .env.example .env
# Edit the development password before any deployment.
docker compose up --build -d db api
curl http://localhost:8000/health
# Safe synthetic rows only:
docker compose --profile ingest run --rm ingest python -m services.ingest.cli --file tests/fixtures/synthetic_cells.csv
curl 'http://localhost:8000/v1/cells?min_lon=34&min_lat=31&max_lon=36&max_lat=33'
```

To use real data, get an API key from OpenCellID and download an authorized country CSV from its own downloads page. Save it locally under `data/` (gitignored) and run `docker compose --profile ingest run --rm ingest python -m services.ingest.cli --file /data/your-file.csv.gz`. Do not commit CSVs, tokens, or a private signed URL. No unattended scheduled download exists yet. Test parser without Docker: `python3 -m unittest discover -s tests -v`.

DuckDB performs a pre-ingest quality profile from raw CSV and feeds canonical validation; PostGIS remains the serving database. A separate measured-RF schema and endpoint are ready for UK/German source adapters, but none are implemented or loaded. See `docs/knowledge-grades.md`.

The `/v1/cells` endpoint returns bounded point estimates, a source license, timestamps, and sample counts. `truncated=true` at limit means the answer is partial. Never interpret this as a complete tower inventory, radio coverage, or signal power.

Source attribution: cell data from [OpenCellID](https://opencellid.org), [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Any derivative data release needs appropriate attribution and ShareAlike treatment. See `docs/data-sources.md` and `docs/architecture.md` for limitations and future work. Code: Apache-2.0 (see LICENSE).

## Offline country-export refresh

`scripts/refresh_opencellid.py` takes an OpenCellID country GZIP already downloaded through your own authorized access. It does not fetch data or use your token. Pass the three-digit MCC and write a separate compact inferred-inventory JSON and a provenance manifest:

```sh
python3 scripts/refresh_opencellid.py data/your-country.csv.gz \
  --mcc 232 --output data/austria-inventory.json \
  --manifest data/austria-inventory-manifest.json --min-rows 100
```

Check the reported row counts, SHA256, source date, geographic fit and license before publishing either file. The script rejects malformed and mostly invalid snapshots and writes each file with an atomic replacement, but **the pair is not an atomic publication**. Keep staged outputs outside `docs/assets/`, then publish the validated data and manifest together. Country exports are estimated cell locations, not surveyed towers or RF coverage. Do not put a download token or raw export in Git. There is no automatic downloader or schedule.
