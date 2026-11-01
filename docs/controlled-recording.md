# Controlled recording and recapture

Generate a repeatable source video before coordinating a camera test:

```sh
python3 scripts/generate_controlled_recording.py
```

This creates `data/controlled-recordings/v1/`: a 120-second, 1920×1080, 60 fps H.264 MP4 with no audio, using Python's standard library and FFmpeg/ffprobe. No camera or server is started. Open `recording.mp4` in a local video player. The source includes panel corner markers, orange seven-segment digits, and a reference strip below the panel with source frame number, source time, section and visible values. The strip is outside recognition regions. The drawing is independent of the recognizer's segment-pattern table.

## Bundle and scenario

| Source time | Test |
| --- | --- |
| 0–10 s | Alignment: 18:48, scores 8–8 |
| 10–30 s | Home 0 through 9, two seconds each; away 0 |
| 30–50 s | Away 0 through 9, two seconds each; home 0 |
| 50–60 s | Clock 19:59 through 19:50; scores 2–3 |
| 60–70 s | Paused 19:50; scores 2–3 |
| 70–90 s | Seconds/tenths 29.9 through 10.0; scores 2–3 |
| 90–105 s | Three-second corrections: 6–9, 9–6, 0–0, 1–0, 1–1; clock resets too |
| 105–110 s | Clock completely blank; scores 3–4 |
| 110–115 s | Home completely covered; clock 05:10, away 4 |
| 115–120 s | Recovery: 05:05 through 05:01; scores 3–4 |

`timeline.json` records every source frame, intended values, deliberately visible values, visibility reasons, explicit layout, source/video/calibration hashes, encoding command and decoded frame-count verification. `visible` is null for a deliberately unavailable field; `intended` preserves what would otherwise have appeared. Neither means a captured blank should be labelled zero. `clock_slots` describes intended slots, including the final blank in the seconds/tenths layout; canonical tenths values use `00:SS.t`.

`reference-calibration.json` copies the tracked reference geometry. `source-clock-layout-plan.json` selects `mmss` at source time 0, `seconds_tenths` at 70, and `mmss` at 90. These files apply to the generated source directly. They are not activated and do not replace an existing local profile. A recapture requires its own calibration and layout schedule in captured-video time.

The bundle also includes `README.txt` and `ffmpeg.log`. All generated bundle files are ignored by Git. Existing directories are refused; use `--output data/controlled-recordings/another-take` for a new bundle. An interrupted or failed run leaves `INCOMPLETE.txt`; do not use that bundle. `--frames 12` creates an explicitly marked prefix for encoder smoke checks, not the complete capture scenario. A full run verifies all 7,200 decoded frames before removing the marker.

## Coordinated capture

1. Agree which application owns the capture device before opening it. Use the existing OBS capture path if that is the agreed owner; do not add a second camera consumer or change running servers during this preparation.
2. Play the MP4 fullscreen on the display being filmed, at normal speed without looping. Hide controls and move the cursor clear. Keep all four central-panel corners and the entire reference strip visible in the recording. The title above the panel is optional framing context.
3. Keep camera position and capture settings fixed. Record the display refresh rate, video resolution/frame rate, camera exposure/shutter and OBS settings where available. Preserve a separate calibration for this framing; do not overwrite `data/calibration.local.json` or the tracked reference merely to try the test.
4. Start capture a few seconds before playback. Play the complete video once without pausing or seeking, and stop capture a few seconds after it ends. Preserve the original captured file locally, including its lead-in and tail.
5. Check that the reference counter and scoreboard strokes are readable, and that the blank/covered intervals and final recovery were captured. Retain failed captures too; use new names for subsequent takes.

This display-and-camera test exercises that capture chain. It does not reproduce a physical scoreboard's LED refresh, brightness or venue conditions. A later physical-scoreboard recording is still required.

## Review and offline evaluation

The source frame counter helps align captured samples to the source timeline, but does not establish the truth of captured scoreboard pixels. Rolling shutter, display refresh, motion blur and compression can mix states even when the counter is readable. Review the clock, home and away fields independently. Mark mixed, covered, blank or unreadable fields with explicit reasons. Do not copy intended values into those labels or interpolate an unreadable clock.

Use the existing [offline comparison and per-field audit](../experiments/README.md). Freeze a separate recapture calibration, choose explicit layouts from reviewed captured frames, and save the layout plan in captured-video time. Source time 70 seconds is not automatically capture time 70 seconds. No automatic counter alignment or recapture annotation importer is implemented here.

A baseline comparison can use an empty JSON label list (`[]`) to produce availability and confirmation timelines without claiming correctness. Then review exact sequentially decoded sample indices at the report's sample rate, as described in the audit instructions. Bind the review to the captured video's hash and rate, not the generated MP4's hash. Use fresh output names so previous evidence survives. The generated calibration and source plan can be used for a direct-source smoke comparison only.

Report readable-field correctness, fresh confirmations on unreadable fields, held-value age and stale status, and recovery after the two deliberate interruptions. Measure recognition delay from the first clearly readable changed state in captured samples to confirmation. This does not measure end-to-end live hardware/OBS latency. Coverage and confidence margins remain diagnostics, not accuracy.

The clean-source optional test checks selected rendered anchors, including every score digit and unavailable intervals. It does not validate camera recapture or every encoded frame's recognition. Candidate output remains diagnostic-only and disabled for OBS; this generator changes no recognition, state or server behavior. Real recapture review and remaining blurred mixed-stroke failures must precede any output promotion.
