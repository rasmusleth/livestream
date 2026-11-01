# Working plan: compare learned OCR with calibrated digit recognition

Status: planned; this document adds no recognizer, model, package, capture or output change. The aim is to decide whether local learned OCR is a better recognition route for this project, then establish what evidence is needed for broader scoreboard support. OCR is a hypothesis to test, not the selected replacement.

The current region candidate, calibration, recorded inputs and confirmation/audit tools remain the baseline. Stop routine segment-mask tuning during this comparison, apart from correctness fixes required to keep the benchmark valid. The work already done on explicit uncertainty, frame identity, independent confirmation and held ages remains useful with either recognizer.

## Scope and invariants

- Start offline on the four existing recordings, with frozen matching profiles and exact sequential sample indices. All four are development/regression evidence from the current setup; they do not establish performance on unseen physical scoreboard designs.
- Give OCR original full-resolution colour crops of whole home, away and clock fields, including punctuation. Geometric rectification and declared padding are allowed. Do not feed it only the current segment masks or a concatenated strip of individual digits. Compare the same source frames and field visibility; allow documented engine-specific preprocessing.
- Keep processing local. An isolated optional environment and explicitly provisioned model weights must not change default application dependencies. Save footage, crops, profiles, labels, weights and numeric outputs outside Git; do not upload footage to an API.
- Preserve raw OCR text and native confidence separately from parsed observations and confirmed state. Missing/ambiguous input stays unavailable. Never repair `O` into `0`, truncate digits, infer missing punctuation/slots from past output, generate a clock tick or fill an unavailable score with zero.
- Keep clock-format selection explicit. Reuse confirmation, duplicate-frame handling, correction/reset rules, statuses and held-value ages without relaxing them for OCR. Each engine has separate confirmation history; engine agreement is not source truth.
- Candidate/OCR output stays disabled for OBS throughout the comparison. Cameras and existing servers stay untouched. Automatic field discovery, manual corrections, production packaging and output promotion are separate later work.

## Sequence of reviewable tasks

Each task should fit one focused ready-for-review PR into updated `main`, with implementation, tests, documentation and evidence together. Finish it and wait for the user's merge before beginning dependent implementation. Do not create stacked PRs. Tasks 1–4 answer whether pretrained OCR is promising on the present setup. Task 5 is required for claims about other boards. Task 6 is conditional diagnostic integration, not live-output approval.

| Task | Concrete deliverable | Done when |
| --- | --- | --- |
| 1. Freeze the benchmark and decision rules | Versioned benchmark/field specification, ignored local input manifest and review inventory | Inputs, labels, readable/unreadable cases, development/verification separation and comparison gates are fixed before model tuning |
| 2. Prove local model feasibility | Reproducible isolated OCR smoke runner and pinned model/runtime record | At least one pretrained recognizer reads local whole-field crops without network inference, and compatibility, setup cost and three-field processing cost are measured |
| 3. Add the offline comparison path | Engine-neutral observations, strict whole-field parsing and an OCR adapter using existing confirmation/audits | A complete recording yields auditable raw/observed/confirmed timelines; old readers retain their behavior and OCR cannot affect output |
| 4. Run the frozen comparison and decide | Paired results, failure review and a written go/stop/inconclusive decision | Correctness, abstention, stale holds, recovery and local runtime are compared on locked inputs/configurations, with all exclusions and limitations visible |
| 5. Check generalization on new boards and conditions | Independently reviewed footage groups and an untouched verification run | Any portability claim is supported by genuinely new scoreboard/capture groups, including different layouts and multi-digit scores where relevant |
| 6. Try the selected reader in diagnostic shadow mode | Recorded-path equivalence, then a separately coordinated camera test | Same-frame diagnostics agree with offline results, throughput/age/loss behavior are measured, and output remains disabled |

### Task 1 — Benchmark and decision contract

Inventory these existing sources without overwriting their saved profiles, reviews or results:

- `scoreboard-2-min-clip.mp4` and tracked calibration.
- `scoreboard-live-test-01.mkv` and its saved calibration/layout schedule.
- `mock-scoreboard-testing-clip.mkv` and its frozen registration profile/reviews.
- `data/controlled-recordings/v1/recording-camera-footage.mkv`, geometric probe profile, diagnostic score-window template, captured-time layout plan and 75-timestamp per-field review.

Record file hashes, reader revision, decode/sample settings, field quadrilaterals/padding, calibration and layout hashes, review provenance and scenario/time windows in a local manifest. Add a portable specification and validation fixtures to Git; keep private assets local. Verify whole-field crops geometrically against source images before seeing OCR results. The candidate's per-digit boxes need not be suitable OCR field boxes; preserve the colon/decimal and distinguish real blank space from clipping.

Retain the existing reviewed anchors as regression checks. Add prediction-free review of complete short sequences covering static digits, both score sweeps, changing/paused clocks, tenths, corrections, blank/covered input, recovery and mixed/unreadable transitions. Labels come from captured pixels, not generated source intention. Report which windows were newly reviewed and which were already used in development. Preserve synthetic clean/mixed exposure cases separately: a blended rendering has no physical truth label, although a third digit absent from both sources is a useful diagnostic.

Assign development and locked verification groups before tuning. Within-recording windows from the same board may help check a frozen configuration, but are not independent cross-board validation. Do not randomly split adjacent frames into train/test. In task 5, split by physical board/capture session and keep near-duplicate photos or clips together. If a verification set is inspected to tune a model/threshold, relabel it as development and obtain a fresh verification group.

Pre-register comparison priorities and the exact report schema:

1. Wrong fresh confirmations on readable fields; fresh confirmations on unreadable fields remain a separate risk count.
2. Correct readable observations and correct fresh confirmations, including previously failing examples; rejected readable fields count as unavailable, never correct.
3. Held-value correctness, age/staleness, recovery delay and recognition delay relative to first clearly readable sampled evidence.
4. Runtime, memory, dependencies and setup/calibration effort on the actual streaming Mac.

Use conservative research gates: no new wrong fresh readable result on frozen reviewed cases, no additional fresh confirmations on reviewed unreadable cases, preservation of the recovered clean-score regressions, and a useful coverage/recovery or portability benefit at practical cost. A regression blocks recommending replacement until resolved or explicitly reviewed as a tradeoff. Zero observed errors in a finite review is not a production error-rate guarantee. Agree any numerical production tolerance separately before output promotion.

Use 10 source frames/s across all three fields as the initial throughput target, matching the existing benchmark. A 100 ms/source-frame processing budget is a provisional single-worker design target, not an already agreed live-latency requirement. Record costs for all three fields together, not only the fastest crop. Separate throughput, processing delay and source-frame age; define a maximum queue/age policy before any streaming integration.

Completion evidence: validated manifest/crop examples, review inventory, locked splits/settings, baseline reader hashes and a machine-readable scorecard specification. No OCR training is part of this task.

### Task 2 — Local pretrained OCR feasibility

Check official model/runtime documentation at implementation time. A provisional small shortlist is PaddleOCR's PP-OCRv6 tiny and small recognizers: test one practical local model first; add the second only to measure a meaningful speed/accuracy tradeoff. These names are candidates, not a claim of macOS/Python compatibility or scoreboard accuracy. Verify model licence, CPU/architecture support, Python/package requirements, model availability, hashes and weight size before choosing the pinned environment. Keep it separate from the current NumPy/OpenCV environment if requirements conflict.

Provision weights explicitly, then run with network inference disabled and no implicit downloads during evaluation. Make missing weights/packages a clear failure, not a successful empty result. Do not send image data to a hosted demo or API. Retain model identity, runtime/backend/precision, decoder settings and preprocessing in each result.

Use task 1 development crops of clear clocks/scores and deliberately unreadable fields for a smoke check, including warm/cold start. Measure all three field crops per source sample, CPU load and resident memory on the intended Mac. Performance runs should be isolated from concurrent heavy experiments. Distinguish model-only inference from decoding/cropping/parsing/state cost. Do not infer camera-to-OBS latency from these timings.

The historical Tesseract/masked-strip result is a reference only. If useful and inexpensive, run a fresh whole-field Tesseract control on the same colour crops; do not present the historical configuration as a fair test of every OCR approach. Prefer a bounded pretrained experiment before custom training or a broad engine search.

Completion evidence: reproducible installation/provisioning commands, pinned runtime/model record, local smoke results and a documented choice of engine configuration(s) to bring into task 3. If local execution is impractical, report that result and reassess the shortlist rather than migrating the application stack.

### Task 3 — Whole-field adapter and common evaluation

The current `CandidateState.update` expects six digit slots, and the audit validates one-digit scores. Factor a recognizer-neutral per-field observation entry point while preserving the existing slot parser/wrapper and all its behavior. A clock observation should carry its observed canonical text, explicit layout and numeric ticks; OCR must not fabricate blank digit slots merely to fit the old API.

Each engine result needs source sample/time/frame identity, field geometry, raw text, native confidence, parsed value or explicit rejection reason, engine/configuration identity and timing. OCR and region recognition use the same confirmation policy in separate state instances. Keep raw unfiltered OCR results available alongside any development-selected confidence rejection. Confidence scales are engine-specific diagnostics, not interchangeable correctness probabilities.

Start confirmed-output comparison with the formats/one-digit scores already supported by the baseline. Require the complete score string and exact clock grammar for the selected layout; retain punctuation and leading zeros in raw text. Canonicalization may express reviewed `SS.t` as `00:SS.t`, but cannot recover missing characters. Unsupported multi-digit scores must remain present in raw results with an explicit out-of-scope parsed status; never turn `10` into `1` or `0`. Task 5 covers multi-digit raw recognition and the separately tested state/audit schema extension needed to confirm those scores.

Reuse `experiments/audit_readings.py` and its provenance/grid/status/age checks. Add meaningful generated tests for parser boundaries, missing/extra characters, unsupported values, duplicate frames, clock progression/pause/correction, independent field loss, held age/staleness and recovery. Re-run old readers to prove that the common entry point did not change their output. Freeze confidence thresholds/preprocessing on development data before the comparison run.

Completion evidence: end-to-end offline reports for one full source, strict parser/confirmation tests, provenance and state invariants, unchanged baseline output and an explicit proof that the adapter has no route to OBS output. No new runtime default or automatic reader selection.

### Task 4 — Frozen head-to-head evaluation

Run the active reader as reference, current region candidate as the main baseline, and selected OCR configuration(s) over the same exact sampled source frames. Compare original colour fields through each documented pipeline; avoid bias from forcing OCR through the region reader's colour masks. Keep engine-specific raw recognition separate from the common parsing/confidence/confirmation stage so that a model's guesses cannot disappear from the report as unexplained missing data.

Report per field, recording and scenario rather than one aggregate accuracy number:

- Readable raw correct/wrong/unavailable and fresh correct/wrong; unreviewed fields explicitly counted.
- Unreadable raw availability and fresh output; held status/age/value separately.
- Longest holds, stale duration and sampled recovery/confirmation delay around labelled transitions.
- Clean and mixed synthetic cases, including all preserved third-digit failures, with no invented mixture truth.
- Paired disagreement examples, dependency/model footprint, cold start, memory/CPU and isolated three-field processing median/p95 plus sustained throughput.

Review disagreements against source pixels with predictions hidden; do not silently relabel to match a recognizer. Keep frozen scores intact and describe any corrected annotation with provenance and a rerun. Treat samples from one sequence/board as correlated; avoid treating thousands of nearby frames as thousands of independent tests or claiming universal accuracy from sparse zero-error labels.

The task ends with a concrete decision, even if it is negative:

| Finding | Next action |
| --- | --- |
| OCR passes the research gates with a useful benefit | Continue to task 5; retain both readers as regression references |
| Benefit is narrow, mixed or statistically/data-limited | Record the limits; define at most one bounded follow-up with new evidence and a stop condition |
| OCR is less reliable or impractical locally | Keep the current route and document why; close the experiment without promoting OCR |
| Pretrained OCR is promising but misses a consistent display family | Propose a separate fine-tuning/specialized digit-recognition study only after checking data quantity/diversity and keeping a true holdout |

Do not use automatic voting, agreement or fallback between recognizers to conceal a poor individual result. Any ensemble would be a later measured experiment with its own output/uncertainty rules. No training is assumed necessary before the pretrained comparison has answered its question.

Completion evidence: reproducible paired reports, retained failures, task 1 gate assessment and a recommendation explaining correctness, practical cost and what remains unknown. This can establish promise on the current setup; it cannot establish out-of-the-box multi-board support.

### Task 5 — Unseen boards, conditions and multi-digit scores

Proceed only if task 4 warrants it. Obtain independently reviewed, legally usable material from genuinely different physical boards and capture sessions. At this point coordinate any new user recording; do not open a device or change a server automatically. Appropriately licensed external examples can supplement local footage, but still photos cannot validate temporal recovery or flicker behavior.

Cover different seven-segment shapes and at least one other display style where available, lighting/exposure changes, glare, focus/blur, perspective/scale, clock punctuation/formats, leading blanks, multi-digit scores and unavailable fields. Record actual coverage and gaps rather than asserting an arbitrary sample count proves generalization. Keep whole board/session groups out of development. Do not train on synthetic variations of a held-out board template and then describe that board as unseen.

Begin with raw whole-field recognition and explicit field boxes; automatic identification of home/away/clock is outside this comparison. For confirmed multi-digit evaluation, explicitly extend the experimental score range, parser, state/audit validators and fixtures while retaining one-digit baseline regressions. Reuse common confirmation semantics; preserve the complete observed score and never clip/modulo it into the old range. Unsupported clock layouts remain explicit until separately implemented and reviewed.

Lock the selected OCR/preprocessing/confidence configuration before verification. If adapting to each new board, report the adaptation effort and call it setup-specific, not out-of-the-box. Reassess all task 1 gates by board/session. Any model-training proposal must now specify training/development/test groups, labelling cost, augmentation limits and a measurable stopping rule; it should not expand indefinitely into general vision research.

Completion evidence: verification results and failure examples on new groups, tested multi-digit handling where claimed, practical setup effort, and an evidence-based recommendation for general OCR, specialized recognition, a setup-specific solution or further data collection. Limited data means a limited conclusion.

### Task 6 — Diagnostic integration and coordinated hardware check

Only after a favourable recognition decision, add the selected engine to opt-in diagnostic shadow mode, still output-disabled. First prove full-recorded-path equivalence with the offline observations/confirmed states and unchanged active-reader output. Ensure OCR work does not stall the capture reader; measure bounded queues/frame dropping explicitly and never treat repeated frames or old crop results as fresh source evidence.

A live camera test requires separate coordination over device ownership and existing OBS/server state. Measure arrival-to-observation age, processing throughput, holds/staleness, loss/recovery and operator readability under the agreed setup. End-to-end hardware/OBS delay needs a separately defined measurement. Successful shadow testing does not authorize output promotion: manual correction behavior, production thresholds and an explicit output policy remain separate decisions.

Completion evidence: recorded equivalence, failure isolation, runtime measurements, a coordinated test report with honest omissions, and a recommendation about readiness for the next product milestone. Leave merging and any output promotion to the user.

## Validation and handoff

For every implementation PR run `python3 scripts/check.py`. Recognition/state changes also require the relevant optional synthetic suite, regeneration and regression checks for the supplied original recording, available full comparisons/audits and preservation of earlier reports. Add focused tests for new contracts; do not run private footage or require model downloads in default application CI. Verify optional model integration in its isolated environment and report tests skipped because weights/footage are absent. UI changes require the repository's visual checks; this planning PR changes no UI.

Keep one active PR at a time. The immediate next task is task 1, not model training or live integration. Each PR should state which task is complete, name the evidence and remaining gaps, and update this plan's status without silently treating later tasks as done.

Useful existing references: [comparison method and historical Tesseract limits](recognition-comparison.md), [field review/audit](exposure-validation.md), [controlled recapture](controlled-recapture-validation.md), [current candidate limits](score-chroma-rejection.md), and [experiment commands](../experiments/README.md). Provisional model references: [PaddleOCR official documentation](https://www.paddleocr.ai/main/en/) and [ScoreSight's independently reported OCR comparison](https://royshil.github.io/scoresight/development/ocr-eval.html). External benchmark scores do not predict accuracy or runtime on our footage/Mac; task 2 must verify the actual chosen model and environment.
