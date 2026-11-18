from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh import main, transform, MEASURES
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
    def test_verified_unchanged_download_advances_only_retrieval(self):
        payload = b"sample archive"
        with TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "snapshot"
            target.mkdir()
            manifest = target / "source.json"
            original = {"edition": "2005-01-01", "retrieved": "2005-02-01",
                        "sha256": sha256(payload).hexdigest()}
            manifest.write_text(json.dumps(original))
            with patch("refresh.ROOT", root), patch("sys.argv", ["refresh.py"]), \
                 patch("refresh.current_resource", return_value=("https://example.org/data", original["edition"])), \
                 patch("refresh.download", return_value=BytesIO(payload)):
                main()
            latest = json.loads(manifest.read_text())
            self.assertGreater(latest["retrieved"], original["retrieved"])
            self.assertEqual(latest, dict(original, retrieved=latest["retrieved"]))
            self.assertEqual(list(target.iterdir()), [manifest])
