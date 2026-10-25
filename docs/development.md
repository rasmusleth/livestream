# Development and pull requests

## Branches

- `main` is the integration branch. Use PRs for changes.
- `prototype/scoreboard-reader` preserves the first working prototype at commit `8a127c9`.
- `chore/repository-workflow` builds on that prototype with repository guidance and CI. Its initial PR includes the prototype because `main` started with only the project brief.
- For later work, branch from updated `main` using `feat/`, `fix/`, `docs/`, or `chore/` plus a descriptive name. These are conventions, not enforced prefixes.

Keep changes reviewable. One person or agent owns a change through implementation, validation, and a clear PR description. Use draft PRs for work that needs review before it is ready. Human review decides when to merge; this repository has no automatic merging or scheduled coding agent.

## Local checks

Install Python 3.10+, Node.js 24, and FFmpeg/ffprobe. The application has no third-party Python or npm dependencies.

```sh
python3 scripts/check.py
```

The same command runs in CI. It validates calibration coordinates, compiles Python without writing bytecode, checks JavaScript syntax, and runs tests. Missing required tools fail the check.

Tests generate a small lossless video in a temporary directory to exercise the complete FFmpeg-to-JSON pipeline. They cover clock/score changes, a blank interval, preservation of confirmed values, and recovery. The generated images and video are removed after the test. This validates pipeline behavior on controlled inputs; it is not evidence of recognition accuracy on real footage.

For extraction or calibration changes, also regenerate the available real recording:

```sh
python3 reader.py scoreboard-2-min-clip.mp4
python3 scripts/check.py
```

Five recording regression tests run when generated readings exist and are explicitly skipped otherwise. CI has no private recording or generated readings and reports these skips. For UI changes, run `python3 server.py` and manually check playback, seeking, and the extracted values. Add evidence to the PR when useful.

## CI

`.github/workflows/ci.yml` runs on PRs to `main`, pushes to `main`, and manual dispatch. It does not use path filters, so documentation-only PRs also produce the required result.

- Python checks and tests run on Ubuntu and macOS with Python 3.10 and 3.12.
- Browser JavaScript syntax is checked with Node.js 24 in every matrix job.
- A final **CI** job reports success only when all matrix jobs succeed. Use the check name `CI` for branch protection.
- New runs cancel superseded runs for the same PR/ref. Jobs have time limits and read-only repository permissions; checkout does not persist credentials.
- Actions are pinned to commit IDs. Dependabot checks those action references weekly and proposes updates through PRs.

The workflow has no deployment, video upload, secrets, generated-output commits, or automatic PR approval. Consider linting, formatting, browser automation, and additional Python versions when they address real maintenance needs rather than adding tools before they help.

## GitHub merge rules

The intended rule for `main` is: require a pull request, require the `CI` check to pass against an up-to-date base, and prevent force pushes and branch deletion. For this solo-maintainer stage, do not require another approving reviewer; the PR still provides a review point and test evidence. Add required human approvals when another maintainer joins.

Workflow files define checks; GitHub branch protection is a separate repository setting. Confirm the actual setting in GitHub before claiming that direct pushes or unchecked merges are blocked. Availability can depend on repository visibility and account plan.

## Agent work

`AGENTS.md` is the entry point for coding agents. It describes scope, correctness rules, dependencies, and verification. Keep task-specific plans in the issue or PR, and keep durable decisions in repository docs. Agent output should name checks that ran, checks that were skipped, and remaining uncertainty.
