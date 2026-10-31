# Development and pull requests

## Branches

- `main` is the integration branch. Use PRs for changes.
- `prototype/scoreboard-reader` preserves the first working prototype at commit `8a127c9`.
- `chore/repository-workflow` builds on that prototype with repository guidance and CI. Its initial PR includes the prototype because `main` started with only the project brief.
- For later work, branch from updated `main` using `feat/`, `fix/`, `docs/`, or `chore/` plus a descriptive name. These are conventions, not enforced prefixes.

Keep changes reviewable. One person or agent owns a change through implementation, validation, and a clear PR description. After a completed, validated coding task with a meaningful change, push the feature branch and open or update a draft PR by default, unless the user asks to keep it local. The user has authorized this workflow; merging, releases, deployments, and repository access changes still require separate authorization. Human review decides when to merge; this repository has no automatic merging or scheduled coding agent.

## Local checks

The initial development target is macOS with Python 3.12. CI uses the `macos-26` runner. Install Python 3.12, Node.js 24, and FFmpeg/ffprobe. Other operating systems and Python versions are outside the current support scope. The application has no third-party Python or npm dependencies.

```sh
python3 scripts/check.py
```

The same command runs in CI. It validates calibration coordinates, compiles Python without writing bytecode, checks JavaScript syntax, and runs tests. Missing required tools fail the check. HTTP transport tests bind a temporary loopback port, so the check requires permission to use local sockets.

Tests generate a small lossless video in a temporary directory to exercise the complete FFmpeg-to-JSON pipeline. They cover clock/score changes, a blank interval, preservation of confirmed values, and recovery. The generated images and video are removed after the test. This validates pipeline behavior on controlled inputs; it is not evidence of recognition accuracy on real footage.

For extraction or calibration changes, also regenerate the available real recording:

```sh
python3 reader.py scoreboard-2-min-clip.mp4
python3 scripts/check.py
```

Five recording regression tests run when generated readings exist and are explicitly skipped otherwise. CI has no private recording or generated readings and reports these skips. For UI changes, run `python3 server.py` and manually check playback, seeking, and the extracted values. For overlay changes, also check the separate overlay page while seeking, pausing, stopping replay output, and recovering the connection. Add evidence to the PR when useful.

## CI

`.github/workflows/ci.yml` runs on PRs to any branch (including stacked PRs), pushes to `main`, and manual dispatch. It does not use path filters, so documentation-only PRs also produce the required result.

- One **CI** job runs Python checks and tests on macOS 26 with Python 3.12, plus JavaScript syntax checks with Node.js 24. Use the check name `CI` for branch protection.
- New runs cancel superseded runs for the same PR/ref. Jobs have time limits and read-only repository permissions; checkout does not persist credentials.
- Actions are pinned to commit IDs. Dependabot checks those action references weekly and proposes updates through PRs.

The workflow has no deployment, video upload, secrets, generated-output commits, or automatic PR approval. Consider linting, formatting, browser automation, and additional Python versions when they address real maintenance needs rather than adding tools before they help.

## GitHub merge rules

The intended rule for `main` is: require a pull request, require the `CI` check to pass against an up-to-date base, and prevent force pushes and branch deletion. For this solo-maintainer stage, do not require another approving reviewer; the PR still provides a review point and test evidence. Add required human approvals when another maintainer joins.

Workflow files define checks; GitHub branch protection is a separate repository setting. Confirm the actual setting in GitHub before claiming that direct pushes or unchecked merges are blocked. Availability can depend on repository visibility and account plan.

## Agent work

`AGENTS.md` is the entry point for coding agents. It describes scope, correctness rules, dependencies, and verification. Keep task-specific plans in the issue or PR, and keep durable decisions in repository docs. Agent output should name checks that ran, checks that were skipped, and remaining uncertainty.

## Publish this setup manually

The workflow branch is intentionally local at handoff. The prototype checkpoint is already backed up on GitHub. No pull request or branch protection has been created by this setup task, and hosted CI has not been run yet.

The GitHub CLI login already has `workflow` permission. The initial HTTPS push used a different stored Git credential, which lacked that permission. To configure Git to use the CLI login and publish this branch yourself:

```sh
cd /Users/rasmuswleth/repos/livestream
git switch chore/repository-workflow
gh auth setup-git --hostname github.com
git push -u origin chore/repository-workflow
```

`gh auth setup-git` changes Git's credential helper configuration for GitHub to use the existing CLI login. See the [GitHub CLI documentation](https://cli.github.com/manual/gh_auth_setup-git).

Then:

1. Open a PR with base `main` and compare branch `chore/repository-workflow`. The PR includes the prototype and workflow setup; keep it as a draft while reviewing.
2. Wait for the `CI` check to pass. Resolve failures before treating the hosted workflow as verified.
3. In repository **Settings → Branches**, add a classic branch protection rule for `main`.
4. Require a pull request and the `CI` status check, and require the branch to be up to date. Leave required approving reviews disabled while you are the only maintainer. Keep force pushes and deletion disabled; apply the rule to administrators too if you want the same workflow for your own changes.
5. Review the diff and merge when you are ready. After merge, the main-branch workflow will run again and Dependabot can discover the configuration on the default branch.

GitHub's [branch protection documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule) describes these settings. Branch rules remain a separate manual step; merely committing the CI YAML does not enforce them.
