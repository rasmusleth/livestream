# Livestream

Working name for a tool to make sports livestreams more polished, starting with futsal scoreboards.

## Initial goal

Turn camera footage of a physical scoreboard into digital scores and game time, then display those values in a clean OBS overlay.

The current streaming setup uses one camera for the match and a second camera pointed at the scoreboard. OBS places that scoreboard footage over the match video. This project should retain the scoreboard camera as an input while replacing its visible footage with a digital graphic.

The streaming computer runs macOS. An existing full-game scoreboard recording is available for development and validation; a shorter excerpt can be used for initial experiments.

## Proposed first version

1. Select the scoreboard video input.
2. Identify the regions containing each team's score and the game clock.
3. Read those values from the video and check them across successive frames.
4. Show the current readings and their status in an operator view.
5. Publish a transparent overlay that OBS can display as a browser source.
6. Allow the operator to correct values manually and resume automatic reading.

Start with one known scoreboard and camera setup. Support for other layouts can follow once the first setup works reliably.

## Reliability requirements to explore

- The clock must follow the physical scoreboard, including pauses and corrections.
- Uncertain or missing readings must not silently become zeroes or guessed values.
- Brief interruptions should preserve the last confirmed values, with an obvious stale-input indication for the operator.
- Recovery after a longer interruption, score resets, and clock corrections need explicit handling.
- The operator needs a way to override an incorrect reading during a match.
- Reading accuracy and delay should be measured against representative footage before relying on the tool live. Acceptable thresholds are still to be agreed.

## First development milestone

Use a short recording from the actual scoreboard camera to prove that both scores and the game clock can be extracted consistently. Include clock movement, a stopped clock, and score changes where available.

Inspect the footage before choosing a recognition approach or application stack. Save timestamped readings alongside the source recording so errors and delay can be checked. Once extraction is credible, connect it to the OBS overlay and then a live input.

## Open questions

- What does the physical scoreboard look like in the camera feed?
- Which capture mode works reliably for the USB-C HDMI capture device exposed as “USB video,” with the reader owning that input?
- What clock formats, periods, and reset behavior need to be supported?
- What delay is acceptable between the physical scoreboard and the digital overlay?
- Does this need to work at one venue initially or across several different scoreboards?

## Possible later scope

Team names and branding, periods, fouls, timeouts, player information, sponsor graphics, and broader match production controls could be added later. These are possibilities rather than requirements for the first version.

The product name and broader scope can stay open while the scoreboard workflow is proven.

## Run the first prototype

Initial development target: macOS with Python 3.12. Requirements: `ffmpeg` / `ffprobe` on your PATH. No Python packages or cloud services are needed.

From the project folder:

```sh
python3 reader.py scoreboard-2-min-clip.mp4
python3 server.py
```

Open [the local verification view](http://127.0.0.1:8765). Play or seek through the recording to compare the camera image with the extracted clock and scores. The “Jump to second” control makes it easy to inspect specific moments. Stop the server with Ctrl+C.

Readings are precomputed from the recording at 10 samples per second and saved in `data/readings.json`. The viewer follows the video's playback position, including when seeking backward. It does not read live frames in the browser. The original video is unchanged.

`calibration.json` specifies the six digit regions and seven sample locations per digit, in source-image coordinates. The reader measures the bright LED strokes and decodes their segment patterns. Two consecutive matching samples are required before publishing a reading; otherwise the last confirmed values are held and labelled. A hold of one second or longer is marked stale.

This first version supports this fixed 1920×1080 camera framing and one-digit scores. A changed angle, zoom, scoreboard layout, lighting, or multi-digit score needs further work and validation. A transparent OBS browser overlay can follow the verification player. Live capture and manual overrides are not implemented yet. See [OBS overlay setup](docs/obs-overlay.md).

### Validation

```sh
python3 -m unittest discover -s tests -v
```

Generate readings before running recording regression checks. See [VALIDATION.md](VALIDATION.md) for the first clip's results and limits. Video files and generated readings are excluded from Git.

## Contributing and repository guidance

Read [AGENTS.md](AGENTS.md) for coding-agent instructions, [the architecture document](docs/architecture.md) for implemented and proposed boundaries, and [the development workflow](docs/development.md) for branches, PRs, and CI.

Run the shared local and CI checks with:

```sh
python3 scripts/check.py
```

These checks include a generated-video pipeline test without needing the match recording. Real-recording regression checks additionally run when local generated readings exist.

## Continuous processing and live-input preparation

To emit observations continuously from the existing recording at playback speed:

```sh
python3 reader.py scoreboard-2-min-clip.mp4 --stream --realtime
```

This prints one JSON observation per line without waiting for full-recording analysis. It does not update the existing OBS overlay yet. The live HDMI capture adapter remains to be implemented. See [live-input findings and next steps](docs/live-input.md), including the OBS disruption observed during a shared-device test and its successful recovery.
