"""Recorded state delivery must preserve uncertainty and source-relative time."""
import unittest

from playback import PlaybackState


def dataset():
    return {'duration': 2, 'readings': [
        {'t': 0, 'values': None, 'status': 'unknown', 'age': None},
        {'t': .1, 'values': {'clock': '19:59', 'home': 0, 'away': 0}, 'status': 'confirmed', 'age': 0},
        {'t': 1, 'values': {'clock': '19:59', 'home': 0, 'away': 0}, 'status': 'held', 'age': .9},
        {'t': 1.5, 'values': {'clock': '19:58', 'home': 0, 'away': 1}, 'status': 'confirmed', 'age': 0},
    ]}


class PlaybackDelivery(unittest.TestCase):
    def setUp(self):
        self.now = 10
        self.state = PlaybackState(dataset(), clock=lambda: self.now)

    def test_startup_is_unknown_without_invented_zeroes(self):
        self.assertIsNone(self.state.snapshot()['values'])
        self.assertFalse(self.state.snapshot()['connected'])
        self.state.update(0)
        self.assertIsNone(self.state.snapshot()['values'])

    def test_seeking_backwards_selects_the_source_reading(self):
        self.state.update(1.5)
        self.assertEqual(self.state.snapshot()['values']['away'], 1)
        self.state.update(.3)
        self.assertEqual(self.state.snapshot()['values']['away'], 0)
        self.assertEqual(self.state.snapshot()['values']['clock'], '19:59')

    def test_clock_never_advances_with_wall_time(self):
        self.state.update(.1)
        self.now += 1
        self.assertEqual(self.state.snapshot()['values']['clock'], '19:59')
        self.assertTrue(self.state.snapshot()['connected'])
        self.state.update(.1)  # Heartbeat during paused playback.
        self.assertEqual(self.state.snapshot()['age'], 0)

    def test_lost_publisher_holds_values_then_recovers(self):
        self.state.update(.1)
        self.now += 2
        held = self.state.snapshot()
        self.assertFalse(held['connected'])
        self.assertEqual(held['status'], 'held')
        self.assertEqual(held['values']['clock'], '19:59')
        self.state.update(1.5)
        self.assertTrue(self.state.snapshot()['connected'])
        self.assertEqual(self.state.snapshot()['values']['away'], 1)

    def test_stop_keeps_last_reading_and_marks_it_held(self):
        self.state.update(.1)
        self.state.stop()
        self.assertFalse(self.state.snapshot()['connected'])
        self.assertEqual(self.state.snapshot()['status'], 'held')
        self.assertEqual(self.state.snapshot()['values']['clock'], '19:59')

    def test_invalid_position_does_not_change_published_state(self):
        self.state.update(.1)
        for position in (True, '1', float('nan'), float('inf'), -1, 2.1):
            with self.subTest(position=position), self.assertRaises(ValueError):
                self.state.update(position)
        self.assertEqual(self.state.snapshot()['position'], .1)


if __name__ == '__main__':
    unittest.main()
