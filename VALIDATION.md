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
