#!/usr/bin/env python3
"""Update QQQ/QLD Signal Desk data files from free end-of-day market data."""

from __future__ import annotations

import csv
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
INITIAL_INVESTMENT = 1000.0
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1=915148800&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"


@dataclass
class Row:
    date: str
    qqq_close: float | None = None
    qld_close: float | None = None
    sma200: float | None = None
    ema50: float | None = None
    ema200: float | None = None
    distance_to_sma200_pct: float | None = None
    distance_to_ema200_pct: float | None = None
    qqq_prior_20d_high: float | None = None
    qld_prior_20d_high: float | None = None
    qld_prior_20d_low: float | None = None
    qqq_vol20_annualized_pct: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    model_state: str = "Cash"
    headline_status: str = "Hold Cash"
    action: str = "No action"
    rule_explanation: str = "Waiting for valid trend and risk conditions."
    qqq_weight: float = 0.0
    qld_weight: float = 0.0
    strategy_daily_return_pct: float | None = None
    strategy_value: float | None = None
    qqq_benchmark_value: float | None = None
    strategy_drawdown_pct: float | None = None
    qqq_drawdown_pct: float | None = None


def fetch_yahoo(symbol: str) -> dict[str, float]:
    period2 = int(time.time()) + 86400
    url = YAHOO_URL.format(symbol=symbol, period2=period2)
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not fetch {symbol} data from Yahoo Finance: {exc}") from exc

    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["adjclose"][0]["adjclose"]
    series: dict[str, float] = {}
    for stamp, close in zip(timestamps, closes):
        if close is None:
            continue
        day = datetime.fromtimestamp(stamp, tz=timezone.utc).strftime("%Y-%m-%d")
        series[day] = float(close)
    if not series:
        raise RuntimeError(f"Yahoo Finance returned no usable adjusted-close rows for {symbol}.")
    return series


def ema(values: list[float | None], span: int) -> list[float | None]:
    alpha = 2 / (span + 1)
    output: list[float | None] = []
    current: float | None = None
    seeded: list[float] = []
    for value in values:
        if value is None:
            output.append(current)
            continue
        if current is None:
            seeded.append(value)
            if len(seeded) < span:
                output.append(None)
                continue
            current = sum(seeded[-span:]) / span
        else:
            current = value * alpha + current * (1 - alpha)
        output.append(current)
    return output


def sma(values: list[float | None], window: int) -> list[float | None]:
    output: list[float | None] = []
    for index in range(len(values)):
        sample = [v for v in values[max(0, index - window + 1) : index + 1] if v is not None]
        output.append(sum(sample) / window if len(sample) == window else None)
    return output


def prior_high(values: list[float | None], window: int) -> list[float | None]:
    output: list[float | None] = []
    for index in range(len(values)):
        sample = [v for v in values[max(0, index - window) : index] if v is not None]
        output.append(max(sample) if len(sample) == window else None)
    return output


def prior_low(values: list[float | None], window: int) -> list[float | None]:
    output: list[float | None] = []
    for index in range(len(values)):
        sample = [v for v in values[max(0, index - window) : index] if v is not None]
        output.append(min(sample) if len(sample) == window else None)
    return output


def vol20(values: list[float | None]) -> list[float | None]:
    returns: list[float | None] = [None]
    for prev, current in zip(values, values[1:]):
        if prev is None or current is None or prev <= 0 or current <= 0:
            returns.append(None)
        else:
            returns.append(math.log(current / prev))

    output: list[float | None] = []
    for index in range(len(values)):
        sample = [v for v in returns[max(0, index - 19) : index + 1] if v is not None]
        output.append(statistics.stdev(sample) * math.sqrt(252) * 100 if len(sample) == 20 else None)
    return output


def pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return (numerator / denominator - 1) * 100


def is_ready(row: Row) -> bool:
    fields = [
        row.qqq_close,
        row.qld_close,
        row.ema50,
        row.ema200,
        row.qqq_prior_20d_high,
        row.qld_prior_20d_high,
        row.qld_prior_20d_low,
        row.qqq_vol20_annualized_pct,
        row.distance_to_ema200_pct,
    ]
    return all(value is not None for value in fields)


def qld_entry_ok(row: Row, reentry_after_extension: bool) -> bool:
    if not is_ready(row):
        return False
    extension_limit = 15 if reentry_after_extension else 20
    return bool(
        row.ema50 is not None
        and row.ema200 is not None
        and row.qqq_vol20_annualized_pct is not None
        and row.distance_to_ema200_pct is not None
        and row.qld_close is not None
        and row.qld_prior_20d_high is not None
        and row.ema50 > row.ema200
        and row.qqq_vol20_annualized_pct <= 25
        and row.distance_to_ema200_pct <= extension_limit
        and row.qld_close > row.qld_prior_20d_high
    )


def simulate(rows: list[Row]) -> None:
    state = "Cash"
    dca_day = 0
    reentry_after_extension = False
    last_trade_date: str | None = None

    for row in rows:
        action = "No action"
        explanation = "No action; current model state remains valid."

        if not is_ready(row):
            row.model_state = "Cash"
            row.headline_status = "Hold Cash"
            row.action = "Waiting"
            row.rule_explanation = "Waiting for enough QQQ and QLD history to calculate all indicators."
            continue

        assert row.qqq_close is not None
        assert row.qld_close is not None
        assert row.ema200 is not None
        assert row.qld_prior_20d_low is not None
        assert row.qqq_vol20_annualized_pct is not None
        assert row.distance_to_ema200_pct is not None

        exit_to_cash = (
            row.qqq_close < row.ema200
            or row.qld_close < row.qld_prior_20d_low
            or row.qqq_vol20_annualized_pct > 35
        )

        if state != "Cash" and exit_to_cash:
            state = "Cash"
            dca_day = 0
            reentry_after_extension = False
            action = "Move to Cash"
            explanation = "Risk exit triggered by EMA200, QLD 20-day low, or volatility rule."
            last_trade_date = row.date
        elif state == "Cash":
            assert row.qqq_prior_20d_high is not None
            if row.qqq_close > row.ema200 and row.qqq_close > row.qqq_prior_20d_high and row.qqq_vol20_annualized_pct < 30:
                state = "QQQ"
                action = "Buy QQQ"
                explanation = "QQQ recovered above EMA200, broke its prior 20-day high, and volatility is below 30%."
                last_trade_date = row.date
            else:
                explanation = "Hold cash until QQQ trend, breakout, and volatility conditions confirm recovery."
        elif state == "QLD":
            if row.distance_to_ema200_pct > 20:
                state = "QQQ"
                dca_day = 0
                reentry_after_extension = True
                action = "Reduce to QQQ"
                explanation = "QQQ is more than 20% above EMA200; reduce leverage but stay invested."
                last_trade_date = row.date
        elif state in {"QQQ", "QQQ + QLD"}:
            if qld_entry_ok(row, reentry_after_extension):
                dca_day += 1
                if dca_day >= 5:
                    state = "QLD"
                    reentry_after_extension = False
                    action = "Complete DCA to QLD"
                    explanation = "QLD entry conditions stayed valid through the 5-day DCA process."
                else:
                    state = "QQQ + QLD"
                    action = f"DCA day {dca_day}"
                    explanation = "QLD entry conditions are valid; continue gradual conversion from QQQ to QLD."
                last_trade_date = row.date
            else:
                if state == "QQQ + QLD":
                    action = "Reset DCA"
                    explanation = "QLD entry conditions failed during DCA; reset to QQQ."
                    last_trade_date = row.date
                else:
                    explanation = "Hold QQQ until QLD leverage-entry conditions confirm."
                state = "QQQ"
                dca_day = 0

        row.model_state = state
        row.headline_status = {
            "Cash": "Hold Cash",
            "QQQ": "Hold QQQ",
            "QQQ + QLD": "DCA to QLD",
            "QLD": "Hold QLD",
        }[state]
        row.action = action
        row.rule_explanation = explanation
        row.last_trade_date = last_trade_date  # type: ignore[attr-defined]
        if state == "QQQ":
            row.qqq_weight = 1.0
            row.qld_weight = 0.0
        elif state == "QQQ + QLD":
            row.qld_weight = dca_day / 5
            row.qqq_weight = 1 - row.qld_weight
        elif state == "QLD":
            row.qqq_weight = 0.0
            row.qld_weight = 1.0
        else:
            row.qqq_weight = 0.0
            row.qld_weight = 0.0


def calculate_performance(rows: list[Row]) -> None:
    complete_rows = [row for row in rows if row.qqq_close is not None and row.qld_close is not None]
    if not complete_rows:
        raise RuntimeError("No complete rows are available for performance calculations.")

    strategy_value = INITIAL_INVESTMENT
    benchmark_value = INITIAL_INVESTMENT
    strategy_peak = INITIAL_INVESTMENT
    benchmark_peak = INITIAL_INVESTMENT

    for index, row in enumerate(complete_rows):
        if index == 0:
            strategy_return = 0.0
        else:
            previous = complete_rows[index - 1]
            assert previous.qqq_close is not None
            assert previous.qld_close is not None
            assert row.qqq_close is not None
            assert row.qld_close is not None

            qqq_return = row.qqq_close / previous.qqq_close - 1
            qld_return = row.qld_close / previous.qld_close - 1
            strategy_return = (
                previous.qqq_weight * qqq_return
                + previous.qld_weight * qld_return
            )
            strategy_value *= 1 + strategy_return
            benchmark_value *= 1 + qqq_return

        strategy_peak = max(strategy_peak, strategy_value)
        benchmark_peak = max(benchmark_peak, benchmark_value)
        row.strategy_daily_return_pct = strategy_return * 100
        row.strategy_value = strategy_value
        row.qqq_benchmark_value = benchmark_value
        row.strategy_drawdown_pct = (strategy_value / strategy_peak - 1) * 100
        row.qqq_drawdown_pct = (benchmark_value / benchmark_peak - 1) * 100


def round_value(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    rounded = round(value, digits)
    return 0.0 if rounded == 0 else rounded


def build_rows() -> list[Row]:
    qqq = fetch_yahoo("QQQ")
    qld = fetch_yahoo("QLD")
    dates = sorted(set(qqq) | set(qld))
    rows = [Row(date=day, qqq_close=qqq.get(day), qld_close=qld.get(day)) for day in dates]

    qqq_values = [row.qqq_close for row in rows]
    qld_values = [row.qld_close for row in rows]
    sma200_values = sma(qqq_values, 200)
    ema50_values = ema(qqq_values, 50)
    ema200_values = ema(qqq_values, 200)
    ema12_values = ema(qqq_values, 12)
    ema26_values = ema(qqq_values, 26)
    macd_line = [
        fast - slow if fast is not None and slow is not None else None
        for fast, slow in zip(ema12_values, ema26_values)
    ]
    signal_line = ema(macd_line, 9)
    qqq_high20 = prior_high(qqq_values, 20)
    qld_high20 = prior_high(qld_values, 20)
    qld_low20 = prior_low(qld_values, 20)
    volatility = vol20(qqq_values)

    for index, row in enumerate(rows):
        row.sma200 = sma200_values[index]
        row.ema50 = ema50_values[index]
        row.ema200 = ema200_values[index]
        row.distance_to_sma200_pct = pct(row.qqq_close, row.sma200)
        row.distance_to_ema200_pct = pct(row.qqq_close, row.ema200)
        row.qqq_prior_20d_high = qqq_high20[index]
        row.qld_prior_20d_high = qld_high20[index]
        row.qld_prior_20d_low = qld_low20[index]
        row.qqq_vol20_annualized_pct = volatility[index]
        row.macd = macd_line[index]
        row.macd_signal = signal_line[index]
        row.macd_histogram = (
            row.macd - row.macd_signal
            if row.macd is not None and row.macd_signal is not None
            else None
        )

    simulate(rows)
    calculate_performance(rows)
    return rows


def csv_row(row: Row) -> dict[str, object]:
    return {
        "date": row.date,
        "qqq_close": round_value(row.qqq_close),
        "qld_close": round_value(row.qld_close),
        "sma200": round_value(row.sma200),
        "ema50": round_value(row.ema50),
        "ema200": round_value(row.ema200),
        "distance_to_sma200_pct": round_value(row.distance_to_sma200_pct),
        "distance_to_ema200_pct": round_value(row.distance_to_ema200_pct),
        "qqq_vol20_annualized_pct": round_value(row.qqq_vol20_annualized_pct),
        "qqq_prior_20d_high": round_value(row.qqq_prior_20d_high),
        "qld_prior_20d_high": round_value(row.qld_prior_20d_high),
        "qld_prior_20d_low": round_value(row.qld_prior_20d_low),
        "macd": round_value(row.macd),
        "macd_signal": round_value(row.macd_signal),
        "macd_histogram": round_value(row.macd_histogram),
        "model_state": row.model_state,
        "headline_status": row.headline_status,
        "action": row.action,
        "rule_explanation": row.rule_explanation,
        "qqq_weight_pct": round_value(row.qqq_weight * 100),
        "qld_weight_pct": round_value(row.qld_weight * 100),
        "strategy_daily_return_pct": round_value(row.strategy_daily_return_pct, 4),
        "strategy_value": round_value(row.strategy_value),
        "qqq_benchmark_value": round_value(row.qqq_benchmark_value),
        "strategy_drawdown_pct": round_value(row.strategy_drawdown_pct),
        "qqq_drawdown_pct": round_value(row.qqq_drawdown_pct),
    }


def latest_complete(rows: Iterable[Row]) -> Row:
    complete = [row for row in rows if row.qqq_close is not None and row.qld_close is not None]
    if not complete:
        raise RuntimeError("No complete QQQ/QLD rows are available.")
    return complete[-1]


def write_outputs(rows: list[Row]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    complete_rows = [row for row in rows if row.qqq_close is not None and row.qld_close is not None]
    latest = latest_complete(rows)
    recent = complete_rows[-45:]
    last_actions = [row for row in complete_rows if row.action not in {"No action", "Waiting"}]
    last_trade = last_actions[-1] if last_actions else None
    strategy_drawdowns = [
        row.strategy_drawdown_pct
        for row in complete_rows
        if row.strategy_drawdown_pct is not None
    ]
    benchmark_drawdowns = [
        row.qqq_drawdown_pct
        for row in complete_rows
        if row.qqq_drawdown_pct is not None
    ]

    csv_path = DATA_DIR / "signals.csv"
    fieldnames = list(csv_row(latest).keys())
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in complete_rows:
            writer.writerow(csv_row(row))

    macd_status = "Neutral"
    if latest.macd is not None and latest.macd_signal is not None:
        if latest.macd > latest.macd_signal and latest.macd_histogram and latest.macd_histogram > 0:
            macd_status = "Bullish"
        elif latest.macd < latest.macd_signal and latest.macd_histogram and latest.macd_histogram < 0:
            macd_status = "Bearish"

    payload = {
        "project": "QQQ/QLD Signal Desk",
        "last_updated": latest.date,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": "Yahoo Finance chart API adjusted close",
        "current": {
            "model_state": latest.model_state,
            "headline_status": latest.headline_status,
            "rule_explanation": latest.rule_explanation,
            "last_trade_date": last_trade.date if last_trade else None,
            "last_trade_action": last_trade.action if last_trade else None,
        },
        "market": {
            "qqq_close": round_value(latest.qqq_close),
            "qld_close": round_value(latest.qld_close),
            "sma200": round_value(latest.sma200),
            "ema50": round_value(latest.ema50),
            "ema200": round_value(latest.ema200),
            "distance_to_sma200_pct": round_value(latest.distance_to_sma200_pct),
            "distance_to_ema200_pct": round_value(latest.distance_to_ema200_pct),
            "qqq_prior_20d_high": round_value(latest.qqq_prior_20d_high),
            "qld_prior_20d_high": round_value(latest.qld_prior_20d_high),
            "qld_prior_20d_low": round_value(latest.qld_prior_20d_low),
            "qqq_vol20_annualized_pct": round_value(latest.qqq_vol20_annualized_pct),
        },
        "macd_context": {
            "macd": round_value(latest.macd),
            "signal": round_value(latest.macd_signal),
            "histogram": round_value(latest.macd_histogram),
            "status": macd_status,
            "rule_role": "Display-only context; not part of the trading rule.",
        },
        "bands": {
            "trend_status": "Above SMA200"
            if latest.distance_to_sma200_pct is not None and latest.distance_to_sma200_pct >= 0
            else "Below SMA200",
            "ema_status": "EMA50 above EMA200"
            if latest.ema50 is not None and latest.ema200 is not None and latest.ema50 >= latest.ema200
            else "EMA50 below EMA200",
            "risk_status": "Extended"
            if latest.distance_to_ema200_pct is not None and latest.distance_to_ema200_pct > 20
            else "Exit risk"
            if latest.qqq_vol20_annualized_pct is not None and latest.qqq_vol20_annualized_pct > 35
            else "Normal",
        },
        "performance": {
            "tracking_start_date": complete_rows[0].date,
            "initial_investment": INITIAL_INVESTMENT,
            "strategy_value": round_value(latest.strategy_value),
            "qqq_buy_hold_value": round_value(latest.qqq_benchmark_value),
            "strategy_max_drawdown_pct": round_value(min(strategy_drawdowns)),
            "qqq_max_drawdown_pct": round_value(min(benchmark_drawdowns)),
            "current_strategy_drawdown_pct": round_value(latest.strategy_drawdown_pct),
            "current_qqq_drawdown_pct": round_value(latest.qqq_drawdown_pct),
        },
        "recent_history": [csv_row(row) for row in recent],
    }

    json_path = DATA_DIR / "signals.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    try:
        rows = build_rows()
        write_outputs(rows)
    except Exception as exc:
        print(f"update_signals failed: {exc}", file=sys.stderr)
        return 1
    print("Updated data/signals.json and data/signals.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
