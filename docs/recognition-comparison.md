# Offline recognition comparison

The experiment favors a rectified whole-digit reader over the current fixed probes and the tested off-the-shelf Tesseract configuration. It is **not enabled in the server or OBS overlay**. The candidate still has failure cases, including a wrong score under a deliberate 10-pixel alignment error, so increased coverage is not a production accuracy claim.

## Inputs and method

Two local recordings of the same scoreboard were analyzed at 10 Hz:

- Original MP4: 163.8256 s, 1920×1080, nominal 25 fps; 1,638 samples. Uses tracked `calibration.json`.
- New MKV: 51.384 s, 1920×1080, nominal 60 fps; 514 samples. Uses a snapshot of the user's saved local calibration, including its four panel corners. Nominal container frame rate does not establish unique camera-frame delivery.

No camera device was opened. Footage, local calibration snapshots, image crops, annotations, and generated readings remain local and are excluded from Git. Experiment packages were installed in a temporary virtual environment; the application remains dependency-free beyond its existing tools.

The three pipelines are:

1. **Current:** unchanged `reader.recording_rows`, including its FFmpeg crop/half-scale and fixed RGB thresholds. Uses the relevant recording's calibration.
2. **Regions:** warp each full RGB frame from the supplied panel corners into the original reference view using [OpenCV perspective transforms](https://docs.opencv.org/4.13.0/da/d6e/tutorial_py_geometric_transformations.html), then read the six reference digit regions. A brightness threshold adapts between each region's median and 95th percentile; red/yellow foreground is separated from background, small components removed, and small gaps closed. Foreground bounds normalize each digit before measuring broad segment areas. A narrow-shape rule handles this display's `1`. Invalid or marginal patterns remain unknown.
3. **OCR:** the same rectification and foreground masks as Regions, scaled into a tightly spaced black-on-white digit strip. Local Tesseract 5.5.1 uses digits only, dictionaries disabled, and raw-line mode (`--psm 13`). Modes 7 and 13 and spacing were explored on development frames; 13 was retained. Missing/extra characters invalidate the entire observation. The preparation and segmentation choices follow [Tesseract’s quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html). No confidence cutoff is applied, so this configuration exposes plausible OCR mistakes rather than hiding them. This is one OCR baseline, not a verdict on trained or specialized OCR.

Both candidates distinguish an observed blank leading minute slot from an unknown digit, and support the observed last-minute layout with a blank final slot. The user verified that `46:8` means 46.8 seconds; experiment output expresses that as `00:46.8`. Automatic format inference is a prototype assumption: an obscured or flickering digit could resemble a blank. Production format changes need additional safeguards.

All pipelines use the same all-fields, two-consecutive-matching-observations confirmation rule and held-value semantics. Independent field confirmation is **not** implemented in this experiment. Candidate input uses full-resolution RGB frames; baseline uses its original half-resolution path. The comparison tests complete pipelines, not an isolated effect of one algorithm change.

## Coverage over complete recordings

Coverage means the method emitted a complete valid-looking raw observation. It does not mean it was correct. “Fresh” counts observations accepted by the confirmation rule, excluding held values.

| Recording | Method | Raw coverage | Fresh confirmation |
| --- | --- | --- | --- |
| Original | Current | 1,586/1,638 (96.8%) | 1,456/1,638 (88.9%) |
| Original | Regions | 1,614/1,638 (98.5%) | 1,504/1,638 (91.8%) |
| Original | OCR | 300/1,638 (18.3%) | 91/1,638 (5.6%) |
| New | Current | 1/514 (0.2%) | 0/514 (0.0%) |
| New | Regions | 372/514 (72.4%) | 277/514 (53.9%) |
| New | OCR | 116/514 (22.6%) | 12/514 (2.3%) |

To separate format support from other gains, the first 25 s of the new recording retain four-digit `MM:SS`. There, Current emits 1/250 complete raw readings (0.4%), Regions 235/250 (94.0%), and OCR 73/250 (29.2%). The improvement is therefore not solely from accepting blank-leading or fractional clock formats.

The longest interval without a fresh confirmation is 0.4 s / 0.3 s / 37.3 s on the original recording and 51.4 s / 5.6 s / 21.6 s on the new recording, respectively. Startup counts in these intervals; held values remain explicitly held.

## Visually reviewed timestamps

The assistant inspected source images for 11 original and 15 new timestamp samples. Eighteen initial timestamps were available during development; eight additional timestamp samples were selected and reviewed after the final shape rule was fixed (four per clip). Those eight are a small temporal holdout from the same recordings, not new-venue validation or an independently human-labelled test set. Not every frame has an annotation.

Labels refer to the **exact FFmpeg 10 Hz output samples**, not separately sought frames. This matters for fractional seconds: the sampled frame at 45.0 s reads 46.6 seconds and at 50.0 s reads 41.8, while independently sought frames showed different tenths. Corrections were made by inspecting those sampled images, not by copying model predictions.

| Recording | Method | Reviewed raw correct / wrong / unknown | Wrong fresh confirmations at reviewed timestamps |
| --- | --- | --- | --- |
| Original (11) | Current | 11 / 0 / 0 | 0 |
| Original (11) | Regions | 11 / 0 / 0 | 0 |
| Original (11) | OCR | 0 / 2 / 9 | 1 |
| New (15) | Current | 0 / 0 / 15 | 0 |
| New (15) | Regions | 11 / 0 / 4 | 0 |
| New (15) | OCR | 1 / 2 / 12 | 0 |

On the eight additional timestamps, Regions produces seven correct raw readings and one unknown; Current produces four correct and four unknown; OCR produces one wrong and seven unknown. Stale held clocks often differ from current truth; they are counted separately from wrong fresh confirmations. Zero wrong Regions confirmations in these sparse spot checks does not establish zero errors elsewhere.

### Confirmation limitation for tenths

At 10 Hz, a running tenths display may change on every sample. The existing requirement for two identical complete readings can therefore prevent fresh output even with perfect recognition. Repeated frames or a paused clock can occasionally satisfy it, but they are not a reliable confirmation strategy. Unknown gaps in the experiment combine visual failures with this state-rule limitation; they must not all be attributed to recognition quality.

Production integration needs a separately tested rule that confirms successive observed clock values consistent with their source timing, while preserving pauses, explicit resets/corrections, and uncertainty. It must never generate an unseen tick to fill missing input. Independent score/clock confirmation is also needed, but separating fields alone does not solve this tenths issue.

## Deliberate framing errors

Each of the eight additional frames was translated with calibration left unchanged. The two candidates saw the same shifted pixels. These are single-frame raw checks, not confirmation tests, and only translations were tested; no zoom, rotation, or moving-camera accuracy is claimed.

| Source-image shift | Cases per method | Regions correct / wrong / unknown | OCR correct / wrong / unknown |
| --- | --- | --- | --- |
| None | 8 | 7 / 0 / 1 | 0 / 1 / 7 |
| ±5 px horizontally or vertically | 32 | 28 / 0 / 4 | 0 / 5 / 27 |
| ±10 px horizontally or vertically | 32 | 27 / 1 / 4 | 1 / 5 / 26 |

The Regions error is the new recording at 32.5 s shifted upward 10 px: the away score `1` becomes `9`. This exposes an unsafe shape/crop boundary case. Two identical wrong observations could still satisfy the existing confirmation rule. Do not activate this prototype solely because its raw coverage is higher.

## Timing

Regions preprocessing plus recognition takes a median 6.3–6.8 ms/sample (95th percentile 8.1–9.6 ms). OCR, including shared preprocessing, PNG encoding and CLI process startup, takes a median 88.8–89.6 ms (95th percentile 98.3–100.0 ms). These are local experimental timings; decoding is excluded from candidate timers, runs overlapped, and they do not measure capture-to-OBS delay. Baseline decoding plus recognition took about 17.3 s for the original and 2.3 s for the new clip; that aggregate is not directly comparable with candidate per-sample timings.

Two visually checked clock changes in the new sample stream first clearly show `17:50` at 0.6 s and `17:49` at 1.7 s. Regions confirms them at 0.7 s and 1.8 s (one 0.1 s sample later); neither Current nor OCR confirms the correct new state in the following 0.8 s windows. This limited check measures confirmation delay relative to sampled visible evidence, not live physical latency.

## Next implementation

Proceed with whole-region recognition in an opt-in shadow mode first. Preserve the existing reader as a comparison, display per-field candidate/confirmation status, and exercise the same single-owner camera path. Before allowing the candidate to drive OBS:

- Reject cropped or ambiguous glyph shapes, particularly `1` versus `7`/`9`, and rerun the failed shift case on sequences.
- Make clock-format handling explicit and safe across leading blanks, fractional seconds, resets, obscured digits, and signal loss.
- Validate independent clock/home/away confirmation without inventing missing digits or advancing the clock independently.
- Obtain more labelled sequences and separate footage after tuning; include score changes, pauses, exposure/flicker changes, small zoom/rotation errors, and end-to-end live delay.

The current reference reader and runtime overlay behavior are unchanged by this PR.
