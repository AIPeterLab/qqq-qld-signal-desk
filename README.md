# QQQ/QLD Signal Desk

Static GitHub Pages dashboard for the **volatility-gated Donchian20 QLD -> QQQ -> Cash strategy**.

The stateful Donchian20 signal comes from QLD adjusted closes. A new QLD breakout entry is allowed only when adjusted ATR(20) is at or below 4% of adjusted QLD close; the gate never forces an exit. The model holds QLD while the signal is 1, reduces to QQQ after a Donchian exit, and moves QQQ to Cash when QQQ closes below EMA200. Cash remains Cash until an eligible QLD breakout.

## Files

- `index.html` is the live operational dashboard.
- `data/signals.json` is the dashboard snapshot.
- `data/signals.csv` is the full daily model history.
- `scripts/update_signals.py` downloads adjusted market data and rebuilds the model.
- `scripts/send_ntfy_notification.py` sends the post-refresh phone alert through ntfy.
- `Real_Account_Tracking_System.doc` is the governing operating manual.

## Exact Rules

1. If signal 0 and QLD closes strictly above its prior 20-day high, allow the entry only when adjusted ATR(20) / adjusted QLD close is at or below 4%, or before 20 ATR observations exist. An entry blocked above 4% leaves the signal at 0 and follows the normal QQQ/Cash rules.
2. While signal 1, continue holding QLD.
3. If signal 1 and QLD closes strictly below its prior 20-day low, signal becomes 0 and the full account moves from QLD to QQQ.
4. If QQQ is below EMA200 while held, move the full account to Cash.
5. While signal remains 0, Cash does not re-enter merely because QQQ rises above EMA200. A new eligible QLD breakout is required.

The volatility gate is entry-only and never forces a QLD exit. There is no DCA, EMA50 filter, SMA200 rule, or EMA200-deviation filter.

## Data And Performance

The updater uses Yahoo Finance chart API adjusted closes for QQQ and QLD. For QLD True Range, raw daily highs and lows are multiplied by the daily `adjusted_close / raw_close` factor. ATR(20) uses Wilder's `ewm(alpha=1/20, adjust=False, min_periods=20)` recurrence. Model tracking starts with `$1,000` on QLD's first available date. The benchmark is QQQ Hold from the same date and initial value.

The 4% threshold originated from validation on raw closes. Production follows the repository's adjusted-data convention, so the threshold still requires dedicated revalidation on adjusted data.

The operating manual contains a saved historical research snapshot built from legacy research files that include synthetic pre-QLD history. The live dashboard does not import that inherited pre-launch signal state. It rebuilds the investable model from actual QLD history, initializes the Donchian signal at `0`, and waits for 20 completed QLD trading days before allowing the first breakout.

Run locally:

```powershell
python scripts/update_signals.py
```

## Automation

The shared AIPeterLab scheduler starts all dashboards at 6:15 PM `America/New_York` on trading weekdays. If Yahoo Finance has not yet published both QQQ and QLD for the current New York date, only QLD and its dependent dashboards retry every 15 minutes through 7:00 PM. The workflow refuses early dispatches and never writes an older market date.

Phone alerts are published to the shared `aipeterlab-market-alert-1` ntfy topic. No repository secret is required for notification delivery.

## Cloudflare Pages

This repo is ready to deploy as a no-framework Cloudflare Pages static site while keeping the dashboard method unchanged. The daily schedule is centralized in the AIPeterLab Cloudflare Worker, which dispatches this repo's GitHub Actions refresh workflow at the New York times described above.

Use these Pages settings:

- Project name: `qld-signal-desk`
- Production branch: `main`
- Framework preset: `None`
- Build command: `exit 0`
- Build output directory: `/`
- Root directory: leave blank / repository root
- Environment variables: none required

After the first Pages deployment, attach the custom domain `qld.aipeterlab.com` in the Cloudflare Pages project. The Cloudflare Worker owns the daily timing, dispatches the GitHub Actions workflow, and that workflow pushes verified `data/signals.json` and `data/signals.csv` updates to `main`; Cloudflare Pages will redeploy from GitHub after those pushes.
