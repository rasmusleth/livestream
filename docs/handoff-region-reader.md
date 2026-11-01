# Handoff: robust scoreboard reading

Prepared 2026-10-31. The user agreed to pursue whole-region recognition, beginning with an opt-in shadow mode. This document records the next task; it does not mean that task is implemented. Read `AGENTS.md`, `README.md`, `docs/architecture.md`, `VALIDATION.md`, and `docs/development.md` before changing code.

Follow-up: the first offline glyph-safety stage is now implemented on `codex/region-glyph-safety`; see [evidence and coverage costs](recognition-comparison.md#glyph-safety-follow-up). The known shifted-score window is fixed, with conservative rejection elsewhere. The remaining stages below—explicit safe clock formats, independent field/tenths confirmation, and monitor shadow integration—are still pending. The preparation-time checkout/PR details below describe the starting point.

Second follow-up: `codex/independent-candidate-confirmation` implements explicit selected layouts and independent candidate field confirmation offline. See [rules and validation](candidate-confirmation.md). Synthetic tenths progression confirms from observed values; the real new recording still has no complete tenths observations under the strict glyph checks. Automatic layout detection and monitor shadow integration remain pending. The numbered plan and runtime description below retain their preparation-time context.

## Goal and current position

Make the reader tolerate ordinary setup differences without positioning 42 tiny probes perfectly. Keep processing local and use the reader as the sole owner of the scoreboard capture device. OBS receives digital output through its browser overlay.

The monitor and calibration editor work, including four-corner panel alignment and optional per-digit adjustments. Calibration checks inspect a single draft frame; they never publish confirmed values. Saving calibration writes an ignored local profile, which requires restarting the reader with that profile to activate it.

The runtime still uses the original fixed-probe reader and requires two identical complete clock/home/away observations before confirming. An unreadable field can block the whole output. The overlay correctly remains empty until confirmation and holds previously confirmed values with status and age. Do not solve recognition failures by publishing uncertain data.

An isolated offline comparison now exists in `experiments/`. It rectifies the panel using its four corners and examines whole digit regions, normalizing the visible glyph before evaluating broad segment areas. It is **not connected to the monitor, live reader, or OBS output**. OpenCV and NumPy are optional experiment dependencies only.

## Evidence and unresolved problems

Read [the full comparison](recognition-comparison.md) and [reproduction instructions](../experiments/README.md).

- On the new 51-second recording, complete raw coverage increased from 0.2% for the current reader to 72.4% for Regions. In the first 25 seconds, with the ordinary four-digit clock, Regions reached 94%. These are coverage measurements, not accuracy estimates.
- Regions returned 11 correct, zero wrong, and four unknown readings at 15 visually reviewed new-clip timestamps. These sparse samples and a small temporal holdout from the same footage do not establish general accuracy.
- The tested generic Tesseract baseline performed substantially worse. Continue with Regions; no need to build a general OCR service now.
- A deliberate 10-pixel upward shift at new-clip time 32.5 seconds turns the away score `1` into `9`. Repeated wrong readings could pass the existing confirmation rule. Reject cropped or ambiguous glyphs before enabling output.
- The display switches to seconds and tenths near the end. The user confirmed that `46:8` means 46.8 seconds. The experiment expresses this as `00:46.8`. Treating a blank as a format signal can be unsafe under occlusion or flicker.
- Two identical clock values is unsuitable for a running tenths clock sampled at 10 Hz: a perfectly read sequence such as 46.8, 46.7, 46.6 may never confirm. Independent fields alone will not fix this. Confirmation must assess observed progression and source timing without generating unseen ticks.

## Next implementation, in order

Keep the first deliverable focused: a safer region candidate visible in the monitor alongside the current reader, with OBS still following the existing path.

1. Inspect the checkout and PR state before branching. Preserve all local footage, calibration, labels, and generated data. Use a descriptive `codex/` branch based on the required existing work; do not reset or clean the checkout.
2. Harden region recognition against clipped glyphs and ambiguous `1`/`7`/`9` shapes. Reproduce the known shift failure and evaluate sequences, not just isolated frames. Missing or ambiguous input must remain unknown. Explain any runtime dependencies if promoting experiment code into the application; do not import experiment packages into the default path accidentally.
3. Define explicit clock-format handling for four digits, an observed leading blank, and seconds/tenths. Preserve unknown versus observed blank. Guard format changes against lost or obscured digits.
4. Add independent home, away, and clock confirmation, each with observed value, confirmed value, freshness/held status, age, and rejection reason. Confirm a clock as one observed value, never by combining digits from different frames. Test timed progression, pauses, resets/corrections, duplicate frames, gaps, and recovery. Never advance the displayed clock independently of footage.
5. Add an opt-in shadow mode to the existing continuous reader/monitor. Compare candidates using the same captured frames and single capture owner. Show per-field diagnostics clearly. Default reader and overlay behavior remain unchanged; candidate output must not automatically drive OBS.
6. Validate offline first, then coordinate a hardware check with the user. Collect more independently reviewed sequences, including score changes and pauses, and evaluate small rotation/zoom, exposure, flicker, and dropouts. Measure live end-to-end delay separately from batch processing time. Enabling candidate output is a later decision after evidence, not part of the initial shadow-mode task.

Acceptance evidence should include the known shifted-score case becoming correct or explicitly unknown, no fabricated clock ticks during loss, tenths progression that can confirm from observed evidence, independent field freshness, and a monitor demonstration that shadow output cannot change OBS. Report any missed targets honestly rather than lowering confirmation safeguards for coverage.

## Local material to preserve

All paths below are relative to the repository and are ignored. Do not upload or commit their contents.

| Path                                           | Purpose                                                                          |
| ---------------------------------------------- | -------------------------------------------------------------------------------- |
| `scoreboard-2-min-clip.mp4`                    | Original 1920×1080 recording, about 164 seconds; use tracked `calibration.json`. |
| `scoreboard-live-test-01.mkv`                  | New 1920×1080 recording, about 51 seconds. Read directly; no conversion needed.  |
| `data/calibration.local.json`                  | User's editable saved camera profile. Do not overwrite it for experiments.       |
| `data/recognition-live-calibration.json`       | Snapshot matching the new MKV; use this for reproducible comparison.             |
| `data/recognition-{original,live}-labels.json` | Visually inspected exact 10 Hz sample labels, with development/heldout splits.   |
| `data/recognition-{original,live}-final.json`  | Comparison timelines, metrics, configuration, labels, versions, and hashes.      |
| `data/recognition-{original,live}-stress.json` | Translation stress results.                                                      |
| `data/readings.json`                           | Regenerated original-reader results used by recording regression tests.          |

The optional Python 3.12 environment was created at `/tmp/livestream-recognition-venv`; it may disappear. Recreate it with `experiments/requirements.txt` if needed. Local Tesseract 5.5.1 was available, but is unnecessary for the Regions-only implementation. Labels must refer to actual FFmpeg sampled frames: at 45.0 and 50.0 seconds the sampled new-clip images show 46.6 and 41.8 seconds respectively. Independently seeking the video can yield different tenths.

## Hardware and running processes

The development Mac is also the streaming Mac. The generic HDMI-to-USB-C capture device is `USB video` in OBS and `usb video` in FFmpeg. Simultaneous direct OBS and FFmpeg capture previously corrupted the OBS picture; reconnecting the device restored it. Shared device access is not validated.

Do not open another capture process or restart/stop the user's server without coordination. Inspect existing processes first. A camera monitor previously ran at port 8771; browser tabs at 8770 and other ports may be older recording demos with held frames, so a visible page alone is not evidence of live input. This offline comparison never opened the camera. Ask the user to close OBS before a new hardware test if its state is unknown. OBS should ultimately use only the overlay for this device; the match camera is separate.

## Git and review handoff

At preparation time, the clean checkout was `codex/recognition-comparison`:

- [Draft PR #7](https://github.com/rasmusleth/livestream/pull/7): `codex/camera-calibration-editor` → `main`.
- [Draft PR #8](https://github.com/rasmusleth/livestream/pull/8): `codex/recognition-comparison` → `codex/camera-calibration-editor`, stacked on #7. Contains the offline comparison and this handoff, without changing runtime recognition.

Recheck these states: they may have changed since preparation. If the base was squash-merged, adapt the stack deliberately and preserve the comparison commits. Do not merge or force-push automatically. Open or update a draft PR after the next meaningful validated task; the user has authorized that workflow. Human review controls merging.

## Verification

The comparison task passed the application check (39 tests with local recording data) and seven separate experiment tests; hosted CI also passed before this handoff addition. These are previous results, not results for future implementation.

Run the required application check for the next change:

```sh
python3 scripts/check.py
```

For recognition changes, regenerate the original recording before the final check, and run optional candidate tests separately:

```sh
python3 reader.py scoreboard-2-min-clip.mp4
python3 scripts/check.py
/tmp/livestream-recognition-venv/bin/python -m unittest discover -s experiments -p 'test_*.py' -v
```

Repeat both real-footage comparisons and stress cases using the commands in `experiments/README.md`, keeping new outputs local and preserving comparison evidence. UI changes also require opening the local monitor and checking readability, diagnostics, loading, playback/seeking where applicable, uncertain/held states, and the overlay boundary. CI lacks private footage and skips its recording regressions; optional experiment tests are not in application CI. Distinguish synthetic checks, sparse reviewed correctness, coverage, and actual live validation in the PR.
