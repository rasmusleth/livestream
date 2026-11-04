"""OCR orchestration invariants without models, optional dependencies or footage."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.ocr_feasibility import (check_model, native_result, percentile,
                                         provision, require_network_denied, select_samples)
from experiments.ocr_benchmark import identity, write_new


class LocalOcrSafety(unittest.TestCase):
    def test_model_missing_changed_or_extra_files_are_hard_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            model = base/'weights'
            spec = {'files':[{'name':'inference.json','bytes':1,'sha256':'0'*64}]}
            with self.assertRaisesRegex(ValueError, 'missing'):
                check_model(spec,model)
            model.mkdir();p=model/'inference.json';p.write_bytes(b'x')
            item = identity(p);spec['files']=[{'name':p.name,'bytes':item['bytes'],'sha256':item['sha256']}]
            self.assertEqual(len(check_model(spec,model)),1)
            p.write_bytes(b'y')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                check_model(spec,model)
            p.write_bytes(b'x');(model/'extra').write_bytes(b'z')
            with self.assertRaisesRegex(ValueError,'inventory'):
                check_model(spec,model)

    def test_verification_recording_cannot_enter_smoke_workload(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            crop=base/'rgb.png';crop.write_bytes(b'fixture')
            index=base/'index.json';recipe=base/'recipe.json'
            entry={'recording_id':'source','index':5,'t':.5,
                   'crops':{f:identity(crop) for f in ('home','away','clock')}}
            write_new(index,{'entries':[entry]});write_new(recipe,{'crop_index':str(index)})
            manifest={'recordings':[{'id':'source','split':'development'}],
                      'crop_export':{'recipe':{'path':str(recipe)}}}
            workload={'samples':[{'recording_id':'source','index':5}]}
            self.assertEqual(select_samples(manifest,workload),[entry])
            manifest['recordings'][0]['split']='verification'
            with self.assertRaisesRegex(ValueError,'Verification recording'):
                select_samples(manifest,workload)
            manifest['recordings'][0]['split']='development'
            workload['samples']*=2
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                select_samples(manifest,workload)
            workload['samples']=workload['samples'][:1]
            crop.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'crop changed'):
                select_samples(manifest,workload)

    def test_raw_text_confidence_and_empty_are_preserved_without_repairs(self):
        for text,score in [('O',.99),('X',.97),('19.16',.995),('',0),('10',.9),('日',.99)]:
            self.assertEqual(native_result({'rec_text':text,'rec_score':score}),
                             {'raw_text':text,'native_confidence':score})
        for text,score in [(None,.9),('0',float('nan')),('0',float('inf')),('0',True)]:
            with self.assertRaises(ValueError):
                native_result({'rec_text':text,'rec_score':score})

    def test_missing_model_cannot_trigger_implicit_download(self):
        with tempfile.TemporaryDirectory() as folder, patch('urllib.request.urlopen') as network:
            with self.assertRaises(ValueError):
                check_model({'files':[]},Path(folder)/'missing')
            network.assert_not_called()

    def test_explicit_provision_checks_hash_and_refuses_existing_directory(self):
        import io
        from experiments.ocr_benchmark import digest
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);p=base/'fixture';p.write_bytes(b'weights')
            spec={'repository':'PaddlePaddle/fixture','revision':'a'*40,
                  'files':[{'name':'inference.json','bytes':7,'sha256':digest(p)}]}
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'weights')) as network:
                provision(spec,base/'model')
                self.assertIn('/resolve/'+ 'a'*40+'/',network.call_args.args[0])
            with self.assertRaises(FileExistsError):
                provision(spec,base/'model')
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'corrupt')):
                with self.assertRaisesRegex(ValueError,'hash mismatch'):
                    provision(spec,base/'corrupt')

    def test_inference_requires_denied_network_before_optional_imports(self):
        with patch('sys.platform','linux'):
            with self.assertRaisesRegex(ValueError,'network-deny'):
                require_network_denied()
        with patch('sys.platform','darwin'), patch('ctypes.CDLL') as lib:
            lib.return_value.sandbox_check.return_value=0
            with self.assertRaisesRegex(ValueError,'Network must be denied'):
                require_network_denied()
            lib.return_value.sandbox_check.return_value=1
            require_network_denied()

    def test_nearest_rank_timings_include_slow_tail(self):
        self.assertEqual(percentile(list(range(1,22)),.95),20)
        self.assertEqual(percentile([.5,1,10],.95),10)
        with self.assertRaises(ValueError):
            percentile([],.95)
