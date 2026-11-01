# Controlled camera recapture: 2026-11-01

The new display/camera/OBS recording is usable for offline development. With a separate geometric calibration, the active reader confirms minutes/seconds and scores; the candidate also confirms the tenths clock independently. Neither path is ready for live reliance. Candidate score guards reject some clearly readable threes and fours, leaving long stale holds. No recognition or server behavior changes in this evaluation; candidate output remains disabled.

## Input, registration and review scope

Local input: `data/controlled-recordings/v1/recording-camera-footage.mkv`, 1920×1080 at 60 fps, 119.934 seconds, 7,196 decoded video frames. Its two audio streams are excluded from analysis. SHA-256:

```text
18257e5cd966978c9bac40d168908003eea1bb10eb5097fb262d7673c4bef718
```

The [controlled source](controlled-recording.md) is visible with all four panel corners and the reference strip. The recording starts during the alignment section, without the requested lead-in; the source strip is already around 0.15 seconds at analysis time zero. Later reviewed source times are around 0.15–0.18 seconds ahead of capture time. All scenario sections, including final recovery, are present. This is alignment context, not an assumption that every source/capture frame pair has a fixed offset.

The existing comparison decoder sampled the full capture sequentially at 10 Hz: 1,199 rows, from 0.0 through 119.8 seconds. The coding agent visually reviewed captured scoreboard pixels on 61 selected samples, then 25 focused boundary samples (14 additional unique samples), for 75 unique per-field reviews. Prediction-free contact sheets retained the clock, scores and reference strip. Labels were transcribed from scoreboard strokes, not assigned from source intention or reader output. Six blank-clock samples and nine covered-home samples remain explicitly unreadable. No mixed sample in this selected review was assigned an invented physical value. Most samples are unreviewed: 1,124 per field. This is development evidence, not a whole-clip accuracy estimate or independent human validation.

The 61 initial review times are:

```text
0, 5, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29,
31, 33, 35, 37, 39, 41, 43, 45, 47, 49, 55, 60, 65,
69.6, 69.7, 69.8, 69.9, 70, 71, 75, 80, 85, 89,
89.6, 89.7, 89.8, 89.9, 90, 91, 94, 97, 100, 103,
104.7, 104.8, 105, 106, 108, 109.7, 109.8, 110, 111,
113, 114.7, 114.8, 115, 116, 118, 119
```

Additional unique boundary reviews: 70.1, 70.2, 70.3, 90.1, 90.2, 104.9, 109.9, 110.1, 110.2, 110.3, 114.9, 115.1, 115.2 and 115.3 seconds. Use the exact sequential `fps=10` sample indices; independent timestamp seeks can return different images. The final per-field review binds to the capture hash and sample rate. The complete-reading comparison labels cover only the 51 fully readable initial samples; final per-field audits cover all 75.

## Separate development calibrations

Existing local profiles and tracked calibration were preserved. The central-panel corner registration, inspected initially at capture time 10 seconds, is `[[459,138],[1533,137],[1530,842],[456,841]]` in source pixels. `calibration.align_profile` maps the tracked profile to these corners in `camera-calibration.json`. This is geometric development registration, not an independently held-out setup.

Three stages were preserved locally:

1. **Mapped old profile:** both candidate scores are rejected on all 1,199 samples. Inspection of a rectified patch at 5 seconds shows the padded window includes the bottom of the printed HOME label, which enters the warmed foreground mask and touches its top edge. AWAY has the same rejection. The active reader has no complete raw reading with its old mapped probe positions either.
2. **Candidate score-window template:** copy the tracked reference into `camera-score-window-template.json`, changing only source-template digit boxes to `home=[621,727,105,110]` and `away=[1297,732,107,110]`. These windows retain the generated score strokes and padding while excluding the labels. Clock boxes, masks, thresholds and edge guards are unchanged. This is a drawing-specific diagnostic template, not a general calibration fix or an activated server profile. Candidate score observations become available; active rows stay exactly unchanged.
3. **Geometric probe profile:** the generated strokes differ from the physical-scoreboard probe calibration. Derive each source probe from the midpoint of `scripts.generate_controlled_recording.LINES`, scaled/translated with clock origins `(735,524)`, `(845,524)`, `(990,524)`, `(1110,524)` at scale 1.3, and home `(643,724)`, away `(1319,729)` at scale 1. Round source coordinates, then apply the same corner registration with `align_profile`. Use the score-window boxes above. Save the source profile as `camera-geometric-source-profile.json` and mapped profile as `camera-geometric-probes.json`. Probe placement comes from drawing geometry, without selecting recognition outcomes. The active reader now produces 899 complete raw readings and 858 fresh complete confirmations. Candidate observations and every independent field state exactly match stage 2 because its rectification is unchanged.

Freeze these profiles before future comparisons; the same inspected anchors were reused during this calibration investigation. Do not treat their improvements as independent validation. None replaces `calibration.json` or `data/calibration.local.json`. The candidate template selection is an offline comparison option; this evaluation does not add a template selector to the server.

The explicit captured-time layout plan is `[{"start":0,"layout":"mmss"},{"start":69.9,"layout":"seconds_tenths"},{"start":89.9,"layout":"mmss"}]`, saved as `camera-layout-plan-reviewed.json`. At 69.8 and 89.8 seconds the previous formats are still visible; the following samples visibly use the new formats. An initial exploratory run with switches one sample early is retained separately and is not the final evidence. Layouts are reviewed selections, never inferred from unavailable digits.

## Final results with geometric probes and score windows

Counts over all 1,199 rows describe availability, not correctness:

| Path/field | Available observations | Fresh confirmations |
| --- | ---: | ---: |
| Active complete reading | 899 | 858 |
| Candidate home | 988 | 969 |
| Candidate away | 656 | 617 |
| Candidate clock | 1,129 | 1,077 |

The legacy all-fields candidate comparison has 533 available complete raw readings and 499 fresh complete confirmations; use the independent per-field candidate rows for its actual confirmation semantics.

Final per-field audits on the 75 reviewed samples:

| Path/field | Readable | Fresh correct / wrong | Readable held / unknown | Held value differs from readable field | Unreadable / fresh on unreadable |
| --- | ---: | --- | --- | ---: | --- |
| Active home | 66 | 44 / 0 | 21 / 1 | 8 | 9 / 0 |
| Active away | 75 | 44 / 0 | 30 / 1 | 17 | 0 / 0 |
| Active clock | 69 | 44 / 0 | 24 / 1 | 24 | 6 / 0 |
| Candidate home | 66 | 46 / 0 | 19 / 1 | 18 | 9 / 0 |
| Candidate away | 75 | 30 / 0 | 44 / 1 | 25 | 0 / 0 |
| Candidate clock | 69 | 60 / 0 | 8 / 1 | 8 | 6 / 0 |

No observed or fresh-confirmed value is wrong on these reviewed readable fields, and neither path freshly confirms on the selected unreadable fields. Held values frequently differ from the visible scoreboard; that is explicitly reported rather than counted as fresh correctness. No claim is made about unreviewed transitions.

The active reader still confirms all fields together and supports only `MM:SS`. It holds `19:50 / 2–3` through the tenths section, reaching age 20.1 seconds before confirming the corrected `05:00 / 6–9` at 90.0. A blank clock then prevents all-field confirmation, followed immediately by a covered home score. It holds `19:55 / 1–1` through both intervals and confirms recovery at 115.0, one sample after the first reviewed readable recovery at 114.9.

The candidate clock confirms the tenths progression at 70.1, two samples after the first reviewed new-format frame at 69.9. It holds `19:55` while blank, reaching age 5.2 seconds at 110.0, then confirms the visible `05:10` at 110.1, two samples after the first reviewed clock return at 109.9. Recovery to `05:05` confirms at 115.1. These are sampled recognition delays, not physical-event or end-to-end live latency measurements.

Candidate score availability remains poor for some readable digits. At reviewed 17/19 seconds (home 3/4) and 37/39 seconds (away 3/4), primary and local masks recognize the visible digit, while the stricter score-core mask loses horizontal strokes and reports 1. The existing disagreement veto correctly keeps that conflicting evidence unavailable rather than substituting 1, but causes false rejections on these readable frames. There are 161 home and 541 away `score_mask_disagreement` rejections across the full timeline. The final home value stays held at 1 from 104.8 through the end, reaching age 15.0 seconds despite visible recovered home 3. Away has a maximum held age of 40.1 seconds. Clock maximum age is 5.2 seconds. Stale status and ages remain explicit; no missing field is filled with zero or an advancing clock.

## Reproduction and preserved evidence

All paths below are local and ignored under `data/controlled-recordings/v1/`; footage, profiles, labels, contact sheets and reports are not committed or uploaded. The final run used the code from `c058abe`, with no recognition changes. Use fresh output filenames to preserve these reports:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/compare_readers.py \
  data/controlled-recordings/v1/recording-camera-footage.mkv \
  --calibration data/controlled-recordings/v1/camera-geometric-probes.json \
  --template data/controlled-recordings/v1/camera-score-window-template.json \
  --labels data/controlled-recordings/v1/camera-reviewed-labels.json \
  --clock-layout-plan data/controlled-recordings/v1/camera-layout-plan-reviewed.json \
  --skip-ocr --output data/controlled-recordings/v1/camera-comparison-geometric-probes-repeat.json

python3 experiments/audit_readings.py \
  data/controlled-recordings/v1/camera-comparison-geometric-probes-repeat.json \
  data/controlled-recordings/v1/camera-field-review-final.json \
  --output data/controlled-recordings/v1/camera-audit-geometric-repeat.json
```

OCR was skipped. `camera-comparison-reviewed.json` preserves stage 1 with the reviewed plan; `camera-comparison-score-window.json` preserves stage 2. `camera-audit-reference-final.json`, `camera-audit-score-window-final.json` and `camera-audit-geometric-final.json` retain the final reviews against each stage. `camera-review-sheets/` preserves prediction-free source contact sheets and the contaminated score mask.

For the active reader, `camera-active-field-view.json` exposes its saved all-fields rows to the same audit: for each field copy the row's shared `status` and `age`, take `value` from `values` and `observed` from `raw`, keeping null rows null. It records the original comparison JSON hash and the transformation method. `camera-active-field-audit.json` checks that view against the same final review, including full-timeline age/status invariants. `camera-evaluation-summary.json` indexes hashes of the input, frozen profiles, reviews, comparison reports and audits alongside the final counts. Audit invariants pass for all three candidate stages and the final active field view.

## Validation and next step

Original readings were regenerated: 1,638 samples, 52 uncertain. `python3 scripts/check.py` passes all 78 application tests, including original-recording regressions. The isolated optional suite passes all 36 tests. No application code or UI changed; no browser UI check, packed shadow equivalence rerun or additional old-recording comparisons were performed. No camera or existing server was opened or altered. Audio was not analyzed. Candidate output remains disabled.

The next focused implementation should reproduce the readable 3/4-to-core-1 disagreement in generated tests, then improve the score-core evidence without relaxing the known mixed-stroke safeguards. Preserve this frozen capture and its labels for regression; use fresh held-out footage for later accuracy claims. Score-window calibration, physical-scoreboard exposure/refresh evidence, unreviewed transitions, manual corrections and coordinated live throughput/delay testing remain open. This capture does not establish readiness to promote candidate output.
