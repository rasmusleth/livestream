# Generated candidate exposure sequences: 2026-11-01

The diagnostic candidate can confirm a third score when a generated image blends two different source digits. The new offline `experiments/exposure_stress.py` makes this failure repeatable without private footage or camera access. It adds validation infrastructure and evidence; recognition, confirmation rules, the active reader and OBS output are unchanged. Candidate output stays disabled.

The later [score-mask disagreement guard](score-mask-disagreement.md) reduces fresh third-digit confirmations from twenty to four per LED colour on this matrix, without losing clean raw readings. The baseline counts below preserve this initial experiment. A subsequent [local RGB guard](local-score-contrast.md) rejects the balanced six/nine cases in the original matrix; newly repeatable blur variants still expose third-digit failures.

## Why this test

The [existing per-field reviews](exposure-validation.md) include candidate confirmations on visually ambiguous source fields. Their physical truth is unresolved. Local inspection of selected reviewed samples found that changing adaptive mask fractions between 0.4 and 0.8, or comparing per-segment brightness, did not consistently separate ambiguous source fields from readable ones. Those exploratory checks were not adopted as recognition rules. The review labels remain unchanged; no predicted clock or threshold agreement supplies ground truth.

A controlled exposure stress test can establish which images were generated and how confirmation behaves, while keeping its limits explicit. It lets a future extraction change be compared against clean digits, persistent mixed strokes, loss and recovery instead of adding a rule solely to fit a few ambiguous video samples. More temporal agreement alone cannot guarantee recognition correctness.

## Generated scene and timeline

The runner uses the tracked reference calibration with independent slanted line drawings of all ten digits. Its stroke definitions and geometry do not import the recognizer's patterns or normalized sampling areas. There are three LED colours: white `(255,250,255)`, orange `(255,100,0)` and red `(255,0,0)`, on a fixed brown background. No real pixels, local profile or recording are required.

Only home changes. Away stays one and the clock stays 17:51. For each directed score pair and blend weight, a fresh `CandidateState` receives fifteen RGB frames at 10 Hz:

1. Three clean old-score frames.
2. Three copies of the mixed rendering.
3. Three clean new-score frames.
4. Three missing-home frames, retaining the clock and away score.
5. Three clean new-score recovery frames.

A blend is `(1-weight) × old RGB + weight × new RGB`, rounded to bytes, at new-source weights 0.25, 0.50 and 0.75. This is blending in encoded RGB, not a calibrated optical exposure, LED flicker, rolling-shutter or camera-noise model. It does not establish a physical score during the mixed phase. The three persistent mixed samples deliberately stress repeated evidence, without claiming that real transition artifacts last 0.3 seconds.

A tiny changing pixel outside every region gives each full frame a unique SHA-256 identity. This avoids the candidate's intentionally conservative identical-payload hold; duplicate rejection remains enabled. There is no camera, HTTP server, output publisher, clock extrapolation or fallback value. Tests additionally verify that home loss leaves the independently recognized away score and clock fresh.

The shared `RegionReader` and `CandidateState` process these frames. Every row retains source time, phase, per-digit evidence, and each field's observation/value/status/age/stale flag. Only clean phases have an expected score. Summary correctness is assigned only to those clean home observations and fresh confirmations. Older held values remain held, even if they differ from a new clean digit. Mixed confirmations and values outside both source digits have separate counters; neither agreeing with a source nor producing another digit assigns physical truth to the blend. The missing phase records unavailable observations and held age separately.

## Full generated matrix

All 90 directed changes between different digits were run at all three blend weights, separately for each colour. These include corrections and resets as well as ordinary increments; they are not a distribution of real match events. Each colour contributes 270 sequences and 4,050 samples:

| LED colour | Clean home raw correct / wrong / unavailable | Clean fresh correct / wrong | Mixed fresh / samples | Mixed fresh outside both source digits | Missing fresh / samples |
| --- | --- | --- | --- | --- | --- |
| White | 2,430 / 0 / 0 | 1,728 / 0 | 560 / 810 | 20 | 0 / 810 |
| Orange | 2,430 / 0 / 0 | 1,728 / 0 | 560 / 810 | 20 | 0 / 810 |
| Red | 2,430 / 0 / 0 | 1,728 / 0 | 560 / 810 | 20 | 0 / 810 |

Each colour has 432 clean held states and 270 initial unknowns. All 810 missing-home states are held, with no observation or fresh confirmation. Ten pair/weight sequences per colour confirm a value outside both source digits; each contributes two such fresh confirmations. The colours reuse the same geometry and timeline and give identical aggregate counts here. They are controlled variations, not independent footage or an accuracy estimate.

For example, a 25% new-source blend of one and five is read as nine. The first mixed sample holds one while observing nine; the second and third confirm nine. Clean one and five are correctly recognized before and afterward. This demonstrates an image/confirmation failure in controlled input, not a newly established error timestamp in the recordings. The tool intentionally reports it rather than asserting that repeated evidence makes it safe.

Reports are ignored local files `data/candidate-exposure-{white,orange,red}-matrix.json`. They contain the exact calibration, tool versions, source hashes of the generator/reader/state modules, source pairs/weights and complete timelines. The existing reports, real-footage labels and calibration files were preserved. No generated image or numeric report is committed.

## Checks and next boundary

`python3 scripts/check.py` passes all 70 application tests, including the existing generated-video pipeline and five available original-recording regressions. All 27 optional experiment tests pass, including six new tests for actual candidate loss/recovery and independent fields, blend construction, honest mixed-field accounting, invalid inputs, report provenance and overwrite protection.

Every generated sequence in all three matrix reports passes the existing audit's timeline invariants for fresh observation equality, held values and advancing age. These checks establish accounting and controlled fixture behavior, not general recognition safety. The stress command writes measurements; a successful command exit is not a clean bill of health for mixed exposure.

No extraction, candidate state, UI or transport code changed. Original batch readings, three-recording comparisons, translation stress, packed shadow delivery and browser visual checks were not rerun in this stage; their preceding validation remains recorded in the [probe guard report](probe-core-rejection.md). No camera or existing user server was touched. The standard HTTP tests used their own temporary loopback server. No new dependency was added; the runner uses the existing optional image environment.

The next extraction hypothesis should reduce these demonstrated mixed-stroke failures while retaining clean-digit correctness and explicit loss/recovery behavior, then be checked against the unchanged real-footage labels and full timelines. A single image can be indistinguishable from a real third digit, so no software-only rejection rule is assumed to solve every exposure mixture. Independently readable reference footage and coordinated exposure/capture testing remain necessary. This stage neither promotes candidate output nor implements manual corrections.

## Reproduction

Use the [existing optional environment](../experiments/README.md). Output paths must be new; the command refuses to overwrite existing evidence.

```sh
# Small default set covering 0/1/8/9 confusions:
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --output data/candidate-exposure-default.json

# Complete directed score matrix; repeat for orange and red:
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --all-pairs --color white --output data/candidate-exposure-white-matrix.json

# One diagnostic case:
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --pairs 15 --weights .25 --output data/candidate-exposure-one-five.json
```

`--pairs` and `--all-pairs` are mutually exclusive. Scores remain one digit; this generator provides no multi-digit or arbitrary-framing validation. It currently exercises score mixtures with a stable clock, not mixed tenths-clock images or an end-to-end video decoder/capture pipeline.
