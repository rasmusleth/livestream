# Bounded colour-contrast score rejection: 2026-11-01

The diagnostic candidate now rejects the preserved blurred orange one/five and one/six mixtures instead of confirming nine or eight. A complementary red-colour view finds the competing one; the score becomes unavailable, never replaced with that one. The recovered clean threes/fours remain covered by regression tests. Candidate output stays disabled.

This fixes the selected orange failure, not blur generally. A wider all-pairs blur scan exposes six other third-digit cases per colour, and repeatable sequences still confirm those third digits. Recorded physical-truth ambiguity and live readiness remain unresolved.

## Evidence and bounded veto

In the previous [score-core balance stage](score-core-balance.md), the selected blurred orange mixtures have valid primary/local nine or eight, while the light-core mask is inconclusive. Combining red colour contrast and neutral light in one signal cannot expose a competing digit in these cases. The new view separately measures colour contrast in each rectified score patch:

```text
chroma = red - max(green, blue)
low, high = percentile50(chroma), percentile99(chroma)
threshold = max(20, low + 0.6 × (high - low))
foreground = primary_foreground and red > 150 and red >= 0.95 × green
             and chroma > threshold and high - low >= 20
```

The patch is floating-point RGB; this is an encoded-colour heuristic, not a physical exposure model. The primary masks are computed once and reused. This view deliberately retains only primary foreground, rather than introducing different coloured structures from the panel. It uses the existing cleanup, minimum component area, edge/narrow-glyph/aspect/segment guards. No primary, core-light, local-contrast, clock, calibration or confirmation rule changes.

Two additional bounds prevent a colour-only view from inventing a competing score:

- If at least 1% of the patch has all channels at least 200, the view is inconclusive (`neutral_cores`). Dropping bright neutral LED centres can leave only red glow; that cannot establish a competing digit. These reuse the existing white-core constants.
- Because this view removes primary foreground, its normalized alternative must not add an on-segment absent from the primary digit's decoded pattern. Such a shape becomes inconclusive (`unsupported_added_segments`), with its pre-filter digit retained as `score_chroma.mask_value`. A thin coloured rim and weak middle glow can otherwise normalize into eight inside a primary zero.

A remaining valid integer different from the primary triggers the existing `score_mask_disagreement` rejection. It never supplies output or rescues an unavailable primary. Existing core/light and local-contrast vetoes remain active independently; they are not subject to this new view's subset restriction. Inconclusiveness/agreement does not establish correctness.

`score_chroma` retains its value, reason, levels, bounds, mask value, bright-neutral fraction and rounded low/high/threshold diagnostics. Decisions use unrounded values. The comparison report records the fraction, percentiles, contrast floor and gate/subset rules. No new package is required beyond the candidate's existing optional NumPy/OpenCV environment.

Six new optional tests cover the targeted blurred mixtures, all ten clean digits in white/orange/red under the existing blur/dim/shift variants, clean threes/fours with close colour contrasts, actual shadow holds/staleness/recovery, coloured zero rims, and a valid alternative never rescuing primary crop rejection. Existing uneven-brightness and white-core/halo regressions remain unchanged.

## Generated exposure evidence

The original unblurred matrix was rerun unchanged: 90 directed pairs × three weights × three colours, 810 sequences / 12,150 frames. Each colour retains 2,430 correct clean raw scores with no wrong/unavailable clean scores, and zero third-digit mixed observations or confirmations. Missing-home frames stay unavailable with held ages preserved. A mixed rendering has no assigned physical score; confirmations matching a source digit still are not labelled correct.

The selected six-pair blur check (`15 16 51 61 69 96`, weight 0.5) was rerun for each colour, 18 sequences / 270 frames total. Orange third-digit fresh confirmations fall from eight to zero. White and red remain zero. All 54 clean observations per colour remain correct. A persistent rejected orange mixture holds the earlier score with advancing age and stale status, while the clock/away stay independently fresh; clean recovery requires fresh confirmation evidence.

A separate scan evaluates one blurred observation for every directed pair/weight/colour: 810 observations, not a confirmation-sequence benchmark. It uses the same 5×5 Gaussian blur with sigma 1. The baseline reader is the pre-change source from `6429ecd`; the report records both reader source hashes and the generator hash. Remaining third-digit observations are six per colour, versus baseline white six, orange ten and red six. The four removed orange cases are the targeted one/five and one/six directions.

The remaining cases are balanced `24`, `42`, `57`, `67`, `75` and `76`: 2/4 blends read eight; 5/7 blends read nine; 6/7 blends read eight. Repeating those six directed pairs at weight 0.5 through the actual confirmation sequence still yields twelve fresh third-digit confirmations per colour, despite all selected clean endpoints staying correct. They are retained as explicit failures, not assigned physical truth or hidden by the successful selected check.

Ignored reports use `data/candidate-exposure-{white,orange,red}-chroma-bounded.json`, `-chroma-bounded-blur.json` and `-chroma-bounded-residual-blur.json`. The broader observation scan is `data/candidate-chroma-bounded-all-blur-scan.json`. Earlier baseline and exploratory reports remain intact. Full generated timelines are checked for observation/value/status/age invariants and matching source hashes.

## Controlled capture and older recordings

The complete controlled recapture was decoded again with its frozen geometric profile, score-window template, captured-time layouts and unchanged 75 per-field reviews. The reviewed results remain home 66/66, away 75/75 and clock 69/69 correct raw readable fields; fresh correct counts stay 62, 70 and 60. No wrong reviewed observation/fresh output or fresh confirmation on the nine covered-home/six blank-clock samples is introduced. Most timestamps remain unreviewed; these are reused development/calibration anchors.

Across all 1,199 rows, home and clock states are exactly unchanged. Away loses one unreviewed observation at 0.4 seconds: eight is held with age 0.1, then the next observed eight awaits evidence at 0.5 with age 0.2 before confirming again. Available/fresh away counts change 1,189/1,163 → 1,188/1,161. This is an additional conservative hold, not a demonstrated accuracy improvement on that unreviewed frame. Every active-reader row is unchanged. The prior three/four recovery and deliberate blank/covered hold behavior are preserved.

Final local reports are `data/controlled-recordings/v1/camera-comparison-chroma-bounded.json` and `camera-audit-chroma-bounded.json`. The packed single-decoder recorded adapter and actual `ShadowReader` are checked against all 1,199 offline active rows and candidate field states with output disabled. No live camera or server is needed for that comparison.

## Checks, reproduction and limits

All three older full recordings were decoded again with their frozen profiles, unchanged labels and explicit layouts. Every active row, legacy candidate output row and independent field state remains exactly unchanged; complete raw candidate counts remain 1,520 / 471 / 1,284. Their per-field audits pass with the same unresolved confirmations on unreadable transitions. All three translation-window runs also retain exactly the same independent states: 342 reused anchors/offsets have 197 correct / zero wrong / 145 unknown complete raw observations and no wrong fresh field at labelled anchors. Neighbouring frames remain unlabelled. Reports use `data/recognition-{original,live,mock}-chroma-bounded{,-audit,-stress}.json`.

Original readings were regenerated (1,638 samples / 52 uncertain). `python3 scripts/check.py` passes all 78 application tests, including available original-recording regressions, and all 45 optional experiment tests pass. See the final entry in [VALIDATION.md](../VALIDATION.md). No UI code changed; a browser UI check is not required for this extraction-only change. No camera or existing user server was opened or altered. Media, calibration profiles, labels, numeric reports and review images stay ignored and local. No dependencies are added.

Use the [existing experiment environment](../experiments/README.md) and new output paths. Repeat the four full recording comparison/audit commands and three older translation-window commands with the frozen profiles/templates/layouts and `chroma-bounded` output names. Generated examples:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --all-pairs --color orange --output data/candidate-exposure-orange-chroma-bounded-repeat.json
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --pairs 15 16 51 61 69 96 --weights .5 --color orange --variant blur --output data/candidate-exposure-orange-chroma-bounded-blur-repeat.json
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --pairs 24 42 57 67 75 76 --weights .5 --color orange --variant blur --output data/candidate-exposure-orange-chroma-bounded-residual-repeat.json
```

Repeat for white/red. To broaden the observation scan into complete sequences, use the existing `--all-pairs --variant blur` options with a new destination; that full sequence matrix was not run in this change. No physical truth is assigned to mixtures in either mode.

Candidate output remains disabled. The newly enumerated blurred cases, unreviewed recorded transitions, drawing-specific calibration, physical-scoreboard exposure/refresh evidence, manual correction/output policy and coordinated live throughput/delay remain open. A successful generated run means the measurement completed, not that the scoreboard is safe for match use.
