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

For the intended live path, prefer one owner of the scoreboard capture input: the reader captures the scoreboard, and OBS consumes the digital browser overlay. The separate match camera remains an OBS input. The live capture adapter and its connection to the overlay are not implemented yet.

## Continuous recognition from a recording

The reader can now emit observations as frames are decoded instead of waiting for a complete batch JSON file:

```sh
python3 reader.py scoreboard-2-min-clip.mp4 --stream --realtime
```

Each stdout line is one JSON observation with the same fields as a row in `data/readings.json`: timestamp, raw reading, confirmed values, status, age, confidence margin, and segment evidence. Output is flushed after each observation. `--realtime` paces the recording input at normal speed; without it, streaming runs as fast as decoding permits. It is a playback pacing option, not a live latency measurement.

Press Ctrl+C to stop. The reader closes and terminates its FFmpeg child when streaming stops early. The streaming path keeps recognition state without accumulating a full recording in memory. It does not write `data/readings.json` or drive the OBS overlay yet; the existing viewer/overlay still uses the batch dataset.

The original batch command remains available:

```sh
python3 reader.py scoreboard-2-min-clip.mp4
```

Both modes share `FrameReader`, including the same recognition thresholds and two-observation confirmation. Before either recorded input mode starts, the source dimensions must match calibration.

## Remaining work

1. Establish a suitable capture mode with the scoreboard capture input owned by one application.
2. Add a live input adapter with explicit device selection, configuration errors, and clean shutdown.
3. Check or recalibrate the scoreboard regions against actual live camera framing. A camera pointed at something else is not a valid recognition test.
4. Feed continuous confirmed observations into shared server state so the overlay no longer depends on a publishing playback tab.
5. Measure delay and test signal loss, recovery, stopped clocks, score changes, and manual correction before match use.

Device discovery is documented in the official [FFmpeg AVFoundation documentation](https://ffmpeg.org/ffmpeg-devices.html#avfoundation). Device names and indices can change after reconnecting; select the intended device explicitly rather than assuming index 0 is always the scoreboard camera.
