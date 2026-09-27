"""Validate an OpenCellID country snapshot and atomically replace a local extract.

Offline stage only. Download at most twice/day using the owner's token from the
vendor's download page; keep token and raw input out of Git. Source is CC BY-SA 4.0.
A scheduled fetch must be wired to an authorized persistent runner separately.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile

RADIOS = {'GSM', 'UMTS', 'LTE', 'NR', 'CDMA'}


def build(source: Path, mcc: str, output: Path, manifest: Path, *, min_rows=1, expected_sha256=None):
    if not (mcc.isascii() and mcc.isdigit() and len(mcc) == 3):
        raise ValueError('MCC must be three ASCII digits')
    if source.resolve() in (output.resolve(), manifest.resolve()):
        raise ValueError('Source and output paths must differ')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if expected_sha256 and digest.lower() != expected_sha256.lower():
        raise ValueError('Source SHA256 mismatch')
    records, seen, invalid, duplicate, raw_rows = [], set(), 0, 0, 0
    with gzip.open(source, 'rt', newline='', encoding='utf-8') as fh:
        for row in csv.reader(fh):
            raw_rows += 1
            if len(row) != 14:
                invalid += 1
                continue
            try:
                radio, country, net, area, cell, _unit, lon, lat, radius, samples, _changeable, _created, updated, _signal = row
                if country != mcc or radio not in RADIOS:
                    raise ValueError('Wrong country or radio')
                lon, lat = float(lon), float(lat)
                # Null Island is a known missing-coordinate sentinel, not an observed cell.
                if not (-180 <= lon <= 180 and -90 <= lat <= 90) or (lon == 0 and lat == 0):
                    raise ValueError('Invalid position')
                if any(x.strip() == '' for x in (net, area, cell)):
                    raise ValueError('Missing network identity')
                samples, radius, updated = int(samples), int(radius), int(updated)
                if samples < 1 or radius < 0 or updated < 1:
                    raise ValueError('Invalid source metadata')
                key = (radio, country, net, area, cell)
                if key in seen:
                    duplicate += 1
                    continue
                seen.add(key)
                records.append([round(lon, 6), round(lat, 6), radio, net, area, cell, samples, radius, updated])
            except (ValueError, TypeError):
                invalid += 1
    if min_rows < 1:
        raise ValueError("min_rows must be positive")
    if len(records) < min_rows or raw_rows and invalid > raw_rows * .5:
        raise ValueError(f'Rejected suspect snapshot: {len(records)} valid of {raw_rows} raw, {invalid} invalid')
    metadata = {
        'source': 'OpenCellID country export', 'source_url': 'https://opencellid.org/downloads.php',
        'source_license': 'CC BY-SA 4.0', 'knowledge_grade': 'inferred_inventory',
        'mcc': mcc, 'source_sha256': digest, 'source_rows': raw_rows,
        'valid_unique_cells': len(records), 'invalid_rows': invalid, 'duplicate_rows': duplicate,
        'latest_cell_updated_unix': max(r[-1] for r in records),
        'meaning': 'Estimated cell positions, not towers, measured RF, or coverage.',
    }
    # Each replacement is atomic; the pair is not. Stage both before touching either output.
    staged = []
    try:
        for path, payload in ((output, json.dumps(records, separators=(',', ':'))),
                              (manifest, json.dumps(metadata, indent=2) + '\n')):
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile('w', dir=path.parent, prefix='.' + path.name, delete=False) as temp:
                temp.write(payload)
                staged.append((path, Path(temp.name)))
        for path, temp in staged:
            os.replace(temp, path)
    finally:
        for _, temp in staged:
            temp.unlink(missing_ok=True)
    return metadata


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--mcc', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--min-rows', type=int, default=100)
    p.add_argument('--expected-sha256')
    args = p.parse_args()
    print(json.dumps(build(args.source, args.mcc, args.output, args.manifest,
                           min_rows=args.min_rows, expected_sha256=args.expected_sha256), indent=2))


if __name__ == '__main__':
    main()
