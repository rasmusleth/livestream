"""Test the overlay transport and preserve video seeking over real local HTTP."""
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest

from playback import PlaybackState
from live import ContinuousState
from server import Handler
from test_playback import dataset


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class OverlayHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='livestream-http-')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.server.video = Path(cls.temporary.name) / 'test.mp4'
        cls.server.video.write_bytes(b'0123456789')
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temporary.cleanup()

    def setUp(self):
        self.server.playback = PlaybackState(dataset())
        self.server.source = None

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_overlay_reads_server_selected_state(self):
        status, _, body = self.request('POST', '/api/playback', json.dumps({'position': 1.5}),
                                       {'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['values']['away'], 1)
        status, headers, body = self.request('GET', '/api/state')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(json.loads(body)['values']['clock'], '19:58')
        status, _, body = self.request('POST', '/api/playback', '{"position":null}',
                                       {'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)['connected'])
        self.assertEqual(json.loads(body)['values']['away'], 1)

    def test_invalid_or_cross_origin_updates_are_rejected(self):
        for body in ('{}', 'not json', '{"position":-1}', '{"position":NaN}', '{"position":true}'):
            with self.subTest(body=body):
                self.assertEqual(self.request('POST', '/api/playback', body,
                                               {'Content-Type': 'application/json'})[0], 400)
        self.assertEqual(self.request('POST', '/api/playback', '{"position":1}',
            {'Content-Type': 'application/json', 'Origin': 'https://example.org'})[0], 403)
        self.assertIsNone(self.server.playback.snapshot()['values'])

    def test_routes_remain_allowlisted(self):
        self.assertEqual(self.request('GET', '/overlay')[0], 200)
        self.assertEqual(self.request('GET', '/overlay.js')[0], 200)
        self.assertEqual(self.request('GET', '/.git/config')[0], 404)
        self.assertEqual(self.request('POST', '/other', '{}')[0], 404)

    def test_continuous_input_cannot_be_overwritten_by_a_playback_tab(self):
        self.server.source = ContinuousState('recording', 'test recording')
        self.server.source.update(dataset()['readings'][1])
        status, _, body = self.request('GET', '/api/state')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['values']['clock'], '19:59')
        status, _, _ = self.request('POST', '/api/playback', '{"position":1.5}',
                                    {'Content-Type': 'application/json'})
        self.assertEqual(status, 409)
        self.assertEqual(self.server.source.snapshot()['values']['away'], 0)
        self.assertEqual(self.request('GET', '/readings.json')[0], 404)
        self.assertIn(b'Continuous input', self.request('GET', '/')[2])

    def test_preview_endpoints_are_read_only_and_continuous_only(self):
        for route in ('/api/preview', '/api/calibration'):
            self.assertEqual(self.request('GET', route)[0], 404)
        self.server.source = ContinuousState('recording', 'fixture')
        self.server.calibration = {'reference_size': [2, 2]}
        self.server.calibration_name = 'fixture.json'
        self.assertEqual(self.request('GET', '/api/preview')[0], 204)
        self.server.source.update_preview(b'abc', 1, 1)
        status, headers, body = self.request('GET', '/api/preview')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'abc')
        self.assertEqual(headers['X-Preview-Width'], '1')
        self.assertEqual(headers['X-Preview-Height'], '1')
        self.assertEqual(headers['X-Preview-Sequence'], '1')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertGreaterEqual(float(headers['X-Preview-Age']), 0)
        self.assertEqual(json.loads(self.request('GET', '/api/calibration')[2]),
                         {'profile': 'fixture.json', 'config': self.server.calibration})
        self.assertEqual(self.request('POST', '/api/calibration', '{}')[0], 404)

    def test_video_ranges_still_allow_seeking(self):
        status, headers, body = self.request('GET', '/video', headers={'Range': 'bytes=2-5'})
        self.assertEqual(status, 206)
        self.assertEqual(headers['Content-Range'], 'bytes 2-5/10')
        self.assertEqual(body, b'2345')


if __name__ == '__main__':
    unittest.main()
