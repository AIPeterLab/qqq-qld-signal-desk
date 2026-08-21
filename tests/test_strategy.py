import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from update_signals import (
    Row,
    ensure_not_older_market_date,
    simulate,
    validate_current_market_date,
)


def row(date, qqq, qld, ema200, high, low):
    return Row(
        date=date,
        qqq_close=qqq,
        qld_close=qld,
        ema200=ema200,
        distance_to_ema200_pct=(qqq / ema200 - 1) * 100,
        qld_prior_20d_high=high,
        qld_prior_20d_low=low,
    )


class DonchianExitStrategyTests(unittest.TestCase):
    def test_exact_transition_order_and_cash_reentry_rule(self):
        rows = [
            row("2026-01-02", 100, 50, 90, 49, 40),
            row("2026-01-05", 95, 39, 90, 55, 40),
            row("2026-01-06", 85, 38, 90, 55, 40),
            row("2026-01-07", 100, 45, 90, 55, 40),
            row("2026-01-08", 101, 56, 90, 55, 40),
        ]

        simulate(rows)

        self.assertEqual(rows[0].donchian_signal, 1)
        self.assertEqual(rows[0].model_state, "QLD")
        self.assertEqual(rows[0].trade_reason, "toQLD")

        self.assertEqual(rows[1].donchian_signal, 0)
        self.assertEqual(rows[1].model_state, "QQQ")
        self.assertEqual(rows[1].trade_reason, "QLD->QQQ_on_Donchian_exit")

        self.assertEqual(rows[2].model_state, "Cash")
        self.assertEqual(rows[2].trade_reason, "QQQ->Cash_below_EMA200")

        self.assertEqual(rows[3].model_state, "Cash")
        self.assertEqual(rows[3].action, "No action")

        self.assertEqual(rows[4].donchian_signal, 1)
        self.assertEqual(rows[4].model_state, "QLD")
        self.assertEqual(rows[4].trade_reason, "toQLD")

    def test_donchian_exit_can_pass_through_qqq_to_cash_same_close(self):
        rows = [
            row("2026-02-02", 100, 50, 90, 49, 40),
            row("2026-02-03", 85, 39, 90, 55, 40),
        ]

        simulate(rows)

        self.assertEqual(rows[1].model_state, "Cash")
        self.assertEqual(
            rows[1].trade_reason,
            "QLD->QQQ_on_Donchian_exit; QQQ->Cash_below_EMA200",
        )


class RefreshSafetyTests(unittest.TestCase):
    def test_requires_current_date_for_both_qqq_and_qld(self):
        with self.assertRaisesRegex(RuntimeError, "QLD"):
            validate_current_market_date(
                {"2026-08-21": 100.0},
                {"2026-08-20": 50.0},
                "2026-08-21",
            )

    def test_refuses_to_replace_newer_published_market_date(self):
        with self.assertRaisesRegex(RuntimeError, "older date"):
            ensure_not_older_market_date("2026-08-20", "2026-08-21")


if __name__ == "__main__":
    unittest.main()
