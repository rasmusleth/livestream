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
- Use one active PR targeting `main`. Branch from updated `main`, complete implementation, validation and documentation, then push and open or update a ready-for-review PR. Wait for the user to merge it before beginning dependent implementation; do not stack PRs. Keep closely related stages together when splitting would require a stack. This is the user’s standing preference; do not ask again unless the scope or destination is unclear. Honor explicit requests to keep work local.
- Leave merging to the user. Do not merge, release, deploy, or change repository access without separate authorization.

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

The initial development target is macOS with Python 3.12. Node.js 24, FFmpeg, and ffprobe are also required for the complete check. The main application and its standard validation checks require no third-party Python or npm packages. Experimental tooling may have separate dependencies; see the requirements files under `experiments/`.

The check compiles Python in memory, validates browser JavaScript syntax and calibration bounds, and runs unit and generated-video pipeline tests. Real-recording tests are skipped when `data/readings.json` is absent. When changing extraction behavior and the recording is available, also run:

```sh
python3 reader.py scoreboard-2-min-clip.mp4
python3 scripts/check.py
```

For UI changes, open the local viewer and check loading, playback, seeking, readability, and uncertain-reading status. CI does not replace that visual check.

In the PR, explain the concrete change, validation performed, and material limitations. Do not report a check as passing if it was skipped or could not run.

## Dependencies

### General principles

- Prefer Python's standard library and existing project dependencies where practical.
- Introduce new dependencies only when they provide a clear benefit over the existing implementation.
- Keep production and experimental dependencies separate. Do not introduce experimental dependencies into the main application unless explicitly justified.
- Avoid broad or unrelated dependency upgrades.
- Keep dependency manifests and lockfiles synchronized where applicable.
- Prefer pinned versions and reproducible dependency resolution.

### Security verification

Before introducing a new third-party dependency:

1. **Verify legitimacy:** Confirm the exact package name on its official registry (PyPI, npm, etc.). Check its publisher, repository, and maintenance status.
2. **Check vulnerabilities:** Check for known security advisories affecting the selected version using appropriate tools (e.g., `pip-audit`, `npm audit`).
3. **Evaluate necessity:** Consider whether existing dependencies or standard-library functionality could provide the same capability.
4. **Verify the source:** Prefer official package registries. Do not install packages from unverified registries, Git repositories, or arbitrary URLs.

If verification cannot be completed, explain the limitation and request user approval before installing the dependency.

### Installation and execution

- Use isolated Python virtual environments for third-party Python packages.
- Do not install Python packages globally or modify the system Python environment.
- Do not bypass sandbox restrictions to install dependencies without explicit user approval.
- Do not execute remote installation scripts (e.g., `curl ... | sh`) without explicit user approval.
- Do not disable security checks or weaken sandbox restrictions to complete an installation.
- Never inspect, expose, or transmit credentials, private keys, or API tokens during dependency installation.
- Keep dependency installation and execution within the permitted development environment.

### Validation and reporting

- Run the appropriate dependency vulnerability audit when dependencies change.
- Report any vulnerabilities or unresolved security concerns.
- Summarize newly introduced direct dependencies, their purpose, and whether they are production or experimental dependencies.
