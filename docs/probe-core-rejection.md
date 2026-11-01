# Active probe reader: white-core rejection, 2026-11-01

The active reader now rejects contradictory white-core evidence instead of confirming the four reviewed wrong readings on `mock-scoreboard-testing-clip.mkv`. This is a conservative rejection change, not successful recognition of the recapture. With the existing frozen calibration, all 1,637 output states are now unknown; no values are confirmed. The candidate remains diagnostic-only and cannot drive OBS.

## Failure mechanism

The [recapture review](mock-capture-validation.md) found four fresh complete confirmations, at 123.4, 144.1, 161.9 and 162.0 seconds. All report home/away 9–7 instead of visible 0–1; the first also reports 18:47 instead of 18:41. Investigation used the existing sequential 10 Hz crop/scale path and saved `data/recognition-mock-registration-calibration.json`, without moving probes or changing any calibration.

The active pixel test counts `red > 220`, `green > 60`, `red > 1.03 × green`. A neutral white LED centre fails that last condition. The home zero's lower-left probe has colour occupancy 0.10, 0.15, 0.15 and 0.10 at the four failure samples, respectively, despite white occupancy 1.00, 1.00, 0.95 and 1.00. Meanwhile red glow in the visibly hollow middle has colour occupancy 0.80, 0.77, 1.00 and 1.00. The resulting pattern is nine. Two repeated observations confirm that persistent error; repetition is not an accuracy guarantee.

The slanted cap of a visible one also contains bright red glow at the top probe. At 123.4 the away top probe has colour occupancy 1.00 but mean RGB approximately (253, 92, 134); the seconds-units top has colour occupancy 0.70 and mean RGB approximately (227, 78, 103). These produce false sevens. The new guard blocks the complete output through the contradictory home digit; it does not repair those glow-induced sevens or infer the intended clock/score.

## Guard and state semantics

Each existing probe additionally measures the fraction of pixels with all three RGB channels at least 200. If a probe is off under the colour threshold (occupancy below 0.25), but white occupancy is at least 0.305 (the existing 0.25 threshold plus its 0.055 margin), that entire digit becomes unavailable. This applies to all six digits. Rejection sets its confidence margin to zero. White evidence never adds strokes, selects an alternative digit or fills a missing value.

Rows retain the original `segments` colour occupancies and add `white_segments` with the same seven-probe ordering, plus a `rejections` map from digit name to `white_core_on_off_probe`. Decisions use unrounded fractions; diagnostics are rounded to two decimals, as before. These are heuristic pixel diagnostics, not calibrated probabilities or proof that a physical stroke is lit. Bright reflections, exposure and calibration errors can also cause rejection.

Confirmation logic is unchanged. A rejected digit makes the complete raw observation null, clears the pending repetition sequence, and holds any previous confirmed output with its original confirmation time and increasing age. Before the first confirmation, values and age remain null with unknown status. Recovery still requires two successive matching complete observations. The reader never substitutes zero or advances a clock independently.

A broader replacement brightness mask was explored locally but rejected because it discarded many original-clip observations. The selected veto leaves original/newer output unchanged while addressing the demonstrated contradiction. It intentionally does not make white-only digits readable. A glow-only error without a contradictory white probe can still survive.

## Full-recording validation

All three recordings were decoded again with the same saved calibrations, existing labels, explicit candidate clock layouts and OCR skipped. Input hashes and profiles match the prior score-core reports. Reports are ignored local files named `data/recognition-{original,live,mock}-probe-guard.json`; pre-fix reports are preserved.

| Recording | Samples | Complete probe raw before → after | Fresh complete confirmations before → after |
| --- | --- | --- | --- |
| Original | 1,638 | 1,586 → 1,586 | 1,456 → 1,456 |
| Newer | 514 | 1 → 1 | 0 → 0 |
| Monitor recapture | 1,637 | 21 → 2 | 4 → 0 |

Every pre-existing row field on the original and newer recording is exactly unchanged. The newer reader's lone raw reading remains unvalidated and is not confirmed. On the recapture, the guard rejects home on 1,412 samples, away on 847, and minutes-tens on 238; these counts overlap. All four known failures now have null raw/output values, null age and unknown status, with explicit home rejection. At the same 48 completely readable reviewed timestamps, probe complete raw changes from zero correct / five wrong / 43 unknown to zero correct / zero wrong / 48 unknown. The two explicitly unreadable transition fields in the fifty-sample review remain unlabelled.

The two remaining complete raw observations, at 153.6 and 153.8, report 18:29 / 8–7. Sequential FFmpeg samples at those exact indices were additionally inspected after freezing the guard: both visibly show 18:29 / 0–1. This is a new diagnostic review of reused footage, not held-out validation. Its local labels are in `data/recognition-mock-probe-residual-review.json`; the existing fifty-sample review is unchanged. The two wrong raw readings are separated by an unavailable sample and never confirm. They remain a concrete residual recognition risk; the guard does not justify reliable operation on this setup, different framing, or different exposure. No whole-clip accuracy is claimed.

Candidate digit diagnostics and every independent candidate field state are exactly unchanged on all three recordings. All three existing per-field candidate audits pass again, including their unresolved fresh confirmations on unreadable transitions. No candidate recognition or output policy changed. Translation stress was not rerun because the candidate is unchanged; the earlier candidate stress results do not validate the active reader.

The original batch readings were regenerated: 1,638 samples, 52 uncertain. `python3 scripts/check.py` passes all 70 application tests, including five original-recording regressions. Four new RGB probe tests exercise the false-nine case, blank rejection, all ten ordinary colour digits, white-only uncertainty, held age and recovery. The extended generated-video test also exercises white-core rejection, held age and recovery through batch, streamed, preview and shadow-packed input. The separate optional experiment suite passes all 21 tests.

A full recapture run through the actual single-decoder packed shadow adapter matches all 1,637 updated active-reader rows and all candidate field states. Candidate output remains disabled and active output stays empty. Its ignored summary is `data/recognition-mock-probe-guard-shadow.json`. No UI changed or browser visual check was performed. No camera or existing user server was opened, stopped or changed; the HTTP tests use their own temporary loopback server. No video, calibration, annotation, crop or numeric report is committed.

## Reproduction and remaining work

Use the [existing optional experiment environment](../experiments/README.md). Repeat its three score-core comparison commands with output destinations ending in `-probe-guard.json` instead of `-score-cores-final.json`, preserving the same videos, profiles, labels and layouts. Repeat the per-field audit commands with these new report/output names. To run only the active recapture path:

```sh
python3 reader.py mock-scoreboard-testing-clip.mkv --calibration data/recognition-mock-registration-calibration.json --output data/recognition-mock-probe-guard-readings.json
python3 reader.py scoreboard-2-min-clip.mp4
python3 scripts/check.py
```

Further extraction/calibration work must address glow-induced score and clock misclassification without recovering availability by guessing. Manual correction/output policy, tenths recapture, broader exposure/framing coverage and coordinated live throughput/delay testing remain open. This guard prevents the demonstrated confirmed failures by making output unavailable; it does not make this camera setup ready for a match.
