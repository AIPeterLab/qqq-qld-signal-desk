# Codex Command File: QQQ/QLD Signal Desk

## Project

- Name: QQQ/QLD Signal Desk
- Repository: `AIPeterLab/qqq-qld-signal-desk`
- Public page: `https://aipeterlab.github.io/qqq-qld-signal-desk/`
- Strategy: `Donchian20 QLD -> QQQ -> Cash exit strategy`
- Benchmark: `QQQ Hold`

## Governing Rulebook

Use `Real_Account_Tracking_System.doc` as the source of truth.

Do not add DCA, volatility, EMA50, SMA200, or EMA200-deviation rules.

## Required State Machine

1. Signal starts at 0.
2. Signal 0 changes to 1 only when QLD adjusted close is strictly above the prior 20-day QLD high.
3. Signal 1 changes to 0 only when QLD adjusted close is strictly below the prior 20-day QLD low.
4. Signal 1 requires a full QLD position.
5. A QLD Donchian exit moves the full account to QQQ.
6. QQQ below EMA200 moves the full account to Cash.
7. Cash remains Cash while signal is 0, even if QQQ rises above EMA200.
8. A new signal-1 QLD breakout moves QQQ or Cash fully into QLD.

## Daily Outputs

`data/signals.csv` must include:

- Date and adjusted closes
- QQQ EMA200 and distance
- Prior 20-day QLD high and low
- Prior and current Donchian signals
- Ending model state
- Required action and trade reason
- Cash, QQQ, and QLD values
- Strategy and QQQ benchmark values
- Strategy and benchmark drawdowns

`data/signals.json` must include:

- Latest status and action
- Latest Donchian and EMA metrics
- Performance summary
- Recent transitions
- Recent daily history

## Automation

- Run at 6:15 PM New York time through GitHub Actions.
- Commit refreshed JSON and CSV.
- Send a Pushover notification after a successful refresh.
