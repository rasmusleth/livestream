# Opt-in region reader comparison

The continuous monitor can show the whole-region candidate beside the established reader's output. This is diagnostic shadow mode. OBS continues to poll `/api/state`, which contains only the established reader's confirmed values. Candidate state is read separately from `/api/shadow`; there is no promotion route or control.

## Start with recorded input

Default setup is unchanged and does not import NumPy/OpenCV. Shadow mode needs these optional packages, pinned in `requirements-shadow.txt`. Use a separate environment:

```sh
python3 -m venv /tmp/livestream-shadow-venv
/tmp/livestream-shadow-venv/bin/python -m pip install -r requirements-shadow.txt
/tmp/livestream-shadow-venv/bin/python server.py --mode recording --shadow-regions --port 8788
```

Open `http://127.0.0.1:8788`. The original clip and tracked calibration are the defaults. Missing packages or panel geometry fail startup before opening an input; a processing failure stops the candidate, displays its error and preserves its previous values with age while the established reader continues.

The candidate table shows each field's observed and confirmed value, status, age, stale flag and rejection/holding reason. Unknown stays a dash. The candidate clock never runs independently of input. Expand digit diagnostics to inspect bounds, segment levels and reasons. Preview freeze affects the image only; recognition and both status feeds continue. The preview updates more slowly and is not a frame-synchronized accuracy review tool. After EOF or loss, candidate values are explicitly held and age; a lost HTTP connection marks freshness unavailable instead of leaving a confirmed badge.

## Select the clock layout explicitly

`--shadow-clock-layout` accepts `mmss` (default), `mss` (leading blank), or `seconds_tenths` (final blank). A missing digit never automatically selects another layout. The monitor displays the selection, but has no layout-editing or output-promotion controls. See [candidate confirmation rules](candidate-confirmation.md) for the remaining recognition limits.

For the supplied newer MKV and its matching local calibration:

```sh
/tmp/livestream-shadow-venv/bin/python server.py --mode recording \
  --video scoreboard-live-test-01.mkv \
  --calibration data/recognition-live-calibration.json \
  --shadow-regions --shadow-clock-layout-plan data/recognition-live-layout-plan.json \
  --port 8788
```

The optional plan is the explicitly reviewed local JSON schedule described in [the experiment instructions](../experiments/README.md). It is allowed only for recorded input. No plan or private profile is shipped in Git. For a fixed-layout recording, select a single layout instead.

The default continuous monitor reports shadow mode as off. Replay mode retains its original player and seeking; `--shadow-regions` is rejected there. Shadow clock options without shadow mode are also rejected. Calibration edits remain drafts and local saves still require a deliberate restart to activate; they do not reconfigure either running reader.

## One source and the overlay boundary

Opt-in capture uses one FFmpeg decoder, splitting each input frame three ways: the existing half-resolution preview, the unchanged crop/scale path for the established reader, and a full-resolution RGB image for the candidate. All three are padded/packed into one raw frame. Python unpacks them, processes one frame at a time and retains only the latest preview and candidate diagnostic result. No second camera opener, disk recording, numeric history or background task queue is added.

`region_reader.py` is the same hardened glyph implementation used by offline experiments; the experiment wrapper retains its separate OCR and legacy comparison assembly. Optional image imports happen only when constructing an enabled candidate. Tesseract is not needed for shadow mode. The default FFmpeg filter and reader path remain unchanged.

Full-resolution transport increases pipe bandwidth and synchronous candidate work can delay source delivery. At the reference size, each packed frame is about 10.4 MB; higher capture rates cost more than 10 Hz recorded sampling. No live throughput or capture-to-OBS latency is established. Per-frame candidate processing time excludes capture, transport and OBS delivery.

The camera CLI supports the same explicit opt-in flag and retains its resolution guard and single input owner, but it has **not been hardware-tested for shadow mode**. Do not start a camera demo until coordinating with the operator and ensuring OBS is not directly capturing the scoreboard device. Live layout selection and camera performance need further work. OBS should eventually receive only the browser overlay for this device; the match camera is separate.

## Validation on 2026-11-01

The merged main baseline passed all 53 application tests before implementation. A duplicated development-guide paragraph left by merge resolution was removed, and the repository guidance now records one ready-for-review PR against `main`, with no dependent work until the user merges it.

The completed change passes all 58 application tests, including the five private-recording regressions, and all 13 separate optional experiment tests. Generated-video checks prove a single decoder, complete full-source candidate pixels, preview dimensions and identical original-reader observations when shadow packing is enabled. Tests also cover shadow camera resolution rejection without opening hardware, default imports without image packages, candidate failure isolation, held age after EOF and a read-only endpoint that cannot alter OBS state.

Both full recordings were processed through the packed shadow path. All 1,638 original and 514 newer established-reader rows match the saved baseline exactly, including raw/confirmed values, timestamps, status, ages and diagnostics. Every candidate field state matches its saved independent offline timeline. The original batch regeneration still yields 1,638 samples with 52 uncertain raw readings. Reports remain in ignored `data/recognition-{original,live}-shadow.json` files. This establishes equivalence, not accuracy on unlabelled frames; the recognition algorithm and safeguards were not relaxed.

Browser checks used only new recorded/replay demo servers, later stopped. The monitor loaded both enabled and disabled states, displayed independent score freshness with an uncertain/stale clock, continued recognition during preview freeze, and held/aged values at EOF. On the newer recording, candidate scores were visible while the separate overlay stayed empty because the established reader had no confirmation. Replay loading, playback and seeking to 120 s retained `0–1`, `18:41`. The connection-loss view was checked after stopping the demo. No capture device was opened or existing user server stopped/restarted; footage, profiles, screenshots and numeric reports stayed local.

Real-footage tenths recognition remains unavailable in the selected 42.5 s interval. The monitor exposes that limitation; it does not fill it with synthetic ticks. More independently reviewed footage, glyph-window work, exposure/flicker/rotation/zoom checks and coordinated camera/OBS latency validation remain necessary before considering candidate output.

## Recorded glyph follow-up

The subsequent [tenths window/brightness fix](tenths-recognition.md) improves the shared region implementation without changing this transport or the OBS boundary. Current results are 77 available and 51 freshly confirmed tenths clocks in the newer clip's 89-sample selected interval; the zero-coverage result above describes the integration baseline. Camera and exposure limits still apply.
