import gzip
import json
from pathlib import Path
import tempfile
import unittest
from scripts.refresh_opencellid import build

class RefreshTest(unittest.TestCase):
    def test_good_snapshot_and_atomic_files(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);src=base/'232.csv.gz';out=base/'inventory.json';manifest=base/'manifest.json'
            rows=['LTE,232,1,100,200,0,16.37,48.20,120,8,1,1600000000,1790000000,0',
                  'LTE,232,1,100,200,0,16.37,48.20,120,8,1,1600000000,1790000000,0',
                  'LTE,425,1,100,200,0,34.5,31.5,120,8,1,1600000000,1790000000,0']
            with gzip.open(src,'wt') as f:f.write('\n'.join(rows)+'\n')
            m=build(src,'232',out,manifest)
            self.assertEqual((m['valid_unique_cells'],m['duplicate_rows'],m['invalid_rows']),(1,1,1))
            self.assertEqual(json.loads(out.read_text())[0][:3],[16.37,48.2,'LTE'])
            self.assertEqual(json.loads(manifest.read_text())['knowledge_grade'],'inferred_inventory')
    def test_rejects_checksum_mismatch_and_invalid_threshold(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);src=base/'232.gz';out=base/'inventory.json';manifest=base/'manifest.json'
            with gzip.open(src,'wt') as f:
                f.write('LTE,232,1,100,200,0,16.37,48.20,120,8,1,1600000000,1790000000,0\n')
            for kwargs in ({'expected_sha256':'0'*64}, {'min_rows':0}, {'min_rows':2}):
                with self.assertRaises(ValueError):build(src,'232',out,manifest,**kwargs)
                self.assertFalse(out.exists());self.assertFalse(manifest.exists())
    def test_rejects_mostly_invalid_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);src=base/'232.gz';out=base/'inventory.json';manifest=base/'manifest.json'
            with gzip.open(src,'wt') as f:
                f.write('LTE,232,1,100,200,0,16.37,48.20,120,8,1,1600000000,1790000000,0\n')
                f.write('bad\ninvalid\n')
            with self.assertRaises(ValueError):build(src,'232',out,manifest)
            self.assertFalse(out.exists());self.assertFalse(manifest.exists())
    def test_rejects_bad_refresh_without_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);src=base/'bad.gz';out=base/'inventory.json';manifest=base/'manifest.json'
            out.write_text('old');manifest.write_text('old')
            with gzip.open(src,'wt') as f:f.write('LTE,425,1,100,200,0,34.5,31.5,120,8,1,1600000000,1790000000,0\n')
            with self.assertRaises(ValueError):build(src,'232',out,manifest)
            self.assertEqual(out.read_text(),'old');self.assertEqual(manifest.read_text(),'old')
if __name__=='__main__':unittest.main()
