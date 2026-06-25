#!/usr/bin/env python3
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_PATH = ROOT / "data" / "signals.json"
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"
DASHBOARD_URL = "https://aipeterlab.github.io/qqq-qld-signal-desk/"


def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main():
    app_token = required_env("PUSHOVER_APP_TOKEN")
    user_key = required_env("PUSHOVER_USER_KEY")

    with SIGNALS_PATH.open(encoding="utf-8") as signal_file:
        signals = json.load(signal_file)

    current = signals["current"]
    market = signals["market"]
    update_date = signals["last_updated"]

    body = urllib.parse.urlencode(
        {
            "token": app_token,
            "user": user_key,
            "title": f"Donchian20: {current['headline_status']}",
            "message": "\n".join(
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
            ),
            "url": DASHBOARD_URL,
            "url_title": "Open dashboard",
            "priority": "0",
        }
    ).encode("utf-8")

    request = urllib.request.Request(PUSHOVER_URL, data=body, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    if result.get("status") != 1:
        raise RuntimeError(f"Pushover rejected the notification: {result}")

    print(f"Pushover notification sent for market date {update_date}.")


if __name__ == "__main__":
    main()
