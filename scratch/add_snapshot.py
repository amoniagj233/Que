with open("continuous_tp_reopen_daemon.py", "r", encoding="utf-8") as f:
    text = f.read()

target = '''            # 4. Enforce live SL/TP policies across all active positions
            enforce_live_position_policies(positions, symbol)'''

replacement = '''            # Save live snapshot for AGENT SETTINGS Supreme Commander
            try:
                import json
                snapshot = {
                    "timestamp": time.time(),
                    "total_open": len(positions),
                    "account": {
                        "balance": acc.balance if acc else 0.0,
                        "equity": acc.equity if acc else 0.0,
                        "margin": acc.margin if acc else 0.0
                    },
                    "positions": [
                        {
                            "ticket": p.ticket,
                            "magic": p.magic,
                            "profit": p.profit,
                            "volume": p.volume,
                            "sl": p.sl,
                            "tp": p.tp,
                            "comment": p.comment
                        } for p in positions
                    ]
                }
                with open(os.path.join(BASE_DIR, "data_cache", "fleet_live_status.json"), "w", encoding="utf-8") as sf:
                    json.dump(snapshot, sf)
            except Exception:
                pass

            # 4. Enforce live SL/TP policies across all active positions
            enforce_live_position_policies(positions, symbol)'''

assert target in text, "target not found"
text = text.replace(target, replacement, 1)

with open("continuous_tp_reopen_daemon.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Added fleet_live_status.json snapshot to continuous_tp_reopen_daemon.py")
