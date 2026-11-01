# Experimental independent candidate state

`candidate_state.py` implements independent experimental candidate state. It is used by experiments, tests and the explicitly enabled [monitor shadow reader](shadow-reader.md). The original reader and OBS output keep their existing path. The module uses the standard library; opt-in region recognition needs optional image packages. The local evidence below records the preceding offline stage; the shadow guide records integration validation.

## Explicit layouts

The caller selects the known physical layout. A blank never selects a layout automatically:

| Selection | Required four observed slots | Canonical clock |
| --- | --- | --- |
| `mmss` | Four digits; seconds below 60 | `17:51` |
| `mss` | Observed blank, minute digit, two second digits | `09:17` |
| `seconds_tenths` | Two second digits, tenths digit, observed blank | `00:46.8` |

A missing/ambiguous digit (`None`) stays unknown, distinct from a mask reporting no retained foreground (`blank`). Non-digit values, invalid seconds and layout mismatches are rejected. A clock is parsed from four slots in one frame; previous digits are never substituted. This is the supplied scoreboard's known layout, not punctuation detection or general scoreboard support.

An explicit selection prevents a lost leading/final digit from automatically changing a four-digit clock into another format. It does not prove the selection matches the actual display. An obscured required blank or an erased glyph can still fool visual recognition within a wrongly selected layout. An operator must review layout changes; automatically detecting a safe change is not implemented.

Offline commands accept either `--clock-layout` (default `mmss`) or `--clock-layout-plan PATH`. A plan is a local JSON array of `{start, layout}` entries starting at source time zero and increasing strictly. This is a replay evaluation aid, not automatic format inference or a proposed live workflow. Unknown intervals remain unknown until the selected layout and observed slots agree.

For the new recording, the local evaluation plan selects `mmss` from zero, `mss` from 30 s, and `seconds_tenths` from 42.5 s. Those points use existing visually reviewed layout examples; they are conservative evaluation selections, not measured physical transition times. Earlier layout changes may therefore be rejected. The plan and numeric reports stay ignored and local.

## Evidence and held output

Home, away and clock have separate histories. Each exposes `observed`, confirmed `value`, `status` (`unknown`, `held`, `confirmed`), `age` in source seconds, a one-second `stale` flag and a reason when not confirming. Clock state also exposes observed/confirmed layout. No aggregate mixed-age scoreboard value is published by this module.

- Scores need two consecutive matching valid observations, including score corrections/resets. Unknown input clears that field's pending evidence without disturbing other fields.
- A stable clock normally needs two matching observations. A layout change or a jump incompatible with the last confirmed clock needs three stable observations, or three coherent observations of progression in the new clock sequence.
- A running clock can confirm the latest of three coherent observed values. All three have the same explicit layout. Pairwise and whole-window countdown movement must be nonnegative and no larger than source elapsed time plus one display quantum (1 s or 0.1 s) and 30 ms timing tolerance. Pauses are allowed. A sequence such as 46.8, 46.7, 46.6 at 0.1 s intervals confirms **46.6**, never an interpolated or extrapolated value.
- A gap longer than 0.35 s breaks pending evidence. This is an experimental threshold for the current 10 Hz input. Recovery starts with new evidence; confirmation age continues from the last acceptance.
- Source timestamps must increase strictly. Seeking requires a new state. Exact duplicate frame payloads found among the last 32 arrivals cannot confirm or refresh any field and clear pending evidence. Offline input uses full-frame SHA-256 identities. Identical pixels from a truly static camera are conservatively held too; this is not a general frozen-camera detector.
- Snapshot reads without new input hold the same values and increase age. No timer generates clock ticks, including after loss or EOF.

The rules are bounded heuristics. Repeated wrong scores or coherent wrong clocks can still confirm. The thresholds need broader footage and latency evaluation. Source time is supplied by the adapter; inaccurate capture timestamps would weaken the timing check.

## Local evidence

The original recording was regenerated: 1,638 samples, 52 uncertain raw observations, unchanged. The full application check passes 53 tests, including 14 new dependency-free candidate tests and five private-recording regressions. The separate optional suite passes 13 tests. Controlled cases cover formats and lost digits, leading blanks, invalid seconds, progression, pauses, corrections/resets, layout changes, duplicate frames/timestamps, gaps, recovery, separate freshness and no ticks during missing input. These tests do not establish recognition accuracy.

Full Regions comparisons and all translation windows were rerun for both recordings, with OCR skipped. Legacy `rows`/`metrics` retain their historical auto-format/all-fields-repeat comparison semantics. New `independent_rows`/`independent_metrics` use the explicitly selected layouts and independent state. The per-field metrics never count held output as fresh. Reports store the layout plan and rule parameters. Candidate timing now includes independent confirmation and frame hashing; it is not directly comparable to earlier recognition-only timers or live latency.

| Recording | Home fresh | Away fresh | Clock observations available | Clock fresh |
| --- | --- | --- | --- | --- |
| Original, 1,638 samples | 1,637 | 1,636 | 1,559 | 1,502 |
| New, 514 samples | 463 | 513 | 241 | 202 |

At the 11 original and 15 new reused reviewed timestamps, no fresh field confirmation was wrong. Held clocks can differ from the current display and must remain visibly held. Reviewed timestamps are sparse, reused regression anchors, not independent accuracy validation.

The new recording's 89 samples from 42.5 s onward produce **zero available or confirmed tenths clocks**: foreground boundary/fragment rejection still prevents a complete clock observation. The timed progression rule succeeds on synthetic evidence, but real-footage tenths confirmation is not demonstrated. Do not lower glyph safeguards to hide this failure. The new scores can still confirm independently during this interval.

At completion of this offline stage, monitor integration was pending. It is now available as a separate opt-in [shadow comparison](shadow-reader.md), with recorded-input boundary validation. No hardware check, live latency claim, automatic candidate output, or new runtime dependency is included in this stage. The remaining recognition work is to address the visible glyph failures with reviewed evidence before considering candidate output.
