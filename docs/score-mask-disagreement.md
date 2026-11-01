# Candidate score-mask disagreement: 2026-11-01

The diagnostic candidate now rejects a score when its normal mask and a stronger-light mask produce different valid digits. This prevents the generated one/five and one/six mixtures from confirming nine and eight, respectively. It never substitutes the stronger mask's digit. Balanced six/nine mixtures still confirm five, and previously ambiguous recorded transitions remain unresolved. Candidate output stays disabled; the active reader and OBS output are unchanged.

## Focused rule

`RegionReader.observe(frame)` rectifies the source once and extracts the existing patches. It inspects the unchanged primary masks, then a second set of masks using the existing [score-light signal](score-core-recognition.md):

```text
light = max(red - max(green, blue), (red + min(green, blue)) / 2)
core threshold = max(75, median(light) + 0.8 × (percentile99(light) - median(light)))
```

The second score mask requires red above 150 and red at least 0.95 × green. It retains the existing low-contrast rejection: the 95th-percentile contrast must reach 20, or the 99th percentile is tried; if neither reaches 20, no foreground is retained. Unlike the primary mask's conditional white-core rule, this complementary mask uses the light signal for all score colours. The 0.8 fraction and percentile selection are heuristics, not learned probabilities or calibrated exposure thresholds.

Both masks retain the same cleanup, minimum component size, crop boundary guard, narrow-glyph checks, aspect rejection and segment margins. If both produce integer scores and those integers differ, the final observation is null with reason `score_mask_disagreement`. The alternative digit is not output. A rejected primary observation is never rescued. A secondary blank or rejected shape is inconclusive and does not independently veto a primary digit; agreement or inconclusiveness is not proof of correctness.

Score diagnostics retain the primary `mask_value` and nested `score_core` evidence (value, reason, levels and bounds), alongside the final observation and reason. Clock masks and clock evidence remain unchanged. No previous digits or predicted clock values fill gaps. Independent confirmation rules are unchanged: rejecting home clears its pending evidence and holds its last value with increasing age, while away and clock can remain fresh.

Full RGB recognition now uses `observe` consistently in offline comparison, translation stress, generated exposure sequences and the actual `ShadowReader`. The `masks`, `inspect` and `digit` helpers remain available for primary-mask/shape diagnostics and the separate OCR experiment; they do not implement the two-mask veto. OCR was skipped in this validation. The extra mask pass adds processing cost even when its result is inconclusive; camera throughput and live delay remain unmeasured.

## Generated exposure matrix

The same [generated experiment](candidate-exposure-stress.md) was rerun: all 90 directed score changes, three new-source blend weights and white/orange/red LEDs, totalling 810 sequences and 12,150 frames. No fixture or expected value changed. Each colour gives the same counts on the shared controlled geometry:

| Per-colour result | Before → after |
| --- | --- |
| Clean home raw correct / wrong / unavailable | 2,430 / 0 / 0 → 2,430 / 0 / 0 |
| Clean fresh correct / wrong | 1,728 / 0 → 1,689 / 0 |
| Clean held / initial unknown | 432 / 270 → 471 / 270 |
| Mixed raw available | 678 → 420 |
| Mixed fresh confirmations | 560 → 349 |
| Mixed fresh values outside both source digits | 20 → 4 |
| Missing home fresh / held | 0 / 810 → 0 / 810 |

In eight former third-digit pair/weight cases per colour, the primary mask sees nine or eight and the core mask sees one. The observation is now rejected rather than confirming either interpretation. The clean phase has 39 fewer fresh confirmations per colour: after some mixtures are rejected, the first clean new score must await another observation. This is a confirmation-delay tradeoff, not lost clean raw availability. All generated timelines pass the existing observation/value/status/age audit.

The remaining two third-digit cases per colour are 50/50 six/nine and nine/six blends. Both masks read five, so the guard has no disagreement to detect and each sequence still has two fresh five confirmations. A valid-looking image can remain indistinguishable from a real third digit to this method. Mixed images have no assigned physical score; their confirmations are not counted as correct or wrong physical truth. No real-camera accuracy percentage follows from these controlled drawings.

Reports are ignored local files `data/candidate-exposure-{white,orange,red}-score-agreement.json`. The earlier matrix reports are preserved. They retain exact source pairs, blend weights, calibration, source hashes, package versions and every field state and diagnostic.

## Existing recordings and translations

All three recordings were decoded again with the same frozen profiles, unchanged labels and explicit clock layouts. Input hashes and profiles match the preceding reports:

| Recording | Samples | Complete candidate raw | Fresh independent clock |
| --- | --- | --- | --- |
| Original | 1,638 | 1,520 | 1,499 |
| Newer | 514 | 471 | 379 |
| Monitor recapture | 1,637 | 1,284 | 1,197 |

Every active-reader row, candidate independent field state and pre-existing digit diagnostic is exactly unchanged. The secondary mask is inconclusive for 236 available original away observations, 305 newer home observations and 38 recapture away observations. None of these full recordings produces a conflicting valid secondary score. Rejecting all inconclusive secondary masks would have discarded those primary observations without establishing a competing digit, so the rule deliberately requires a valid conflict. These are reused development recordings, not evidence of general safety under different exposure.

All three per-field audits pass with unchanged readable correctness, held ages and fresh confirmations on unreadable transitions. Those unresolved transitions are not fixed by this score-only change. Neither the unchanged observations nor a lack of mask conflict proves the physical display was correctly read.

The same translation windows were rerun. Every pre-existing row field and all independent states match the earlier score-core stress reports after excluding the two new diagnostic keys. At the 342 reused anchors/offsets, complete raw correct / wrong / unknown counts remain original 20 / 0 / 16, newer 87 / 0 / 66, and recapture 90 / 0 / 63. No fresh field confirmation is wrong at those labelled anchors. Neighbouring frames retain no inferred truth.

Final local reports are `data/recognition-{original,live,mock}-score-agreement.json`, with corresponding `-audit.json` and `-stress.json` reports. Candidate processing median/p95 was 19.75/29.96 ms, 23.40/83.80 ms and 20.83/44.39 ms, respectively, during concurrent offline comparisons. These timings include candidate recognition/state/frame hashing but exclude decoding, capture and OBS delivery, and were collected under contention. They are not a before/after throughput benchmark or evidence of live suitability.

## Checks and remaining limits

The original batch readings were regenerated: 1,638 samples, 52 uncertain. `python3 scripts/check.py` passes all 70 application tests, including generated-video tests and five available original-recording regressions. All 30 optional experiment tests pass. Three new tests cover competing masks across all LED colours and the affected directed mixtures, all ten clean digits through the full observation API, and disagreement/held age/recovery through the actual shadow reader with other fields remaining fresh. Existing failure-isolation tests now mock the full observation API.

Full recapture delivery through the real single-decoder packed shadow adapter matches all 1,637 updated active-reader rows and candidate field states, with candidate output disabled. Its ignored summary is `data/recognition-mock-score-agreement-shadow.json`. No UI code changed and no browser visual check was performed. No camera or existing user server was opened, stopped or changed; HTTP tests used their own temporary loopback server. No footage, local profile, label, generated image or numeric report is committed, and no dependency was added.

Before candidate output promotion, remaining exposure ambiguity, output/correction policy, independently readable reference footage, tenths recapture and coordinated live throughput/delay still need work. This rule rejects some demonstrated competing interpretations; it is not a complete mixed-exposure detector and does not make this setup match-ready.

## Reproduction

Use the [existing optional environment](../experiments/README.md). Repeat the three comparison, per-field audit and translation commands using new output destinations ending in `-score-agreement.json` / `-score-agreement-stress.json`, retaining the same profiles, labels and layout selections. For the generated matrix:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --all-pairs --color white --output data/candidate-exposure-white-score-agreement.json
```

Repeat for orange and red with corresponding new output names. The generator refuses existing report paths; preserve earlier evidence and choose a new suffix when reproducing locally.
