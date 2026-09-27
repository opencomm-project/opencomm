import unittest
from packages.geo.cell import parse_cell

ROW = dict(radio="LTE",mcc="425",net="01",area="10",cell="20",unit="",lon="34.8",lat="32.1",range="500",samples="4",changeable="1",created="1700000000",updated="1700000100",averageSignal="0")
class CellTest(unittest.TestCase):
    def test_parse(self):
        c = parse_cell(ROW)
        self.assertEqual((c.mcc,c.mnc,c.lon,c.samples), (425,1,34.8,4))
    def test_country_filter(self):
        self.assertIsNone(parse_cell(ROW, 310))
    def test_reject_bad_coordinates(self):
        with self.assertRaises(ValueError): parse_cell({**ROW,"lat":"nan"})
    def test_negative_samples(self):
        with self.assertRaises(ValueError): parse_cell({**ROW,"samples":"-1"})
if __name__ == "__main__": unittest.main()
