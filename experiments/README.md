# Local recognition experiments

These scripts compare candidates offline. They do not modify calibration files, start a camera, publish values, or change the server. See [the findings](../docs/recognition-comparison.md) for results and limits.

Use a separate environment with Python 3.12, FFmpeg/ffprobe, and local Tesseract (tested with 5.5.1 and English data):

```sh
python3 -m venv /tmp/livestream-recognition-venv
/tmp/livestream-recognition-venv/bin/python -m pip install -r experiments/requirements.txt
/tmp/livestream-recognition-venv/bin/python -m unittest discover -s experiments -p 'test_*.py' -v
```

OpenCV/NumPy are shared optional dependencies for experiments and opt-in shadow mode; default application setup does not require them. The standard repository check compiles these files without importing them; it runs the application and dependency-free candidate-state tests. The 17 experiment tests require this environment and are run separately.

Keep recordings, local profiles, labels, and outputs in ignored local paths. The original benchmark uses tracked `calibration.json`; the new one needs the saved profile matching its framing. Preserve a copy of that profile before further edits. Our local copy is `data/recognition-live-calibration.json`; do not substitute a calibration made for another framing.

Labels are visually inspected values for exact FFmpeg sample indices on a 10 Hz grid, with synthetic example structure:

```json
[
  {
    "t": 2.5,
    "values": { "clock": "19:58", "home": 0, "away": 0 },
    "split": "heldout"
  }
]
```

`split` documents development versus later timestamp checks; it does not imply independent footage. Unsupported or unreadable frames should be excluded with an explanation, rather than given guessed values. The final-minute format in this known scoreboard is normalized to `00:SS.t`; all blank slots elsewhere remain unavailable. Confirm any different scoreboard's formats before interpreting them.

The supplied local annotation files and all output reports are ignored. They are not downloaded or checked into CI. Run the full comparisons:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/compare_readers.py scoreboard-2-min-clip.mp4 --calibration calibration.json --labels data/recognition-original-labels.json --output data/recognition-original-tenths.json --skip-ocr --clock-layout mmss
/tmp/livestream-recognition-venv/bin/python experiments/compare_readers.py scoreboard-live-test-01.mkv --calibration data/recognition-live-calibration.json --labels data/recognition-live-tenths-all-labels.json --output data/recognition-live-tenths-reviewed.json --skip-ocr --clock-layout-plan data/recognition-live-layout-plan.json
python3 experiments/summarize_results.py data/recognition-original-tenths.json data/recognition-live-tenths-reviewed.json
```

These output names preserve the original `*-final.json`, `*-glyph-safety.json` and `*-independent.json` evidence. The local `recognition-live-tenths-all-labels.json` combines the original 15 newer-clip labels with 13 further clear exact-frame samples from two sequences; seven ambiguous clocks were left unlabelled in a separate local review note. These private files are not shipped in Git. Use the original label file to reproduce the original-anchor metrics only. See [tenths evidence and exclusions](../docs/tenths-recognition.md). For the new recording, create an ignored local `data/recognition-live-layout-plan.json` containing `[{"start":0,"layout":"mmss"},{"start":30,"layout":"mss"},{"start":42.5,"layout":"seconds_tenths"}]`. These are explicit selections based on reviewed layout examples, not exact physical change times or an automatic inference rule. Without a plan, the new independent candidate uses `mmss` throughout. Available fixed selections are `mmss`, `mss` (leading blank) and `seconds_tenths` (final blank). Lost/unknown digits never switch layouts. See [candidate rules and limitations](../docs/candidate-confirmation.md).

`rows`/`metrics` and the summary command retain the legacy auto-format/all-fields-repeat comparison. `independent_rows`/`independent_metrics` hold the new per-field observed/confirmed values, freshness, age, stale flag and reasons, with the explicit plan and confirmation parameters in report metadata. A held output is never counted as a fresh confirmation. Remove `--skip-ocr` to rerun OCR against the updated shared masks (the historical OCR results do not apply to these masks). `--limit N` limits candidate output for development (the baseline is still decoded fully); `--ocr-psm 7` compares an alternate OCR line mode. A missing/broken OCR tool fails the run rather than reporting an empty result as successful. Tesseract errors are not swallowed. Reports include input SHA-256, the exact calibration/template/labels, tool versions, raw and confirmed timelines, held ages, reviewed correctness counts, candidate processing times, region guard configuration and per-digit rejection evidence. These are batch experiments; coverage is not accuracy and timing excludes candidate decoding/capture/OBS delivery. Region timers now include independent state and full-frame hashing.

Stress-test windows around labels marked `heldout`, using the same pixel translations for each sample:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/stress_readers.py scoreboard-live-test-01.mkv --calibration data/recognition-live-calibration.json --labels data/recognition-live-tenths-all-labels.json --output data/recognition-live-tenths-reviewed-stress.json --skip-ocr --clock-layout-plan data/recognition-live-layout-plan.json
/tmp/livestream-recognition-venv/bin/python experiments/stress_readers.py scoreboard-2-min-clip.mp4 --calibration calibration.json --labels data/recognition-original-labels.json --output data/recognition-original-tenths-stress.json --skip-ocr --clock-layout mmss
```

The default `--sequence-radius 5` includes up to five samples before and after each reviewed anchor (11 samples at an interior anchor). `--sequence-radius 0` reproduces the former single-frame procedure. Each window/offset has separate confirmation history. Only its anchor has expected full-reading truth; `correct: null` on neighbouring samples means unlabelled, not correct. Use `raw` and `evidence` to distinguish unavailable observations from unlabelled available ones. Output adds source `t`, `anchor_t`, candidate digits, per-digit reasons, legacy confirmed values/status/age, and an `independent` per-field state with the selected `clock_layout`. Remove `--skip-ocr` to include OCR. Existing heldout anchors are now reused regression checks, not independent validation of the hardened reader.

No images or audio are saved by these scripts. Numeric output files may be large; keep them ignored. The Regions prototype and OCR baseline still make mistakes. The region implementation is also used by opt-in diagnostic shadow mode; neither candidate drives the overlay. See [the safety follow-up](../docs/recognition-comparison.md#glyph-safety-follow-up) for the fixed shifted-score case and the substantial coverage loss from conservative rejection.

The legacy shared two-identical-observation rule is intentionally retained for comparison. It can fail on a perfectly recognized running tenths clock at 10 Hz. The separate independent state accepts observed timed progression in synthetic tests, and the updated glyph reader now supplies 77 available and 51 freshly confirmed clocks in the new recording's selected 89-sample tenths interval. Mixed exposure still causes unknown/held or plausible raw glitches; these counts are not accuracy. Neither path drives runtime output; [opt-in monitor shadow integration](../docs/shadow-reader.md) now exposes independent candidate diagnostics.

## Explicit per-field source review

Use `audit_readings.py` to retain unreadable fields in the evidence instead of excluding the entire frame. It needs only Python's standard library. A separate review object binds to the report's `video_sha256` and `fps`, describes the manual inspection in `method`, and contains `reviews` entries like this synthetic example:

```json
{
  "t": 47.0,
  "fields": {
    "clock": { "unreadable": "Mixed LED strokes; physical truth not assigned" },
    "home": { "value": 1 },
    "away": { "value": 1 }
  }
}
```

Give the top-level review the exact `video_sha256` and `fps` from the matching report, after checking the video hash. Inspect exact sequential FFmpeg sample indices at that rate; independently seeking video frames can select different images. Give each reviewed field exactly `value` or a nonempty `unreadable` reason. Scores are integers 0–9; clocks use `MM:SS` or `00:SS.t`. Omit fields that were not reviewed. Never use null or a predicted clock as ground truth.

The following commands use ignored local reviews from the [exposure audit](../docs/exposure-validation.md); those private files are not shipped with the repository:

```sh
python3 experiments/audit_readings.py data/recognition-original-tenths.json data/recognition-original-field-review.json --output data/recognition-original-field-audit.json
python3 experiments/audit_readings.py data/recognition-live-tenths.json data/recognition-live-field-review.json --output data/recognition-live-field-audit.json
```

Inputs must have matching video hash/rate and unique exact-grid review timestamps within the full `independent_rows` timeline. The audit checks observation/output equality for fresh confirmations and unchanged values/advancing ages on holds throughout the saved timeline. It writes counts and per-field reviewed states, plus hashes of both input JSON files; it refuses to overwrite either input. It reports fresh confirmations on unreadable frames separately from readable correctness, and counts unreviewed fields explicitly. It does not decode the video or verify the human labels itself. These synthetic accounting/integrity tests run in the normal application CI job without footage or optional packages.

The [monitor recapture benchmark](../docs/mock-capture-validation.md) adds a third local recording, a separate frozen calibration and fifty per-field reviewed timestamps. It demonstrates wrong fresh score confirmations despite high candidate availability. See that report for commands, the distinction between geometric development calibration and validation, and the four established-reader confirmation failures. Its private assets also remain outside Git.
