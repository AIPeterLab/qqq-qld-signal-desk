#!/usr/bin/env python3
"""Send the latest QQQ/QLD signal to the shared AIPeterLab ntfy topic."""

import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_PATH = ROOT / "data" / "signals.json"
NTFY_URL = "https://ntfy.sh/aipeterlab-market-alert-1"
DASHBOARD_URL = "https://aipeterlab.github.io/qqq-qld-signal-desk/"


def main() -> None:
    with SIGNALS_PATH.open(encoding="utf-8") as signal_file:
        signals = json.load(signal_file)

    current = signals["current"]
    market = signals["market"]
    update_date = signals["last_updated"]
    message = "\n".join(
        [
            f"Market date: {update_date}",
            f"Signal: {current['donchian_signal']}",
            f"Position: {current['model_state']}",
            f"Action: {current['required_action']}",
            f"QQQ: ${market['qqq_close']:.2f}",
            f"QLD: ${market['qld_close']:.2f}",
            f"QQQ vs EMA200: {market['qqq_distance_to_ema200_pct']:+.2f}%",
            current["rule_explanation"],
        ]
    ).encode("utf-8")

    request = urllib.request.Request(
        NTFY_URL,
        data=message,
        headers={
            "Title": f"Donchian20: {current['headline_status']}",
            "Priority": "high",
            "Click": DASHBOARD_URL,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    if result.get("event") != "message" or result.get("topic") != "aipeterlab-market-alert-1":
        raise RuntimeError(f"ntfy rejected the notification: {result}")

    print(f"ntfy notification sent for market date {update_date}.")


if __name__ == "__main__":
    main()
