"""
AGENT SETTINGS — SUPREME SETTINGS COMMANDER
Standalone Autonomous Master Launcher
Runs the background autonomous optimization, audit, elimination, and portfolio risk management.
"""

import os
import sys

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from agent_settings.commander import SupremeSettingsCommander

def main():
    print("=" * 80)
    print("STARTING AGENT SETTINGS — SUPREME SETTINGS COMMANDER")
    print("Mandate: Strict > 80% Win Rate | Max 10 Open Positions | 1 Trade Per Bot")
    print("=" * 80)
    commander = SupremeSettingsCommander()
    commander.start()

if __name__ == "__main__":
    main()
