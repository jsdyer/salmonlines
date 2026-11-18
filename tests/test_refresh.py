from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh import transform, MEASURES
def source(site='12', amount='0', year='2001'):
    return {'POP_ID':'19','GFE_ID':site,'ANALYSIS_YR':year,
            'SPECIES':'Coho','AREA':'29B','POPULATION':'Example','WATERBODY':'Test River','RUN_TYPE':'',
            'ADULT_PRESENCE':'NONE OBSERVED','ENUMERATION_METHODS':'Walk',
            **dict.fromkeys(MEASURES,''),'NATURAL_ADULT_SPAWNERS':amount}
class RefreshTests(unittest.TestCase):
    def test_multiple_sites_and_measures_stay_separate(self):
        _, series, ref = transform([source(),source('13','3.5'),source(amount='', year='2003')])
        self.assertEqual(ref['populations'],1)
        self.assertEqual(ref['series'],2)
        self.assertEqual(series['19-12'][0][1:5],[0,None,None,None])
        self.assertIsNone(series['19-12'][1][1])
        self.assertEqual(series['19-13'][0][1],3.5)
    def test_duplicate_population_site_and_year_blocks_refresh(self):
        with self.assertRaisesRegex(ValueError,"Multiple estimates"): transform([source(),source(amount='23')])
