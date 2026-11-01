# Retain unevenly bright score strokes: 2026-11-01

The diagnostic candidate now reads the clear threes and fours that its stronger score mask rejected in the [controlled camera recapture](controlled-recapture-validation.md). The core view retains moderately dimmer strokes beside brighter right-hand stems. It still only vetoes a competing primary digit; it never supplies a replacement or rescues an unavailable primary observation. Candidate output remains disabled.

## Reproduction and bounded change

The recapture's primary and local masks correctly saw some scores as 3 or 4, while the high core threshold erased their horizontal/left strokes and left a valid-looking 1. An independent generated RGB fixture reproduces this without private pixels: use the existing slanted line geometry, a brown `(180,130,110)` background, bright right strokes `(255,220,170)` and other active strokes `(255,170,130)`. The former rule rejects the otherwise readable score due to disagreement. These are controlled encoded colours, not a physical illumination model.

Only `RegionReader.SCORE_CORE_FRACTION` changes, from 0.8 to 0.6:

```text
light = max(red - max(green, blue), (red + min(green, blue)) / 2)
core threshold = max(75, median(light) + 0.6 × (percentile99(light) - median(light)))
```

The primary light mask uses 0.6 of the 95th-percentile contrast (with its existing narrow-digit tail fallback); the complementary core mask still uses the 99th percentile. Sharing the contrast fraction reduces loss of legitimate weaker strokes while retaining a higher reference where bright competing strokes occupy the tail. This is a heuristic validated on the fixtures and reused recordings below, not a learned confidence or universal exposure threshold.

Primary masks, local RGB contrast, minimum contrast, colour gates, cleanup, crop/narrow-glyph/segment checks, explicit clock layouts, confirmation rules and held ages are unchanged. A valid core or local digit different from the primary still rejects the observation with `score_mask_disagreement`. Inconclusive alternatives remain inconclusive. Lowering the threshold also changes decisions on mixed drawings; the measurements below expose that tradeoff rather than treating agreement as correctness.

Three new optional tests reproduce the former 3/4-to-core-1 failure, retain all ten clean scores under two levels of uneven brightness without modifying source frames, and exercise actual `ShadowReader` confirmation/loss/staleness/recovery with clock and away remaining independently fresh. The existing competing one/five, one/six, balanced six/nine, white halo zero, crop and clean-colour/blur/dim/shift tests pass unchanged.

## Same controlled recapture, frozen calibration and labels

The full 1,199-sample capture was decoded again using the frozen geometric probe profile, diagnostic score-window template, captured-time layout plan, 51 complete-reading labels and 75 per-field reviews from the previous evaluation. No calibration or label was adjusted for the new output. Every active-reader row and independent candidate clock state is exactly unchanged.

| Candidate field | Available observations before → after | Fresh confirmations before → after | Maximum held age before → after |
| --- | --- | --- | --- |
| Home | 988 → 1,149 | 969 → 1,130 | 15.0 → 5.1 s |
| Away | 656 → 1,189 | 617 → 1,163 | 40.1 → 0.3 s |
| Clock | 1,129 → 1,129 | 1,077 → 1,077 | 5.2 → 5.2 s |

Legacy complete candidate raw availability rises from 533 to 1,071; the independent fields above describe actual candidate confirmation behavior. Availability is not accuracy.

| Reviewed candidate field | Readable | Correct observed before → after | Correct fresh before → after | Wrong observed / fresh after | Readable held / unknown after | Unreadable / fresh on unreadable |
| --- | ---: | --- | --- | --- | --- | --- |
| Home | 66 | 49 → 66 | 46 → 62 | 0 / 0 | 3 / 1 | 9 / 0 |
| Away | 75 | 33 → 75 | 30 → 70 | 0 / 0 | 4 / 1 | 0 / 0 |
| Clock | 69 | 69 → 69 | 60 → 60 | 0 / 0 | 8 / 1 | 6 / 0 |

Every reviewed readable field now has the correct raw observation. Held values remain distinct from fresh correctness; two reviewed readable held samples each for home and away still differ from the visible score while awaiting confirmation. Most timestamps (1,124 per field) remain unreviewed. These are reused development/calibration samples, not a whole-clip accuracy estimate or held-out validation.

At 104.9 seconds, visible home 3 and away 4 are observed, then confirmed at 105.0 despite the blank clock. Home 3 is held through the covered interval with advancing age, reaches 5.1 seconds at the first reviewed recovery frame (114.9), and confirms again at 115.0. Clock behavior is unchanged: blank input holds the last clock and recovery/corrections await evidence. No zero substitution or independent ticking is introduced. Home score-mask disagreements fall from 161 to zero; away disagreements fall from 541 to eight, so not all unreviewed score ambiguity is resolved.

Ignored results are `data/controlled-recordings/v1/camera-comparison-core-balance.json` and `camera-audit-core-balance.json`. Full delivery through the actual single-decoder packed recording adapter with `ShadowReader` matches all 1,199 active rows and independent candidate field states. `camera-core-balance-shadow.json` retains the report hash and equivalence result with output disabled. This verifies recorded transport/state agreement, not camera throughput or OBS latency.

## Mixed-exposure regression and tradeoff

The original matrix was regenerated unchanged for all 90 directed score pairs, three blend weights and three colours: 810 sequences / 12,150 frames. All 2,430 clean home observations per colour remain correct, with no wrong or missing clean raw values. All missing-home samples remain unavailable and held with explicit age. No unperturbed matrix observation or fresh confirmation is a third digit absent from both sources.

| Per-colour matrix result | White before → after | Orange before → after | Red before → after |
| --- | --- | --- | --- |
| Correct clean fresh | 1,674 → 1,701 | 1,674 → 1,674 | 1,674 → 1,701 |
| Mixed available observations | 324 → 486 | 324 → 324 | 324 → 486 |
| Mixed fresh confirmations | 270 → 405 | 270 → 270 | 270 → 405 |
| Mixed third-digit observations / fresh | 0/0 → 0/0 | 0/0 → 0/0 | 0/0 → 0/0 |

Mixed images still have no assigned physical score. The lower threshold admits more source-like mixed readings in white and red; that is not evidence that those readings are correct or that mixed-exposure safety is solved. See the final matrix counts and remaining blurred failure below.

The same selected blur check was repeated for directed pairs 15, 16, 51, 61, 69 and 96 at weight 0.5 in all three colours. Orange still produces eight fresh third-digit confirmations (unchanged). Red falls from eight to zero; white remains zero. All 54 clean samples per colour stay correct. Orange blur remains an unresolved, reproducible failure, and a zero count on another selected fixture is not a general safety claim.

Reports use `data/candidate-exposure-{white,orange,red}-core-balance.json` and corresponding `-core-balance-blur.json` names. They preserve every observation/state, source hashes and explicit output-disabled metadata. The earlier reports remain intact. Full generated timelines pass value/status/age consistency checks.

## Older recordings and validation

All three previous full recordings were decoded again with unchanged saved profiles, labels and explicit layouts; OCR was skipped. Every active row, candidate independent field state and legacy candidate output row is exactly unchanged. Complete candidate raw counts remain original 1,520, newer 471 and monitor recapture 1,284. Fresh independent clocks remain 1,499, 379 and 1,197. Score-core diagnostics may differ; this threshold change does not fix the existing confirmations on unreadable recorded transitions.

All three per-field audits pass with the same reviewed counts and unresolved unreadable confirmations. The same translation windows were rerun: all independent states remain exactly unchanged, and 342 reused anchors/offsets retain 197 correct / zero wrong / 145 unknown complete raw observations with no wrong fresh field at labelled anchors. Unlabelled neighbouring frames retain no inferred truth. Results use `data/recognition-{original,live,mock}-core-balance{,-audit,-stress}.json` names.

Original batch readings were regenerated: 1,638 observations / 52 uncertain. `python3 scripts/check.py` passes all 78 application tests, including the generated pipeline and available original-recording regressions. All 39 optional tests pass. No UI changed or browser UI check was performed. No camera or existing user server was opened or altered; HTTP tests use their own temporary loopback server. No packages, private pixels, media, profiles, labels or reports are added to Git.

## Reproduction and remaining work

Use the [existing optional environment](../experiments/README.md) and new output filenames. Repeat the controlled comparison/audit commands in the [recapture report](controlled-recapture-validation.md) with the frozen profiles/review and a `core-balance` output suffix. Repeat the three older recording comparison/audit/translation commands with that suffix and unchanged inputs. Generate the matrix and selected blur check for every colour:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --all-pairs --color white --output data/candidate-exposure-white-core-balance-repeat.json
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --pairs 15 16 51 61 69 96 --weights .5 --color orange --variant blur --output data/candidate-exposure-orange-core-balance-blur-repeat.json
```

Candidate output stays disabled. Orange blurred mixtures, unreviewed transitions, the drawing-specific score-window setup, physical-scoreboard exposure/refresh evidence, manual correction/output policy and coordinated live throughput/delay still block any claim of reliable match use. The next exposure work should target the preserved blurred orange failure without sacrificing these recovered clean scores or known rejection cases; later accuracy claims require fresh independently reviewed footage.

The subsequent [bounded colour-contrast veto](score-chroma-rejection.md) rejects the selected orange one/five and one/six blur cases while retaining the reviewed recovered scores. Broader all-pairs blur checks expose additional failures in every colour, so that follow-up still leaves candidate output disabled.
