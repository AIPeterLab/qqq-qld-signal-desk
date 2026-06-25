#!/usr/bin/env python3
"""Refresh the Donchian20 QLD -> QQQ -> Cash Signal Desk."""

from __future__ import annotations

import csv
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
INITIAL_INVESTMENT = 1000.0
YAHOO_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1=915148800&period2={period2}&interval=1d"
    "&events=history&includeAdjustedClose=true"
)


@dataclass
class Row:
    date: str
    qqq_close: float | None = None
    qld_close: float | None = None
    ema200: float | None = None
    distance_to_ema200_pct: float | None = None
    qld_prior_20d_high: float | None = None
    qld_prior_20d_low: float | None = None
    qld_channel_position_pct: float | None = None
    prior_signal: int = 0
    donchian_signal: int = 0
    model_state: str = "Cash"
    headline_status: str = "Hold Cash"
    action: str = "Waiting"
    trade_reason: str = ""
    rule_explanation: str = "Waiting for enough QLD history to calculate the Donchian20 channel."
    cash_value: float = INITIAL_INVESTMENT
    qqq_value: float = 0.0
    qld_value: float = 0.0
    strategy_value: float = INITIAL_INVESTMENT
    qqq_benchmark_value: float = INITIAL_INVESTMENT
    strategy_drawdown_pct: float = 0.0
    qqq_drawdown_pct: float = 0.0


def fetch_yahoo(symbol: str) -> dict[str, float]:
    period2 = int(time.time()) + 86400
    request = Request(
        YAHOO_URL.format(symbol=symbol, period2=period2),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not fetch {symbol} from Yahoo Finance: {exc}") from exc

    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    adjusted = result["indicators"]["adjclose"][0]["adjclose"]
    series: dict[str, float] = {}
    for stamp, close in zip(timestamps, adjusted):
        if close is None:
            continue
        day = datetime.fromtimestamp(stamp, tz=timezone.utc).strftime("%Y-%m-%d")
        series[day] = float(close)
    if not series:
        raise RuntimeError(f"Yahoo Finance returned no adjusted-close data for {symbol}.")
    return series


def ema(values: list[float | None], span: int) -> list[float | None]:
    alpha = 2 / (span + 1)
    output: list[float | None] = []
    seed: list[float] = []
    current: float | None = None
    for value in values:
        if value is None:
            output.append(None)
            continue
        if current is None:
            seed.append(value)
            if len(seed) < span:
                output.append(None)
                continue
            current = sum(seed[-span:]) / span
        else:
            current = value * alpha + current * (1 - alpha)
        output.append(current)
    return output


def prior_extreme(
    values: list[float | None], window: int, use_maximum: bool
) -> list[float | None]:
    output: list[float | None] = []
    for index in range(len(values)):
        sample = [value for value in values[max(0, index - window) : index] if value is not None]
        if len(sample) != window:
            output.append(None)
        else:
            output.append(max(sample) if use_maximum else min(sample))
    return output


def pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return (numerator / denominator - 1) * 100


def round_value(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    rounded = round(value, digits)
    return 0.0 if rounded == 0 else rounded


def calculate_indicators(rows: list[Row]) -> None:
    qqq_values = [row.qqq_close for row in rows]
    qld_values = [row.qld_close for row in rows]
    ema200_values = ema(qqq_values, 200)
    qld_highs = prior_extreme(qld_values, 20, True)
    qld_lows = prior_extreme(qld_values, 20, False)

    for index, row in enumerate(rows):
        row.ema200 = ema200_values[index]
        row.distance_to_ema200_pct = pct(row.qqq_close, row.ema200)
        row.qld_prior_20d_high = qld_highs[index]
        row.qld_prior_20d_low = qld_lows[index]
        if (
            row.qld_close is not None
            and row.qld_prior_20d_high is not None
            and row.qld_prior_20d_low is not None
            and row.qld_prior_20d_high != row.qld_prior_20d_low
        ):
            row.qld_channel_position_pct = (
                (row.qld_close - row.qld_prior_20d_low)
                / (row.qld_prior_20d_high - row.qld_prior_20d_low)
                * 100
            )


def simulate(rows: list[Row]) -> None:
    complete = [row for row in rows if row.qqq_close is not None and row.qld_close is not None]
    if not complete:
        raise RuntimeError("No common QQQ/QLD adjusted-close rows are available.")

    cash = INITIAL_INVESTMENT
    qqq_shares = 0.0
    qld_shares = 0.0
    position = "Cash"
    signal = 0
    strategy_peak = INITIAL_INVESTMENT
    benchmark_peak = INITIAL_INVESTMENT
    benchmark_shares = INITIAL_INVESTMENT / complete[0].qqq_close

    for row in complete:
        assert row.qqq_close is not None
        assert row.qld_close is not None
        row.prior_signal = signal
        channel_ready = (
            row.qld_prior_20d_high is not None
            and row.qld_prior_20d_low is not None
        )

        if channel_ready:
            if signal == 0 and row.qld_close > row.qld_prior_20d_high:
                signal = 1
            elif signal == 1 and row.qld_close < row.qld_prior_20d_low:
                signal = 0
        row.donchian_signal = signal

        action_parts: list[str] = []
        reason_parts: list[str] = []

        def account_value() -> float:
            return cash + qqq_shares * row.qqq_close + qld_shares * row.qld_close

        if signal == 1 and position != "QLD":
            value = account_value()
            cash = 0.0
            qqq_shares = 0.0
            qld_shares = value / row.qld_close
            position = "QLD"
            action_parts.append("Buy QLD")
            reason_parts.append("toQLD")
        elif signal == 0 and position == "QLD":
            value = account_value()
            cash = 0.0
            qld_shares = 0.0
            qqq_shares = value / row.qqq_close
            position = "QQQ"
            action_parts.append("Reduce QLD to QQQ")
            reason_parts.append("QLD->QQQ_on_Donchian_exit")

        if (
            position == "QQQ"
            and row.ema200 is not None
            and row.qqq_close < row.ema200
        ):
            cash = account_value()
            qqq_shares = 0.0
            qld_shares = 0.0
            position = "Cash"
            action_parts.append("Sell QQQ to Cash")
            reason_parts.append("QQQ->Cash_below_EMA200")

        strategy_value = account_value()
        benchmark_value = benchmark_shares * row.qqq_close
        strategy_peak = max(strategy_peak, strategy_value)
        benchmark_peak = max(benchmark_peak, benchmark_value)

        row.model_state = position
        row.headline_status = f"Hold {position}"
        row.cash_value = cash
        row.qqq_value = qqq_shares * row.qqq_close
        row.qld_value = qld_shares * row.qld_close
        row.strategy_value = strategy_value
        row.qqq_benchmark_value = benchmark_value
        row.strategy_drawdown_pct = (strategy_value / strategy_peak - 1) * 100
        row.qqq_drawdown_pct = (benchmark_value / benchmark_peak - 1) * 100
        row.trade_reason = "; ".join(reason_parts)

        if action_parts:
            row.action = "; ".join(action_parts)
            row.rule_explanation = explain_trade(row.trade_reason)
        elif not channel_ready:
            row.action = "Waiting"
            row.rule_explanation = (
                "Waiting for 20 completed QLD trading days to establish the channel."
            )
        else:
            row.action = "No action"
            row.rule_explanation = explain_hold(position, signal, row)


def explain_trade(reason: str) -> str:
    if reason == "toQLD":
        return "QLD closed above its prior 20-day high; the signal changed to 1 and the account moved fully into QLD."
    if reason == "QLD->QQQ_on_Donchian_exit":
        return "QLD closed below its prior 20-day low; the signal changed to 0 and the account reduced to QQQ."
    if reason == "QQQ->Cash_below_EMA200":
        return "QQQ closed below EMA200 while held; the account moved fully to Cash."
    if reason == "QLD->QQQ_on_Donchian_exit; QQQ->Cash_below_EMA200":
        return "QLD exited its channel and QQQ was below EMA200, so the account passed through QQQ and finished in Cash."
    return reason


def explain_hold(position: str, signal: int, row: Row) -> str:
    if position == "QLD":
        return "Hold QLD while the Donchian20 signal remains 1."
    if position == "QQQ":
        return "Hold QQQ after the Donchian exit while QQQ remains at or above EMA200."
    if signal == 0 and row.ema200 is not None and row.qqq_close is not None:
        return "Hold Cash until QLD creates a new Donchian20 breakout; QQQ moving above EMA200 alone is not a re-entry."
    return "Hold Cash until QLD creates a new Donchian20 breakout."


def build_rows() -> list[Row]:
    qqq = fetch_yahoo("QQQ")
    qld = fetch_yahoo("QLD")
    dates = sorted(set(qqq) | set(qld))
    rows = [Row(date=day, qqq_close=qqq.get(day), qld_close=qld.get(day)) for day in dates]
    calculate_indicators(rows)
    simulate(rows)
    return rows


def csv_row(row: Row) -> dict[str, object]:
    return {
        "date": row.date,
        "qqq_close": round_value(row.qqq_close),
        "qld_close": round_value(row.qld_close),
        "qqq_ema200": round_value(row.ema200),
        "qqq_distance_to_ema200_pct": round_value(row.distance_to_ema200_pct),
        "qld_prior_20d_high": round_value(row.qld_prior_20d_high),
        "qld_prior_20d_low": round_value(row.qld_prior_20d_low),
        "qld_channel_position_pct": round_value(row.qld_channel_position_pct),
        "prior_donchian_signal": row.prior_signal,
        "donchian_signal": row.donchian_signal,
        "model_state": row.model_state,
        "headline_status": row.headline_status,
        "action": row.action,
        "trade_reason": row.trade_reason,
        "rule_explanation": row.rule_explanation,
        "cash_value": round_value(row.cash_value),
        "qqq_value": round_value(row.qqq_value),
        "qld_value": round_value(row.qld_value),
        "strategy_value": round_value(row.strategy_value),
        "qqq_benchmark_value": round_value(row.qqq_benchmark_value),
        "strategy_drawdown_pct": round_value(row.strategy_drawdown_pct),
        "qqq_drawdown_pct": round_value(row.qqq_drawdown_pct),
    }


def drawdown_summary(rows: list[Row], field: str) -> dict[str, object]:
    peak = float("-inf")
    peak_date = ""
    minimum = 0.0
    minimum_peak = ""
    trough_date = ""
    for row in rows:
        value = float(getattr(row, field))
        if value > peak:
            peak = value
            peak_date = row.date
        drawdown = value / peak - 1
        if drawdown < minimum:
            minimum = drawdown
            minimum_peak = peak_date
            trough_date = row.date
    return {
        "pct": round_value(minimum * 100),
        "peak_date": minimum_peak,
        "trough_date": trough_date,
    }


def write_outputs(rows: list[Row]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    complete = [row for row in rows if row.qqq_close is not None and row.qld_close is not None]
    latest = complete[-1]
    trades = [row for row in complete if row.trade_reason]
    recent = complete[-45:]
    strategy_dd = drawdown_summary(complete, "strategy_value")
    benchmark_dd = drawdown_summary(complete, "qqq_benchmark_value")
    lead_dollars = latest.strategy_value - latest.qqq_benchmark_value
    lead_pct = latest.strategy_value / latest.qqq_benchmark_value - 1

    csv_path = DATA_DIR / "signals.csv"
    fieldnames = list(csv_row(latest).keys())
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in complete:
            writer.writerow(csv_row(row))

    channel_status = "Channel forming"
    if latest.qld_prior_20d_high is not None and latest.qld_prior_20d_low is not None:
        if latest.qld_close > latest.qld_prior_20d_high:
            channel_status = "Above prior 20-day high"
        elif latest.qld_close < latest.qld_prior_20d_low:
            channel_status = "Below prior 20-day low"
        else:
            channel_status = "Inside prior 20-day channel"

    payload = {
        "project": "QQQ/QLD Signal Desk",
        "strategy_name": "Donchian20 QLD -> QQQ -> Cash exit strategy",
        "last_updated": latest.date,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": "Yahoo Finance chart API adjusted close",
        "current": {
            "model_state": latest.model_state,
            "headline_status": latest.headline_status,
            "donchian_signal": latest.donchian_signal,
            "required_action": latest.action,
            "rule_explanation": latest.rule_explanation,
            "last_trade_date": trades[-1].date if trades else None,
            "last_trade_action": trades[-1].action if trades else None,
            "last_trade_reason": trades[-1].trade_reason if trades else None,
        },
        "market": {
            "qqq_close": round_value(latest.qqq_close),
            "qld_close": round_value(latest.qld_close),
            "qqq_ema200": round_value(latest.ema200),
            "qqq_distance_to_ema200_pct": round_value(latest.distance_to_ema200_pct),
            "qld_prior_20d_high": round_value(latest.qld_prior_20d_high),
            "qld_prior_20d_low": round_value(latest.qld_prior_20d_low),
            "qld_channel_position_pct": round_value(latest.qld_channel_position_pct),
            "channel_status": channel_status,
        },
        "performance": {
            "tracking_start_date": complete[0].date,
            "initial_investment": INITIAL_INVESTMENT,
            "strategy_value": round_value(latest.strategy_value),
            "qqq_buy_hold_value": round_value(latest.qqq_benchmark_value),
            "lead_lag_dollars": round_value(lead_dollars),
            "lead_lag_pct": round_value(lead_pct * 100),
            "strategy_max_drawdown_pct": strategy_dd["pct"],
            "strategy_max_drawdown_peak_date": strategy_dd["peak_date"],
            "strategy_max_drawdown_trough_date": strategy_dd["trough_date"],
            "qqq_max_drawdown_pct": benchmark_dd["pct"],
            "qqq_max_drawdown_peak_date": benchmark_dd["peak_date"],
            "qqq_max_drawdown_trough_date": benchmark_dd["trough_date"],
            "current_strategy_drawdown_pct": round_value(latest.strategy_drawdown_pct),
            "current_qqq_drawdown_pct": round_value(latest.qqq_drawdown_pct),
        },
        "recent_transitions": [csv_row(row) for row in trades[-12:]],
        "recent_history": [csv_row(row) for row in recent],
    }
    (DATA_DIR / "signals.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    try:
        write_outputs(build_rows())
    except Exception as exc:
        print(f"update_signals failed: {exc}", file=sys.stderr)
        return 1
    print("Updated Donchian20 data/signals.json and data/signals.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
