# Candidate score LED cores: 2026-11-01

The region candidate now reads the reviewed hollow zeros in the monitor recapture as zero, removing the demonstrated zero-to-eight confirmations. This changes the optional diagnostic candidate only. The established probe reader still has its four known wrong confirmations on that recording; it remains the sole source of OBS output. No candidate output is promoted, and this setup is not ready for reliable live use.

## Focused extraction rule

The [recapture investigation](mock-capture-validation.md) found bright white LED centres surrounded by red glow. The former score mask discarded the white centres through its red-minus-blue requirement while retaining red foreground inside visibly hollow zeros. Repeated observations then confirmed the resulting eights.

Only home/away masks change. For each padded score patch, floating-point RGB values define:

```text
neutral = min(green, blue)
light = max(red - max(green, blue), (red + neutral) / 2)
```

The first term retains strong red strokes; the second includes neutral light from white cores. Contrast is measured between the median and 95th percentile of this signal. If that gap is below 20, the 99th percentile is tried because a narrow one can occupy less than 5% of its padded region. If the gap is still below 20, the score has no usable foreground and remains unavailable; it is never replaced with zero. This is an extraction rejection, not proof of a physically blank score.

If at least 1% of patch pixels have all three channels at least 200, the score uses the core-aware mask. Its signal threshold is the greater of 75 and `median + 0.6 × contrast`. Pixels must also have red above 150 and red at least 0.95 × green. Otherwise, scores retain the former red-mask rule, subject to the low-contrast rejection. This restricts the new mask to patches with observed bright white pixels; it does not select a score based on its expected value. Applying the core mask indiscriminately had rejected many orange/red ones in development, so it is not used as a universal replacement.

The existing cleanup, minimum component size, two-clear-pixel crop guard, shape/aspect/segment ambiguity checks and confirmation rules remain unchanged. Clock masks, shared clock brightness reference, explicit layouts and per-field age/status are unchanged. The new constants are heuristics for these recordings and controlled drawings, not calibrated probabilities or support for arbitrary lighting. Different colours, mixed exposure and unreviewed frames can still fail.

## Generated regression tests

Four new optional experiment tests cover:

- Independent full RGB slanted LED drawings with white zero cores and red centre glow. The former implementation reads both scores as eight; the corrected implementation reads and independently confirms zero.
- All ten digits, including a real eight, using white, red/orange and pure-red strokes.
- Low-contrast score texture through the actual `ShadowReader`: unavailable observations hold the last value with increasing age, then recover to a newly observed eight.
- Cropped white zeros remaining unavailable through the existing edge guard.

These inputs are generated during tests; no private pixels are committed. All 21 optional experiment tests pass. The standard application suite passes all 66 tests, including generated-video and five original-recording regressions after regeneration. The application remains dependency-free by default; the candidate uses its existing optional NumPy/OpenCV packages.

## Three-recording comparison

All three recordings were decoded again with frozen matching profiles and the existing labels. OCR was skipped. Pre-fix reports and development runs were preserved; final reports are named `data/recognition-{original,live,mock}-score-cores-final.json`. Coverage figures are availability, not accuracy:

| Recording | Complete candidate raw before → after | Independent home fresh before → after | Independent away fresh before → after |
| --- | --- | --- | --- |
| Original, 1,638 samples | 1,551 → 1,520 | 1,637 → 1,637 | 1,636 → 1,574 |
| Newer, 514 samples | 471 → 471 | 463 → 463 | 513 → 513 |
| Monitor recapture, 1,637 samples | 1,253 → 1,284 | 1,559 → 1,636 | 1,564 → 1,580 |

The original loses 31 complete readings. Thirty-three formerly available away observations are now rejected by the existing narrow-glyph check, reducing fresh away confirmations by 62. The guard was not relaxed to recover them. Original existing complete reviewed results stay nine correct / zero wrong / two unknown. All newer candidate field states and digit diagnostics exactly match the prior report, including its 25 correct / zero wrong / three unknown complete reviewed observations.

Across every source sample in all three recordings, established-reader rows, candidate clock field states and clock digit diagnostics exactly match their pre-fix reports. The unchanged independent clock fresh totals remain 1,499, 379 and 1,197. The original batch regeneration remains 1,638 observations / 52 uncertain raw readings.

### Monitor recapture: same fifty per-field reviews

No labels were adjusted to the new output. Two ambiguous transition fields remain unreadable rather than guessed. The [per-field audit](exposure-validation.md) passes full-timeline observation/value/status/age consistency checks and reports:

| Candidate field | Readable | Fresh correct / wrong before → after | Readable held / unknown after | Unreadable / fresh on unreadable after |
| --- | --- | --- | --- | --- |
| Home | 50 | 0 / 48 → 49 / 0 | 0 / 1 | 0 / 0 |
| Away | 49 | 14 / 32 → 42 / 0 | 6 / 1 | 1 / 1 |
| Clock | 49 | 27 / 0 → 27 / 0 | 21 / 1 | 1 / 1 |

The clock is unchanged. The candidate now freshly confirms zero on the unreadable 118.8 away transition; that remains unresolved, not a correct or wrong label. At the first clearly readable away one (118.9), the raw observation is unavailable and zero is held with age 0.1 s. It observes one at 119.0 and confirms one at 119.1, two samples after the first clearly readable value. Four of the six readable away holds still equal the visible score; two differ. No physical event time or live latency is inferred from this review.

At the 48 completely readable timestamps, candidate complete raw results change from zero correct / 30 wrong / 18 unknown to 30 correct / zero wrong / 18 unknown. Wrong fresh complete confirmations fall from 23 to zero. These are reused development/regression samples, not a whole-clip accuracy estimate; 1,587 source samples per field remain unreviewed by this audit.

The same original/newer per-field reviews also pass with no wrong fresh readable labels. Their ambiguous clock/score confirmations remain explicit; this score-only fix does not resolve mixed-exposure physical truth.

### Translation checks and shadow delivery

The same nine offsets and surrounding confirmation windows were rerun with labelled truth only at each reviewed anchor:

| Recording | Anchor/offset cases | Correct / wrong / unknown complete raw |
| --- | --- | --- |
| Original | 36 | 20 / 0 / 16 |
| Newer | 153 | 87 / 0 / 66 |
| Monitor recapture | 153 | 90 / 0 / 63 |

No fresh independent field confirmation is wrong at these anchors. Original correct complete cases fall from 22 to 20; newer results are unchanged. The known newer 32.5 s / ten-pixel-upward away-score case still observes one throughout its eleven-sample window. The seventeen monitor anchors are reused ten-second review points, not independent held-out footage. Their local label copy uses the existing CLI's `heldout` selector solely to run these checks; neighbouring frames never inherit truth.

A full monitor-recapture run through the actual packed, single-decoder shadow adapter matches all 1,637 offline candidate field states and every established-reader row. Its ignored summary is `data/recognition-mock-score-cores-shadow.json`. This verifies transport/state equivalence; it does not establish live camera throughput or latency. No UI code changed or browser check was performed, and no camera or existing user server was touched.

## Reproduction and remaining work

See [experiment setup](../experiments/README.md). Matching local profiles, labels, videos and numeric reports remain ignored and are not shipped in Git. Run the three final comparisons with the commands there, then use the same per-field reviews:

```sh
python3 experiments/audit_readings.py data/recognition-mock-score-cores-final.json data/recognition-mock-field-review.json --output data/recognition-mock-score-cores-audit.json
python3 experiments/audit_readings.py data/recognition-original-score-cores-final.json data/recognition-original-field-review.json --output data/recognition-original-score-cores-audit.json
python3 experiments/audit_readings.py data/recognition-live-score-cores-final.json data/recognition-live-field-review.json --output data/recognition-live-score-cores-audit.json
```

Before any output promotion, address the established reader's known recapture failures and choose an explicit output/correction policy. Candidate availability losses, unresolved transition truth, tenths recapture, broader framing/exposure coverage and coordinated live throughput/delay testing remain open. No further recording is needed to investigate the demonstrated probe-reader failures. Neither a green test suite nor this candidate improvement makes the current OBS path safe on the recapture.
