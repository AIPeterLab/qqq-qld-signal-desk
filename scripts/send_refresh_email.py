#!/usr/bin/env python3
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_PATH = ROOT / "data" / "signals.json"
DASHBOARD_URL = "https://aipeterlab.github.io/qqq-qld-signal-desk/"
RECIPIENT = "yzheng25@gmail.com"


def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main():
    username = required_env("EMAIL_USERNAME")
    app_password = required_env("EMAIL_APP_PASSWORD")
    smtp_host = os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.environ.get("EMAIL_SMTP_PORT", "465"))

    with SIGNALS_PATH.open(encoding="utf-8") as signal_file:
        signals = json.load(signal_file)

    current = signals["current"]
    market = signals["market"]
    bands = signals["bands"]
    macd = signals["macd_context"]
    update_date = signals["last_updated"]

    message = EmailMessage()
    message["From"] = username
    message["To"] = RECIPIENT
    message["Subject"] = (
        f"QQQ/QLD Signal Desk - {current['headline_status']} - {update_date}"
    )
    message.set_content(
        "\n".join(
            [
                "The QQQ/QLD Signal Desk daily refresh completed successfully.",
                "",
                f"Market date: {update_date}",
                f"Current status: {current['headline_status']}",
                f"Model state: {current['model_state']}",
                f"QQQ close: ${market['qqq_close']:.2f}",
                f"QLD close: ${market['qld_close']:.2f}",
                f"SMA200: {market['sma200']:.2f}",
                f"Distance to SMA200: {market['distance_to_sma200_pct']:+.2f}%",
                f"EMA50 / EMA200: {market['ema50']:.2f} / {market['ema200']:.2f}",
                f"Trend: {bands['trend_status']}",
                f"MACD: {macd['status']} (display-only)",
                "",
                current["rule_explanation"],
                "",
                f"Dashboard: {DASHBOARD_URL}",
            ]
        )
    )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as smtp:
        smtp.login(username, app_password)
        smtp.send_message(message)

    print(f"Refresh email sent to {RECIPIENT}.")


if __name__ == "__main__":
    main()
