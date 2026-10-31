# Local recognition experiments

These scripts compare candidates offline. They do not modify calibration files, start a camera, publish values, or change the server. See [the findings](../docs/recognition-comparison.md) for results and limits.

Use a separate environment with Python 3.12, FFmpeg/ffprobe, and local Tesseract (tested with 5.5.1 and English data):

```sh
python3 -m venv /tmp/livestream-recognition-venv
/tmp/livestream-recognition-venv/bin/python -m pip install -r experiments/requirements.txt
/tmp/livestream-recognition-venv/bin/python -m unittest discover -s experiments -p 'test_*.py' -v
```

OpenCV/NumPy are optional experiment dependencies, not application requirements. The standard repository check compiles these files without importing them; it runs the existing application tests. The seven experiment tests require this environment and are run separately.

Keep recordings, local profiles, labels, and outputs in ignored local paths. The original benchmark uses tracked `calibration.json`; the new one needs the saved profile matching its framing. Preserve a copy of that profile before further edits. Our local copy is `data/recognition-live-calibration.json`; do not substitute a calibration made for another framing.

Labels are visually inspected values for exact FFmpeg sample indices on a 10 Hz grid, with synthetic example structure:

```json
[{"t": 2.5, "values": {"clock": "19:58", "home": 0, "away": 0}, "split": "heldout"}]
```

`split` documents development versus later timestamp checks; it does not imply independent footage. Unsupported or unreadable frames should be excluded with an explanation, rather than given guessed values. The final-minute format in this known scoreboard is normalized to `00:SS.t`; all blank slots elsewhere remain unavailable. Confirm any different scoreboard's formats before interpreting them.

The supplied local annotation files and all output reports are ignored. They are not downloaded or checked into CI. Run the full comparisons:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/compare_readers.py scoreboard-2-min-clip.mp4 --calibration calibration.json --labels data/recognition-original-labels.json --output data/recognition-original-final.json
/tmp/livestream-recognition-venv/bin/python experiments/compare_readers.py scoreboard-live-test-01.mkv --calibration data/recognition-live-calibration.json --labels data/recognition-live-labels.json --output data/recognition-live-final.json
python3 experiments/summarize_results.py data/recognition-original-final.json data/recognition-live-final.json
```

`--limit N` limits candidate output for development (the baseline is still decoded fully); `--skip-ocr` permits faster Regions-only development; `--ocr-psm 7` compares an alternate OCR line mode. A missing/broken OCR tool fails the run rather than reporting an empty result as successful. Tesseract errors are not swallowed. Reports include input SHA-256, the exact calibration/template/labels, tool versions, raw and confirmed timelines, held ages, reviewed correctness counts, and candidate processing times. These are batch experiments; coverage is not accuracy and timing excludes candidate decoding/capture/OBS delivery.

Stress-test only labels marked `heldout`, using the same pixel translations for both candidates:

```sh
/tmp/livestream-recognition-venv/bin/python experiments/stress_readers.py scoreboard-live-test-01.mkv --calibration data/recognition-live-calibration.json --labels data/recognition-live-labels.json --output data/recognition-live-stress.json
/tmp/livestream-recognition-venv/bin/python experiments/stress_readers.py scoreboard-2-min-clip.mp4 --calibration calibration.json --labels data/recognition-original-labels.json --output data/recognition-original-stress.json
```

No images or audio are saved by these scripts. Numeric output files may be large; keep them ignored. The Regions prototype and OCR baseline still make mistakes. Neither is wired into production input or the overlay.
