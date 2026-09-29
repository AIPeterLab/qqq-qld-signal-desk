# Codex Project Instructions

This repository is the durable source of truth for the QQQ/QLD Signal Desk. Do not rely on prior chat history or account-specific Codex settings.

## Read First

- Read `README.md` for the project overview, deployment, and automation.
- Read `CODEX_COMMAND.md` for the exact state machine and required outputs.
- Treat `Real_Account_Tracking_System.doc` as the governing operating manual. When its historical research snapshot differs from the live implementation, follow the live-data distinction documented in `README.md`.
- Read `MIGRATION_HANDOFF.md` for recovery and current operational context.

## Guardrails

- Preserve the Donchian20 QLD -> QQQ -> Cash rules and the production entry-only QLD volatility gate exactly. Do not introduce DCA, EMA50, SMA200, EMA200-deviation, or any additional volatility rules.
- A new QLD entry is blocked only when adjusted ATR(20) / adjusted QLD close is strictly greater than 4%. The gate is inactive until 20 ATR observations exist and never forces an exit.
- Use adjusted closes for QQQ and QLD. A breakout or exit is strict (`>` or `<`) and compares with the prior completed 20-day window.
- Cash cannot re-enter QQQ merely because QQQ rises above EMA200; only a new QLD breakout returns the model to QLD.
- Do not weaken the current-date and no-older-data safety checks in `scripts/update_signals.py`.
- Treat `data/signals.csv` and `data/signals.json` as generated, tracked production outputs. Do not hand-edit them.
- Never commit `.wrangler/`, Python caches, environment files, credentials, tokens, or secret values. The ntfy notification uses the shared public topic documented in `README.md` and requires no repository secret.
- Preserve unrelated local changes. Never force-push this repository.

## Verification

Run the local unit tests after strategy or updater changes:

```powershell
python -m unittest discover -s tests -v
```

The updater uses only the Python standard library and requires network access to Yahoo Finance:

```powershell
python scripts/update_signals.py
```

Use `--expected-market-date YYYY-MM-DD` when reproducing the production freshness gate. Running the updater can change the tracked data outputs, so inspect its diff before committing.

The production refresh is normally dispatched by the shared AIPeterLab Cloudflare Worker. The GitHub Actions workflow performs its own New York-time and market-date checks.
