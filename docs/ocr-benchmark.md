# Frozen local OCR benchmark v1

Task 1 of the [OCR comparison plan](ocr-comparison-plan.md) establishes the inputs and decision rules before learned OCR testing. It implements a prediction-free whole-field crop exporter, a local input lock, drift verification and a portable [machine-readable comparison contract](../experiments/benchmark/contract-v1.json). It does not implement OCR, recognition changes or output integration. Candidate output remains disabled.

## Inputs and split

The private bundle is `data/controlled-recordings/v1/ocr-benchmark-v1/`. Its recipe, lock, pictures, reviews, baseline reports and logs are ignored. The final r2 lock contains 659 assets, SHA-256 `1b915a3e286e621f4ceaf97c7bd6326622a30d01d408fe217b3b01a0ea1d5eb4`; its crop index binds 202 selected source frames / 606 PNG crops. The initial lock is retained with its known annotation issue. Existing recordings, saved calibrations, templates and earlier reviews/results are preserved. The lock records SHA-256 and byte size for every input, exported crop and relevant reader/evaluation source, plus the Git revision, FFmpeg/package versions, FFprobe video metadata, decode recipe, exact sample indices, per-field source quadrilaterals and rectified rectangles. Verification rehashes every frozen asset; it never silently regenerates a changed input.

| Recording | Sequential 10 Hz samples | OCR configuration split | Reviewed timestamps |
| --- | --- | --- | --- |
| Original excerpt | 1,638 | Development | 20 existing |
| Newer camera recording | 514 | Development | 20 existing |
| Monitor recapture | 1,637 | Locked verification | 50 existing |
| Controlled camera recapture | 1,199 | Development | 173: 75 existing plus 98 new |

The split applies to the **whole recording**, including anchors outside the short sequences. Do not use monitor-recapture images or new OCR predictions for feasibility/preprocessing/confidence tuning in tasks 2–3. Freeze that configuration first, then evaluate it there in task 4. If it informs tuning, retire it to development and obtain a fresh verification group. No random adjacent-frame split is used.

All four recordings have already informed region-reader development, and the monitor recapture contains an earlier recording of the same panel. Its labels are reused regression evidence. This is a lock for a new OCR configuration on known footage, not an untouched test of the baseline, independent physical-board evidence or proof of generalization. Task 5 still needs new board/session groups. Verification labels are local and accessible for auditing; the split is a workflow restriction, not a technical access-control claim.

Existing complete-reading anchors and the three previous per-field reviews retain their original files/hashes. The controlled review is copied into the bundle and extended, leaving its earlier 75-timestamp file unchanged. Labels come from captured pixels. Source-video intention, reader predictions, confidence and neighbouring countdown values are not label generators. Omitted fields outside complete windows remain unreviewed.

## New sequence review

The coding agent visually inspected 120 exact source samples in 19 short controlled-capture sequences with reader predictions hidden. Twenty-two timestamps overlap earlier reviews and agree; 98 are new. This is coding-agent review, not independent human annotation or external hardware truth. The r2 review preserves explicit unreadability, including mixed-brightness clocks at 82.3, 82.4, 82.6 and 82.8 seconds. Those frames cannot inherit expected tenths from the generated source timeline.

The first baseline audit exposed one reduced-sheet transcription error at 50.9 s: full-resolution reinspection shows `19:58`, originally entered as `19:59`. The baseline prediction was known during that correction. Revision r2 records this provenance, retains the original review and first manifest unchanged, and binds a new crop index/recipe and corrected review. No recognition setting was changed. All other labels remain unchanged; the correction is explicit rather than silently counted as a recognition fix.

The source-grid windows below include **both endpoints**. They are all development because the whole controlled recording is development.

| Scenario | Windows (seconds) |
| --- | --- |
| Home zero/three/six | 10.8–11.2, 16.8–17.2, 22.3–22.7 |
| Away three/six | 36.8–37.2, 42.3–42.7 |
| Changing clock | 50.5–51.1, 54.2–54.8 |
| Paused clock | 60.5–61.1, 64.2–64.8 |
| Tenths, including mixed strokes | 70.4–71.0, 82.2–82.8 |
| Score correction/reset | 92.8–93.2, 98.2–98.8 |
| Clock loss and blank input | 104.7–105.2, 107.2–107.8 |
| Covered home and clock recovery | 109.7–110.3, 112.2–112.8 |
| Score recovery and later clean clock | 114.7–115.3, 117.2–117.8 |

Earlier controlled anchors cover all ten digits in both score sweeps. Complete sequences from the earlier per-field reviews are retained too: original 70.0–70.9 / 118.6–119.5; newer 43.0–43.9 / 47.0–47.9; monitor recapture 60.0–60.9 / 70.2–71.1 / 118.5–119.4. Sparse anchors outside these windows are not interpolated into sequence truth. All 4,988 samples remain in each baseline timeline from zero, so confirmation state is not restarted at a review window.

## Whole-field geometry

Export decodes original-resolution RGB24 with the existing sequential FFmpeg `fps=10` path, rectifies the panel with the saved board corners and bilinear OpenCV interpolation, then crops a contiguous colour rectangle. It applies no colour threshold, binary mask, digit concatenation, OCR-dependent trim or inference. Images are PNG RGB content; OpenCV's BGR convention is converted explicitly. Engine-specific resizing/preprocessing must be recorded separately in the later comparison.

Rectified reference rectangles are `x,y,width,height`, before any model preprocessing:

| Source group | Clock | Home | Away |
| --- | --- | --- | --- |
| Original/newer/monitor recapture | 710,490,530,210 | 605,695,140,165 | 1280,700,145,165 |
| Controlled recapture | 710,490,530,210 | 610,716,133,122 | 1285,720,135,124 |

These are explicitly selected field windows with background margins, not the candidate's individual digit patches. The controlled score boxes exclude the printed HOME/AWAY labels. Whole-clock crops preserve the colon/decimal and real blank space. Inspection at three source samples per recording checked complete glyphs, punctuation and margins before any OCR result existed; every new controlled sequence was also inspected. Corners map into the source frame without clipping. This establishes usable crops on the inspected examples, not automatic field discovery or guarantees for unseen layouts/multi-digit scores. Geometric review files bind their acceptance and method to the exact exported-crop index hash.

## Freeze and verify

The local recipe has `version: 1`, a `crop_index` path, optional `supplemental_assets`, and a `recordings` array. Each recording names `id`, `split`, `video`, `calibration`, `template`, `samples`, `anchors`, `review`, `layout`, `baseline_report`, `geometry_review`, `field_boxes`, `geometry_samples` and `windows`. A window names `id`, `start`, `end`, `split` and `scenario`. Paths are relative to the repository root or absolute. `geometry_samples` are integer source-sample indices. Review files use the existing per-field audit format; every window sample must explicitly label all three fields with either a valid value or an unreadable reason. Other samples may omit fields.

From the repository root, using the existing optional image environment only for crop export:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/ocr_benchmark.py crops \
  data/controlled-recordings/v1/ocr-benchmark-v1/recipe-r2.json \
  --output data/controlled-recordings/v1/ocr-benchmark-v1/crops-r2
```

The recorded run fully decodes all four sources and checks dimensions and sample counts. Export refuses an existing destination. After prediction-free inspection, a geometry review for each recording contains `recording_id`, `accepted: true`, a nonempty `method`, and `crop_index_sha256`. Freeze/verify need only the standard library:

```sh
python3 experiments/ocr_benchmark.py freeze \
  data/controlled-recordings/v1/ocr-benchmark-v1/recipe-r2.json \
  --output data/controlled-recordings/v1/ocr-benchmark-v1/manifest-r2.json
python3 experiments/ocr_benchmark.py verify \
  data/controlled-recordings/v1/ocr-benchmark-v1/manifest-r2.json
```

Existing lock files are refused. To reproduce an export use a new destination and recipe version, then review and freeze a new bundle; do not overwrite v1. Freeze checks crop/input hashes, complete reviewed windows, unique/grid-bound labels, split consistency, source/crop geometry, baseline video/count/calibration/template/layout identity and full baseline observation/status/age invariants. It inventories review readability and runs the existing per-field audit against each baseline. Hashes preserve provenance but do not prove labels correct. Relevant source edits in later tasks intentionally make v1 drift verification fail for those assets: preserve this baseline lock and record changed source hashes in a **new run manifest**, never silently rewrite the frozen baseline.

The recipe also binds the preserved white/orange/red generated unblurred matrices, selected blurred cases, residual blurred failures, broader single-observation scan and their summary. These are separate synthetic diagnostics without physical mixture truth. Full all-pairs blurred confirmation sequences are still not available; do not claim they ran as part of this freeze.

## Decision contract and validation limits

The versioned JSON contract fixes count names, report identity/evidence fields and pass/fail/inconclusive statuses. Wrong fresh readable output has first priority. Fresh output on unreadable fields is a separate risk, never accuracy. Compare regressions **at the same sample**, so a lower aggregate error count cannot hide a newly introduced failure. Preserve recovered clean-score results and require a reproducible coverage/recovery benefit at practical measured cost. A failed gate prevents a replacement recommendation pending explicit review; no output promotion is authorized here.

Held-value correctness, source-time age/staleness and recovery remain separate from observations and fresh output. Report recovery/confirmation delay only when a complete reviewed sequence establishes its onset and confirmation; otherwise report a censored/unknown delay. Stale duration counts held samples with age at least one second. Runtime measures all three fields, cold/warm setup, CPU, peak RSS, model size and dependency/setup effort. Ten source frames per second / 100 ms per source sample is provisional and does not measure hardware-to-OBS delay. Gate evidence absent means inconclusive, not pass.

All four baseline comparisons were regenerated using the frozen saved profiles/templates, layouts and existing anchors, with OCR skipped. Every active, legacy-candidate and independent-candidate timeline row exactly matches its saved pre-task report across all 4,988 samples. Application extraction, recognition, confirmation, transport and output behavior are unchanged. No model is installed, downloaded, trained or evaluated. No image data leaves the machine. No application UI changes need a browser check. No camera or existing server is opened or altered; standard HTTP tests use their own temporary loopback server.

The required `python3 scripts/check.py` passes all 84 application tests, including six new portable benchmark tests, generated-video pipelines and the five existing local-recording regressions. The existing original `data/readings.json` is used; application batch extraction was not regenerated because extraction behavior did not change. All 46 optional experiment tests pass, including a new real FFmpeg-generated RGB video export test. Old translation stress, synthetic exposure matrices and packed-shadow equivalence were not rerun; their inputs/results are preserved, and recognition/state code is unchanged. No model or UI validation is claimed.

The next task after this PR is merged is **local pretrained OCR feasibility on development crops only**. It must verify current official runtime/model compatibility and licensing, explicitly provision local weights and record model/runtime hashes before inference. This benchmark does not yet tell us whether OCR is better.
