"""Shadow lifecycle, failure isolation and default dependency boundary."""
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from candidate_state import LayoutPlan
from live import ContinuousState
from shadow import ShadowReader


class ShadowSafety(unittest.TestCase):
    def test_default_imports_do_not_load_image_packages(self):
        subprocess.run([sys.executable,'-c',
            "import sys,server,capture; assert 'cv2' not in sys.modules; assert 'numpy' not in sys.modules"],check=True)

    def test_shadow_holds_and_ages_after_eof_without_changing_output(self):
        now=[0]
        source=ContinuousState('recording','fixture',clock=lambda:now[0],shadow=True)
        source.update({'t':0,'values':{'clock':'19:59','home':0,'away':0},'status':'confirmed','age':0})
        row={'t':0,'fields':{'clock':{'observed':'00:46.6','value':'00:46.6','age':0,
                                    'status':'confirmed','reason':None,'stale':False}}}
        source.update_shadow(row)
        row['fields']['clock']['value']='00:00.0'
        source.finish()
        now[0]=3
        shadow=source.shadow_snapshot()
        field=shadow['candidate']['fields']['clock']
        self.assertEqual(field['value'],'00:46.6')
        self.assertEqual(field['age'],3)
        self.assertEqual(field['status'],'held')
        self.assertTrue(field['stale'])
        self.assertFalse(shadow['output_enabled'])
        self.assertEqual(source.snapshot()['values']['clock'],'19:59')
        field['value']='modified snapshot'
        self.assertEqual(source.shadow_snapshot()['candidate']['fields']['clock']['value'],'00:46.6')

    def test_candidate_failure_stops_only_candidate_and_holds_previous_values(self):
        names=('minutes_tens','minutes_units','seconds_tens','seconds_units','home','away')
        evidence={name:{'value':value} for name,value in zip(names,(1,7,5,1,0,1))}
        fake=SimpleNamespace(np=SimpleNamespace(uint8=None,frombuffer=lambda *a:SimpleNamespace(reshape=lambda *a:None)),
                             masks=lambda frame:None,inspect=lambda masks:evidence)
        with patch('region_reader.RegionReader',return_value=fake):
            reader=ShadowReader({'reference_size':[2,2]}, {}, LayoutPlan([{'start':0,'layout':'mmss'}]))
        reader.read(b'a',0)
        confirmed=reader.read(b'b',.1)
        self.assertEqual(confirmed['fields']['clock']['value'],'17:51')
        fake.inspect=lambda masks: (_ for _ in ()).throw(ValueError('deliberate candidate failure'))
        failed=reader.read(b'c',.2)
        self.assertIn('deliberate',failed['error'])
        self.assertEqual(failed['fields']['clock']['status'],'held')
        self.assertEqual(failed['fields']['clock']['value'],'17:51')
        self.assertEqual(reader.read(b'd',2)['fields']['clock']['age'],1.9)
        self.assertEqual(reader.last_t,.1)


if __name__=='__main__':unittest.main()
