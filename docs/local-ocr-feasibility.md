# Local pretrained OCR feasibility

Task 2 of the [comparison plan](ocr-comparison-plan.md) establishes that PP-OCRv6 tiny and small can run locally on this Mac using the frozen development colour crops. It does not establish better recognition than the region candidate. Tiny is the primary configuration to carry into task 3 because the larger model's extra cost does not resolve the demonstrated clock-punctuation or all-segments-lit score problems. Retain both raw reports as references; there is no automatic engine selection, field voting or fallback.

No OCR model is connected to recognition state, the server, camera or OBS. Raw strings and native confidence remain raw diagnostics, including empty text, letters, Chinese characters and confident guesses on ambiguous input. No confidence cutoff, digit whitelist, text repair, training or confirmed-output comparison is implemented. Candidate output stays disabled. The monitor-recapture verification recording is never passed to either OCR engine.

## Verified environment and source

Measured host: Apple M1 Pro / MacBookPro18,3, 32 GiB RAM, macOS 15.7.9 arm64, Python 3.12.2. An isolated `/tmp/livestream-ocr-venv` contains PaddleOCR 3.7.0, PaddleX 3.7.0 and PaddlePaddle 3.3.1. Native arm64 wheels install and `pip check` reports no broken requirements. The [full installed version lock](../experiments/ocr/requirements-macos-arm64.txt) is separate from default application and existing region-experiment dependencies. The environment occupies approximately 966 MiB on disk; lightweight model files do not imply a lightweight full runtime. Dependency-install/download wall time was not instrumented; setup evidence is the reproducible commands, resolved wheel report, footprint, model hashes and startup measurements. Other architectures/Python versions and deployment packaging are not validated.

Official [text-recognition API documentation](https://www.paddleocr.ai/main/en/version3.x/module_usage/text_recognition.html) supplies local `model_dir`, CPU settings and raw `rec_text` / `rec_score`. The [tiny](https://huggingface.co/PaddlePaddle/PP-OCRv6_tiny_rec) and [small](https://huggingface.co/PaddlePaddle/PP-OCRv6_small_rec) official model cards declare Apache-2.0, as does the [PaddleOCR source licence](https://github.com/PaddlePaddle/PaddleOCR/blob/main/LICENSE). The downloaded, hash-pinned README files retain model-card licence metadata. This is local evaluation, not redistribution of a bundled runtime; any later distribution needs the applicable dependency notices.

| Model | Immutable official repository revision | Local specification |
| --- | --- | --- |
| `PP-OCRv6_tiny_rec` | `0736086f72f666350ebcdc0c3a504eeac89cdfad` | [tiny-model.json](../experiments/ocr/tiny-model.json) |
| `PP-OCRv6_small_rec` | `bd619643acac4b9650c040234da8d944476ee3f1` | [small-model.json](../experiments/ocr/small-model.json) |

Each specification pins byte counts and SHA-256 for `inference.json`, `inference.pdiparams`, `inference.yml` and `README.md`. Provisioning is a separate explicit command to the official pinned repository. Inference validates the complete local file inventory and hashes; missing, changed or extra files fail before model construction. No cache lookup or automatic weight download is allowed as a substitute.

## Offline and data boundaries

[ocr_feasibility.py](../experiments/ocr_feasibility.py) has two separate user operations: `provision` downloads public model files without images, and `run` performs local inference. The latter starts each trial in a fresh macOS `sandbox-exec` child with `(deny network*)`. The worker checks the kernel's network-outbound denial before importing the OCR runtime, including when accidentally invoked directly. This is a process policy for the experiment, not a change to the machine's network configuration or any existing server.

Model-source checks and Hugging Face online behavior are disabled; the run's PaddleX cache is local to its output folder. Kernel-policy checks were verified to return allow outside the child and deny inside, without sending a probe packet. Models run successfully with network denied. No private pixels are uploaded. The experiment intentionally requires macOS and fails on platforms without this enforced policy. `sandbox-exec` is an experimental local harness dependency, not a chosen production isolation API.

The [workload](../experiments/ocr/smoke-workload-v1.json) binds the final benchmark manifest hash. It selects 21 exact source samples (63 fields) from original/newer/controlled development recordings, including clear scores/clocks, tenths, mixed exposure, blank clock and covered home. The runner verifies all frozen benchmark assets and rejects any workload entry from a verification recording, duplicate indices, missing exported samples or changed crops. Selection followed the initial tiny API smoke check on some of these development crops and preceded the paired 21-sample measurements; this is reused development input, not an unseen smoke dataset. The runner performs no label-dependent selection. The preliminary short smoke trials are preserved alongside the final longer trials, not silently overwritten.

Only supplied whole-field crops are used. Text detection, orientation correction and document unwarping are omitted because field geometry is already explicit. Colour PNGs are read into BGR arrays, as the native API expects. There is no external masking, crop trimming or resizing. The pinned native recognizer applies aspect-preserving height-48 resizing, padding to at least width 320, channel normalization and its full-vocabulary CTC decoder. The model YAML and installed versions bind that preprocessing. There is no inference-time alphabet restriction or result correction.

## Measurements

Final trials use CPU `paddle_static`, one inference thread, MKL-DNN/HPI disabled and the unquantized FP32 model. OMP/OpenBLAS/Accelerate thread environment variables are set to one. Three sequential fresh-worker trials per model each warm up on three complete triplets, then repeat the same 21-sample workload ten times (210 processed triplets per trial). Repetitions measure cost, not independent recognition evidence or fresh source frames. Models are measured sequentially without concurrent heavy experiments.

The time per triplet includes PNG loading and three sequential native API calls. Each field separately records model-API elapsed time, which includes native preprocessing, inference and decoding. Pure kernel-only time is explicitly unavailable. Video decode, panel rectification/crop export, strict parsing, confirmation state and capture/OBS delivery are excluded. The workload is pre-exported and the finite warm loop does not establish full-pipeline or thermal endurance performance. The provisional 100 ms/frame target applies to the eventual whole pipeline, not just these OCR calls.

Ranges across the three final trials (each percentile is computed within its trial):

| Measurement | Tiny | Small |
| --- | --- | --- |
| Parameter file / complete model bundle | 4,420,410 / 4,608,428 bytes | 21,074,618 / 21,456,674 bytes |
| Three-field warm median | 24.5–25.1 ms | 77.1–80.6 ms |
| Three-field warm p95 | 26.9–27.3 ms | 80.1–92.8 ms |
| Repeated-crop processing rate | 39.4–40.2 triplets/s | 12.2–12.9 triplets/s |
| Worker entry to first triplet | 1.69–2.65 s | 1.96–2.51 s |
| Peak process RSS | 866.8–868.0 MiB | 901.8–924.4 MiB |
| Measured CPU use | 1.11 cores | 1.06–1.07 cores |
| Warm measured window per trial | 5.23–5.34 s | 16.27–17.27 s |

Tiny leaves substantially more of the provisional 100 ms budget for the remaining pipeline. Small's OCR-only p95 reaches 92.8 ms, so these measurements do not demonstrate enough budget for decode/crop/state or concurrent OBS load. Neither number is an end-to-end latency or live-readiness result.

Final ignored reports are `data/controlled-recordings/v1/ocr-feasibility-v1/{tiny,small}-final/summary.json` and the three trial JSON files in each directory. Summary hashes are tiny `15063dc76a6002585a2625328a02286d79ca81e799aedc5e5f0197acef62b90f`, small `d725c9403d40c1bad48575d158894d9711bcb8989c0db9fc65e5e94881e91466`. Their source/workload/model/runtime hashes and per-trial hashes were verified. `evidence-final.json` records ranges' underlying values, repetition consistency, install-report identity and all 659 unchanged benchmark assets. The pip install report retains resolved wheel URLs/hashes; the tracked lock pins installed package versions, rather than claiming a portable cross-platform wheel lock.

CPU use is measured process CPU seconds divided by measured wall seconds, expressed in core equivalents. RSS is the worker process lifetime peak, including imports and model construction, rather than weight size or steady-state incremental memory. Startup is worker entry to the first three-field result; it excludes parent manifest verification, interpreter launch and later steady-state passes. Process wall time is retained separately. OS file/bytecode caches are uncontrolled and reused across trials, so fresh workers are not guaranteed cold-storage starts. The very first exploratory tiny import/load took about 32 seconds before those caches were warm; the formal startup range must not be treated as a worst-case first-install promise.

## Raw behavior and decision

The same source samples produce repeatable raw strings across final passes/trials. Selected examples illustrate both usable recognition and unresolved problems; they are not an accuracy estimate:

| Development pixels / review | Tiny raw text | Small raw text | Implication |
| --- | --- | --- | --- |
| Original 70.0 s clock, `19:16` | `19.16` | `19.16` | Both lose the required colon despite high native scores; no period-to-colon repair is permitted |
| Controlled 0.0 s, home score `8` | `日` | `日` | An all-segments-lit score can look like a character; retain the raw string, later strict parsing must reject it |
| Controlled 50.5 s clock, `19:59` | `19:59` | `19:59` | Usable raw whole-field clock example |
| Newer 43.0 s, canonical tenths `00:48.6` | `48.6` | `48.6` | Later layout-aware parsing may represent complete observed `SS.t` canonically; it cannot invent missing characters |
| Controlled 82.3 s clock, explicitly unreadable mixed strokes | `17.9` | `17.9` | Near-1 native confidence still does not establish physical truth; availability is not correctness |
| Controlled 104.9 s blank clock | empty string | empty string | Preserve empty raw output with its native score, not zero |
| Controlled 109.9 s covered home | `X` | `X` | Full-vocabulary OCR can recognize an occlusion pattern; it is not a numeric score |

Small raises confidence on several scores and fixes a tiny raw digit error at original 119.0 s (`10.41` → `18.41`), but both still use a period there. It also changes a newer mixed-clock guess; that is not a physical-truth correction. No threshold sweep or crop tuning follows these results. High confidence does not make malformed or unreadable output safe. Seven-segment clocks and eights remain material obstacles, and neither OCR model is ready for output.

Proceed to the planned **task 3 offline adapter** with tiny as primary and the original raw settings. Its strict whole-field grammar, per-field observed/confirmed separation, duplicate handling and held-age audit must expose these failures without character substitutions or source-intention truth. Task 4 will assess the frozen correctness/coverage/recovery gates on complete timelines and only then use the reserved verification recording. Keep small as a documented comparison option if a bounded question warrants its extra cost; do not open a broader engine search or start training based on this smoke check. This is technical feasibility with limitations, not a decision that OCR is the better route.

## Reproduce

From the repository root, create a separate environment. The lock is measured for macOS arm64/Python 3.12; do not install it into the application or existing region environment:

```sh
python3 -m venv /tmp/livestream-ocr-venv
/tmp/livestream-ocr-venv/bin/python -m pip install \
  -r experiments/ocr/requirements-macos-arm64.txt
/tmp/livestream-ocr-venv/bin/python -m pip check
```

Choose **new ignored directories** when reproducing; existing model/run destinations are refused. Provision explicitly before inference:

```sh
python3 experiments/ocr_feasibility.py provision \
  --model-spec experiments/ocr/tiny-model.json \
  --model-dir data/controlled-recordings/v1/ocr-feasibility-v1/models-reproduced/PP-OCRv6_tiny_rec
/tmp/livestream-ocr-venv/bin/python experiments/ocr_feasibility.py run \
  --manifest data/controlled-recordings/v1/ocr-benchmark-v1/manifest-r2.json \
  --workload experiments/ocr/smoke-workload-v1.json \
  --model-spec experiments/ocr/tiny-model.json \
  --model-dir data/controlled-recordings/v1/ocr-feasibility-v1/models-reproduced/PP-OCRv6_tiny_rec \
  --output data/controlled-recordings/v1/ocr-feasibility-v1/tiny-reproduced \
  --trials 3 --repeats 10
```

For small, substitute its specification and matching model/destination names. `run` requires permission to start the macOS sandbox child; it never starts a server or opens a camera. A failed worker leaves request/log files and no completed summary. Every successful summary binds benchmark/workload/model/runtime/runner hashes and each trial report; trial reports retain all raw fields, source/crop hashes, timings, versions and memory/CPU. Numeric reports, models, install report and logs stay ignored. Provisioning/network availability errors are failures, not empty successful recognition.

Validation: the required application check passes all 91 tests, including seven new OCR orchestration tests; all 46 optional region/experiment tests pass. Both real models complete three final denied-network trials, each with 210 processed triplets; raw strings and native scores are identical across repetitions/trials for the same source. The committed provisioning command was also exercised against the public tiny model host and reproduced every hash. The original recording was regenerated before the final application check (1,638 samples / 52 uncertain), with prior generated data preserved. All 659 benchmark assets rehash unchanged. No UI code changes, browser check or coordinated hardware test is involved. The regenerated supplied original readings match the preserved dataset; application extraction/confirmation and old comparison reports are unchanged. Default CI tests orchestration/uncertainty boundaries with synthetic files and mocks and does not download packages/models or use private footage. Real optional-model inference is verified separately by the local denied-network runs above.
