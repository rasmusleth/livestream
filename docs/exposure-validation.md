# Per-field exposure and sequence audit: 2026-11-01

The candidate still confirms some fields on frames whose physical truth cannot be assigned confidently by visual inspection. This audit makes those cases explicit rather than dropping them from the evidence. It changes no recognition rules, camera settings, server, UI or OBS output. The established reader remains the only output source.

## Method

The new dependency-free `experiments/audit_readings.py` audits saved `independent_rows` against per-field source reviews. Each reviewed field has either a readable value or an explicit unreadable reason. Omitted fields remain unreviewed. Unreadable frames contribute neither correct nor wrong counts; fresh confirmations on them are reported separately. Raw observations, fresh confirmations, held values differing from the visible reading, and unknown output remain separate.

The review must match the saved report's video SHA-256 and sample rate. The audit requires the full source sample grid from zero and checks output invariants throughout it: fresh output equals an actual observation with zero age; held values cannot change and their age advances from the last confirmation; unknown output has no value or age. This checks saved-state consistency, not whether observations match physical reality. Outputs retain both input file hashes and the reviewed states for traceability.

Both local video hashes were checked against the existing post-tenths-fix reports. Exact FFmpeg `fps=10` source samples were decoded sequentially from zero, then clock and score crops arranged in resized contact sheets for manual inspection. The original recording was newly reviewed at 70.0–70.9 and 118.6–119.5 s. The newer recording's previously reviewed 43.0–43.9 and 47.0–47.9 s sequences were inspected again, retaining the seven unreadable-clock decisions. Values were assigned from visible strokes, without deriving truth from predicted countdown timing or recognition output. There is no independent scoreboard event log or hardware ground truth.

The audit reuses the saved full decoded candidate timelines; extraction was not rerun or modified. Both complete timelines pass the consistency checks. Footage, calibration, annotations, contact sheets and derived numeric reports remain local and outside Git.

## Reviewed results

Each recording contributes 20 frames, with each field reviewed separately. Held means an available older confirmed value, not a fresh confirmation.

| Recording / field | Readable | Fresh correct / wrong | Readable held / unknown | Unreadable | Fresh on unreadable |
| --- | --- | --- | --- | --- | --- |
| Original home | 20 | 20 / 0 | 0 / 0 | 0 | 0 |
| Original away | 19 | 18 / 0 | 1 / 0 | 1 | 1 |
| Original clock | 19 | 19 / 0 | 0 / 0 | 1 | 1 |
| Newer home | 20 | 20 / 0 | 0 / 0 | 0 | 0 |
| Newer away | 20 | 20 / 0 | 0 / 0 | 0 | 0 |
| Newer clock | 13 | 11 / 0 | 2 / 0 | 7 | 2 |

No fresh confirmation disagrees with a readable label in these selected sequences. Four fresh field confirmations occur where no confident physical-truth label was assigned. Those four are unresolved review risks, not proven errors or successes. The remaining 1,618 original and 494 newer source samples are unreviewed by this particular audit, for each field. These selected, reused recordings do not establish general accuracy.

### Original countdown, stopped clock and score change

At 70.0–70.5 s the clock visibly reads 19:16; at 70.7–70.9 it reads 19:15. The intermediate 70.6 sample has faint/changing 6/5 strokes and is conservatively unreadable. The candidate observes and freshly confirms 19:16 on that frame; this audit does not assign a true clock to it. Both scores visibly stay zero throughout the sequence.

Across 118.6–119.5 s the clock visibly stays stopped at 18:41 and is freshly correct on all ten samples. The away score is clearly zero through 118.8, has overlapping old/new strokes at 118.9, and is clearly one from 119.0 onward. Home stays zero. The candidate freshly confirms zero on the ambiguous away-score frame. At 119.0 it observes one while holding zero with age 0.1 s; at 119.1 it confirms one. That is one sample of confirmation delay relative to the first clearly readable one in this review, not an end-to-end live latency measurement or an exact physical event time.

### Newer tenths and mixed exposure

All ten 43.0–43.9 s clocks are freshly correct, showing 48.6 through 47.7 seconds. At 47.1, 47.4 and 47.8 s, the clearly readable values are 44.6, 44.2 and 43.8. The candidate freshly confirms the first and holds 44.6 at the latter two. One held frame has an unavailable raw clock, the other a correct raw observation. Those two older held values differ from the current readable clock; they are not wrong fresh confirmations.

The other seven clock fields in the 47.0–47.9 sequence are explicitly unreadable due to mixed/faint extra strokes. Six have raw observations, two are freshly confirmed (47.0 and 47.9), and five hold prior output. In particular, a repeated/coherent valid-looking transition can pass confirmation despite ambiguous source pixels. Neither temporal confirmation nor availability establishes that it is physically correct. Both scores visibly stay one and are freshly correct on all twenty reviewed newer frames.

## Validation and next boundary

All 66 application tests pass, including eight new dependency-free audit tests and five existing private-recording regressions. The separate optional experiment suite passes 17 tests. The standard check also passes Python compilation, JavaScript syntax, calibration bounds and generated-video pipeline checks. No runtime or UI behavior changed, so no UI or hardware check was performed. No camera or existing user server was touched.

The next evidence needed is a coordinated capture with independently readable clock/score reference, including tenths, pauses, score changes and mixed exposure. Use it to distinguish physical errors from camera transition artifacts and measure candidate behavior before considering any output promotion. Live throughput and end-to-end delay also remain unmeasured. This audit provides the accounting for that review; it does not resolve exposure recognition or enable candidate output.

The later [generated exposure runner](candidate-exposure-stress.md) supplies controlled score mixtures without assigning truth to these ambiguous recording frames. It reproduces fresh third-digit confirmations and checks clean endpoints, held age and recovery. It changes no recognition rule and does not resolve the physical-truth or live-capture limits above.
