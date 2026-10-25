# Recorded replay in an OBS overlay

This milestone connects the recorded verification player to a separate transparent scoreboard. It is a local proof of the overlay workflow, not live camera input. The graphic carries a `REPLAY` label.

## Start the tool

From the project folder, with Python 3.12 and FFmpeg installed:

```sh
# Only needed if readings have not been generated yet:
python3 reader.py scoreboard-2-min-clip.mp4
python3 server.py
```

1. Open `http://127.0.0.1:8765` on the same Mac as OBS.
2. Seek to a point in the recording, then click **Send replay to overlay**.
3. Open `http://127.0.0.1:8765/overlay` to inspect the graphic. The page background is transparent; a normal browser may display that background as white or dark.
4. Play, pause, or seek the recording. The overlay follows the confirmed reading at that source position. It does not run its own clock.

Keep one publishing verification tab open. Multiple publishing tabs can compete for the output position. Output is off by default on a newly opened or reloaded verification page.

## Add it to OBS on macOS

1. Add a **Browser** source to your scene and name it `Scoreboard replay`.
2. Leave **Local file** unchecked.
3. Set **URL** to `http://127.0.0.1:8765/overlay`.
4. Set **Width** to `1920` and **Height** to `1080`.
5. Keep the default transparent-background CSS. No page permissions to control OBS are needed.
6. Place the source above the match footage in the scene's source order. The graphic is positioned 40 pixels from the top and left of its canvas.
7. Keep **Shutdown source when not visible** and **Refresh browser source when scene becomes active** off for this test, so scene switches do not unnecessarily unload or reload the page.

These properties are described in the official [OBS Browser Source documentation](https://obsproject.com/kb/browser-source).

If the default port is busy, run `python3 server.py --port 8766` and use port `8766` in both URLs. The verification page displays the correct overlay URL for its current port.

## Held readings and recovery

- Before any confirmed reading, the graphic uses dashes rather than zero scores.
- Brief recognition uncertainty holds the previous confirmed reading. A source hold of at least one second shows `DATA HELD`.
- Clicking **Stop replay output**, closing the publishing tab, or losing its heartbeat preserves the last values. Missing heartbeats are marked disconnected after two seconds; explicit stop is immediate.
- If the overlay loses its server connection, it preserves the displayed values and shows a connection warning. Reconnecting resumes updates automatically.
- Paused video continues sending heartbeats while output is enabled. Its match clock stays paused and is not considered disconnected.
- Restarting the Python server clears in-memory replay position. The publishing tab can re-establish output on its next successful update.

Browser background throttling may delay the operator heartbeat and cause held-data warnings. Keep the operator visible for this playback experiment. Refreshing OBS or switching scenes cannot restart playback; the verification player owns source position.

## Validation scope

Automated tests cover selection by source timestamp, backward seeking, paused clocks, invalid positions, dropped publishers, recovery, local HTTP delivery, and preservation of video range requests. They use controlled data and require no match footage.

The browser verification covered recorded playback, seeking, pauses, transparency, and stopping/resuming replay output. On 2026-10-25, the user reported following the OBS setup instructions on their Mac and confirmed that everything worked as planned. This establishes a user-reported OBS check of the recorded-playback workflow; it is not validation of live capture or every failure/recovery scenario.

Live capture latency, team-name configuration, manual overrides, and a live-ready graphic are outside this milestone.
