"""Share confirmed recorded-playback readings with local overlay clients."""
from bisect import bisect_right
import math
import threading
import time


class PlaybackState:
    """The operator supplies video position; this class never advances a match clock."""

    def __init__(self, dataset, clock=time.monotonic):
        self.rows = dataset['readings']
        if not self.rows:
            raise ValueError('Recording has no readings')
        self.times = [row['t'] for row in self.rows]
        self.duration = dataset['duration']
        self.clock = clock
        self.lock = threading.Lock()
        self.position = None
        self.seen = None
        self.active = False

    def update(self, position):
        if isinstance(position, bool) or not isinstance(position, (int, float)) or not math.isfinite(position):
            raise ValueError('position must be a finite number')
        if not 0 <= position <= self.duration:
            raise ValueError('position is outside the recording')
        with self.lock:
            self.position = position
            self.seen = self.clock()
            self.active = True

    def stop(self):
        with self.lock:
            self.active = False

    def snapshot(self):
        with self.lock:
            delivery_age = None if self.seen is None else max(0, self.clock() - self.seen)
            connected = self.active and delivery_age is not None and delivery_age < 2
            row = None if self.position is None else self.rows[max(0, bisect_right(self.times, self.position) - 1)]
            values = row['values'] if row else None
            return {'values': values, 'status': row['status'] if connected else 'held' if values else 'unknown',
                    'age': row['age'] if row else None, 'position': self.position,
                    'connected': connected, 'delivery_age': delivery_age}
