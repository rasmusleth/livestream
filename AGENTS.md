# Working in this repository

## Purpose and scope

Read camera footage of a futsal scoreboard and turn the scores and clock into reliable digital values for an OBS overlay. The current implementation is a local prototype for one calibrated camera position. A transparent OBS browser overlay can follow recorded playback, continuous recorded input, or experimental macOS camera input. Live scoreboard recognition accuracy still needs validation against the actual camera framing; manual corrections are not implemented.

Read `README.md` for setup, `docs/architecture.md` for current and intended boundaries, and `VALIDATION.md` for evidence and limits. Read `docs/development.md` before changing the workflow.

## Working agreements

- Make focused changes on a descriptive branch and submit them through a pull request into `main`.
- Inspect the working tree first. Preserve unrelated work, recordings, and generated local data. Do not reset or clean the checkout to make a task easier.
- Use the user's requested scope. Do not turn a scoreboard task into a broader streaming platform or migrate the stack without a concrete need.
- Prefer Python's standard library and the existing plain HTML/CSS/JavaScript. Explain new runtime dependencies in the PR.
- Keep processing local by default. Do not upload footage or add external services without the user's authorization.
- Keep recordings, generated readings, credentials, and large binary artifacts out of Git. Synthetic test inputs should be generated during tests.
- Update the relevant docs when changing behavior, calibration, setup, or architectural decisions. Distinguish implemented features from planned ones.
- Do not merge, release, publish, or change repository access unless the user authorizes that action. Opening a draft PR is appropriate for requested implementation work.

## Scoreboard correctness

- Missing or uncertain readings must stay explicit. Never substitute zero or an independently running clock for unavailable input.
- Preserve the distinction between raw observations and confirmed output. Held values must carry their age and status.
- Treat recognition coverage and confidence margins as diagnostics, not accuracy claims.
- Camera calibration is specific to the recorded setup. Do not claim support for other angles, multi-digit scores, or unseen conditions without evidence.
- For recognition changes, run the synthetic pipeline tests and, when available, regenerate the supplied recording's readings before running its regression checks. Describe missing real-footage validation honestly.

## Verification before a PR

Run from the repository root:

```sh
python3 scripts/check.py
```

The initial development target is macOS with Python 3.12. Node.js 24, FFmpeg, and ffprobe are also required for the complete check. No Python or npm packages are required.

The check compiles Python in memory, validates browser JavaScript syntax and calibration bounds, and runs unit and generated-video pipeline tests. Real-recording tests are skipped when `data/readings.json` is absent. When changing extraction behavior and the recording is available, also run:

```sh
python3 reader.py scoreboard-2-min-clip.mp4
python3 scripts/check.py
```

For UI changes, open the local viewer and check loading, playback, seeking, readability, and uncertain-reading status. CI does not replace that visual check.

In the PR, explain the concrete change, validation performed, and material limitations. Do not report a check as passing if it was skipped or could not run.
