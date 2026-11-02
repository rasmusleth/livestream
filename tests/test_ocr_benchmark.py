"""Portable freeze contract: no private recording, OCR model or image dependencies."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from experiments.ocr_benchmark import (geometry, identity, review_inventory,
                                       sample_index, verify, window_inventory, write_new, freeze, CONTRACT)


class BenchmarkContract(unittest.TestCase):
    def test_review_truth_and_unknown_are_distinct(self):
        review = {'video_sha256': 'a'*64, 'fps': 10, 'method': 'Blind source pixels',
                  'reviews': [{'t': 0, 'fields': {'home': {'value': 0},
                               'clock': {'unreadable': 'Mixed strokes'}}}]}
        rows = review_inventory(review, 'a'*64, 2)
        self.assertEqual(rows[0]['home'], {'value': 0})
        self.assertNotIn('away', rows[0])
        for change in (dict(video_sha256='b'*64), dict(fps=20), dict(method=' ')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                review_inventory({**review, **change}, 'a'*64, 2)
        for label in ({'value': None}, {'value': True}, {'value': 10},
                      {'value': 0, 'unreadable': 'mixed'}, {'unreadable': ''}):
            bad = copy.deepcopy(review)
            bad['reviews'][0]['fields']['home'] = label
            with self.subTest(label=label), self.assertRaises(ValueError):
                review_inventory(bad, 'a'*64, 2)

    def test_review_grid_duplicate_and_range(self):
        for t in (True, -.1, .05, float('nan'), .2):
            review = {'video_sha256': 'a'*64, 'fps': 10, 'method': 'Pixels',
                      'reviews': [{'t': t, 'fields': {'home': {'value': 1}}}]}
            with self.subTest(t=t), self.assertRaises(ValueError):
                review_inventory(review, 'a'*64, 2)
        with self.assertRaises(ValueError):
            sample_index(False)

    def test_complete_sequences_and_split_overlap(self):
        labels = {i: {f: {'value': '00:01' if f == 'clock' else 1}
                      for f in ('home','away','clock')} for i in range(4)}
        window = dict(id='test', start=0, end=.2, split='verification', scenario='Recovery')
        result = window_inventory([window], labels, 4)
        self.assertEqual(result[0]['counts']['home'], {'readable': 3, 'unreadable': 0})
        with self.assertRaises(ValueError):
            window_inventory([window, {**window, 'id': 'dev', 'start': .2,
                                        'end': .3, 'split': 'development'}], labels, 4)
        del labels[1]['away']
        with self.assertRaises(ValueError):
            window_inventory([window], labels, 4)
        with self.assertRaises(ValueError):
            window_inventory([{**window, 'end': .4}], labels, 4)

    def test_field_geometry_keeps_full_clock_and_maps_source(self):
        template = {'reference_size': [100,100],
                    'board_corners': [[0,0],[99,0],[99,99],[0,99]]}
        config = {'reference_size': [200,200],
                  'board_corners': [[0,0],[198,0],[198,198],[0,198]]}
        boxes = {'clock': [10,10,80,20], 'home': [10,40,20,30], 'away': [60,40,20,30]}
        result = geometry(config, template, boxes)
        self.assertEqual(result['clock']['rectified_xywh'], [10,10,80,20])
        self.assertAlmostEqual(result['clock']['source_quad'][1][0], 180)
        for bad in ({**boxes, 'clock': [10,10,100,20]},
                    {**boxes, 'clock': [10,10,-1,20]},
                    {**boxes, 'clock': [10.0,10,80,20]}):
            with self.assertRaises(ValueError):
                geometry(config, template, bad)

    def test_freeze_binds_labels_geometry_baseline_and_split(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            def save(name, value):
                path = base/name
                path.write_text(json.dumps(value))
                return str(path)
            config = {'reference_size':[100,100],
                      'board_corners':[[0,0],[99,0],[99,99],[0,99]]}
            video = base/'video'; video.write_bytes(b'synthetic private input')
            profile = save('profile.json',config)
            labels = {'video_sha256':identity(video)['sha256'], 'fps':10,
                      'method':'Prediction-free generated labels',
                      'reviews':[{'t':0, 'fields':{f:{'value':'00:01' if f=='clock' else 0}
                                  for f in ('home','away','clock')}}]}
            plan = [{'start':0,'layout':'mmss'}]
            state = {f:{'observed':None,'value':None,'status':'unknown','age':None}
                     for f in ('home','away','clock')}
            report = {'video_sha256':identity(video)['sha256'], 'fps':10,
                      'independent_rows':[{'t':0,'fields':state}], 'calibration':config,
                      'template':config,'independent_layout_plan':plan}
            record = {'id':'fixture','split':'development','video':str(video),
                      'calibration':profile,'template':profile,'samples':1,
                      'anchors':save('anchors.json',[]),'review':save('review.json',labels),
                      'layout':save('layout.json',plan),'baseline_report':save('baseline.json',report),
                      'geometry_review':str(base/'geometry-review.json'),
                      'field_boxes':{'clock':[10,10,80,20],'home':[10,40,20,30],'away':[60,40,20,30]},
                      'geometry_samples':[0], 'windows':[dict(id='one',start=0,end=0,
                                     split='development',scenario='static')]}
            recipe = {'version':1,'recordings':[record],'crop_index':str(base/'index.json')}
            recipe['_path']=save('recipe.json',recipe)
            crop = base/'crop.png';crop.write_bytes(b'generated fixture crop')
            from experiments import ocr_benchmark
            index = {'recipe':identity(recipe['_path']),'cropper':identity(ocr_benchmark.__file__),
                     'contract':identity(CONTRACT), 'inputs':{'fixture':{k:identity(record[k])
                                 for k in ('video','calibration','template')}},
                     'entries':[{'recording_id':'fixture','index':0,
                                 'crops':{f:identity(crop) for f in ('home','away','clock')}}]}
            save('index.json',index)
            save('geometry-review.json',{'recording_id':'fixture','accepted':True,
                                        'method':'Generated geometry inspection',
                                        'crop_index_sha256':identity(base/'index.json')['sha256']})
            result = freeze(recipe)
            self.assertEqual(verify(result),len(result['assets']))
            self.assertEqual(result['recordings'][0]['baseline_audit']['home']['readable_unknown'],1)
            record['split']='verification'
            with self.assertRaisesRegex(ValueError,'one OCR configuration split'):
                freeze(recipe)
            record['split']='development'
            report['template']={}
            save('baseline.json',report)
            with self.assertRaisesRegex(ValueError,'calibration/template/layout'):
                freeze(recipe)

    def test_frozen_asset_mutation_and_overwrite_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'private.json'
            write_new(path, {'label': 0})
            manifest = {'assets': [identity(path)]}
            self.assertEqual(verify(manifest), 1)
            with self.assertRaises(FileExistsError):
                write_new(path, {'label': 1})
            path.write_text('{"label": 1}\n')
            with self.assertRaisesRegex(ValueError, 'Frozen input changed'):
                verify(manifest)
