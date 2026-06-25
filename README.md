# QQQ/QLD Signal Desk

Static GitHub Pages dashboard for the **Donchian20 QLD -> QQQ -> Cash exit strategy**.

The stateful Donchian20 signal comes from QLD adjusted closes. The model holds QLD while the signal is 1, reduces to QQQ after a Donchian exit, and moves QQQ to Cash when QQQ closes below EMA200. Cash remains Cash until QLD creates a new Donchian breakout.

## Files

- `index.html` is the live operational dashboard.
- `data/signals.json` is the dashboard snapshot.
- `data/signals.csv` is the full daily model history.
- `scripts/update_signals.py` downloads adjusted closes and rebuilds the model.
- `scripts/send_pushover_notification.py` sends the post-refresh phone alert.
- `Real_Account_Tracking_System.doc` is the governing operating manual.

## Exact Rules

1. If signal 0 and QLD closes strictly above its prior 20-day high, signal becomes 1 and the full account moves to QLD.
2. While signal 1, continue holding QLD.
3. If signal 1 and QLD closes strictly below its prior 20-day low, signal becomes 0 and the full account moves from QLD to QQQ.
4. If QQQ is below EMA200 while held, move the full account to Cash.
5. While signal remains 0, Cash does not re-enter merely because QQQ rises above EMA200. A new QLD breakout is required.

There is no DCA, volatility filter, EMA50 filter, SMA200 rule, or EMA200-deviation filter.

## Data And Performance

The updater uses Yahoo Finance chart API adjusted-close data for QQQ and QLD. Model tracking starts with `$1,000` on QLD's first available date. The benchmark is QQQ Hold from the same date and initial value.

The operating manual contains a saved historical research snapshot built from legacy research files that include synthetic pre-QLD history. The live dashboard does not import that inherited pre-launch signal state. It rebuilds the investable model from actual QLD history, initializes the Donchian signal at `0`, and waits for 20 completed QLD trading days before allowing the first breakout.

Run locally:

```powershell
python scripts/update_signals.py
```

## Automation

GitHub Actions checks at 22:15 and 23:15 UTC and updates only when the New York hour is 6 PM, maintaining an effective 6:15 PM New York schedule through daylight-saving changes.

Pushover uses these repository secrets:

- `PUSHOVER_APP_TOKEN`
- `PUSHOVER_USER_KEY`
