# Toward live input

## Known setup

The development Mac is also the streaming Mac. The camera sends HDMI into a generic device labelled “HD video capture,” connected to the Mac over USB-C. OBS calls its video input “USB video”; FFmpeg's AVFoundation device list reports `usb video`. No manufacturer or model has been identified.

## Hardware check: 2026-10-31

- After the user connected the hardware, FFmpeg discovered `usb video` through AVFoundation.
- A three-second video-only capture to the null output completed successfully at 1920×1080, with UYVY422 selected by FFmpeg. No footage was saved and no audio was captured.
- The requested 25 fps configuration reported a configuration failure and fell back to the device default. Approximately 36 frames arrived over three seconds. This does not establish stable 25 fps operation or a suitable production capture mode.
- The user reported a normal OBS picture before the test, then a green/distorted picture afterward. FFmpeg had exited and no capture process remained. The exact cause is unconfirmed; simultaneous use and format reconfiguration need to be treated as unresolved.
- The user restored the normal OBS picture by quitting OBS, reconnecting the USB device, and reopening OBS.

Do not treat this check as validation of simultaneous OBS/FFmpeg access. Further hardware capture tests should be coordinated with the operator and avoid a competing OBS source using the scoreboard device.

For the intended live path, prefer one owner of the scoreboard capture input: the reader captures the scoreboard, and OBS consumes the digital browser overlay. The separate match camera remains an OBS input. An experimental AVFoundation adapter now feeds the same confirmed-state overlay as continuous recorded input. Actual live scoreboard framing and recognition have not been validated.

## Continuous recognition from a recording

The reader can now emit observations as frames are decoded instead of waiting for a complete batch JSON file:

```sh
python3 reader.py scoreboard-2-min-clip.mp4 --stream --realtime
```

Each stdout line is one JSON observation with the same fields as a row in `data/readings.json`: timestamp, raw reading, confirmed values, status, age, confidence margin, and segment evidence. Output is flushed after each observation. `--realtime` paces the recording input at normal speed; without it, streaming runs as fast as decoding permits. It is a playback pacing option, not a live latency measurement.

Press Ctrl+C to stop. The reader closes and terminates its FFmpeg child when streaming stops early. The streaming path keeps recognition state without accumulating a full recording in memory. This CLI command does not write `data/readings.json` or publish to the overlay. The server-owned modes below connect continuous recognition directly to the overlay; default replay mode retains the batch-backed viewer.

The original batch command remains available:

```sh
python3 reader.py scoreboard-2-min-clip.mp4
```

Both modes share `FrameReader`, including the same recognition thresholds and two-observation confirmation. Before either recorded input mode starts, the source dimensions must match calibration.

## Server-owned inputs

### Recording to overlay

```sh
python3 server.py --mode recording
```

The server recognizes the recording at normal speed and drives `/overlay` directly. The monitor at `/` displays input status and current readings; it does not publish playback positions and can be closed without stopping recognition. No generated readings file is required for this mode. Use `--video /absolute/path/to/recording.mp4` for another calibrated recording.

At the end of the file, the final values are held and explicitly marked disconnected. Restart the server to replay from the beginning. Seeking and looping are not implemented in continuous mode; use default replay mode for the original verification controls.

### Camera to overlay: experimental

1. Quit OBS before starting a hardware test. Keep other applications from opening the scoreboard capture device.
2. Connect and power the camera and HDMI capture device.
3. Use the expected 1920×1080 input resolution. The reference calibration was made from the supplied recording; if framing differs, calibrate it in the monitor after starting the server. Matching resolution alone does not establish correct framing or recognition accuracy.
4. Start the reader with the exact named video input:

```sh
python3 server.py --mode camera --device 'usb video'
```

5. Open `http://127.0.0.1:8765` to inspect the preview and input diagnostics. Match the six digit boxes to the clock/scores and the yellow probes to the LED segments. Use the guide checkboxes for an unobstructed view. Freeze the preview for inspection; recognition and overlay updates continue. Resume to check current framing. If framing differs, use **Calibrate this camera setup → Align whole scoreboard · 4 corners** to mark the central clock-and-scores panel (excluding the numbered side panels). This maps all digits and probes together; use optional fine adjustments only where needed. See the README calibration walkthrough; save locally, then restart with `--calibration data/calibration.local.json`. Validate the activated readings against the scoreboard before relying on them. The camera graphic is labelled `LIVE`; the recording graphic is labelled `REPLAY`.
6. For OBS integration, use a scene collection with the match camera and Browser overlay but no raw scoreboard `USB video` capture source. Keep the previous scene collection as a backup. The reader must remain the sole owner of the scoreboard capture input.
7. Use `http://127.0.0.1:8765/overlay` as a 1920×1080 Browser source. Keep the server running; the monitor tab is optional.
8. Press Ctrl+C in the server terminal to stop recognition and release the device. If input fails or stalls, inspect diagnostics and restart deliberately after resolving the cause. There is no automatic device reconnection.

Use `--port 8767` if the default port is occupied, and change the monitor/overlay URLs accordingly. `--calibration` selects another calibration file. `--capture-fps` requests a capture rate (default 25); the driver may report a fallback, which is visible in diagnostics. A reliable production capture rate remains to be established.

The camera adapter uses AVFoundation with an explicit device name and UYVY422 input, with audio disabled. It rejects default/index-based selection and audio-device syntax. A dimension guard rejects unexpected source dimensions before applying the calibrated crop. It processes actual arriving frames, without generating duplicate camera observations to reach a target rate. Camera observation timestamps use monotonic elapsed time; recording timestamps use source sample time. Neither mode advances the game clock independently.

## Alignment preview

Continuous recording and camera modes show a half-resolution preview (960×540 for this calibration), updated up to twice per second. It comes from the same FFmpeg process as recognition and does not open the device again. The monitor overlays the active calibration's digit boxes and seven probe centers per digit. `GET /api/calibration` exposes only the active profile. Draft edits are checked and saved through separate POST endpoints without modifying the running reader.

The preview displays frame age. Freezing holds only the browser image while capture, recognition, and the OBS overlay continue. EOF, disconnection, or an HTTP failure leaves the last image visible with held/error status and increasing age. Preview and recognition update at different rates, so they are not a frame-exact comparison tool. Before the first frame, the preview remains empty.

Full input frames are resized for display while a separate branch preserves the original crop/scale recognition path. These are packed into one bounded raw frame from one decoder. Only the latest preview is retained in memory; `/api/preview` serves RGB pixels on loopback with caching disabled. No frames are saved or uploaded. Continuous modes require even integer reference dimensions and crop coordinates/sizes, with the crop contained in the reference image. Incompatible profiles fail before capture starts. The local editor can map all six digits and 42 probes from four corners of the central panel, using the known layout and a perspective transform. Optional per-digit corner marking and individual probe placement remain available. An on-screen schematic identifies the required physical panel corners. Legacy profiles without a panel outline need the tracked reference profile for the shortcut. Checks inspect the latest preview without publishing output; saving replaces the ignored local profile and requires restarting to activate it. It does not track a moving camera. See the README for the complete workflow.

## Freshness and shutdown

The server owns input and confirmed-state delivery. `/api/state` reports the latest observation, input status, confirmation age, and bounded FFmpeg diagnostics. Playback-position POSTs are rejected while continuous input owns the output, preventing an old replay tab from overwriting it.

Two seconds without a new frame marks delivery disconnected and holds the last values. Confirmation age includes elapsed wall time since the last frame, so stale confirmed values do not appear fresh. Ten seconds without a complete frame stops the decoder with an error. EOF and errors preserve confirmed values and expose held status. The overlay shows a held-data badge rather than substituting zeroes.

Stopping the server cooperatively stops the worker and terminates its FFmpeg child, with a kill fallback if termination stalls. Frames and diagnostic state are bounded in memory; camera video and audio are not written to disk.

## Validation of this milestone

Automated checks cover generated recording-to-state delivery without a browser publisher, frame assembly, decoder timeout cleanup, calibration dimension guards, lost frames, EOF/error state, and rejection of conflicting playback updates. Recording regression checks remain separate from camera validation.

On 2026-10-31, with the user confirming OBS was closed, a short camera-server test received frames from `usb video` through the calibrated-size guard and exposed connected state over HTTP. The server then stopped via Ctrl+C and exited cleanly. The driver again reported a configuration fallback. This validates frame delivery and server shutdown in that setup, not requested 25 fps operation, live scoreboard recognition, or concurrent OBS use.

Browser verification of continuous recorded input covered the monitor, independent overlay updates, a score change, and held data at EOF. An OBS test of server-owned input remains to be done; the earlier successful OBS check used the recorded-player output.

## Remaining work

1. Use the local calibration editor to align the actual live scoreboard and validate recognition after activating the saved profile.
2. Establish a suitable capture configuration without driver fallback.
3. Test OBS with the reader owning the scoreboard input and OBS using only its browser overlay.
4. Measure end-to-end delay and test signal loss/recovery with the real setup.
5. Add manual correction and explicit recovery controls before relying on the tool during a match.

Device discovery is documented in the official [FFmpeg AVFoundation documentation](https://ffmpeg.org/ffmpeg-devices.html#avfoundation). Device names and indices can change after reconnecting; select the intended device explicitly rather than assuming index 0 is always the scoreboard camera.
