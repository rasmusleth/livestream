# Monitor recapture validation: 2026-11-01

The monitor recording exposes confirmed score errors in both readers. The region candidate repeatedly reads visible zero scores as eight. The established probe reader rarely produces a complete reading with the mapped calibration, but all four of its fresh complete confirmations have incorrect scores. This is a recognition failure on the tested setup, not just missing coverage. Neither reader is validated for use with this framing and image appearance.

No recognition, thresholds, server, UI or OBS behavior was changed in this validation. No camera or existing user server was opened or stopped. All footage, local profiles, labels, contact sheets and numeric reports remain local and outside Git.

The subsequent [candidate score-core fix](score-core-recognition.md) removes the reviewed candidate zero-to-eight confirmations and records its availability tradeoff. The measurements below preserve the pre-fix evidence. The later [active probe safety guard](probe-core-rejection.md) prevents its four wrong confirmations by leaving output unknown; this is not successful recapture recognition. The measurements below preserve the original failures.

## Input and calibration

The operator recorded `scoreboard-2-min-clip.mp4` playing from beginning to end on a monitor, filmed through the camera/capture device and saved through OBS as `mock-scoreboard-testing-clip.mkv`. The new file reports 1920×1080, 60 fps and 163.667 seconds, compared with the source's 163.8256 seconds. File frame-rate metadata does not establish unique camera frames or live capture throughput. The two audio tracks were ignored; analysis decodes video only.

This is a recapture of existing footage. It exercises the monitor, camera and OBS recording chain, including any added blur, color changes and refresh artifacts. It does not establish direct physical-scoreboard performance, and the original footage can already contain LED transition artifacts. The clip has ordinary minutes/seconds, clock stoppages and a score change; it provides no final-minute tenths validation.

The scoreboard occupies a larger part of the image than in the source, so the tracked reference profile cannot be reused directly. A separate local profile was created without replacing `calibration.json`, `data/calibration.local.json` or the earlier newer-clip profile. Initial manual corner alignment produced just 243/1,637 complete raw candidate readings and no complete probe readings. That result was retained as `data/recognition-mock-initial.json`, not treated as recognition evidence independent of alignment quality.

Alignment was then refined geometrically against the source's first sampled frame: OpenCV ORB with 4,000 requested features, source features restricted to the central panel, Hamming two-neighbour matching with a 0.7 ratio filter, and a RANSAC homography with a 2-pixel threshold and random seed zero. There were 406 filtered matches and 238 inliers. The projected reference panel corners, rounded to integer source pixels, were passed through the existing `calibration.align_profile`; both digit boxes and probes were mapped together. Alignment images at the beginning and end were inspected. This is a development calibration using the known source picture, not an automatic runtime calibration feature or an independently held-out framing test.

The resulting profile is saved locally as `data/recognition-mock-registration-calibration.json` and embedded in the comparison report. Its fixed geometry was used for all final measurements below. It is a whole-panel mapping with inherited probes, not an exhaustive manual optimization of the established reader. Geometry refinement improved candidate clock availability substantially, but did not eliminate the score errors. Recognition rules were frozen throughout.

## Full-recording availability

Both readers were decoded at the configured 10 Hz rate, yielding 1,637 samples. The candidate used the explicitly selected `mmss` layout; OCR was skipped. These are availability counts, not correctness counts:

| Output | Available observations | Fresh confirmations |
| --- | --- | --- |
| Established reader, complete reading | 21 | 4 |
| Region candidate, complete legacy comparison | 1,253 | 1,039 |
| Independent candidate home | 1,598 | 1,559 |
| Independent candidate away | 1,602 | 1,564 |
| Independent candidate clock | 1,313 | 1,197 |

Every fresh candidate home value in this report is eight. Candidate away confirmations comprise 1,119 eights and 445 ones. These describe the output timeline; correctness is assigned only at reviewed source samples below. High availability and repeat confirmation do not protect against a persistent visual misclassification.

The remaining clock losses are mostly extraction rejection: the seconds-tens window has 214 edge-foreground and 38 ambiguous-segment rejections; seconds-units has 79 ambiguous-segment rejections. Guards remain enabled. Candidate processing median/p95 is 9.82/12.02 ms in this offline run; this excludes decoding, capture and OBS delivery and is not live latency evidence.

## Exact-frame review

Fifty distinct 10 Hz samples were inspected using sequential FFmpeg decoding from zero and resized clock/score contact sheets:

- Seventeen anchors at 0, 10, …, 160 seconds.
- Ten-frame windows at 60.0–60.9 (paused clock), 70.2–71.1 (seconds transition) and 118.5–119.4 (score change). The overlapping 60.0 anchor is counted once.
- All four established-reader fresh confirmations: 123.4, 144.1, 161.9 and 162.0 seconds. These were selected after seeing the failures and are diagnostic checks, not a random or held-out sample.

Original-video contact sheets were also checked for reference content. The recapture's event times are not assumed to match source timestamps exactly. Labels describe the visible recaptured frames; no clock values are inferred from expected elapsed time. The 70.6 clock and 118.8 away-score transition remain explicitly unreadable. The other 48 samples have complete readable labels. Local reviewed metrics were calculated from the final cached decoded report; the extraction command below reproduces them without that cache.

| Independent candidate field | Readable | Fresh correct / wrong | Readable held / unknown | Unreadable | Fresh on unreadable |
| --- | --- | --- | --- | --- | --- |
| Home | 50 | 0 / 48 | 1 / 1 | 0 | 0 |
| Away | 49 | 14 / 32 | 2 / 1 | 1 | 0 |
| Clock | 49 | 27 / 0 | 21 / 1 | 1 | 1 |

The home score visibly remains zero at all fifty reviewed samples. The candidate observes eight at 49 and has no observation at one; 48 are wrong fresh confirmations. Before the score change, visible away zeros are also repeatedly confirmed as eight. After the change, the reviewed away ones are recognized. The candidate observes the first clearly readable away one at 118.9, holds its older eight, then confirms one at 119.0. That one-sample delay does not remedy the prior wrong score.

No fresh candidate clock disagrees with a readable clock label in this selected review. Of 21 readable held clocks, fourteen still equal the visible value and seven differ. The candidate also freshly confirms on the unreadable 70.6 transition; its physical truth remains unresolved. The full saved independent timeline passes the audit's observation/value/status/age consistency checks. There are 1,587 unreviewed source samples per field in this audit; these selected checks are not a whole-clip accuracy estimate.

Across the 48 fully readable labels, the candidate's legacy complete raw comparison has zero correct / 30 wrong / 18 unknown, and 23 wrong fresh complete confirmations. Separate per-field results above matter because a correct clock can coexist with wrong scores.

### Established reader failures

All four fresh complete probe confirmations in the full recording were visually reviewed:

| Capture time | Visible clock / scores | Confirmed clock / scores |
| --- | --- | --- |
| 123.4 | 18:41 / 0–1 | 18:47 / 9–7 |
| 144.1 | 18:39 / 0–1 | 18:39 / 9–7 |
| 161.9 | 18:28 / 0–1 | 18:28 / 9–7 |
| 162.0 | 18:28 / 0–1 | 18:28 / 9–7 |

The reader holds those values between confirmations. At the 48 fully readable labels its complete raw results are zero correct / five wrong / 43 unknown. No claim is made that manually optimizing every probe could not improve this result. It does show that the existing mapped profile and fixed recognition policy are insufficient, and that repeated evidence alone can confirm a persistent error in either reader.

## Pixel evidence and next implementation

Inspection of the candidate's rectified score masks at approximately 10 seconds shows unwanted foreground inside the visibly hollow zeros, including the middle-segment sampling area. In the home mask the normalized middle level is 0.377 against a peak of 0.486; in the away mask it is 0.236 against a peak of 0.437. Both exceed the current relative 0.4 segment threshold and produce an eight. The color mask also excludes bright white parts of the visible LED strokes while retaining surrounding red pixels. This points to foreground/background separation and saturated-stroke handling as concrete areas to investigate. It does not isolate which monitor/camera/exposure setting caused the changed pixel appearance.

The next focused implementation should reproduce the false-zero case with generated RGB inputs, improve extraction or conservative rejection, and rerun all three recordings plus their reviewed and translation checks. Preserve the pre-fix reports and compare lost availability as well as wrong confirmations. A persistent zero-to-eight error must be corrected or remain explicitly unavailable; repeated agreement cannot be treated as proof. Probe-path calibration and failure behavior also need explicit follow-up rather than assuming the established reader is safe on this recapture.

No further operator recording is needed to investigate these demonstrated failures. After addressing them, a separate tenths recapture can extend the evidence, followed by coordinated live single-owner throughput/delay testing. The monitor recording remains useful regression evidence even if a later direct-scoreboard setup has different image characteristics.

## Reproduction and checks

These commands use ignored local profiles and labels, which are not shipped with the repository. Install the optional environment as described in [experiments/README.md](../experiments/README.md).

```sh
/tmp/livestream-recognition-venv/bin/python experiments/compare_readers.py mock-scoreboard-testing-clip.mkv --calibration data/recognition-mock-registration-calibration.json --labels data/recognition-mock-reviewed-labels.json --output data/recognition-mock-reproduced.json --skip-ocr --clock-layout mmss
python3 experiments/audit_readings.py data/recognition-mock-reproduced.json data/recognition-mock-field-review.json --output data/recognition-mock-reproduced-audit.json
```

The original final comparison is `data/recognition-mock-registered.json`; the cached label evaluation is `data/recognition-mock-registered-reviewed.json`; the per-field audit is `data/recognition-mock-field-audit.json`. Reports retain the input video hash, calibration, policies and diagnostics, and the audit retains its report/review hashes. Earlier files were preserved. Default `data/readings.json` was not overwritten.

`python3 scripts/check.py` passes all 66 tests, including five existing original-recording regressions, generated-video tests, syntax and calibration checks. Those checks do not establish correctness on this new recapture; the failures above are real despite the green suite. This documentation-only stage adds no tests or recognition changes. Extraction was run on the new recapture; the original default readings were not regenerated. The separate optional test suite was not rerun, and no UI or hardware test was performed.
