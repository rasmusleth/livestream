# Offline whole-field OCR adapter

Task 3 connects the pinned local PP-OCRv6 tiny recognizer to the experimental per-field confirmation policy. The region reader still supplies its six digit slots to the existing wrapper; OCR supplies typed observations directly. Each engine has its own state. Scores can confirm while the clock is missing, and a held field keeps its last confirmed value, age and stale flag. Identical full RGB frames in the recent-frame window do not refresh evidence. Nothing advances the clock without a new observation.

| Selected field/layout | Accepted OCR text | Confirmable form |
| --- | --- | --- |
| Home or away | One ASCII digit | Integer 0–9 |
| `mmss` | `MM:SS` | `MM:SS` |
| `mss` | `M:SS` | `0M:SS` |
| `seconds_tenths` | `SS.t` | `00:SS.t` |

The layout comes from the frozen source plan. Seconds must be 00–59. The parser uses the whole raw string, including punctuation, leading zeros and any whitespace. It rejects empty strings, extra or missing characters, and wrong punctuation rather than guessing or changing layouts. Multi-digit strings such as `10` retain their raw value and receive `unsupported_score_width`. Native scores are recorded as diagnostics. The frozen Task 3 configuration uses **no confidence cutoff**, no alphabet restriction and the unchanged Task 2 tiny preprocessing and model settings.

## Run one development timeline

Reuse the isolated region environment (for the same crop export as the benchmark), the [existing OCR environment and pinned tiny weights](local-ocr-feasibility.md), and the local [frozen benchmark](ocr-benchmark.md):

```sh
/tmp/livestream-recognition-venv/bin/python experiments/ocr_adapter.py \
  --manifest data/controlled-recordings/v1/ocr-benchmark-v1/manifest-r2.json \
  --recording original \
  --ocr-python /tmp/livestream-ocr-venv/bin/python \
  --model-dir data/controlled-recordings/v1/ocr-feasibility-v1/models/PP-OCRv6_tiny_rec \
  --output data/controlled-recordings/v1/ocr-adapter-v1-original-reproduced
```

Choose a new ignored output directory. The runner rejects the verification split before opening recording assets. It validates the selected frozen video, geometry, layout, review and region report; it compares new RGB frame and PNG crop hashes with the frozen export anchors before starting inference. It exports the full 10 Hz grid from zero and passes the three colour crops for each sample to the existing network-denied worker. It verifies the complete grid, frame identities and crop identities again when joining the worker's results. Missing weights, bad inputs and incomplete results fail the run.

`trial-1.json` preserves the worker's raw results, runtime, model settings and timings. `report.json` binds the raw results to source index/time/hash, field geometry, native confidence, parsing status, timing and confirmed timeline. `audit.json` uses the same review and audit code for OCR and the frozen region report. It keeps readable correctness, unreadable exposure and unreviewed coverage separate. The report is diagnostic JSON, separate from the runtime replay dataset. No application or shadow route imports the adapter, reads these files or promotes their values. The existing HTTP tests verify that even opt-in region shadow values cannot change `/api/state`.

The original benchmark and Task 2 evidence remain as frozen. Their historical all-assets verifier also checks the historical implementation files; reproduce that historical smoke run from the Task 2 revision. The Task 3 runner checks the selected source assets and binds its own implementation hashes separately.

## Development evidence

The original development clip produced 1,638 source samples and 4,914 raw OCR field results. All 1,638 clock strings failed the selected `MM:SS` grammar (for example, `19.16` at 70.0 s). The OCR clock stayed unknown throughout. Both scores still confirmed independently.

| Field | Readable reviews | Tiny fresh correct / wrong | Regions fresh correct / wrong | Unreadable reviews; fresh tiny / regions |
| --- | ---: | ---: | ---: | ---: |
| Home | 20 | 20 / 0 | 20 / 0 | 0; 0 / 0 |
| Away | 19 | 18 / 0 | 18 / 0 | 1; 1 / 1 |
| Clock | 19 | 0 / 0 | 19 / 0 | 1; 0 / 1 |

Each field has 1,618 unreviewed samples. Tiny produced 1,637 fresh home values and 1,636 fresh away values; the away field held once for 0.1 s. The unreadable away field still got a fresh value from both engines. These are development observations and sparse reviews, not a gate assessment or an accuracy claim. The worker's three-field median/p95 was 29.5/35.8 ms for pre-exported PNG loading plus model API calls; decode, crop export, state, and delivery were outside that timing.

The local evidence is under `data/controlled-recordings/v1/ocr-adapter-v1-original/`. SHA-256: report `0e05cb1f8741345654a34050598699b140ce8f102b9dd7c55231eaadcc19a1bd`; audit `6022b61421d9ec8b438058d3dda33d360fbd17932ceb67748b4aadac49e7d5ac`.

The application check passed 97 tests, including the original recording regressions, and the optional experiment suite passed 46 tests. The regenerated original active-reader dataset matched the existing file byte for byte. Full active and region reruns for all three development recordings matched the frozen reading rows, region diagnostics, independent timelines and audit counts. The new generated tests exercise grammar boundaries, provenance and repeated frames, independent loss, hold age/staleness, clock progression, pause, correction and recovery. No model dependencies were installed or changed. No camera or existing server was accessed. The monitor recapture remains reserved for Task 4.
