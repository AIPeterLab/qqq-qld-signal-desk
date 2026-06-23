# QQQ/QLD Signal Desk

Static GitHub Pages dashboard for the QQQ-signal / QLD-position strategy.

The signal source is QQQ. The model can hold Cash, QQQ, QQQ + QLD during the 5-day transition, or QLD. MACD appears as display-only context and is not part of the trading rule.

## Files

- `index.html` is the live dashboard.
- `data/signals.json` is the dashboard data source.
- `data/signals.csv` is the daily signal history.
- `scripts/update_signals.py` refreshes market data and indicators.
- `Real_Account_Tracking_System.doc` is the operating manual.

## Update Schedule

The GitHub Action runs at `0 22 * * *`, which is 6:00 PM New York during daylight saving time. GitHub Actions schedules are UTC, so the clock-time equivalent changes when New York leaves daylight saving time.

## Data Source

The updater uses free Yahoo Finance chart API adjusted-close data for QQQ and QLD.

## Local Update

```powershell
python scripts/update_signals.py
```

The script writes `data/signals.json` and `data/signals.csv`.

## Strategy Summary

Cash to QQQ requires QQQ above EMA200, QQQ above its prior 20-day high, and QQQ 20-day annualized volatility below 30%.

QQQ to QLD uses a 5-day DCA process when EMA50 is above EMA200, QQQ volatility is at or below 25%, QQQ is no more than 20% above EMA200, and QLD closes above its prior 20-day high.

Any invested state moves to Cash if QQQ closes below EMA200, QLD closes below its prior 20-day low, or QQQ 20-day annualized volatility is above 35%.

When QQQ is more than 20% above EMA200, the model reduces from QLD to QQQ. It can DCA back into QLD after QQQ EMA200 deviation drops below 15% and QLD entry conditions remain valid.
