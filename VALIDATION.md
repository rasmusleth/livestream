# First recording validation

Input: `scoreboard-2-min-clip.mp4`, 1920×1080, 25 fps, 163.8256 seconds.

The reader analyzes 1,638 samples at 10 Hz. Segment locations were calibrated using frames at 0, 10, 60, 120, and 160 seconds. This is a prototype calibrated to this recording, not evidence of general accuracy across other venues or games.

## Results

- 1,586 samples (96.8%) produce a complete raw reading. This is recognition coverage, not an accuracy percentage.
- 52 samples are rejected as uncertain.
- 1,456 samples are confirmed by repeated evidence; 181 hold a previous value; the first sample has no confirmed value yet.
- The longest interval since a confirmation is 0.4 seconds.
- Confirmed clock values count down in single-second steps or remain paused, with no upward jumps or skipped seconds in this clip.
- The output retains the score change from 0–0 to 0–1 and the stopped clock after the goal.
- Seven automated checks pass, covering missing/ambiguous digits, separately reviewed sample frames, clock pauses, confirmation behavior, score persistence, and clock transition glitches.

## Separately reviewed sample frames

These timestamps were not used to position the segment probes. Visible readings were reviewed against extracted source frames and checked against the reader output.

| Video position (seconds) | Clock | Home | Away |
| ------------------------ | ----- | ---- | ---- |
| 30                       | 19:36 | 0    | 0    |
| 50                       | 19:17 | 0    | 0    |
| 70                       | 19:16 | 0    | 0    |
| 90                       | 19:08 | 0    | 0    |
| 110                      | 18:48 | 0    | 0    |
| 130                      | 18:41 | 0    | 1    |
| 150                      | 18:33 | 0    | 1    |

## Limits and next steps

Not every frame has a human annotation. Clock consistency checks can detect many glitches but cannot establish complete correctness by themselves. Raw readings can briefly resemble other digits while LED strokes change; repeated evidence prevents the observed single-sample glitches from reaching the confirmed output.

Sampling adds up to approximately 0.1 seconds before a changed display is observed. Requiring a second matching sample adds another 0.1 seconds, and uncertain frames can extend that delay. These are properties of this offline pipeline; live end-to-end latency has not been measured.

Only scores 0 and 1 appear in the supplied score regions. Higher scores, two-digit scores, obscured inputs, camera movement, other lighting conditions, and new clock formats need additional footage. Period recognition is outside this version.

The verification interface has been checked in the local browser, including video loading and seeking to 120 seconds, where both the source and digital output show 0–1 and 18:41.

## Recorded overlay in OBS

On 2026-10-25, the user confirmed that they followed `docs/obs-overlay.md` on their Mac and that the OBS setup worked as planned. This is user-reported validation of the recorded-playback overlay in OBS, in addition to the local browser checks. It does not establish live HDMI capture compatibility, live latency, or exhaustive failure/recovery coverage.

The live scoreboard camera reaches OBS through an HDMI capture device. Its model and simultaneous access by OBS and the reader remain to be established.

## Continuous processing and capture discovery: 2026-10-31

The recording reader now supports flushed JSON-line observations and real-time-paced replay. The generated-video test checks that output arrives before the recording completes and matches the batch observations. Regenerating the supplied recording still yields 1,638 samples with 52 uncertain raw readings; recording regression checks remain required.

A three-second video-only FFmpeg capture from `usb video` completed at 1920×1080 using UYVY422. Requested frame-rate configuration fell back to device defaults, so 25 fps operation is unverified. The user reported a green/distorted OBS picture after the capture and confirmed recovery after quitting OBS, reconnecting USB, and reopening OBS. Simultaneous use is not validated; the preferred live design gives the reader sole access to the scoreboard capture input. No video or audio recording was retained. See `docs/live-input.md`.

## Server-owned input: 2026-10-31

The continuous server mode now drives the overlay without a publishing playback tab. All 29 local checks pass, including generated input through confirmed state, frame timeout/cleanup, source-dimension guards, stale data, rejection of conflicting player updates, and the five real-recording regression checks. The real-recording reader remains unchanged and its regressions are rerun for this milestone.

With the user confirming OBS was closed, a short run of the actual camera server received frames from `usb video` and exposed connected state over HTTP. The server stopped automatically via Ctrl+C with exit code 0. The driver reported fallback to a default configuration; requested 25 fps operation remains unverified. This test did not validate live scoreboard accuracy or simultaneous OBS access, and retained no camera footage or audio. Browser checks confirmed continuous recorded values and held-data output at EOF.

## Input alignment preview: 2026-10-31

Continuous modes now expose a half-resolution preview with the active calibration's six digit boxes and 42 segment probes. The preview and recognition share one decoded input; a separate crop/scale branch preserves the existing recognition pixels. An offline comparison of all 1,638 rows from the supplied recording against the batch output matched exactly, including raw values, confirmed values, timestamps, status, ages, confidence, and segment diagnostics. Regenerating the batch readings still produced 52 uncertain raw observations.

All 32 local tests pass, including generated-video equivalence with preview enabled, immutable/latest-only preview storage, preview age after EOF, resolution guards, read-only HTTP routes, and the five recording regressions. Browser checks cover preview loading, guide toggles, freezing/resuming while recognition continues, uncertain-reading status, and independent overlay output. Continuous mode does not support seeking; the existing replay mode retains it.

No capture device was opened for this preview milestone. Preview performance and alignment against the actual live camera, capture-rate selection, single-owner OBS integration, and end-to-end delay still need hardware validation. The preview is limited to two updates per second and is not synchronized with every recognized frame. There is no calibration editor or frame export.

## Camera calibration editor: 2026-10-31

The user reports that the live camera preview works through the capture device, but no complete scoreboard reading has been confirmed with the reference calibration. This establishes preview delivery for that setup, not recognition accuracy. Fixed probe geometry is a likely cause; exposure, LED flicker, and other conditions have not been ruled out.

The local editor adds per-digit four-corner placement, interpolated segment probes, precise probe adjustment, single-frame diagnostics, and a saved profile that is activated by restarting the server. Automated tests cover shifted/scaled/sheared synthetic digit geometry, rejection of incomplete/out-of-bounds profiles, derived crops, confirmation requiring fresh repeated evidence, diagnostic-only checks, and local saving without changing active output. All 36 local tests pass, including the five supplied-recording regressions. Regenerating the original clip still yields 1,638 observations and 52 uncertain raw readings.

Browser checks with recorded input covered editor initialization, four-corner placement, numeric probe adjustment, discard, single-frame per-digit diagnostics, local save feedback, and unchanged running output during edits. A server started with the browser-saved profile received and confirmed recorded observations. No new hardware capture was opened. Actual live calibration and recognition remain to be tested by the operator. Standard probe interpolation and preview-frame checks are alignment aids; they are not an accuracy claim or automatic camera tracking.

## Whole-panel alignment: 2026-10-31

The calibration editor now maps the known central clock-and-scores layout from four panel corners. The reference anchors were selected by inspecting the supplied recording; numbered side panels are excluded. Probe centers and enclosing digit regions are projected by a homography. This does not detect new layouts, rectify the input image, change recognition thresholds, scale the sampling window, or track camera movement.

All 39 local tests pass, including identity preservation, comparison with an independent perspective warp, shifted/scaled/sheared synthetic recognition via the whole-panel path, invalid and legacy outlines, outline persistence, and unchanged active output. The reference recording still produces 1,638 observations with 52 uncertain raw readings. Reference probe coordinates and recognition thresholds were not changed.

Browser checks used recorded input only. Four panel clicks positioned all six digit regions and probes. A subsequent diagnostic check produced the complete raw reading 18:41 and 0–1, matching the running recording output; another frame was explicitly incomplete. This is a diagnostic example, not an accuracy measurement. A layout shift between corner prompts was found and fixed so the image remains stable during marking. Real camera alignment and recognition remain unvalidated. No capture device was opened and no footage was uploaded.

## Offline reader comparison

[The comparison report](docs/recognition-comparison.md) records full-clip coverage, visually reviewed timestamps, deliberate framing errors, and limited processing/confirmation-delay measurements for the current reader, a rectified whole-region prototype, and local Tesseract OCR. On the new MKV, complete raw coverage is 1/514, 372/514, and 116/514 respectively. These are coverage figures, not accuracy percentages. The whole-region prototype has no wrong fresh confirmations at the sparse reviewed timestamps, but misreads an away score under one deliberate 10-pixel shift; it remains offline. The original recording still yields the existing 1,638 observations and 52 uncertain raw readings. Footage, local profiles, image crops, numeric outputs, and annotations remain local. See the report for development/holdout distinctions and clock-format limitations.

### Region glyph safety follow-up

The [offline safety stage](docs/recognition-comparison.md#glyph-safety-follow-up) adds crop guards, conservative ambiguous-shape rejection and per-digit reasons. The known upward-shift away-score error now reads `1` throughout the 11-sample 32.0–33.0 s window. Reused stress anchors produce zero wrong complete raw readings across 72 shifted/unshifted cases, with 36 unavailable. This is limited regression evidence; neighbouring samples do not inherit anchor labels.

Complete raw candidate coverage falls to 1,559/1,638 on the original and 224/514 on the new clip. Existing reviewed timestamps yield 10 correct / 0 wrong / 1 unknown and 6 / 0 / 9 respectively. The original runtime regeneration remains 1,638 samples / 52 uncertain. All 39 application tests and 12 separate optional experiment tests pass. Both full Regions comparisons and translation-window stress runs were repeated locally; OCR was skipped. Clock-format safeguards, independent field/tenths confirmation and monitor shadow integration remain pending. No UI or hardware check was performed for this offline-only change, and runtime/OBS output remains unchanged.

### Independent candidate confirmation

The next [offline candidate stage](docs/candidate-confirmation.md) parses explicit selected layouts and confirms each score and clock independently. A blank cannot automatically change formats. Three coherent source-timed clock observations can confirm the latest observed tenths value; snapshots never generate ticks. Gaps, partial digits, duplicate source frames and timestamps, corrections/resets, pauses and recovery have controlled test coverage.

All 53 application tests pass (14 new standard-library state tests), including five regenerated original-recording regressions, plus 13 separate experiment tests. Both full comparisons and translation-window stress runs were repeated locally with OCR skipped. On the original, home/away/clock fresh counts are 1,637/1,636/1,502 of 1,638 samples; on the new clip they are 463/513/202 of 514. None of the fresh field confirmations at existing reviewed timestamps was wrong; sparse reused anchors do not establish general accuracy. The new clip uses a manually selected offline layout schedule described in the candidate document.

Real-footage tenths confirmation remains undemonstrated: all 89 samples from the explicitly selected 42.5 s interval have an unavailable clock under the strict glyph checks. The state rule works on synthetic evidence, while independent scores can remain fresh in the real recording. The original runtime remains 1,638 samples / 52 uncertain, and no candidate state reaches OBS. No UI/hardware check was performed; opt-in monitor integration and its boundary demonstration remain pending.

## Monitor shadow integration: 2026-11-01

The merged baseline passed 53 application tests before this change. The opt-in [shadow monitor](docs/shadow-reader.md) now shares one decoder and the hardened region implementation with offline experiments. Its read-only diagnostics cannot alter `/api/state` or promote candidate output. Default recognition and dependencies remain unchanged; optional shadow packages are explicitly documented.

All 58 application tests and 13 separate optional experiment tests pass. The original recording was regenerated with 1,638 samples and 52 uncertain raw readings. Full packed-input comparisons match all 1,638 original and 514 newer established-reader rows exactly; candidate field states also match their respective offline independent timelines. Generated-video tests cover complete full-source pixels, one decoder and unchanged original output; additional tests cover resolution guards without hardware, candidate failure isolation, age after EOF and the HTTP output boundary.

Recorded-input browser checks covered enabled/disabled monitors, independent score freshness and uncertain/stale clock display, preview freeze while recognition continued, held age at EOF, and connection loss. Candidate scores on the new clip did not appear in the separate empty overlay. Replay loaded, played and sought to 120 s with `0–1`, `18:41`. All temporary demo servers were stopped. No camera or existing user server was touched. Private footage, profiles, screenshots and numeric equivalence reports remain local.

These are integration/equivalence checks, not new accuracy evidence. Real tenths recognition remains unavailable under the strict glyph checks. Shadow mode adds full-frame bandwidth and synchronous work; camera throughput, end-to-end delay, wider framing/lighting conditions and operator hardware validation remain unmeasured. The repository guidance now uses one completed, ready-for-review PR against `main`, without stacking dependent work.

## Recorded tenths glyph windows: 2026-11-01

The [focused region fix](docs/tenths-recognition.md) expands selected clock windows to include wider left strokes and shares a clock brightness reference so brown blank-window texture is not promoted into foreground. The two-pixel edge guard, ambiguity checks, explicit formats and confirmation rules are unchanged. Score extraction, the established reader and OBS output are unchanged.

Both full comparisons and translation stress windows were rerun locally with OCR skipped. Complete candidate raw coverage changes from 1,559 to 1,551/1,638 on the original and from 224 to 471/514 on the newer clip. Independent clock fresh counts are 1,499 and 379. In the selected 89-sample tenths interval, 77 clock observations are available and 51 freshly confirmed, up from zero. These are availability counts, not accuracy estimates. The original's eight fewer complete readings and three fewer fresh clocks remain an explicit limitation.

Two additional exact-sample sequences were visually inspected after freezing the policy. Thirteen clear samples were labelled, with seven mixed/faint-transition clocks left unlabelled rather than inferred from countdown timing. New-label raw results are 12 correct / 0 wrong / 1 unknown; independent clock results are 11 freshly correct and two held. The combined newer-clip review has 28 labelled timestamps. The existing 72 stress anchors give 46 correct / 0 wrong / 26 unknown complete readings; the expanded newer-clip check has 153 anchor/offset cases with 87 / 0 / 66. No fresh field confirmation is wrong at the reviewed anchors. Reused footage and sparse temporal labels do not establish general accuracy or physical-clock truth during mixed exposure.

All 58 application tests pass, including five original-recording regressions after regeneration (1,638 observations, 52 uncertain). The optional experiment suite passes 17 tests, adding full RGB wide-digit/colon/blank-texture cases, persistent crop rejection, missing-digit rejection and observed tenths confirmation with held age during loss. Footage, local calibration, labels, image crops and numeric reports remain local and outside Git. No camera was opened. Live throughput, delay and broader exposure/framing validation remain pending.

A full newer-clip packed shadow check matches all 514 established-reader baseline rows and all updated candidate field states. Recorded-input browser checks showed observed/held tenths and EOF ages while the separate overlay remained empty. Both temporary demo servers were stopped; no existing server or camera was touched. No UI code changed.

## Explicit exposure and sequence audit: 2026-11-01

The [per-field review](docs/exposure-validation.md) retains unreadable fields separately from readable correctness and unreviewed samples. It audits 40 exact source frames across the existing two recordings using cached post-fix candidate timelines, with both video hashes verified. Newly reviewed original-clip sequences cover a seconds transition and the stopped clock/away-score change. The newer review explicitly includes the seven previously excluded mixed-exposure clocks.

No fresh output disagrees with a readable label in these sequences. Four fresh field confirmations occur on visually ambiguous fields: two newer tenths clocks, one original seconds transition and one original score transition. They are unresolved, not proven wrong or correct. Three older held values differ from current readable labels, with held status/age preserved. The score confirms one sample after the first clearly readable new value. Sparse reused footage does not establish physical truth during mixed exposure, general accuracy or live latency.

All 66 application tests pass, including eight new dependency-free audit tests and five existing private-recording regressions; the separate optional suite passes 17 tests. Both complete saved timelines pass consistency checks for observed fresh values and held ages. Recognition/extraction was not changed or rerun, and no UI or hardware check was performed. Local review data and footage remain outside Git. A coordinated capture with independently readable reference and measured throughput/delay remains necessary before considering candidate output promotion.

## Monitor recapture: 2026-11-01

The operator's [monitor recapture](docs/mock-capture-validation.md) reveals confirmed score errors in both readers. After a separate, geometrically refined local calibration, the 1,637-sample candidate timeline contains 1,253 complete raw observations and 1,197 independent fresh clocks. Availability is not correctness: at fifty visually reviewed exact samples, the candidate has 48 wrong fresh home scores and 32 wrong fresh away scores, repeatedly reading visible zeros as eight. Readable reviewed clocks have 27 correct fresh confirmations and none wrong, plus 21 holds; one unreadable clock transition is freshly confirmed and remains unresolved.

The established reader has only 21 complete observations and four fresh complete confirmations with this mapped calibration. All four confirmations were visually reviewed and have wrong scores (9–7 instead of 0–1); one also has the wrong clock. No exhaustive per-probe optimization was performed. Neither the established reader nor the candidate is validated for this image appearance. Pixel masks expose unwanted foreground inside hollow zeros and loss of white LED centers, providing concrete recognition work before another capture or live-output testing.

All 66 application tests pass, including the existing original-recording regressions; that does not negate the new failures. This stage changes documentation only. Recognition, UI and runtime behavior remain unchanged; no original readings were overwritten, no camera or user server was touched, and optional tests were not rerun. Footage, profiles, annotations, image crops and numeric reports remain local. This is camera/monitor/OBS recapture evidence, not direct physical-scoreboard accuracy or live throughput/latency validation. No further capture is needed to investigate the demonstrated errors.

## Candidate score-core fix: 2026-11-01

The [focused score extraction change](docs/score-core-recognition.md) retains bright white LED cores and rejects red glow inside hollow zeros. It applies to the optional candidate's score patches with observed white pixels; red-only patches retain the former mask subject to a low-contrast rejection. Clock extraction, crop/shape safeguards, explicit layouts, the established reader and OBS output are unchanged.

All three full comparisons, per-field audits and translation windows were rerun locally with OCR skipped. At the same fifty recapture reviews, wrong fresh candidate home/away scores fall from 48/32 to zero/zero, with 49 and 42 correct fresh confirmations. Two transition fields remain unreadable and both receive fresh confirmations, so they remain unresolved risks. Among 48 completely readable samples, complete raw results become 30 correct / zero wrong / 18 unknown. Source samples outside the reviews are not accuracy-labelled.

Complete candidate raw availability changes from 1,551 to 1,520 on the original, stays 471/514 on the newer clip, and rises from 1,253 to 1,284/1,637 on the recapture. The original loses 31 complete readings and 62 fresh away confirmations due to retained narrow-shape rejection. Newer field states/diagnostics are exactly unchanged. All established rows and candidate clock states/diagnostics are exactly unchanged across all three recordings; the established reader's four known wrong recapture confirmations remain unfixed.

All 66 application tests and 21 separate optional experiment tests pass. The original reader was regenerated (1,638 observations / 52 uncertain). The 342 reused translation anchor/offset cases produce 197 correct / zero wrong / 145 unknown complete raw readings and no wrong fresh field confirmation at the anchors. Full packed shadow delivery on the recapture matches all 1,637 established rows and candidate field states. Footage, profiles, labels, crops and reports remain local. No UI or camera check was performed and no existing user server was touched. Candidate output remains disabled; probe-reader failure handling, manual correction, broader recognition validation and live throughput/delay remain necessary.

## Active probe white-core rejection: 2026-11-01

The [probe investigation and guard](docs/probe-core-rejection.md) identify contradictory white LED cores: the colour test rejects a bright lower-left stroke while counting red centre glow, turning a visible zero into nine. A new conservative veto makes that digit unavailable; it never inserts strokes or guesses an alternative value. Raw rows add white-probe fractions and explicit rejection reasons. Confirmation and held-value age semantics are unchanged.

With the same saved calibration, full recapture complete raw availability falls from 21 to two isolated observations, and all four known wrong fresh confirmations become unknown with no values. No recapture output confirms anywhere. At the same 48 completely readable reviews, raw results change from zero correct / five wrong / 43 unknown to zero correct / zero wrong / 48 unknown. The remaining 153.6/153.8 raw outputs still report 8–7, so glow-induced errors and reliable recapture recognition remain unresolved. This is failure rejection, not an accuracy claim.

All three comparisons were decoded again. Every pre-existing original/newer active-reader row field is unchanged; original availability remains 1,586 raw / 1,456 fresh confirmations and newer availability remains one raw / zero confirmations. All candidate digit diagnostics and independent field states exactly match the prior reports, and the three per-field candidate audits pass with their existing unresolved transition truth. Candidate output remains disabled. Translation stress was not rerun for this unchanged candidate.

The original readings were regenerated (1,638 samples / 52 uncertain). All 70 application tests pass, including the extended generated-video pipeline and five original-recording regressions; all 21 optional experiment tests pass. Full recapture packed shadow delivery matches all 1,637 active rows and candidate field states with candidate output disabled. No UI visual check was performed because no UI code changed. No camera or existing user server was touched; HTTP tests used a temporary loopback server. Local footage, calibrations, labels, crops and reports remain ignored. Live throughput/delay, manual correction and broader exposure/framing validation remain open.

## Generated candidate exposure stress: 2026-11-01

The new [offline exposure runner](docs/candidate-exposure-stress.md) generates known clean score digits and persistent old/new RGB blends, followed by missing-home input and recovery. It uses the existing candidate unchanged, retaining every observation, confirmation, held age and rejection. Mixed images have no assigned physical score; confirmations outside both source digits have their own diagnostic count.

All 90 directed score changes were run at three weights in white, orange and red: 810 sequences / 12,150 samples total. Each colour has 2,430 correct clean home observations, zero wrong or unavailable clean observations, and 1,728 correct fresh clean confirmations. Yet 560 of its 810 mixed samples confirm, including twenty confirmations of a third digit absent from both sources. A one/five blend can confirm nine. All 810 missing-home samples per colour stay held without fresh observations. The identical counts reuse controlled geometry, not independent footage; these are fixture results, not camera accuracy.

All 70 application tests and 27 optional experiment tests pass, including six new runner tests. Every generated timeline passes observation/value/status/age consistency checks. Recognition, state, UI, transport and output policy are unchanged; batch extraction, recording comparisons, translation stress, packed shadow and browser checks were not rerun. No camera or existing user server was touched. Candidate output remains disabled. The controlled failure now provides a reproducible target for extraction/exposure work; it remains unfixed and does not establish the true score on ambiguous recorded frames.

## Candidate score-mask disagreement: 2026-11-01

The [two-mask score guard](docs/score-mask-disagreement.md) rejects a primary score when a stronger-light mask produces a different valid digit. It preserves both diagnostics, never substitutes the alternative, and leaves an inconclusive core mask as inconclusive. Clock extraction and independent confirmation rules are unchanged; rejected observations hold values with increasing age. All full candidate paths, including the actual shadow reader, now use the same observation API.

The unchanged generated matrix was rerun for all 810 sequences / 12,150 samples. Per colour, fresh mixed confirmations outside both source digits fall from twenty to four, and mixed raw availability falls from 678 to 420/810. All 2,430 clean raw observations stay correct, but clean fresh confirmations fall from 1,728 to 1,689 as some first clean samples wait for another observation after rejection. Balanced six/nine mixtures still confirm five. These are controlled fixture findings, not physical-camera accuracy.

All three complete recordings and translation windows were decoded again with matching saved profiles and unchanged labels/layouts. Every pre-existing active row, candidate field state and digit diagnostic remains exactly unchanged, apart from the added score diagnostics. All three per-field audits pass with their existing unresolved transition truth. Translation anchors retain 197 correct / zero wrong / 145 unknown complete raw readings and no wrong fresh field confirmation.

Original batch readings were regenerated (1,638 samples / 52 uncertain). All 70 application tests and 30 optional tests pass, including three new RGB/full-observation/shadow tests. Every generated timeline passes the age/status audit, and packed recapture shadow delivery matches all 1,637 active rows and candidate field states with candidate output disabled. No browser visual check was performed because no UI code changed. No camera or existing user server was touched. Reports, labels, footage and calibration remain local/ignored. This partial rejection rule does not resolve exposure ambiguity, manual correction/output policy or live throughput/delay validation.
