# Local recognition experiments

These scripts compare candidates offline. They do not modify calibration files, start a camera, publish values, or change the server. See [the findings](../docs/recognition-comparison.md) for results and limits.

Use a separate environment with Python 3.12, FFmpeg/ffprobe, and local Tesseract (tested with 5.5.1 and English data):

```sh
python3 -m venv /tmp/livestream-recognition-venv
/tmp/livestream-recognition-venv/bin/python -m pip install -r experiments/requirements.txt
/tmp/livestream-recognition-venv/bin/python -m unittest discover -s experiments -p 'test_*.py' -v
```

OpenCV/NumPy are shared optional dependencies for experiments and opt-in shadow mode; default application setup does not require them. The standard repository check compiles these files without importing them; it runs the application and dependency-free candidate-state tests. The 35 experiment tests require this environment and are run separately.

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
/tmp/livestream-recognition-venv/bin/python experiments/compare_readers.py scoreboard-2-min-clip.mp4 --calibration calibration.json --labels data/recognition-original-labels.json --output data/recognition-original-score-cores-final.json --skip-ocr --clock-layout mmss
/tmp/livestream-recognition-venv/bin/python experiments/compare_readers.py scoreboard-live-test-01.mkv --calibration data/recognition-live-calibration.json --labels data/recognition-live-tenths-all-labels.json --output data/recognition-live-score-cores-final.json --skip-ocr --clock-layout-plan data/recognition-live-layout-plan.json
/tmp/livestream-recognition-venv/bin/python experiments/compare_readers.py mock-scoreboard-testing-clip.mkv --calibration data/recognition-mock-registration-calibration.json --labels data/recognition-mock-reviewed-labels.json --output data/recognition-mock-score-cores-final.json --skip-ocr --clock-layout mmss
python3 experiments/summarize_results.py data/recognition-original-score-cores-final.json data/recognition-live-score-cores-final.json data/recognition-mock-score-cores-final.json
```

These output names preserve the earlier `*-final.json`, `*-glyph-safety.json`, `*-independent.json`, `*-tenths.json` and `*-registered-reviewed.json` evidence. The local `recognition-live-tenths-all-labels.json` combines the original 15 newer-clip labels with 13 further clear exact-frame samples from two sequences; seven ambiguous clocks were left unlabelled in a separate local review note. These private files are not shipped in Git. Use the original label file to reproduce the original-anchor metrics only. See [tenths evidence and exclusions](../docs/tenths-recognition.md). For the new recording, create an ignored local `data/recognition-live-layout-plan.json` containing `[{"start":0,"layout":"mmss"},{"start":30,"layout":"mss"},{"start":42.5,"layout":"seconds_tenths"}]`. These are explicit selections based on reviewed layout examples, not exact physical change times or an automatic inference rule. Without a plan, the new independent candidate uses `mmss` throughout. Available fixed selections are `mmss`, `mss` (leading blank) and `seconds_tenths` (final blank). Lost/unknown digits never switch layouts. See [candidate rules and limitations](../docs/candidate-confirmation.md).

`rows`/`metrics` and the summary command retain the legacy auto-format/all-fields-repeat comparison. `independent_rows`/`independent_metrics` hold the new per-field observed/confirmed values, freshness, age, stale flag and reasons, with the explicit plan and confirmation parameters in report metadata. A held output is never counted as a fresh confirmation. Remove `--skip-ocr` to rerun OCR against the updated shared masks (the historical OCR results do not apply to these masks). `--limit N` limits candidate output for development (the baseline is still decoded fully); `--ocr-psm 7` compares an alternate OCR line mode. A missing/broken OCR tool fails the run rather than reporting an empty result as successful. Tesseract errors are not swallowed. Reports include input SHA-256, the exact calibration/template/labels, tool versions, raw and confirmed timelines, held ages, reviewed correctness counts, candidate processing times, region guard configuration and per-digit rejection evidence. These are batch experiments; coverage is not accuracy and timing excludes candidate decoding/capture/OBS delivery. Region timers now include independent state and full-frame hashing.

Stress-test windows around labels marked `heldout`, using the same pixel translations for each sample:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/stress_readers.py scoreboard-live-test-01.mkv --calibration data/recognition-live-calibration.json --labels data/recognition-live-tenths-all-labels.json --output data/recognition-live-score-cores-stress.json --skip-ocr --clock-layout-plan data/recognition-live-layout-plan.json
/tmp/livestream-recognition-venv/bin/python experiments/stress_readers.py scoreboard-2-min-clip.mp4 --calibration calibration.json --labels data/recognition-original-labels.json --output data/recognition-original-score-cores-stress.json --skip-ocr --clock-layout mmss
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

The [score-core follow-up](../docs/score-core-recognition.md) changes candidate score extraction only, fixes the reviewed recapture zero-to-eight cases, and documents the loss of 31 complete original-clip readings. Its four new generated RGB tests cover all digits with red/white strokes, halo zeros, low-contrast loss/recovery and white crop rejection. At that stage all 21 optional tests passed and the established reader's four wrong recapture confirmations were unchanged. The later [probe guard](../docs/probe-core-rejection.md) rejects those confirmations; candidate results still do not reach OBS.

## Generated mixed-exposure sequences

`exposure_stress.py` exercises the same candidate with independent synthetic RGB digits, without video, local calibration, camera, server or publishing. See the [method, matrix findings and limits](../docs/candidate-exposure-stress.md). Use the existing optional environment:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --pairs 15 --weights .25 --output data/candidate-exposure-one-five.json
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --all-pairs --color white --output data/candidate-exposure-white-matrix.json
```

Repeat the matrix for `--color orange` and `--color red`, choosing corresponding new output names. Without `--pairs` or `--all-pairs`, the default directed pairs are 01, 10, 08, 80, 09, 90, 18 and 81. Default new-source blend weights are .25, .5 and .75. Existing output paths are refused. Reports retain the source pairs, phase, clean expected digits, every candidate field state and digit diagnostic, calibration, package versions and generator/recognizer/state source hashes. They are numeric ignored data, not recordings or image assets.

Only clean home phases have correctness labels; mixed images have no assigned physical score. Fresh confirmations on mixed images and outputs outside both source digits are reported separately. A zero wrong-clean count does not make mixed exposure safe, and a successful command exit reports completed measurement rather than successful recognition. The full white/orange/red matrices each expose twenty fresh confirmations outside both source digits. This is a controlled blend test, not calibrated camera exposure, clock-mixture, arbitrary-framing or live validation. Candidate output remains disabled.

## Candidate score-mask disagreement

Full candidate recognition now uses `RegionReader.observe(frame)` for the [score-mask disagreement guard](../docs/score-mask-disagreement.md). It rejects competing valid primary/core digits, preserves both interpretations in diagnostics, and never substitutes the core digit. Mask-only helpers remain shape/OCR diagnostics and do not apply the veto. Comparison, translation, generated exposure and actual shadow paths all use the full API.

Repeat the existing three recording comparisons/audits and translation commands with new output names containing `score-agreement`, keeping their profiles, labels and explicit layouts. Repeat all three generated matrices with names such as `data/candidate-exposure-white-score-agreement.json`, preserving the initial reports. At that stage generated fresh third-digit counts were four per colour, down from twenty; balanced six/nine blends still confirmed five. Existing recorded field states and translation results are unchanged. The optional suite now has 30 tests. Candidate output remains disabled.

## Local RGB contrast and controlled variants

The [local contrast guard](../docs/local-score-contrast.md) adds score-only RGB top-hat evidence to the full observation API. It can veto a conflicting primary digit, never replace it. The original unblurred matrix now has zero third-digit observations/confirmations, with clean raw readings retained and fifteen fewer fresh clean confirmations per colour than the previous guard. Recorded field states remain unchanged.

`exposure_stress.py --variant none|blur|dim|shift` retains the selected recipe in its reports. Default `none` preserves previous rendering; `blur` is 5×5 Gaussian/sigma 1, `dim` is encoded-RGB gain 0.8, and `shift` is +3/+2 pixels. These transformations apply before frame-identity variation. They are controlled drawings, not calibrated camera models. For example:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --pairs 15 16 51 61 69 96 --weights .5 --color orange --variant blur --output data/candidate-exposure-orange-local-blur.json
```

This blurred check still exposes eight fresh third-digit confirmations for orange, and eight for red. White has none in that selected check. Preserve these failures alongside the successful unperturbed matrix; they remain unresolved. Repeat the three recording comparison/audit/translation commands with `local-contrast` output names and the original profiles, labels and layouts. The optional suite now has 35 tests. Candidate output remains disabled.

## Controlled source preparation

See [controlled recording and recapture](../docs/controlled-recording.md) for the dependency-free source generator, timeline semantics and coordinated capture procedure. The optional suite includes a clean-source anchor check for all score digits, both explicit layouts and deliberately unavailable fields (36 optional tests at this stage). This is a direct generated-drawing check, not evidence of capture-chain accuracy.

The first [controlled recapture evaluation](../docs/controlled-recapture-validation.md) uses separate local profile/template files and the existing comparison/audit commands. It preserves the initial label-contaminated score windows, a geometric window adjustment and a source-stroke-derived probe calibration. No recognition rules changed. Its 75 reviewed timestamps expose false score-core disagreements on visible threes/fours; other timestamps remain unreviewed.

## Uneven score brightness

The [score-core balance follow-up](../docs/score-core-balance.md) changes the complementary light fraction from 0.8 to 0.6, retaining its 99th-percentile reference and all disagreement/shape guards. Repeat the four recording comparisons with their frozen profiles/templates/layouts, the existing reviews, translation windows and generated matrix/blur commands, using new `core-balance` output names. The optional suite now has 39 tests, including independent uneven-brightness RGB score drawings and actual shadow loss/staleness/recovery. White/red source-like mixed confirmations increase despite zero unblurred third digits; blurred orange remains failing. Neither availability nor the test count enables candidate output.
