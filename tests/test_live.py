"""Continuous state uses frame arrivals, without a publishing browser or clock extrapolation."""
import threading
import unittest

from live import ContinuousState, InputWorker


class ContinuousDelivery(unittest.TestCase):
    def setUp(self):
        self.now = 10
        self.state = ContinuousState('camera', 'test camera', clock=lambda: self.now)
        self.row = {'t': .1, 'values': {'clock': '19:59', 'home': 0, 'away': 0},
                    'status': 'confirmed', 'age': 0}

    def test_preview_is_bounded_immutable_and_ages_after_input_ends(self):
        self.assertIsNone(self.state.preview_snapshot())
        frame = bytearray([1, 2, 3])
        self.state.update_preview(frame, 1, 1)
        frame[0] = 9
        self.assertEqual(self.state.preview_snapshot(), (b'\x01\x02\x03', 1, 1, 1, 0))
        self.state.update_preview(b'abc', 1, 1)
        self.state.finish()
        self.now += 3
        self.assertEqual(self.state.preview_snapshot(), (b'abc', 1, 1, 2, 3))
        self.assertEqual(self.state.snapshot()['preview'], {'available': True, 'sequence': 2, 'age': 3})
        with self.assertRaises(ValueError):
            self.state.update_preview(b'ab', 1, 1)

    def test_startup_never_invents_values(self):
        state = self.state.snapshot()
        self.assertIsNone(state['values'])
        self.assertFalse(state['connected'])
        self.assertTrue(state['running'])

    def test_missing_frames_hold_values_and_increase_real_age(self):
        self.state.update(self.row)
        self.now += 2
        state = self.state.snapshot()
        self.assertFalse(state['connected'])
        self.assertEqual(state['status'], 'held')
        self.assertEqual(state['values']['clock'], '19:59')
        self.assertEqual(state['age'], 2)
        self.assertEqual(state['position'], .1)
        self.state.update(self.row)
        self.assertTrue(self.state.snapshot()['connected'])
        self.assertEqual(self.state.snapshot()['age'], 0)

    def test_end_or_error_preserves_reading(self):
        self.state.update(self.row)
        self.state.finish(RuntimeError('Device disconnected'))
        state = self.state.snapshot()
        self.assertFalse(state['connected'])
        self.assertEqual(state['values'], self.row['values'])
        self.assertEqual(state['error'], 'Device disconnected')

    def test_worker_can_finish_without_any_browser(self):
        def rows(stop):
            yield self.row
        worker = InputWorker(self.state, rows)
        worker.start()
        worker.thread.join(timeout=2)
        self.assertFalse(worker.thread.is_alive())
        state = self.state.snapshot()
        self.assertEqual(state['values'], self.row['values'])
        self.assertFalse(state['running'])
        self.assertFalse(state['connected'])

    def test_stopping_worker_closes_source(self):
        started, closed = threading.Event(), threading.Event()
        def rows(stop):
            try:
                started.set()
                yield self.row
                stop.wait(2)
            finally:
                closed.set()
        worker = InputWorker(self.state, rows)
        worker.start()
        self.assertTrue(started.wait(1))
        worker.stop()
        self.assertTrue(closed.is_set())
        self.assertFalse(self.state.snapshot()['running'])

    def test_worker_reports_input_failure(self):
        def rows(stop):
            raise OSError('Input unavailable')
            yield
        worker = InputWorker(self.state, rows)
        worker.start()
        worker.thread.join(timeout=2)
        self.assertEqual(self.state.snapshot()['error'], 'Input unavailable')
        self.assertIsNone(self.state.snapshot()['values'])


if __name__ == '__main__':
    unittest.main()
