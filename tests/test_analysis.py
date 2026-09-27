import unittest
from pathlib import Path
from services.ingest.analysis import quality_profile, iter_rows

FIXTURE = (Path(__file__).parent / "fixtures/synthetic_cells.csv").read_bytes()

class AnalysisTest(unittest.TestCase):
    def test_profile(self):
        self.assertEqual(quality_profile(FIXTURE,425), {"total_rows":2,"country_rows":2,"invalid_coordinates":0,"invalid_samples":0})
    def test_row_stream(self):
        rows=list(iter_rows(FIXTURE))
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["mcc"],"425")
    def test_missing_header(self):
        with self.assertRaises(ValueError): quality_profile(b"radio,mcc\nLTE,425\n",425)
if __name__ == "__main__": unittest.main()
