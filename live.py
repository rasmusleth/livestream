"""Server-owned continuous scoreboard state and input-worker lifetime."""
import threading
import time


class ContinuousState:
    def __init__(self, mode, source, clock=time.monotonic):
        self.mode, self.source, self.clock = mode, source, clock
        self.lock = threading.Lock()
        self.row = None
        self.seen = None
        self.running = True
        self.error = None
        self.diagnostics = ''

    def update(self, row):
        with self.lock:
            self.row = row
            self.seen = self.clock()

    def diagnostic(self, text):
        with self.lock:
            self.diagnostics = text[-4096:]

    def finish(self, error=None):
        with self.lock:
            self.running = False
            self.error = str(error)[:4096] if error else None

    def snapshot(self):
        with self.lock:
            elapsed = None if self.seen is None else max(0, self.clock() - self.seen)
            connected = self.running and elapsed is not None and elapsed < 2
            row = self.row
            values = row['values'] if row else None
            age = row['age'] + elapsed if values is not None else None
            return {'mode': self.mode, 'source': self.source, 'values': values,
                    'status': row['status'] if connected else 'held' if values else 'unknown',
                    'age': age, 'position': row['t'] if row else None, 'connected': connected,
                    'delivery_age': elapsed, 'running': self.running, 'error': self.error,
                    'diagnostics': self.diagnostics, 'observation': row}


class InputWorker:
    def __init__(self, state, rows):
        self.state = state
        self.rows = rows
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        iterator = None
        error = None
        try:
            iterator = self.rows(self.stop_event)
            for row in iterator:
                if self.stop_event.is_set():
                    break
                self.state.update(row)
        except Exception as caught:
            error = caught
        finally:
            try:
                if iterator is not None:
                    iterator.close()
            except Exception as caught:
                error = error or caught
            self.state.finish(error)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise RuntimeError('Input worker did not shut down cleanly')
