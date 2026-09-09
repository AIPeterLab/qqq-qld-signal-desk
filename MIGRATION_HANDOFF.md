# Migration Handoff

This file makes the QQQ/QLD Signal Desk recoverable without Personal ChatGPT history or account-specific Codex configuration. It records only durable context not already covered by the repository documentation.

## Purpose and Current Status

The project publishes a static operational dashboard for the Donchian20 QLD -> QQQ -> Cash strategy. The production branch is `main`; GitHub Actions refreshes the tracked signal data, and Cloudflare Pages can redeploy the static site from GitHub.

The strategy, live-data assumptions, project files, automation, and Cloudflare Pages settings are documented in `README.md`. The exact state machine and output contract are in `CODEX_COMMAND.md`. `Real_Account_Tracking_System.doc` remains the governing operating manual. Tests in `tests/test_strategy.py` cover the transition order, Cash re-entry rule, and refresh-date safety checks.

## Project Structure

- `index.html`: static dashboard application.
- `data/signals.csv`: complete generated daily model history.
- `data/signals.json`: generated dashboard snapshot.
- `scripts/update_signals.py`: Yahoo Finance download, indicator/state simulation, validation, and output generation.
- `scripts/send_pushover_notification.py`: optional production notification.
- `.github/workflows/daily-update.yml`: guarded, manually dispatched production refresh workflow.
- `tests/test_strategy.py`: standard-library unit tests.
- `README.md`, `CODEX_COMMAND.md`, `AGENTS.md`: durable project and Codex instructions.

## Design and Operational Decisions

- The live model begins with actual QLD history, signal `0`, and no inherited synthetic pre-launch state. The operating manual's legacy research snapshot is retained for reference but is not imported into the live dashboard.
- Generated data is committed because the static dashboard consumes it directly.
- Production scheduling is centralized in a shared AIPeterLab Cloudflare Worker. The repository workflow is `workflow_dispatch`-based and independently rejects early, duplicate, stale, or older-market-date refreshes.
- Cloudflare Pages is a no-framework static deployment with repository root as output. The expected project name is `qld-signal-desk`, production branch `main`, and custom domain `qld.aipeterlab.com`.

## Recreate and Verify

Requirements are Git, internet access, and Python 3.12 or newer. Runtime and test code use only the Python standard library; there is no package installation step or database.

```powershell
git clone https://github.com/AIPeterLab/qqq-qld-signal-desk.git
cd qqq-qld-signal-desk
python -m unittest discover -s tests -v
```

To regenerate current data (this changes tracked output files):

```powershell
python scripts/update_signals.py
```

External dependencies and services:

- Yahoo Finance chart API: public market-data source used by the updater.
- GitHub repository and GitHub Actions: source backup and production refresh execution.
- Cloudflare Worker and Cloudflare Pages: scheduler and static hosting; their account-side configuration is not stored in this repository.
- Pushover: optional notification service using GitHub secret names `PUSHOVER_APP_TOKEN` and `PUSHOVER_USER_KEY`.

No secret values belong in the repository. A replacement GitHub/Business account must be granted repository access and, if it will administer operations, appropriate GitHub, Cloudflare, and Pushover access. Repository secrets and Cloudflare configuration should be verified separately after any account or organization change.

## Unfinished Work and Known Risks

- There is no known unfinished code change at the time of this handoff.
- The shared Cloudflare scheduler and Cloudflare Pages project are external account-side resources; cloning the repository does not recreate them.
- GitHub Actions secret values cannot be recovered from Git. If the repository is transferred or recreated, re-enter the two Pushover secrets.
- A local untracked directory named `Project holder1` is an unrelated IRA/Roth planning workspace, not part of the QQQ/QLD Signal Desk. It is deliberately neither ignored nor committed here. Five of its seven top-level files exactly match files in `C:\Users\Ella\Documents\401k Allocation`; its newer `build_roth_guide.py` and `Roth guide.docx` differ from that separate folder and need a separate backup before the Personal ChatGPT account is retired.

## Next Steps for a Fresh Codex Session

1. Read `AGENTS.md`, then the linked documentation.
2. Confirm `git status --short --branch` and `git remote -v` before editing.
3. Run the unit tests.
4. Verify GitHub Actions, Cloudflare scheduling/deployment, the custom domain, and Pushover delivery if operational continuity is required.
5. Preserve the state-machine rules and freshness safeguards when making changes.
