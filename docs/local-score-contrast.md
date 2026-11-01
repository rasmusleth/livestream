# Candidate local RGB score contrast: 2026-11-01

The candidate now rejects the remaining balanced six/nine mixtures in the original generated matrix. A complementary local-contrast mask exposes dim strokes missing from both existing masks; their competing valid interpretation makes the score unavailable rather than replacing it. The original matrix has zero third-digit observations or confirmations after this change. This is not a complete exposure fix: a new repeatable blurred-input check still produces third digits for red/orange mixtures. Candidate output remains disabled, and all three existing recorded timelines are unchanged.

## Local evidence and bounded veto

The [previous guard](score-mask-disagreement.md) rejects competing valid primary/core digits. In a 50/50 six/nine drawing, both existing masks see five. The lower-left and upper-right strokes are dimmer than the shared strokes and disappear under their thresholds.

`RegionReader.observe` now additionally inspects local RGB contrast in each rectified score patch. For each channel, a grayscale morphological opening with a 21×21 square kernel estimates broad background structure. Positive differences from that estimate define the contrast magnitude:

```text
background = opening(RGB, 21×21)
delta = max(0, RGB - background)             # independently per channel
contrast = sqrt(delta_red² + delta_green² + delta_blue²)
threshold = max(20, 0.45 × percentile99(contrast))
foreground = red > 150 and red >= 0.95 × green and contrast > threshold
```

This is a heuristic on encoded RGB, not a physical illumination model. The fixed kernel is in the known rectified template's pixel coordinates; it is not automatically adapted to other scoreboard layouts or stroke widths. It can expose narrow local structures while suppressing broad glow, but texture, reflections, blur, broad strokes and camera appearance can still defeat it.

The mask receives the existing cleanup, component-size, crop-edge, narrow-glyph, aspect and segment checks. If its result is a valid integer different from the valid primary digit, the final observation becomes null with the existing `score_mask_disagreement` reason. The stronger-core veto remains active too. Neither complementary mask supplies a replacement value, rescues a rejected primary digit, or fills a missing score. A rejected/blank alternative is inconclusive, and agreeing masks do not establish physical truth.

The new nested `score_local` diagnostic retains value, reason, levels, bounds, `contrast_tail` and `contrast_threshold`. Reported contrast numbers are rounded to three decimals; decisions use unrounded values. Existing `mask_value` and `score_core` diagnostics remain intact. One shared rectification supplies all views. Cleanup was factored into a common helper without changing its operations. Clock recognition, calibration, independent confirmation rules and the active reader are unchanged. Score rejection clears pending evidence and holds any confirmed value with increasing age; clock and away can remain independently fresh.

A red-channel-only local mask was explored and discarded because it admitted red glow and vetoed many recapture zeros. Positive local changes across RGB preserve white LED cores while rejecting the generated red centre glow. This is a measured choice on current development inputs, not evidence of general colour/exposure support.

## Original generated matrix

All 90 directed score changes, three blend weights and three LED colours were rerun: 810 sequences / 12,150 samples, using the same unperturbed drawings and clean expected values. Per-colour counts are identical on this shared geometry:

| Per-colour result | Previous guard → local RGB guard |
| --- | --- |
| Clean raw correct / wrong / unavailable | 2,430 / 0 / 0 → 2,430 / 0 / 0 |
| Clean fresh correct / wrong | 1,689 / 0 → 1,674 / 0 |
| Clean held / initial unknown | 471 / 270 → 486 / 270 |
| Mixed raw available | 420 → 324 |
| Mixed fresh confirmations | 349 → 270 |
| Mixed raw / fresh outside both source digits | 6 / 4 → 0 / 0 |
| Missing home fresh / held | 0 / 810 → 0 / 810 |

Balanced six/nine and nine/six now have primary five, core five and local eight; the observation stays unavailable. Eight is never output as the correction. Fifteen fewer clean samples per colour freshly confirm because rejecting preceding mixtures requires new confirmation evidence; clean raw availability is unchanged. The 270 remaining fresh mixed observations per colour agree with one of the source digits, but the mixed image has no assigned physical score, so these are not counted as correct.

Final ignored reports are `data/candidate-exposure-{white,orange,red}-local-contrast-final.json`. Earlier matrix and development reports are preserved. All generated timelines pass the existing value/status/age invariants and all final source hashes match the code used to generate them.

## Controlled variants expose a remaining limit

The exposure runner now accepts `--variant none|blur|dim|shift`. The default `none` preserves its previous frame construction. All variants apply to each complete generated frame before the unique identity pixel is added, including missing-home frames:

- `blur`: OpenCV Gaussian blur, 5×5 kernel, sigma 1.
- `dim`: multiply encoded RGB by 0.8 and round to bytes.
- `shift`: translate three pixels right and two down, with the usual black source border.

The selected variant and exact recipes are retained in reports and each sequence. These are controlled transformations of existing drawings, not calibrated camera exposure, a measured optical blur model, or independent footage. Clean full-observation tests retain all ten digits in all three colours under all three variants, without mutating cached source images.

A targeted blurred run covers directed pairs 15, 16, 51, 61, 69 and 96 at weight 0.5, separately for each colour: eighteen sequences / 270 frames total. All 54 clean home observations per colour are correct, with no missing or wrong clean raw values. White mixtures have no fresh confirmations. Orange and red each have twelve available mixed observations and eight fresh third-digit confirmations: one/five and five/one confirm nine; one/six and six/one confirm eight. Balanced six/nine remains rejected. These blur failures are explicitly unresolved; zero third digits on the original matrix must not be treated as universal mixed-exposure safety.

The repeatable blurred reports are `data/candidate-exposure-{white,orange,red}-local-blur.json`. An additional local exploratory scan of the ten historically failing pair/weight cases under blur, dimming and shifting also retained clean digits; its blurred red/orange failures motivated shipping these repeatable variants rather than hiding the limitation. No physical truth label was assigned to a blend.

## Existing recordings, transport and checks

All three complete comparisons were decoded again with matching saved profiles, unchanged labels and explicit layouts; OCR was skipped. Video hashes and calibration match the previous reports. Every active-reader row, candidate independent field state, legacy candidate comparison row and pre-existing primary/core diagnostic is exactly unchanged, apart from the added local diagnostic. Complete candidate raw counts remain 1,520 / 471 / 1,284; fresh independent clocks remain 1,499 / 379 / 1,197 for original/newer/recapture. The three per-field audits pass with their existing unresolved confirmations on unreadable transitions. No recorded physical-truth issue is claimed fixed.

All translation windows were rerun. Every pre-existing row field and independent state is unchanged after excluding `score_local`. The 342 reused reviewed anchors/offsets retain 197 correct / zero wrong / 145 unknown complete raw observations, with no wrong fresh field confirmation at those anchors. Neighbouring frames do not inherit labels. Reports use the suffix `local-contrast`, with corresponding audit and stress files.

The original batch readings were regenerated (1,638 observations / 52 uncertain). `python3 scripts/check.py` passes all 70 application tests, including generated-video and five available original-recording regressions. All 35 optional experiment tests pass. Five new tests cover the balanced mixtures in all colours, actual shadow hold/recovery age and independent fields, white zeros with red centre glow, a valid local digit never rescuing primary edge rejection, and clean blur/dim/shift variants. The existing all-ten-clean-digit test also checks the local view.

Full recapture delivery through the single-decoder packed shadow adapter matches all 1,637 active-reader rows and candidate states, with candidate output disabled. Its ignored summary is `data/recognition-mock-local-contrast-shadow.json`. No UI changed or browser visual check was performed. No camera or existing user server was opened, stopped or changed; HTTP tests used their own temporary loopback server. No new dependencies, private pixels, recordings, calibration, labels or numeric reports are committed.

The additional morphology/inspection adds processing work. Concurrent offline comparison medians/p95 were 19.98/40.16 ms, 23.08/105.85 ms and 20.80/63.65 ms, including candidate recognition/state/hash work but excluding decoding/capture/OBS delivery. Contention and different stages prevent treating these figures as a throughput benchmark. Live throughput/delay, independently readable reference footage, tenths recapture, output/correction policy and blurred/mixed-exposure recognition remain necessary before output promotion.

## Reproduction

Use the [existing optional environment](../experiments/README.md), keep earlier reports, and choose new output paths. Repeat the existing recording comparison/audit/translation commands with `local-contrast` output suffixes and unchanged profiles/labels/layouts. Generated examples:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --all-pairs --color white --output data/candidate-exposure-white-local-contrast-final.json
/tmp/livestream-recognition-venv/bin/python experiments/exposure_stress.py --pairs 15 16 51 61 69 96 --weights .5 --color orange --variant blur --output data/candidate-exposure-orange-local-blur.json
```

Repeat the matrix and blurred check for each LED colour with corresponding new destinations. The runner refuses existing paths. A successful experiment exit means measurement completed, not that mixed exposure is safe.
