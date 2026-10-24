"""
test_profit_chaser.py
=====================
Automated verification test suite for Smart Dynamic Profit Chasing,
Pullback and Recovery System (Option B).
"""

import os
import json
import unittest
from pathlib import Path
from smart_profit_chaser import (
    SmartProfitChaser,
    ProfitChaserConfig,
    ProfitMode,
    PullbackMethod,
    TrailingMethod,
    PositionState
)

class TestSmartProfitChaser(unittest.TestCase):
    def setUp(self):
        self.state_file = "test_profit_chaser_state.json"
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
            
        # Clean test configuration
        self.config = ProfitChaserConfig(
            enabled=True,
            profit_mode=ProfitMode.ACCOUNT_CURRENCY,
            activation_threshold=10.0,
            pullback_method=PullbackMethod.PERCENT_PEAK,
            pullback_value=20.0,  # 20% drop from peak
            adaptive_pullback=False,
            recovery_hysteresis_pct=2.0,
            trailing_enabled=True,
            trailing_method=TrailingMethod.PERCENT_GIVEBACK,
            max_giveback_pct=35.0,  # 35% max retracement
            min_guaranteed_profit=4.0,
            max_profit_target_enabled=False,
            use_milestones=True,
            milestones=[
                {"threshold": 50.0, "protection_pct": 50.0, "name": "50% Lock"},
                {"threshold": 80.0, "protection_pct": 70.0, "name": "70% Lock"}
            ]
        )
        self.chaser = SmartProfitChaser(config=self.config, state_file=self.state_file)
        # Mock close handler
        self.closed_tickets = []
        self.chaser.close_handler = lambda ticket, sym, reason: self.closed_tickets.append((ticket, reason)) or True

    def tearDown(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)

    def test_01_initialization_and_peak_tracking(self):
        """Rule 1 & 2: Initializes state and updates highest profit without resetting."""
        ticket = 1001
        pos = self.chaser.register_position(ticket, "BTC", "BUY", 0.01, 80000.0)
        self.assertEqual(pos.highest_profit, 0.0)
        self.assertEqual(pos.state, PositionState.TRACKING_NEW_HIGH)

        # Profit rises to $15
        res = self.chaser.update_position(ticket, 15.0, 80150.0)
        self.assertEqual(res["action"], "HOLD")
        self.assertEqual(pos.highest_profit, 15.0)
        self.assertTrue(pos.trailing_armed)

        # Profit rises to $25
        res = self.chaser.update_position(ticket, 25.0, 80250.0)
        self.assertEqual(pos.highest_profit, 25.0)
        
        # Profit drops to $22 -> Highest profit MUST NOT reset downward
        res = self.chaser.update_position(ticket, 22.0, 80220.0)
        self.assertEqual(pos.highest_profit, 25.0)

    def test_02_option_b_pullback_and_recovery_cycle(self):
        """
        CRITICAL TEST - Option B Recovery Logic:
        1. Profit hits $50 -> Peak = $50
        2. Profit drops to $38 -> Pullback mode activated (24% drop > 20% threshold)
        3. Profit recovers to $50 -> RECOVERY COMPLETED. TRADE KEPT OPEN!
        4. Profit breaks to $70 -> NEW PEAK RECORDED immediately!
        5. Profit drops to $55 -> Pullback mode activated again
        6. Profit recovers to $70 -> RECOVERY COMPLETED! TRADE KEPT OPEN!
        7. Profit hits $100 -> NEW PEAK RECORDED!
        """
        ticket = 2002
        pos = self.chaser.register_position(ticket, "VOL_20", "BUY", 0.01, 800000.0)

        # 1. Profit reaches $50
        self.chaser.update_position(ticket, 50.0, 800500.0)
        self.assertEqual(pos.highest_profit, 50.0)
        self.assertFalse(pos.pullback_active)

        # 2. Profit drops to $38 (pullback is $12 = 24%, threshold is 20% = $10)
        self.chaser.update_position(ticket, 38.0, 800380.0)
        self.assertTrue(pos.pullback_active)
        self.assertEqual(pos.state, PositionState.PULLBACK_DETECTED)
        self.assertEqual(len(self.closed_tickets), 0, "Trade must NOT be closed on pullback!")

        # 3. Profit returns to $50 -> Recovery completed!
        res = self.chaser.update_position(ticket, 50.0, 800500.0)
        self.assertEqual(res["action"], "HOLD", "Option B Rule: DO NOT CLOSE on recovery!")
        self.assertFalse(pos.pullback_active, "Pullback Mode must be deactivated upon recovery!")
        self.assertEqual(pos.recovery_count, 1)
        self.assertEqual(pos.state, PositionState.RECOVERY_COMPLETED)
        self.assertEqual(len(self.closed_tickets), 0, "Trade must remain active and open!")

        # 4. Profit surges to $70 -> New Peak recorded
        res = self.chaser.update_position(ticket, 70.0, 800700.0)
        self.assertEqual(res["action"], "HOLD")
        self.assertEqual(pos.highest_profit, 70.0)
        self.assertEqual(pos.state, PositionState.NEW_PEAK_RECORDED)

        # 5. Profit drops to $54 (pullback is $16 = 22.8%, threshold is 20% = $14)
        self.chaser.update_position(ticket, 54.0, 800540.0)
        self.assertTrue(pos.pullback_active)
        self.assertEqual(pos.state, PositionState.PULLBACK_DETECTED)
        self.assertEqual(len(self.closed_tickets), 0)

        # 6. Profit recovers back to $70
        res = self.chaser.update_position(ticket, 70.0, 800700.0)
        self.assertEqual(res["action"], "HOLD")
        self.assertFalse(pos.pullback_active)
        self.assertEqual(pos.recovery_count, 2)
        self.assertEqual(pos.state, PositionState.RECOVERY_COMPLETED)

        # 7. Profit advances to $100
        res = self.chaser.update_position(ticket, 100.0, 801000.0)
        self.assertEqual(pos.highest_profit, 100.0)
        self.assertEqual(pos.state, PositionState.NEW_PEAK_RECORDED)
        self.assertEqual(len(self.closed_tickets), 0)

    def test_03_trailing_profit_protection_exit(self):
        """Section 5: Protected floor ratchets up and triggers exit when breached."""
        ticket = 3003
        pos = self.chaser.register_position(ticket, "ETH", "BUY", 0.01, 2300.0)

        # Peak hits $100 -> Milestone 2 (70% lock) applies -> Floor = $70
        self.chaser.update_position(ticket, 100.0, 2400.0)
        self.assertEqual(pos.highest_profit, 100.0)
        self.assertTrue(pos.protected_floor >= 70.0)

        # Profit retraces to $80 -> Still above floor ($70) -> HOLD
        res = self.chaser.update_position(ticket, 80.0, 2380.0)
        self.assertEqual(res["action"], "HOLD")
        self.assertEqual(len(self.closed_tickets), 0)

        # Profit retraces to $68 -> Breaches floor ($70) -> MUST CLOSE!
        res = self.chaser.update_position(ticket, 68.0, 2368.0)
        self.assertEqual(res["action"], "CLOSE")
        self.assertEqual(pos.state, PositionState.PROFIT_PROTECTION_TRIGGERED)
        self.assertEqual(len(self.closed_tickets), 1)
        self.assertEqual(self.closed_tickets[0][0], ticket)

    def test_04_state_persistence_and_recovery(self):
        """Section 9: State survives restart without losing historical peaks."""
        ticket = 4004
        pos = self.chaser.register_position(ticket, "BOOM_100", "SELL", 0.01, 1400000.0)
        self.chaser.update_position(ticket, 65.0, 1399350.0)
        self.chaser.update_position(ticket, 45.0, 1399550.0)
        self.assertTrue(pos.pullback_active)
        self.assertEqual(pos.highest_profit, 65.0)

        # Simulate bot restart by creating a new chaser instance from same file
        reloaded_chaser = SmartProfitChaser(config=self.config, state_file=self.state_file)
        self.assertIn(ticket, reloaded_chaser.positions)
        restored_pos = reloaded_chaser.positions[ticket]
        self.assertEqual(restored_pos.highest_profit, 65.0)
        self.assertEqual(restored_pos.current_profit, 45.0)
        self.assertTrue(restored_pos.pullback_active)

if __name__ == "__main__":
    unittest.main()
