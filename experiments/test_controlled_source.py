"""Optional independent candidate checks of the clean controlled source drawing."""
import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.generate_controlled_recording import Renderer,frame_state,FPS,WIDTH,HEIGHT
from region_reader import RegionReader
from candidate_state import clock_observation


class ControlledSource(unittest.TestCase):
    def test_clean_source_drawings_match_manifest_and_hidden_fields_stay_unavailable(self):
        config=json.loads((ROOT/'calibration.json').read_text())
        renderer,reader=Renderer(config),RegionReader(config,config)
        anchors=[0,*range(10,50,2),50,59,60,70,70.1,80,89.9,90,93,96,99,102,105,110,115,119]
        for t in anchors:
            with self.subTest(t=t):
                state=frame_state(round(t*FPS))
                frame=np.frombuffer(renderer.render(state),np.uint8).reshape(HEIGHT,WIDTH,3)
                evidence=reader.observe(frame)
                clock,_=clock_observation([evidence[n]['value'] for n in
                    ('minutes_tens','minutes_units','seconds_tens','seconds_units')],state['layout'])
                observed={'clock':clock.text if clock else None}
                for name in ('home','away'):
                    value=evidence[name]['value']
                    observed[name]=value if type(value) is int else None
                self.assertEqual(observed,state['visible'])


if __name__=='__main__':unittest.main()
