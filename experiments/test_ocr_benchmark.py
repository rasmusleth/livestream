"""Verify RGB crop export on a tiny generated video; no private input or OCR."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import cv2
from experiments.ocr_benchmark import export


class WholeFieldExport(unittest.TestCase):
    def test_colour_geometry_sample_grid_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            video = base/'synthetic.mkv'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',
                            'color=c=0xff3000:size=100x100:rate=10:duration=0.3',
                            '-c:v','ffv1',str(video)],check=True)
            config = base/'calibration.json'
            config.write_text(json.dumps({'reference_size':[100,100],
                                          'board_corners':[[0,0],[99,0],[99,99],[0,99]]}))
            recipe = {'version':1, 'recordings':[{
                'id':'generated','video':str(video),'calibration':str(config),
                'template':str(config),'samples':3,'geometry_samples':[0],
                'windows':[{'start':.1,'end':.2}],
                'field_boxes':{'clock':[10,10,80,20], 'home':[10,40,20,30],
                               'away':[60,40,20,30]}}]}
            path = base/'recipe.json';path.write_text(json.dumps(recipe));recipe['_path']=str(path)
            result = export(recipe,base/'crops')
            self.assertEqual([e['index'] for e in result['entries']], [0,1,2])
            self.assertIn('generated',result['probes'])
            crop = cv2.imread(result['entries'][1]['crops']['clock']['path'])
            self.assertEqual(crop.shape,(20,80,3))
            # OpenCV reads BGR; no grayscale/binary masking or letter clipping.
            self.assertGreater(int(crop[0,0,2]),240)
            self.assertGreater(int(crop[0,0,1]),35)
            self.assertLess(int(crop[0,0,0]),10)
            with self.assertRaises(FileExistsError):
                export(recipe,base/'crops')
