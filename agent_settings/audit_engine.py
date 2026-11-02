"""
AGENT SETTINGS — SUPREME SETTINGS COMMANDER
Audit & Policy Verification Engine
Evaluates live, demo, and backtest results against the Strict 80% Performance Policy:
- RULE A (>80%): Performance Candidate
- RULE B (=80%): Flagged for Improvement
- RULE C (<80%): Automatic Retirement Candidate (>= 200 trades for permanent deletion)
- RULE D (WR >80% but Profit <= 0): Classified UNPROFITABLE -> Immediate Suspension
- UNVERIFIED (<200 trades): Protective testing state
"""

import os
import sys
import logging
from typing import Dict, Any, List

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from agent_settings.database import SettingsDatabase

logger = logging.getLogger("AGENT_SETTINGS_AUDIT")

class AuditEngine:
    def __init__(self, db: SettingsDatabase):
        self.db = db

    def audit_ea(self, ea: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifies an EA according to the Strict 80% Performance Policy.
        """
        wr = ea.get("verified_win_rate", 0.0)
        trades = ea.get("total_trades", 0)
        profit = ea.get("net_profit", 0.0)
        pf = ea.get("profit_factor", 0.0)
        status = ea.get("status", "ACTIVE")

        verdict = {
            "ea_id": ea["ea_id"],
            "name": ea["name"],
            "magic": ea["magic"],
            "win_rate": wr,
            "total_trades": trades,
            "net_profit": profit,
            "profit_factor": pf,
            "policy_rule": "UNKNOWN",
            "action_required": "NONE",
            "eligible_for_live": False,
            "retirement_ready": False,
            "notes": ""
        }

        # Rule D: High win rate but unprofitable after costs
        if wr > 80.0 and profit <= 0:
            verdict["policy_rule"] = "RULE_D_UNPROFITABLE"
            verdict["action_required"] = "SUSPEND_AND_INVESTIGATE"
            verdict["eligible_for_live"] = False
            verdict["notes"] = f"Win rate is {wr:.2f}% but net profit is negative (${profit:.2f}). Unprofitable EA."
            return verdict

        # Insufficient trade evidence (< 200 trades)
        if trades < 200:
            verdict["policy_rule"] = "UNVERIFIED_EVIDENCE"
            verdict["action_required"] = "CONTINUE_TESTING"
            verdict["eligible_for_live"] = wr > 80.0
            verdict["notes"] = f"Trade count {trades} is below the 200-trade evidence threshold for permanent retirement."
            return verdict

        # Rule A: Win rate > 80%
        if wr > 80.0:
            if profit > 0 and pf >= 1.10:
                verdict["policy_rule"] = "RULE_A_HIGH_PERFORMANCE"
                verdict["action_required"] = "MAINTAIN_DEPLOYMENT"
                verdict["eligible_for_live"] = True
                verdict["notes"] = f"Verified win rate {wr:.2f}% > 80% with positive expectancy (${profit:.2f}, PF: {pf:.2f})."
            else:
                verdict["policy_rule"] = "RULE_A_MARGINAL_EXPECTANCY"
                verdict["action_required"] = "OPTIMIZE_EXIT_SETTINGS"
                verdict["eligible_for_live"] = True
                verdict["notes"] = f"Win rate {wr:.2f}% is strong, but profit factor {pf:.2f} needs improvement."
            return verdict

        # Rule B: Win rate exactly 80.0%
        if 79.99 <= wr <= 80.01:
            verdict["policy_rule"] = "RULE_B_AT_THRESHOLD"
            verdict["action_required"] = "FLAG_FOR_OPTIMIZATION"
            verdict["eligible_for_live"] = False
            verdict["notes"] = "Win rate exactly 80.0%. Does not exceed target. Flagged for parameter engineering."
            return verdict

        # Rule C: Win rate < 80%
        if wr < 80.0:
            verdict["policy_rule"] = "RULE_C_BELOW_TARGET"
            verdict["action_required"] = "OPTIMIZE_OR_ELIMINATE"
            verdict["eligible_for_live"] = False
            verdict["retirement_ready"] = True
            verdict["notes"] = f"Verified win rate {wr:.2f}% is below the mandatory 80% threshold ({trades} trades)."
            return verdict

        return verdict

    def run_full_fleet_audit(self) -> List[Dict[str, Any]]:
        eas = self.db.get_all_eas()
        audit_results = []
        for ea in eas:
            res = self.audit_ea(ea)
            audit_results.append(res)
            
            # Log significant findings
            if res["policy_rule"] in ["RULE_C_BELOW_TARGET", "RULE_D_UNPROFITABLE"]:
                self.db.log_activity(
                    level="ALERT",
                    event_type="POLICY_BREACH",
                    message=f"EA {ea['name']} (Magic {ea['magic']}) triggered {res['policy_rule']}: {res['notes']}",
                    details=res
                )
        return audit_results

if __name__ == "__main__":
    db = SettingsDatabase()
    engine = AuditEngine(db)
    results = engine.run_full_fleet_audit()
    print("=" * 80)
    print("AGENT SETTINGS: FLEET AUDIT REPORT (80% POLICY)")
    print("=" * 80)
    for r in results:
        status_flag = "PASS" if r["eligible_for_live"] else "FLAGGED"
        print(f"[{status_flag:<7}] {r['name']:<24} | WR: {r['win_rate']:>6.2f}% | Trades: {r['total_trades']:<5} | Rule: {r['policy_rule']:<26} | Action: {r['action_required']}")
