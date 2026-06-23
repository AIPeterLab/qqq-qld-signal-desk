# Codex Command File: QQQ/QLD Signal Desk

## Operating Boundary

Do not run the build, create the GitHub repository, push code, enable GitHub Pages, or schedule automation until the user explicitly says to proceed.

This file is the full build instruction/specification for the project. Use it as the source of truth when the user approves execution.

## Project Identity

- Project name: QQQ/QLD Signal Desk
- GitHub account: AIPeterLab
- GitHub repo name: qqq-qld-signal-desk
- Intended public repo URL: https://github.com/AIPeterLab/qqq-qld-signal-desk
- Intended GitHub Pages URL: https://aipeterlab.github.io/qqq-qld-signal-desk/

The name matters because the signal source is QQQ, while the strategy can hold Cash, QQQ, QQQ + QLD during transition, or QLD.

## Deliverables

Create a simple static GitHub Pages dashboard with:

- `index.html`
- `data/signals.json`
- `data/signals.csv`
- `scripts/update_signals.py`
- `.github/workflows/daily-update.yml`
- `Real_Account_Tracking_System.doc`
- `README.md`

The Word-readable file is the operating manual. The GitHub Pages site is the live display. The CSV/JSON files are the daily calculated indicator records.

## Source Rulebook

Use the existing QQQ rulebook as the rule reference:

- Source file: `C:\Users\Ella\Documents\QQQbacktest\Real_Account_Tracking_System.doc`
- Main strategy: `QLD / QQQ / Cash with 5-Day DCA from QQQ to QLD`
- Benchmark: `QQQ Hold`
- Cash is a normal model state, not a failure state.

Do not simplify the strategy into only "QLD or Cash." The dashboard should show the actual model state.

## Model States

The dashboard must support these real model states:

- `Cash`
- `QQQ`
- `QQQ + QLD`
- `QLD`

Also show a plain-English headline:

- Cash: `Hold Cash`
- QQQ: `Hold QQQ`
- QQQ + QLD: `DCA to QLD`
- QLD: `Hold QLD`

## Strategy Rules

### Cash to QQQ

When the model is in Cash, buy QQQ when all conditions are true:

- QQQ price is above EMA200.
- QQQ closes above its prior 20-day high.
- QQQ 20-day annualized volatility is below 30%.

### QQQ to QLD: 5-Day DCA

When the model is already in QQQ, begin converting QQQ into QLD when all conditions are true:

- QQQ EMA50 is above QQQ EMA200.
- QQQ 20-day annualized volatility is less than or equal to 25%.
- QQQ EMA200 deviation is less than or equal to 20%.
- QLD closes above its prior 20-day high.

Use this DCA schedule:

- Day 1: Convert 1/5 of remaining QQQ value into QLD.
- Day 2: Convert 1/4 of remaining QQQ value into QLD.
- Day 3: Convert 1/3 of remaining QQQ value into QLD.
- Day 4: Convert 1/2 of remaining QQQ value into QLD.
- Day 5: Convert all remaining QQQ value into QLD.

If QLD entry conditions fail during DCA, reset the DCA counter. If any exit rule triggers, stop DCA and move to Cash.

### QLD to QQQ: Reduce Leverage

When QQQ is too extended above EMA200, reduce from QLD to QQQ:

- QQQ EMA200 deviation is greater than 20%.

This is not a full exit. It reduces from 2x exposure to 1x exposure.

### QQQ to QLD Again

After reducing from QLD to QQQ, use the 5-day DCA back into QLD when all conditions are true:

- QQQ EMA200 deviation is less than 15%.
- QLD closes above its prior 20-day high.
- QLD entry conditions remain valid.

### Any Position to Cash

Move to Cash if any one of these risk exit rules is true:

- QQQ closes below EMA200.
- QLD closes below its prior 20-day low.
- QQQ 20-day annualized volatility is greater than 35%.

## Indicators to Calculate

Calculate and display:

- Last update date
- QQQ adjusted close
- QLD adjusted close
- QQQ SMA200
- QQQ EMA50
- QQQ EMA200
- QQQ distance above/below SMA200
- QQQ distance above/below EMA200
- QQQ prior 20-day high
- QLD prior 20-day high
- QLD prior 20-day low
- QQQ 20-day annualized volatility
- MACD, MACD signal, and MACD histogram as display-only context
- Current model state
- Plain-English current status
- Buy/sell/risk band status
- Current rule explanation in one short line
- Recent signal history
- Last trade date

MACD is not part of the trading rule unless the user later changes the rule. Label it clearly as display-only context.

## Data Source

Use free end-of-day market data suitable for GitHub Actions. Preferred source:

- Yahoo Finance chart API with adjusted close values.

Use QQQ as the primary signal source and QLD for leveraged holding/entry and exit checks.

Do not use synthetic QLD history for live dashboard decisions. Live dashboard should use real QQQ and QLD market data.

## Daily Update Timing

Update every day at 6:00 PM New York time.

GitHub Actions schedules use UTC. For the first version, use:

```yaml
on:
  schedule:
    - cron: "0 22 * * *"
  workflow_dispatch:
```

This equals 6:00 PM New York during daylight saving time. Add a README note that UTC scheduling does not automatically track New York daylight saving changes unless the workflow is adjusted or the script handles time-zone logic.

## Dashboard Design

Build a simple, readable static dashboard. Do not make a marketing landing page.

First screen should show:

- Current status headline
- Model state
- Last update date
- One-line rule explanation
- QQQ close
- SMA200
- Distance above/below SMA200
- EMA50 / EMA200
- MACD status as context
- Buy/sell/risk band status
- Last trade date

Below the first screen, show:

- Recent signal history table
- Indicator table
- Rule checklist
- Data freshness note

Use restrained, financial-dashboard styling. Keep it fast and legible.

## JSON Shape

Write `data/signals.json` with this structure:

```json
{
  "project": "QQQ/QLD Signal Desk",
  "last_updated": "YYYY-MM-DD",
  "data_source": "Yahoo Finance chart API adjusted close",
  "current": {
    "model_state": "Cash | QQQ | QQQ + QLD | QLD",
    "headline_status": "Hold Cash | Hold QQQ | DCA to QLD | Hold QLD",
    "rule_explanation": "Short plain-English explanation",
    "last_trade_date": "YYYY-MM-DD or null",
    "last_trade_action": "string or null"
  },
  "market": {
    "qqq_close": 0,
    "qld_close": 0,
    "sma200": 0,
    "ema50": 0,
    "ema200": 0,
    "distance_to_sma200_pct": 0,
    "distance_to_ema200_pct": 0,
    "qqq_prior_20d_high": 0,
    "qld_prior_20d_high": 0,
    "qld_prior_20d_low": 0,
    "qqq_vol20_annualized_pct": 0
  },
  "macd_context": {
    "macd": 0,
    "signal": 0,
    "histogram": 0,
    "status": "Bullish | Bearish | Neutral"
  },
  "bands": {
    "trend_status": "Above SMA200 | Below SMA200",
    "ema_status": "EMA50 above EMA200 | EMA50 below EMA200",
    "risk_status": "Normal | Extended | Exit risk"
  },
  "recent_history": []
}
```

## CSV Columns

Write `data/signals.csv` with at least these columns:

- `date`
- `qqq_close`
- `qld_close`
- `sma200`
- `ema50`
- `ema200`
- `distance_to_sma200_pct`
- `distance_to_ema200_pct`
- `qqq_vol20_annualized_pct`
- `qqq_prior_20d_high`
- `qld_prior_20d_high`
- `qld_prior_20d_low`
- `macd`
- `macd_signal`
- `macd_histogram`
- `model_state`
- `headline_status`
- `action`
- `rule_explanation`

## Word Operating Manual

Create `Real_Account_Tracking_System.doc` as a Word-openable HTML `.doc` file.

It should explain:

- Strategy purpose
- Data source
- Daily update timing
- Model states
- Exact rules
- What each indicator means
- How to interpret dashboard status
- What to do when the model says Cash, QQQ, QQQ + QLD, or QLD
- MACD is display-only unless promoted to a rule later
- Manual trade log discipline
- Weekly and monthly review checklists

Use the existing QQQbacktest rulebook as the format and rule reference, but write this as the operating manual for the `QQQ/QLD Signal Desk` dashboard.

## GitHub Pages Setup

When the user approves execution:

1. Initialize the local repo if needed.
2. Create or connect remote repo `AIPeterLab/qqq-qld-signal-desk`.
3. Commit the static dashboard, data files, script, workflow, manual, and README.
4. Push to `main`.
5. Enable GitHub Pages from the repo root or from the selected Pages source.
6. Verify the live page URL.

If Pages is configured for root, `index.html` should be at repo root. If Pages is configured for `/docs`, move the static site into `docs/` and update the README. Prefer repo root for this simple project unless GitHub account settings require `/docs`.

## Verification Before Completion

After build approval and implementation, verify:

- `scripts/update_signals.py` runs successfully.
- `data/signals.json` is valid JSON.
- `data/signals.csv` opens as a CSV.
- `index.html` renders locally.
- Dashboard shows the latest calculated model state.
- MACD is clearly labeled as display-only.
- GitHub Action can be manually triggered.
- GitHub Pages URL loads after publishing.

## Important Constraints

- Preserve QQQ as the signal source.
- Preserve QLD as the leveraged ETF holding.
- Preserve Cash as a normal state.
- Preserve QQQ Hold as benchmark language in documentation.
- Do not treat this as a simple QQQ SMA200-only QLD/Cash dashboard.
- Do not use synthetic history for the live signal.
- Do not execute build/publish steps until the user explicitly approves.
