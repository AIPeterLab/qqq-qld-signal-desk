import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from update_signals_volgate import Row, simulate, wilder_atr


def row(date, qqq, qld, ema200, high, low, atr_pct=None):
    return Row(
        date=date,
        qqq_close=qqq,
        qld_close=qld,
        ema200=ema200,
        distance_to_ema200_pct=(qqq / ema200 - 1) * 100,
        qld_prior_20d_high=high,
        qld_prior_20d_low=low,
        qld_atr20_pct=atr_pct,
    )


class VolatilityGateStrategyTests(unittest.TestCase):
    def test_gate_blocks_entry_above_four_percent(self):
        rows = [row("2026-01-02", 100, 50, 90, 49, 40, 4.01)]

        simulate(rows)

        self.assertEqual(rows[0].donchian_signal, 0)
        self.assertEqual(rows[0].model_state, "Cash")
        self.assertTrue(rows[0].volatility_gate_blocked)
        self.assertEqual(rows[0].action, "No action")

    def test_gate_allows_entry_below_or_at_four_percent(self):
        for atr_pct in (3.99, 4.0):
            with self.subTest(atr_pct=atr_pct):
                rows = [row("2026-01-02", 100, 50, 90, 49, 40, atr_pct)]

                simulate(rows)

                self.assertEqual(rows[0].donchian_signal, 1)
                self.assertEqual(rows[0].model_state, "QLD")
                self.assertFalse(rows[0].volatility_gate_blocked)

    def test_high_volatility_never_forces_an_exit(self):
        rows = [
            row("2026-01-02", 100, 50, 90, 49, 40, 3.0),
            row("2026-01-05", 101, 51, 90, 55, 40, 8.0),
        ]

        simulate(rows)

        self.assertEqual(rows[1].donchian_signal, 1)
        self.assertEqual(rows[1].model_state, "QLD")
        self.assertFalse(rows[1].volatility_gate_blocked)
        self.assertEqual(rows[1].action, "No action")

    def test_gate_is_inactive_before_twenty_atr_bars(self):
        rows = [
            Row(
                date=f"2026-01-{index + 1:02d}",
                qld_high=102.0,
                qld_low=98.0,
                qld_close=100.0,
            )
            for index in range(19)
        ]

        atr_values = wilder_atr(rows)

        self.assertEqual(atr_values, [None] * 19)

        twentieth = Row(
            date="2026-01-20",
            qld_high=102.0,
            qld_low=98.0,
            qld_close=100.0,
        )
        self.assertEqual(wilder_atr(rows + [twentieth])[-1], 4.0)

        breakout = row("2026-02-02", 100, 50, 90, 49, 40, None)
        simulate([breakout])
        self.assertEqual(breakout.donchian_signal, 1)
        self.assertEqual(breakout.model_state, "QLD")


if __name__ == "__main__":
    unittest.main()
