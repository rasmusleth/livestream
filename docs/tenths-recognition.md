# Recorded tenths recognition: 2026-11-01

The region candidate can now recognize and confirm observed seconds/tenths in the supplied newer recording. It remains an opt-in diagnostic reader. The established reader and OBS output are unchanged, and no camera was opened for this change.

## Cause and focused change

Inspection used exact FFmpeg 10 Hz sample images, not independently sought video frames. At 42.5, 45.0 and 50.0 s the source shows 49.1, 46.6 and 41.8 seconds. The probe-era boxes cut through wider clock digits on the left. In the blank fourth slot, independently adapting the brightness threshold to brown panel texture could promote that texture into false foreground. The existing edge and fragment checks then correctly rejected the incomplete observation.

`RegionReader` now gives the first, second and fourth clock boxes more room on the left: 20%, 12% and 12% of their original width, rounded upward. The third stays at 4% to keep the physical colon out. Right padding stays 4%, vertical padding 12%. Score windows are unchanged. This is geometry for the known rectified panel, not automatic digit finding or support for other scoreboard layouts.

The four clock windows also share a brightness reference: the median red level across their pixels and the largest of the windows' 95th-percentile red levels. Their adaptive threshold remains median + 0.6 × contrast, with the existing minimum of 150. This shared reference is an additional floor: each clock window uses the larger of its own adaptive threshold and this floor. It can only raise a window's threshold. It does not assign blank because contrast is low; a blank still means no foreground survived the normal extraction/cleanup.

The two-clear-pixel edge guard, segment margins, narrow/aspect ambiguity checks, explicit clock layout selection and independent confirmation rules are unchanged. Neither missing digits nor missing ticks are filled from prior frames. Masking dim strokes can still erase a digit; explicitly selected layouts and uncertainty remain necessary. Exposure behavior outside these recordings is unvalidated.

## Evidence and limits

Both full recordings and the existing translation-window stress cases were rerun locally, with OCR skipped. Private recordings, calibration, labels, image crops and numeric reports remain outside Git. The new report names end in `-tenths.json` and `-tenths-stress.json`, preserving prior evidence.

| Recording | Complete raw Regions before → after | Independent clock fresh before → after |
| --- | --- | --- |
| Original, 1,638 samples | 1,559 → 1,551 | 1,502 → 1,499 |
| Newer, 514 samples | 224 → 471 | 202 → 379 |

Complete raw coverage on the newer recording rises from 43.6% to 91.6%. This is availability, not accuracy. The original has eight fewer complete raw readings and three fewer fresh clock confirmations, a small availability loss even though the default reader is unchanged. Original reviewed raw results are 9 correct / 0 wrong / 2 unknown, versus 10 / 0 / 1 before. Newer existing reviewed timestamps give 13 / 0 / 2, versus 6 / 0 / 9 before. No independent fresh field confirmation is wrong at those sparse reused timestamps.

In the explicitly selected tenths interval from 42.5 s through 51.3 s, the candidate has 77 available clock observations and 51 fresh confirmations out of 89 samples, up from zero. Remaining observations are unknown or held with age. The known 32.5 s / 10-pixel-upward away-score case still reads `1` in all 11 surrounding samples; the score extraction path was not changed.

At the eight reused stress anchors across both recordings, 72 translations/unshifted cases give 46 correct complete raw readings, zero wrong and 26 unknown. These are sparse regression checks, not arbitrary-framing accuracy evidence.

## Additional visual sequence review

After freezing the extraction policy, two further exact-sample sequences were inspected: 43.0–43.9 s and 47.0–47.9 s. All ten first-sequence images have clearly visible clocks from 48.6 through 47.7 seconds, and both scores remain 1. Each candidate clock matches its frame and is freshly confirmed; the legacy identical-repeat comparison holds an older clock throughout, showing why the independent progression rule matters.

The second sequence contains faint/mixed extra LED strokes and transition exposure. Only 47.1, 47.4 and 47.8 s were assigned clear visible-clock labels (44.6, 44.2 and 43.8 respectively). Seven other clocks remain unlabelled; no physical-clock truth was guessed from expected countdown timing. Both scores visibly remain 1. This is temporal validation from the same recording, not independent footage or hardware ground truth.

Across the 13 new clear labels, complete raw readings are 12 correct / 0 wrong / 1 unknown. The independent clock is freshly correct at 11 and held at two; no fresh reviewed clock is wrong. The combined 28-label newer-clip report gives 25 correct / 0 wrong / 3 unknown complete raw observations. All new labels, excluded-frame notes and derived reviewed metrics remain ignored/local. Reviewed metrics were calculated from the same cached decoded rows; the full command with the combined label file reproduces them without that cache.

Mixed exposure remains a real failure mode: raw valid-looking clocks can jump upward, for example two `44.9` observations after `44.6` in the second sequence. Independent confirmation holds `44.6` for those two observations rather than accepting a correction without its third piece of evidence. Other apparent transitions can look like valid digits and repeated/coherent errors may still confirm. The excluded frames do not establish the true physical clock; they must not be counted as correct merely because a prediction looks plausible.

The extended newer-clip translation check uses 17 reviewed anchors × 9 offsets (153 cases): 87 correct complete raw readings, zero wrong and 66 unknown. There are no wrong fresh field confirmations at these reviewed anchors. More diverse, independently reviewed footage and exposure/flicker testing remain necessary.

## Integration verification

The original batch reader was regenerated and still produces 1,638 observations / 52 uncertain raw readings. All 58 application tests pass, including five private-recording regressions. The optional experiment suite passes 17 tests, including independent full RGB drawings that exercise wide left strokes, colon exclusion, blank texture, crop rejection, missing required digits and observed tenths progression/held age through `ShadowReader`.

The newer recording was also processed through the actual packed shadow adapter. All 514 established-reader rows match the saved baseline exactly; all candidate field states match the updated offline timeline. The ignored report is `data/recognition-live-tenths-shadow.json`. Browser checks on temporary recorded-input servers displayed observed and held tenths with explicit age, including `43.8` observed while `44.6` remained held after mixed exposure, then held/aged values at EOF. The separate overlay stayed empty because the established reader had no confirmation on this framing. No UI behavior was changed. Both temporary demo servers were stopped; no camera or existing user server was touched.

This change does not address general exposure correction, automatic format selection, other scoreboard layouts, live throughput or end-to-end delay. Candidate output remains disabled. Those limits, the eight additional original-clip unknowns and the seven unlabelled transition clocks remain visible in the evidence rather than being hidden by lower safeguards.
