"""Experimental, dependency-free candidate state. Never imported by runtime output."""
from collections import deque
from dataclasses import dataclass
import math

LAYOUTS = ('mmss', 'mss', 'seconds_tenths')
CLOCK_SLOTS = ('minutes_tens', 'minutes_units', 'seconds_tens', 'seconds_units')
MAX_GAP = .35
TIMING_TOLERANCE = .03
FRAME_HISTORY = 32


class LayoutPlan:
    """Explicit operator-selected layout, optionally scheduled for offline review."""
    def __init__(self, entries):
        if not isinstance(entries, list) or not entries:
            raise ValueError('Expected a nonempty clock-layout plan')
        self.entries = []
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {'start', 'layout'}:
                raise ValueError('Each layout entry needs start and layout')
            start, layout = entry['start'], entry['layout']
            if type(start) not in (int, float) or not math.isfinite(start) or start < 0 or layout not in LAYOUTS:
                raise ValueError('Invalid layout entry')
            if not self.entries and start != 0 or self.entries and start <= self.entries[-1]['start']:
                raise ValueError('Layout plan must start at zero and increase strictly')
            self.entries.append(dict(entry))

    def at(self, t):
        if type(t) not in (int, float) or not math.isfinite(t) or t < 0:
            raise ValueError('Expected nonnegative source time')
        return next(entry['layout'] for entry in reversed(self.entries) if entry['start'] <= t)


def digit(value):
    return type(value) is int and 0 <= value <= 9


@dataclass(frozen=True)
class ClockObservation:
    text: str
    ticks: int  # Integer tenths; this is an observed value, never a ticking timer.
    layout: str


def clock_observation(slots, layout):
    """Parse one frame in an explicitly selected layout; never infer from blanks."""
    if layout not in LAYOUTS:
        raise ValueError('Choose an explicit supported clock layout')
    if len(slots) != 4:
        raise ValueError('Expected four clock slots from one frame')
    if any(value is None for value in slots):
        return None, 'unknown_digit'
    a, b, c, d = slots
    if layout == 'mmss' and all(digit(v) for v in slots):
        minutes, seconds = 10*a+b, 10*c+d
        if seconds < 60:
            return ClockObservation(f'{minutes:02}:{seconds:02}', (minutes*60+seconds)*10, layout), None
        return None, 'invalid_seconds'
    if layout == 'mss' and a == 'blank' and all(digit(v) for v in (b,c,d)):
        seconds = 10*c+d
        if seconds < 60:
            return ClockObservation(f'0{b}:{seconds:02}', (b*60+seconds)*10, layout), None
        return None, 'invalid_seconds'
    if layout == 'seconds_tenths' and d == 'blank' and all(digit(v) for v in (a,b,c)):
        seconds = 10*a+b
        if seconds < 60:
            return ClockObservation(f'00:{seconds:02}.{c}', seconds*10+c, layout), None
        return None, 'invalid_seconds'
    return None, 'layout_mismatch'


class FieldState:
    def __init__(self, clock=False):
        self.clock = clock
        self.pending = deque(maxlen=3)
        self.value = None
        self.at = None
        self.observed = None
        self.reason = 'no_observation'
        self.accepted = False

    def reset_evidence(self, reason):
        self.pending.clear()
        self.accepted = False
        self.reason = reason

    @staticmethod
    def compatible(a, b, dt):
        if a.layout != b.layout:
            return False
        # Pauses and quantization are allowed. A countdown cannot move faster
        # than source time plus one display quantum and 30 ms timing tolerance.
        quantum = 1 if a.layout == 'seconds_tenths' else 10
        return 0 <= a.ticks-b.ticks <= (dt+TIMING_TOLERANCE)*10+quantum+1e-9

    def update(self, observed, t, reason=None):
        self.observed = observed
        self.accepted = False
        if observed is None:
            self.reset_evidence(reason or 'unavailable')
            return
        pending_reason = 'awaiting_evidence'
        if self.pending:
            previous, at = self.pending[-1]
            if t-at > MAX_GAP+1e-9:
                self.pending.clear()
                pending_reason = 'source_gap'
            elif self.clock and not self.compatible(previous, observed, t-at):
                self.pending.clear()
                pending_reason = 'layout_change' if previous.layout != observed.layout else 'clock_discontinuity'
            elif not self.clock and observed != previous:
                self.pending.clear()
        self.pending.append((observed, t))
        values = [value for value, _ in self.pending]
        stable = len(values) >= 2 and values[-1] == values[-2]
        if not self.clock:
            self.accepted = stable
        else:
            # A correction/reset or explicit layout change needs a third piece
            # of evidence. No digit from an older frame is used to form a clock.
            discontinuity = self.value is not None and not self.compatible(
                self.value, observed, t-self.at)
            if discontinuity:
                pending_reason = 'clock_correction_pending'
            stable = stable and (not discontinuity or len(values) == 3 and len(set(values)) == 1)
            progression = (len(values) == 3 and values[0].ticks > values[-1].ticks
                           and self.compatible(values[0], values[-1], t-self.pending[0][1]))
            self.accepted = stable or progression
        self.reason = None if self.accepted else pending_reason
        if self.accepted:
            self.value, self.at = observed, t

    def snapshot(self, t):
        def public(value):
            return value.text if isinstance(value, ClockObservation) else value
        return {'observed': public(self.observed), 'value': public(self.value),
                'layout': self.value.layout if isinstance(self.value, ClockObservation) else None,
                'observed_layout': self.observed.layout if isinstance(self.observed, ClockObservation) else None,
                'status': 'confirmed' if self.accepted else 'held' if self.value is not None else 'unknown',
                'age': None if self.at is None else round(t-self.at, 3),
                'stale': self.at is not None and t-self.at >= 1,
                'reason': self.reason}


class CandidateState:
    """Independent field evidence; caller supplies source time and frame identity."""
    def __init__(self):
        self.fields = {name: FieldState(clock=name == 'clock') for name in ('home','away','clock')}
        self.t = None
        self.recent_frames = deque(maxlen=FRAME_HISTORY)

    def update(self, evidence, t, *, layout, frame_id):
        clock, clock_reason = clock_observation([evidence[name]['value'] for name in CLOCK_SLOTS], layout)
        observations = {'clock': clock}
        reasons = {'clock': clock_reason}
        for name in ('home', 'away'):
            value = evidence[name]['value']
            observations[name] = value if digit(value) else None
            reasons[name] = evidence[name].get('reason') or 'unavailable'
        return self.update_observations(observations, t, reasons=reasons, frame_id=frame_id)

    def update_observations(self, observations, t, *, reasons, frame_id):
        """Confirm parsed whole-field values; None carries an explicit rejection reason."""
        if type(t) not in (int, float) or not math.isfinite(t) or t < 0:
            raise ValueError('Expected nonnegative finite source time')
        if self.t is not None and t <= self.t:
            raise ValueError('Source time must increase; start a new state after seeking')
        if not isinstance(frame_id, str) or not frame_id:
            raise ValueError('Expected stable source-frame identity')
        if observations.keys() != self.fields.keys() or reasons.keys() != self.fields.keys():
            raise ValueError('Expected all three named observations and reasons')
        for name, value in observations.items():
            if value is None:
                if not isinstance(reasons[name], str) or not reasons[name]:
                    raise ValueError('Missing observations need a reason')
            elif name == 'clock':
                if not isinstance(value, ClockObservation) or value.layout not in LAYOUTS:
                    raise ValueError('Expected a parsed clock observation')
            elif not digit(value):
                raise ValueError('Expected a one-digit score observation')
        duplicate = frame_id in self.recent_frames
        self.recent_frames.append(frame_id)
        self.t = t
        for name, field in self.fields.items():
            if duplicate:
                field.observed = observations[name]
                field.reset_evidence('duplicate_frame')
            else:
                field.update(observations[name], t, reasons[name])
        return self.snapshot(t)

    def snapshot(self, t):
        if type(t) not in (int, float) or not math.isfinite(t) or t < 0 or self.t is not None and t < self.t:
            raise ValueError('Snapshot must not precede the last observation')
        result = {}
        for name, field in self.fields.items():
            state = field.snapshot(t)
            # A read without a new source frame is explicitly held, even though
            # its value is unchanged. Never refresh confirmation age by polling.
            if self.t is not None and t > self.t:
                state['status'] = 'held' if field.value is not None else 'unknown'
                state['reason'] = 'no_new_frame'
            result[name] = state
        return {'t': t, 'fields': result}
