"""Opt-in diagnostic reader. Has no reference to the overlay's confirmed state."""
import hashlib
import time
from candidate_state import CandidateState


class ShadowReader:
    def __init__(self, config, template, plan):
        # No optional imports occur unless the operator enables shadow mode.
        from region_reader import RegionReader
        self.reader = RegionReader(config, template)
        self.state = CandidateState()
        self.plan = plan
        self.size = config['reference_size']
        self.error = None
        self.evidence = None
        self.last_t = None

    def read(self, payload, t):
        before = time.monotonic()
        if self.error is None:
            try:
                width, height = self.size
                frame = self.reader.np.frombuffer(payload, self.reader.np.uint8).reshape(height,width,3)
                self.evidence = self.reader.inspect(self.reader.masks(frame))
                self.state.update(self.evidence,t,layout=self.plan.at(t),
                                  frame_id=hashlib.sha256(payload).hexdigest())
                self.last_t = t
            except Exception as error:
                # A candidate failure must never stop the established reader.
                # Stop candidate processing; retain its values with explicit age.
                self.error = str(error)[:1024] or type(error).__name__
        result = self.state.snapshot(t)
        if self.error:
            for field in result['fields'].values():
                field['status'] = 'held' if field['value'] is not None else 'unknown'
                field['reason'] = 'candidate_error'
        return {**result, 'layout':self.plan.at(t), 'evidence':self.evidence,
                'error':self.error, 'last_observation_t':self.last_t,
                'processing_ms':round((time.monotonic()-before)*1000,2)}
